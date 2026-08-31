"""Dynamically verify missing-issue candidates without touching held-out repos."""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import json
from pathlib import Path

from scripts.phase2_common import PHASE2, json_dump, load_dev_candidates, slug
from scripts.validate_candidates import validate


MIN_MERGE_YEAR = 2019


def rescue_static_eligible(candidate: dict) -> bool:
    return (
        candidate.get("rejection_reason") == "no_linked_issue"
        and bool(candidate.get("test_files"))
        and bool(candidate.get("source_files"))
        and bool(candidate.get("parent_sha"))
        and candidate.get("changed_file_count", 10**9) <= 300
        and int(candidate["merged_at"][:4]) >= MIN_MERGE_YEAR
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--image", default="crucible-sandbox:phase1")
    parser.add_argument("--workers", type=int, default=3)
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--limit", type=int)
    args = parser.parse_args()
    output_dir = PHASE2 / "validation"
    jobs = []
    for candidate in load_dev_candidates():
        if not rescue_static_eligible(candidate):
            continue
        output = output_dir / slug(candidate["repo"]) / f"pr-{candidate['pr_number']}.json"
        if args.force or not output.exists():
            jobs.append((candidate, output))
    jobs.sort(key=lambda pair: (pair[0]["repo"], pair[0]["pr_number"]))
    if args.limit is not None:
        jobs = jobs[: args.limit]
    print(f"validating {len(jobs)} missing-issue candidates (merge year >= {MIN_MERGE_YEAR})", flush=True)
    failures = 0
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = {pool.submit(validate, candidate, args.image): (candidate, output) for candidate, output in jobs}
        for future in as_completed(futures):
            candidate, output = futures[future]
            try:
                result = future.result()
            except Exception as exc:  # retain an auditable record instead of losing the batch
                failures += 1
                result = {
                    "schema_version": 3, "repo": candidate["repo"],
                    "pr_number": candidate["pr_number"], "rejection_reason": "validator_exception",
                    "note": f"{type(exc).__name__}: {exc}", "transition_tests": [],
                    "transition_kind": None, "transition_scope": None,
                }
            json_dump(output, result)
            status = result.get("rejection_reason") or "accepted"
            print(f"{candidate['repo']}#{candidate['pr_number']}: {status}", flush=True)
    return int(failures > 0)


if __name__ == "__main__":
    raise SystemExit(main())
