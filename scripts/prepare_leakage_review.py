"""Freeze 50 naturally sampled baseline statements for blinded human review."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from scripts.phase2_common import PHASE2, gold_patch, json_dump, load_case_set, stable_rank


SEED = 55317
N = 50


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=PHASE2 / "leakage-review-set.json")
    args = parser.parse_args()
    case_set = load_case_set()
    cases = {item["case_id"]: item for item in case_set["cases"]}
    pool = []
    for baseline in ("b0", "b1", "b2"):
        path = Path("results") / f"{baseline}.json"
        if not path.exists():
            raise RuntimeError(f"missing {path}; all three full baseline outputs are required")
        payload = json.loads(path.read_text(encoding="utf-8"))
        if payload.get("n") != len(cases):
            raise RuntimeError(f"{path} is not a full-case-set result")
        for item in payload["results"]:
            pool.append({
                "review_id": f"{baseline}:{item['case_id']}", "baseline": baseline.upper(),
                "case_id": item["case_id"], "problem_statement": item["problem_statement"],
                "detector": item["leakage"], "gold_patch": gold_patch(cases[item["case_id"]], unified=3),
            })
    # This samples the natural 300-output union uniformly. It does not inspect
    # or balance detector verdicts, so the observed leak rate is preserved.
    selected = sorted(pool, key=lambda item: stable_rank(SEED, item["review_id"]))[:N]
    json_dump(args.output, {
        "schema_version": 1, "seed": SEED, "n": N,
        "sampling": "uniform seeded sample from the union of full B0/B1/B2 outputs; detector verdict not used for selection",
        "items": selected,
    })
    counts = {name: sum(item["baseline"] == name for item in selected) for name in ("B0", "B1", "B2")}
    print(f"wrote {N} blinded-review items: {counts}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
