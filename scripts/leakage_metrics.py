"""Compare deterministic detector verdicts with completed human labels."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from scripts.phase2_common import PHASE2, json_dump


def ratio(numerator: int, denominator: int) -> float | None:
    return numerator / denominator if denominator else None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--queue", type=Path, default=PHASE2 / "leakage-review-set.json")
    parser.add_argument("--labels", type=Path, default=PHASE2 / "human-leakage-labels.json")
    parser.add_argument("--output", type=Path, default=Path("results/leakage-detector-validation.json"))
    args = parser.parse_args()
    queue = json.loads(args.queue.read_text(encoding="utf-8"))
    labels = json.loads(args.labels.read_text(encoding="utf-8"))
    items = {item["review_id"]: item for item in queue["items"]}
    usable = [item for item in labels["labels"] if item["verdict"] != "unsure"]
    tp = tn = fp = fn = 0
    disagreements = []
    for label in usable:
        reviewed = items[label["review_id"]]
        predicted = reviewed["detector"]["verdict"]
        actual = label["verdict"]
        if actual == "leaked" and predicted == "leaked": tp += 1
        elif actual == "leak_free" and predicted == "leak_free": tn += 1
        elif actual == "leak_free" and predicted == "leaked": fp += 1
        else: fn += 1
        if predicted != actual:
            disagreements.append({
                "review_id": label["review_id"], "human_verdict": actual,
                "detector_verdict": predicted, "human_note": label["note"],
                "problem_statement": reviewed["problem_statement"],
                "detector_evidence": reviewed["detector"]["evidence"],
            })
    n = len(usable)
    observed = ratio(tp + tn, n)
    actual_positive = tp + fn
    actual_negative = tn + fp
    predicted_positive = tp + fp
    predicted_negative = tn + fn
    expected = (
        (actual_positive * predicted_positive + actual_negative * predicted_negative) / (n * n)
        if n else None
    )
    kappa = ((observed - expected) / (1 - expected)) if expected is not None and expected != 1 else None
    payload = {
        "schema_version": 1, "labeler": labels["labeler"], "labeled_count": len(labels["labels"]),
        "unsure_count": len(labels["labels"]) - n, "confusion_matrix": {"tp": tp, "tn": tn, "fp": fp, "fn": fn},
        "tpr": ratio(tp, tp + fn), "tnr": ratio(tn, tn + fp), "cohens_kappa": kappa,
        "fitness": "fit" if ratio(tp, tp + fn) is not None and ratio(tn, tn + fp) is not None and ratio(tp, tp + fn) >= .9 and ratio(tn, tn + fp) >= .9 else "revise_or_incomplete",
        "disagreements": disagreements,
    }
    json_dump(args.output, payload)
    print(json.dumps({key: payload[key] for key in ("confusion_matrix", "tpr", "tnr", "cohens_kappa", "fitness")}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
