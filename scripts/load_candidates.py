"""Load candidate JSONL while making held-out access explicit."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]


def load_candidates(split: str, *, allow_heldout: bool = False) -> list[dict[str, Any]]:
    if split == "heldout" and not allow_heldout:
        raise PermissionError("held-out loading requires allow_heldout=True / --allow-heldout")
    directory = ROOT / "data/candidates" / split
    return [json.loads(line) for path in sorted(directory.glob("*.jsonl")) for line in path.read_text(encoding="utf-8").splitlines()]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("split", choices=("dev", "heldout"))
    parser.add_argument("--allow-heldout", action="store_true")
    args = parser.parse_args()
    records = load_candidates(args.split, allow_heldout=args.allow_heldout)
    print(f"loaded {len(records)} {args.split} candidates")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
