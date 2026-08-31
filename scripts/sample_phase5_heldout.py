"""Build the deterministic held-out case set with the Phase 3 funnel and sampler."""

from __future__ import annotations

from collections import Counter, defaultdict
import json

from scripts.phase3_common import SAMPLE_SEED, SAMPLE_TARGET, case_id, json_dump
from scripts.phase5_common import HELDOUT_CASE_SET, HELDOUT_VALIDATION, heldout_candidate_pool
from scripts.sample_phase3 import allocations, slim


def main() -> int:
    candidates = heldout_candidate_pool()
    verified = []
    missing = []
    filter_counts = Counter()
    for candidate in candidates:
        filter_counts["post_cutoff_no_test_pool"] += 1
        path = HELDOUT_VALIDATION / candidate["repo"].replace("/", "--") / f"pr-{candidate['pr_number']}.json"
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
        raise RuntimeError(f"{len(missing)} held-out candidates lack validation")
    target = min(SAMPLE_TARGET, len(verified))
    if not target:
        raise RuntimeError("no held-out candidates survived validation")
    strata = defaultdict(list)
    validations = {}
    for candidate, validation in verified:
        strata[(candidate["repo"], int(candidate["merged_at"][:4]))].append(candidate)
        validations[case_id(candidate)] = validation
    counts = allocations(strata, target)
    selected = []
    composition = []
    from scripts.phase3_common import stable_rank
    for key in sorted(strata):
        ranked = sorted(strata[key], key=lambda item: stable_rank(SAMPLE_SEED, case_id(item)))
        chosen = ranked[:counts[key]]
        selected.extend(slim(item, validations[case_id(item)]) for item in chosen)
        composition.append({"repo": key[0], "merge_year": key[1], "verified_pool": len(ranked), "sample_count": len(chosen)})
    selected.sort(key=lambda item: (item["repo"], item["merge_year"], item["pr_number"]))
    json_dump(HELDOUT_CASE_SET, {
        "schema_version": 1,
        "split_seed": 41729,
        "seed": SAMPLE_SEED,
        "target": target,
        "dev_target": SAMPLE_TARGET,
        "selection": "proportional repo x merge-year allocation with minimum one and SHA-256 seeded rank",
        "filter_counts": dict(filter_counts),
        "verified_pool_count": len(verified),
        "composition": composition,
        "cases": selected,
    })
    print(f"wrote {len(selected)} held-out cases from {len(verified)} verified candidates")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
