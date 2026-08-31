"""Annotate cached Phase 1b validations and narrow collection fan-out."""

from __future__ import annotations

import argparse
import json

from scripts.phase2_common import ROOT, case_id, json_dump, load_dev_candidates
from scripts.validate_candidates import transition_tests


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="fail instead of rewriting stale records")
    args = parser.parse_args()
    candidates = {case_id(item): item for item in load_dev_candidates()}
    stale = 0
    for path in sorted((ROOT / "data/validation").glob("*/*.json")):
        record = json.loads(path.read_text(encoding="utf-8"))
        candidate = candidates.get(f"{record['repo']}#{record['pr_number']}")
        runs = record.get("runs", {})
        parent = (runs.get("parent") or [None])[0]
        fix = (runs.get("fix") or [None])[0]
        transitions, kind, scope = ([], None, None)
        if parent and fix and record.get("rejection_reason") is None:
            transitions, kind, scope = transition_tests(parent, fix, candidate)
        updated = dict(record)
        updated.update({
            "schema_version": 3,
            "transition_tests": transitions,
            "transition_kind": kind,
            "transition_scope": scope,
        })
        if updated != record:
            stale += 1
            if not args.check:
                json_dump(path, updated)
    print(f"{stale} stale validation records")
    return int(args.check and stale > 0)


if __name__ == "__main__":
    raise SystemExit(main())
