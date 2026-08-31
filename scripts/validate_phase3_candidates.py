"""Verify Phase 3 case quality and cache G5 endpoint controls."""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from collections import Counter
import json
from pathlib import Path
import re
import time
from typing import Any

from scripts.phase3_common import (
    CASE_WALL_CAP_S, PHASE3, TEST_TIMEOUT_S, behavior_change_evidence, case_id,
    changed_fix_lines, compact_run, existing_test_selectors, fingerprint, json_dump,
    phase3_candidate_pool, run_phase3_test,
)


def static_evidence(candidate: dict[str, Any]) -> dict[str, Any]:
    issue_text = candidate.get("issue_body_text", "").strip()
    issue_usable = len(issue_text) >= 40 and len(re.findall(r"[A-Za-z]", issue_text)) >= 20
    changed_lines = changed_fix_lines(candidate) if candidate.get("source_files") else {}
    checks = {
        "rejection_bucket": candidate.get("rejection_reason") == "no_test_files_touched",
        "post_2019_cutoff": int(candidate["merged_at"][:4]) >= 2019,
        "linked_issue_present": bool(candidate.get("linked_issues")),
        "linked_issue_text_usable": issue_usable,
        "source_file_present": bool(candidate.get("source_files")),
        "no_gold_test_files": not candidate.get("test_files"),
        "parent_present": bool(candidate.get("parent_sha")),
        "coverable_fix_line_present": any(changed_lines.values()),
    }
    behavior = behavior_change_evidence(candidate) if candidate.get("source_files") else {
        "status": "fail", "reason": "no_source_files", "files": []
    }
    passed = all(checks.values()) and behavior["status"] == "pass"
    return {
        "status": "pass" if passed else "fail", "checks": checks,
        "issue_character_count": len(issue_text), "behavior_change": behavior,
        "changed_fix_lines": changed_lines,
    }


