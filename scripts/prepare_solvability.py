"""Freeze matched rescued/control samples for the bounded solver evaluation."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from scripts.phase2_common import PHASE2, case_id, json_dump, load_dev_candidates, stable_rank


SEED = 99173
N_PER_GROUP = 30


def metadata(candidate: dict[str, Any], statement: str, group: str, validation: dict[str, Any]) -> dict[str, Any]:
    return {
        "case_id": case_id(candidate), "group": group, "repo": candidate["repo"],
        "pr_number": candidate["pr_number"], "merged_at": candidate["merged_at"],
        "problem_statement": statement, "parent_sha": candidate["parent_sha"],
        # The runner needs the fix SHA solely to transplant hidden tests. It is
        # never placed in the model prompt, and no gold source diff is read.
        "hidden_test_patch_sha": candidate["merge_commit_sha"],
        "test_files": candidate["test_files"], "source_files": candidate["source_files"],
        "transition_tests": validation["transition_tests"],
        "transition_kind": validation.get("transition_kind"),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--n", type=int, default=N_PER_GROUP)
    parser.add_argument("--output", type=Path, default=PHASE2 / "solvability-set.json")
    args = parser.parse_args()
    b2_path = Path("results/b2.json")
    if not b2_path.exists():
        raise RuntimeError("results/b2.json is required before solvability sampling")
    b2 = json.loads(b2_path.read_text(encoding="utf-8"))
    case_set = json.loads((PHASE2 / "case-set.json").read_text(encoding="utf-8"))
    rescue_cases = {item["case_id"]: item for item in case_set["cases"]}
    rescued_pool = [item for item in b2["results"] if item["leakage"]["verdict"] == "leak_free"]
    rescued_pool.sort(key=lambda item: stable_rank(SEED, f"rescued:{item['case_id']}"))

    accepted_pool = [
        item for item in load_dev_candidates()
        if item["status"] == "accepted" and item.get("issue_body_text", "").strip()
    ]
    accepted_pool.sort(key=lambda item: stable_rank(SEED, f"control:{case_id(item)}"))
    actual_n = min(args.n, len(rescued_pool), len(accepted_pool))
    if actual_n < args.n:
        print(f"requested {args.n} per group but only {actual_n} matched cases are feasible")
    cases = []
    for result in rescued_pool[:actual_n]:
        candidate = rescue_cases[result["case_id"]]
        cases.append(metadata(candidate, result["problem_statement"], "rescued", candidate["validation"]))
    for candidate in accepted_pool[:actual_n]:
        statement = candidate["issue_body_text"].strip()
        cases.append(metadata(candidate, statement, "control", candidate["validation"]))
    cases.sort(key=lambda item: (item["group"], item["case_id"]))
    json_dump(args.output, {
        "schema_version": 1, "seed": SEED, "requested_n_per_group": args.n,
        "actual_n_per_group": actual_n, "single_attempt": True, "cases": cases,
    })
    print(f"wrote {actual_n} rescued + {actual_n} control solver cases")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
