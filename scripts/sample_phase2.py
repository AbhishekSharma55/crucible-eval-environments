"""Build the deterministic repo/year-stratified Phase 2 evaluation case set."""

from __future__ import annotations

import argparse
from collections import defaultdict
import json
import math
from pathlib import Path
from typing import Any

from scripts.phase2_common import PHASE2, case_id, json_dump, load_dev_candidates, slug, stable_rank
from scripts.validate_rescue_candidates import MIN_MERGE_YEAR, rescue_static_eligible


SEED = 82631
TARGET = 100


def year_yield(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for item in rows:
        grouped[int(item["merged_at"][:4])].append(item)
    return [
        {
            "merge_year": year, "candidate_count": len(items),
            "accept_count": sum(item["status"] == "accepted" for item in items),
            "accept_rate": sum(item["status"] == "accepted" for item in items) / len(items),
        }
        for year, items in sorted(grouped.items())
    ]


def dynamic_year_yield(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return year_yield([item for item in rows if item.get("validation")])


def _allocations(strata: dict[tuple[str, int], list[dict[str, Any]]], target: int) -> dict[tuple[str, int], int]:
    if target < len(strata):
        raise RuntimeError("target is too small to represent every non-empty repo/year stratum")
    total = sum(map(len, strata.values()))
    exact = {key: target * len(items) / total for key, items in strata.items()}
    allocations = {key: min(len(strata[key]), max(1, math.floor(value))) for key, value in exact.items()}
    while sum(allocations.values()) > target:
        choices = [key for key, count in allocations.items() if count > 1]
        key = max(choices, key=lambda item: (allocations[item] - exact[item], stable_rank(SEED, str(item))))
        allocations[key] -= 1
    while sum(allocations.values()) < target:
        choices = [key for key, count in allocations.items() if count < len(strata[key])]
        if not choices:
            break
        key = max(choices, key=lambda item: (exact[item] - allocations[item], stable_rank(SEED, str(item))))
        allocations[key] += 1
    return allocations


def _slim(candidate: dict[str, Any], validation: dict[str, Any]) -> dict[str, Any]:
    keys = (
        "repo", "pr_number", "title", "body", "url", "merged_at", "parent_sha", "merge_commit_sha",
        "files_changed", "test_files", "source_files", "non_test_files", "patches",
    )
    return {
        **{key: candidate[key] for key in keys},
        "case_id": case_id(candidate),
        "merge_year": int(candidate["merged_at"][:4]),
        "validation": {
            "valid_transition": validation.get("rejection_reason") is None,
            "transition_kind": validation.get("transition_kind"),
            "transition_scope": validation.get("transition_scope"),
            "transition_tests": validation.get("transition_tests", []),
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target", type=int, default=TARGET)
    parser.add_argument("--seed", type=int, default=SEED)
    parser.add_argument("--output", type=Path, default=PHASE2 / "case-set.json")
    args = parser.parse_args()
    if args.seed != SEED:
        raise RuntimeError(f"the committed seed is {SEED}; change the source deliberately to revise it")
    if not 80 <= args.target <= 120:
        raise RuntimeError("Phase 2 target must remain between 80 and 120")
    rows = load_dev_candidates()
    eligible = [item for item in rows if rescue_static_eligible(item)]
    verified: list[tuple[dict[str, Any], dict[str, Any]]] = []
    missing: list[str] = []
    for item in eligible:
        path = PHASE2 / "validation" / slug(item["repo"]) / f"pr-{item['pr_number']}.json"
        if not path.exists():
            missing.append(case_id(item))
            continue
        validation = json.loads(path.read_text(encoding="utf-8"))
        if validation.get("rejection_reason") is None and validation.get("transition_tests"):
            verified.append((item, validation))
    if missing:
        raise RuntimeError(
            f"{len(missing)} eligible candidates lack dynamic validation; run make validate-rescue first"
        )
    if len(verified) < args.target:
        raise RuntimeError(f"only {len(verified)} verified rescuable candidates; target is {args.target}")
    strata: dict[tuple[str, int], list[dict[str, Any]]] = defaultdict(list)
    validations: dict[str, dict[str, Any]] = {}
    for item, validation in verified:
        strata[(item["repo"], int(item["merged_at"][:4]))].append(item)
        validations[case_id(item)] = validation
    allocations = _allocations(strata, args.target)
    selected: list[dict[str, Any]] = []
    composition = []
    for key in sorted(strata):
        ranked = sorted(strata[key], key=lambda item: stable_rank(args.seed, case_id(item)))
        chosen = ranked[:allocations[key]]
        selected.extend(_slim(item, validations[case_id(item)]) for item in chosen)
        composition.append({
            "repo": key[0], "merge_year": key[1], "verified_pool": len(ranked), "sample_count": len(chosen)
        })
    selected.sort(key=lambda item: (item["repo"], item["merge_year"], item["pr_number"]))
    payload = {
        "schema_version": 1, "seed": args.seed, "target": args.target,
        "selection": "proportional allocation across repo x merge-year strata, minimum one per non-empty stratum; SHA-256 seeded rank within strata",
        "included_merge_years": list(range(MIN_MERGE_YEAR, 2027)),
        "excluded_merge_years": list(range(2014, MIN_MERGE_YEAR)),
        "exclusion_reason": "Pre-2019 has only four dynamically eligible issue-backed candidates across 2016-2018 and zero accepts except one in 2018; modern pinned dependencies make those sparse historical yields uninterpretable.",
        "verified_rescuable_pool_count": len(verified),
        "year_yield": year_yield(rows),
        "dynamically_eligible_issue_linked_year_yield": dynamic_year_yield(rows),
        "composition": composition, "cases": selected,
    }
    json_dump(args.output, payload)
    print(f"wrote {len(selected)} cases from {len(verified)} verified candidates to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
