"""Build the deterministic repo/year-stratified Phase 3 case set."""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import json
import math
from pathlib import Path
from typing import Any

from scripts.phase3_common import (
    PHASE3, SAMPLE_SEED, SAMPLE_TARGET, case_id, json_dump, phase3_candidate_pool, stable_rank,
)


def allocations(strata: dict[tuple[str, int], list[dict[str, Any]]], target: int) -> dict[tuple[str, int], int]:
    if target < len(strata):
        raise RuntimeError("target cannot represent every repo/year stratum")
    total = sum(len(items) for items in strata.values())
    exact = {key: target * len(items) / total for key, items in strata.items()}
    result = {key: min(len(strata[key]), max(1, math.floor(value))) for key, value in exact.items()}
    while sum(result.values()) > target:
        choices = [key for key, value in result.items() if value > 1]
        result[max(choices, key=lambda key: (result[key] - exact[key], stable_rank(SAMPLE_SEED, str(key))))] -= 1
    while sum(result.values()) < target:
        choices = [key for key, value in result.items() if value < len(strata[key])]
        if not choices:
            break
        result[max(choices, key=lambda key: (exact[key] - result[key], stable_rank(SAMPLE_SEED, str(key))))] += 1
    return result


def slim(candidate: dict[str, Any], validation: dict[str, Any]) -> dict[str, Any]:
    keys = (
        "repo", "pr_number", "title", "body", "url", "merged_at", "parent_sha", "merge_commit_sha",
        "linked_issues", "issue_body_text", "files_changed", "test_files", "source_files", "non_test_files", "patches",
    )
    return {
        **{key: candidate[key] for key in keys}, "case_id": case_id(candidate),
        "merge_year": int(candidate["merged_at"][:4]), "phase3_prevalidation": validation,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=int, default=SAMPLE_SEED)
    parser.add_argument("--target", type=int, default=SAMPLE_TARGET)
    parser.add_argument("--output", type=Path, default=PHASE3 / "case-set.json")
    args = parser.parse_args()
    if args.seed != SAMPLE_SEED:
        raise RuntimeError(f"committed seed is {SAMPLE_SEED}; source change required")
    if not 80 <= args.target <= 100:
        raise RuntimeError("Phase 3 target must remain in the requested 80-100 range")
    candidates = phase3_candidate_pool()
    verified = []
    missing = []
    filter_counts = Counter()
    for candidate in candidates:
        filter_counts["post_cutoff_no_test_pool"] += 1
        path = PHASE3 / "candidate-validation" / candidate["repo"].replace("/", "--") / f"pr-{candidate['pr_number']}.json"
        if not path.exists():
            missing.append(case_id(candidate))
            continue
        validation = json.loads(path.read_text(encoding="utf-8"))
        static = validation.get("static") or {}
        checks = static.get("checks") or {}
        running = bool(checks.get("linked_issue_present"))
        if running: filter_counts["after_linked_issue_present"] += 1
        running &= bool(checks.get("linked_issue_text_usable"))
        if running: filter_counts["after_linked_issue_text_usable"] += 1
        running &= bool(checks.get("source_file_present"))
        if running: filter_counts["after_source_file_present"] += 1
        running &= static.get("behavior_change", {}).get("status") == "pass"
        if running: filter_counts["after_behavior_change"] += 1
        running &= bool(checks.get("coverable_fix_line_present"))
        if running: filter_counts["after_coverable_fix_line_present"] += 1
        attempts = validation.get("control_selection_attempts") or []
        parent_built = any(
            item.get("parent_stage") == "test"
            or (item.get("parent_stage") == "build" and item.get("parent_exit_code") == 0)
            for item in attempts
        )
        if running and parent_built:
            filter_counts["after_parent_build"] += 1
        if running and validation.get("rejection_reason") is None:
            filter_counts["after_endpoint_existing_tests"] += 1
            verified.append((candidate, validation))
    if missing:
        raise RuntimeError(f"{len(missing)} candidates lack validation; run the validator first")
    if len(verified) < args.target:
        raise RuntimeError(f"only {len(verified)} verified cases; requested target is {args.target}")
    strata: dict[tuple[str, int], list[dict[str, Any]]] = defaultdict(list)
    validations = {}
    for candidate, validation in verified:
        strata[(candidate["repo"], int(candidate["merged_at"][:4]))].append(candidate)
        validations[case_id(candidate)] = validation
    counts = allocations(strata, args.target)
    selected = []
    composition = []
    for key in sorted(strata):
        ranked = sorted(strata[key], key=lambda item: stable_rank(args.seed, case_id(item)))
        chosen = ranked[:counts[key]]
        selected.extend(slim(item, validations[case_id(item)]) for item in chosen)
        composition.append({"repo": key[0], "merge_year": key[1], "verified_pool": len(ranked), "sample_count": len(chosen)})
    selected.sort(key=lambda item: (item["repo"], item["merge_year"], item["pr_number"]))
    json_dump(args.output, {
        "schema_version": 1, "seed": args.seed, "target": args.target,
        "selection": "proportional repo x merge-year allocation with minimum one and SHA-256 seeded rank",
        "filter_counts": dict(filter_counts), "verified_pool_count": len(verified),
        "composition": composition, "cases": selected,
    })
    print(f"wrote {len(selected)} cases from {len(verified)} verified candidates")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
