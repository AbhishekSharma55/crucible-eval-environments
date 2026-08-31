"""Minimal interactive CLI for human leakage ground-truth labels."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path

from scripts.phase2_common import PHASE2, json_dump


CHOICES = {"f": "leak_free", "l": "leaked", "u": "unsure"}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--queue", type=Path, default=PHASE2 / "leakage-review-set.json")
    parser.add_argument("--labels", type=Path, default=PHASE2 / "human-leakage-labels.json")
    parser.add_argument("--labeler", required=True, help="real human's name or stable identity")
    args = parser.parse_args()
    queue = json.loads(args.queue.read_text(encoding="utf-8"))
    if args.labels.exists():
        labels = json.loads(args.labels.read_text(encoding="utf-8"))
        if labels["labeler"] != args.labeler:
            raise RuntimeError(f"label file belongs to {labels['labeler']!r}, not {args.labeler!r}")
    else:
        labels = {
            "schema_version": 1, "labeler": args.labeler,
            "started_at": datetime.now(timezone.utc).isoformat(), "completed_at": None, "labels": [],
        }
    done = {item["review_id"] for item in labels["labels"]}
    remaining = [item for item in queue["items"] if item["review_id"] not in done]
    for index, item in enumerate(remaining, start=len(done) + 1):
        print("\n" + "=" * 80)
        print(f"Item {index}/{len(queue['items'])}  {item['review_id']}")
        print("\nPROBLEM STATEMENT\n")
        print(item["problem_statement"])
        print("\nGOLD PATCH\n")
        print(item["gold_patch"])
        while True:
            choice = input("Verdict [f=leak_free, l=leaked, u=unsure, q=save/quit]: ").strip().lower()
            if choice == "q":
                json_dump(args.labels, labels)
                print(f"saved {len(labels['labels'])} labels")
                return 0
            if choice in CHOICES:
                break
        note = input("Note (optional): ").strip()
        labels["labels"].append({
            "review_id": item["review_id"], "verdict": CHOICES[choice], "note": note,
            "labeled_at": datetime.now(timezone.utc).isoformat(),
        })
        json_dump(args.labels, labels)
    labels["completed_at"] = datetime.now(timezone.utc).isoformat()
    json_dump(args.labels, labels)
    print(f"complete: saved {len(labels['labels'])} labels")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