def validate(candidate: dict[str, Any], image: str, timeout_s: int, case_cap_s: int) -> dict[str, Any]:
    started = time.monotonic()
    static = static_evidence(candidate)
    record: dict[str, Any] = {
        "schema_version": 1, "case_id": case_id(candidate), "repo": candidate["repo"],
        "pr_number": candidate["pr_number"], "static": static, "existing_test_selectors": [],
        "control_selection_attempts": [],
        "endpoint_runs": {"parent": [], "fix": []}, "rejection_reason": None, "wall_s": 0,
    }
    if static["status"] != "pass":
        failed = [name for name, passed in static["checks"].items() if not passed]
        record["rejection_reason"] = failed[0] if failed else static["behavior_change"]["reason"]
        record["wall_s"] = round(time.monotonic() - started, 3)
        return record
    candidates = existing_test_selectors(candidate)
    if not candidates:
        record["rejection_reason"] = "no_existing_tests_selectable"
        record["wall_s"] = round(time.monotonic() - started, 3)
        return record
    for selector in candidates:
        first_runs = {}
        for endpoint in ("parent", "fix"):
            elapsed = time.monotonic() - started
            if elapsed >= case_cap_s:
                record["rejection_reason"] = "validation_wall_clock_exceeded"
                record["wall_s"] = round(elapsed, 3)
                return record
            run_timeout = max(1, min(timeout_s, int(case_cap_s - elapsed)))
            first_runs[endpoint] = compact_run(run_phase3_test(
                candidate, None, endpoint, selectors=[selector], image=image, timeout_s=run_timeout
            ))
        first_pass = all(run["stage"] == "test" and run["exit_code"] == 0 for run in first_runs.values())
        record["control_selection_attempts"].append({
            "selector": selector, "passed_once_at_both_endpoints": first_pass,
            "parent_stage": first_runs["parent"]["stage"], "parent_exit_code": first_runs["parent"]["exit_code"],
            "fix_stage": first_runs["fix"]["stage"], "fix_exit_code": first_runs["fix"]["exit_code"],
        })
        if first_pass:
            record["existing_test_selectors"] = [selector]
            record["endpoint_runs"] = {"parent": [first_runs["parent"]], "fix": [first_runs["fix"]]}
            break
    if not record["existing_test_selectors"]:
        record["rejection_reason"] = "no_existing_test_passes_both_endpoints"
        record["wall_s"] = round(time.monotonic() - started, 3)
        return record
    for endpoint in ("parent", "fix"):
        elapsed = time.monotonic() - started
        if elapsed >= case_cap_s:
            record["rejection_reason"] = "validation_wall_clock_exceeded"
            record["wall_s"] = round(elapsed, 3)
            return record
        run_timeout = max(1, min(timeout_s, int(case_cap_s - elapsed)))
        record["endpoint_runs"][endpoint].append(compact_run(run_phase3_test(
            candidate, None, endpoint, selectors=record["existing_test_selectors"], image=image, timeout_s=run_timeout
        )))
    for endpoint in ("parent", "fix"):
        runs = record["endpoint_runs"][endpoint]
        if fingerprint(runs[0]) != fingerprint(runs[1]):
            record["rejection_reason"] = f"nondeterministic_{endpoint}_existing_tests"
            break
        if any(run["stage"] != "test" or run["exit_code"] != 0 for run in runs):
            record["rejection_reason"] = f"existing_tests_fail_at_{endpoint}"
            break
    record["wall_s"] = round(time.monotonic() - started, 3)
    return record


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--image", default="crucible-sandbox:phase1")
    parser.add_argument("--workers", type=int, default=6)
    parser.add_argument("--timeout", type=int, default=TEST_TIMEOUT_S)
    parser.add_argument("--case-cap", type=int, default=CASE_WALL_CAP_S)
    parser.add_argument("--limit", type=int)
    parser.add_argument("--case", action="append", help="limit to owner/repo#PR (repeatable)")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    candidates = sorted(phase3_candidate_pool(), key=case_id)
    requested = set(args.case or [])
    if requested:
        candidates = [item for item in candidates if case_id(item) in requested]
    if args.limit is not None:
        candidates = candidates[:args.limit]
    jobs = []
    for candidate in candidates:
        output = PHASE3 / "candidate-validation" / candidate["repo"].replace("/", "--") / f"pr-{candidate['pr_number']}.json"
        if args.force or not output.exists():
            jobs.append((candidate, output))
    print(f"validating {len(jobs)} Phase 3 candidates", flush=True)
    failures = 0
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = {pool.submit(validate, candidate, args.image, args.timeout, args.case_cap): (candidate, output) for candidate, output in jobs}
        for future in as_completed(futures):
            candidate, output = futures[future]
            try:
                result = future.result()
            except Exception as exc:
                failures += 1
                result = {
                    "schema_version": 1, "case_id": case_id(candidate), "repo": candidate["repo"],
                    "pr_number": candidate["pr_number"], "rejection_reason": "validator_exception",
                    "exception": f"{type(exc).__name__}: {exc}",
                }
            json_dump(output, result)
            print(f"{case_id(candidate)}: {result.get('rejection_reason') or 'verified'}", flush=True)
    records = []
    for candidate in sorted(phase3_candidate_pool(), key=case_id):
        path = PHASE3 / "candidate-validation" / candidate["repo"].replace("/", "--") / f"pr-{candidate['pr_number']}.json"
        if path.exists():
            records.append(json.loads(path.read_text(encoding="utf-8")))
    histogram = Counter(item.get("rejection_reason") or "verified" for item in records)
    json_dump(PHASE3 / "candidate-validation-summary.json", {
        "schema_version": 1, "raw_post_cutoff_pool": len(phase3_candidate_pool()),
        "validated_records": len(records), "outcomes": dict(sorted(histogram.items())),
    })
    return int(failures > 0)


if __name__ == "__main__":
    raise SystemExit(main())
