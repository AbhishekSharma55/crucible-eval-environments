"""Validate the once-opened held-out pool with the unchanged Phase 3 filters."""

from __future__ import annotations

import argparse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
import json

from scripts.phase3_common import CASE_WALL_CAP_S, TEST_TIMEOUT_S, case_id, json_dump
from scripts.phase5_common import HELDOUT_VALIDATION, PHASE5, heldout_candidate_pool
from scripts.validate_phase3_candidates import validate


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--image", default="crucible-sandbox:phase3")
    parser.add_argument("--workers", type=int, default=6)
    parser.add_argument("--timeout", type=int, default=TEST_TIMEOUT_S)
    parser.add_argument("--case-cap", type=int, default=CASE_WALL_CAP_S)
    args = parser.parse_args()
    candidates = sorted(heldout_candidate_pool(), key=case_id)
    existing = list(HELDOUT_VALIDATION.glob("*/pr-*.json"))
    if existing:
        raise RuntimeError("held-out validation outputs already exist; refusing a second pass")
    print(f"validating {len(candidates)} held-out candidates exactly once", flush=True)
    failures = 0
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = {pool.submit(validate, item, args.image, args.timeout, args.case_cap): item for item in candidates}
        for future in as_completed(futures):
            candidate = futures[future]
            output = HELDOUT_VALIDATION / candidate["repo"].replace("/", "--") / f"pr-{candidate['pr_number']}.json"
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
    records = [json.loads(path.read_text(encoding="utf-8")) for path in sorted(HELDOUT_VALIDATION.glob("*/pr-*.json"))]
    histogram = Counter(item.get("rejection_reason") or "verified" for item in records)
    json_dump(PHASE5 / "heldout-candidate-validation-summary.json", {
        "schema_version": 1,
        "raw_post_cutoff_pool": len(candidates),
        "validated_records": len(records),
        "outcomes": dict(sorted(histogram.items())),
        "validator_exceptions": failures,
    })
    return int(failures > 0)


if __name__ == "__main__":
    raise SystemExit(main())
