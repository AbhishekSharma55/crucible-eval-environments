"""Verify the split boundary without parsing held-out candidate records."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def repo_from_filename(path: Path) -> str:
    return path.stem.replace("--", "/")


def main() -> int:
    root = ROOT / "data/candidates"
    dev_files = sorted((root / "dev").glob("*.jsonl"))
    heldout_files = sorted((root / "heldout").glob("*.jsonl"))
    if not dev_files or not heldout_files:
        raise SystemExit("both dev and held-out must be populated")
    dev = {repo_from_filename(path) for path in dev_files}
    heldout = {repo_from_filename(path) for path in heldout_files}
    overlap = dev & heldout
    if overlap:
        raise SystemExit(f"repo leakage across split: {sorted(overlap)}")
    assignment = json.loads((ROOT / "config/split.json").read_text(encoding="utf-8"))["assignment"]
    if dev != {repo for repo, split in assignment.items() if split == "dev"}:
        raise SystemExit("dev filenames do not match committed split assignment")
    if heldout != {repo for repo, split in assignment.items() if split == "heldout"}:
        raise SystemExit("held-out filenames do not match committed split assignment")
    print(f"split verified: dev_repos={len(dev)} heldout_repos={len(heldout)} overlap=0")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
