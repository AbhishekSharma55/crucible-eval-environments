"""Shared held-out Phase 5 paths and sealed-corpus loading."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from scripts.load_candidates import load_candidates
from scripts.phase2_common import ROOT
from scripts.phase3_common import MIN_MERGE_YEAR


PHASE5 = ROOT / "data/phase5"
PHASE5_RESULTS = ROOT / "results/phase5"
HELDOUT_VALIDATION = PHASE5 / "heldout-candidate-validation"
HELDOUT_CASE_SET = PHASE5 / "heldout-case-set.json"


def heldout_candidate_pool() -> list[dict[str, Any]]:
    """Apply the exact Phase 3 no-test bucket, cutoff, and source normalization."""
    rows = load_candidates("heldout", allow_heldout=True)
    selected = [
        item for item in rows
        if item.get("rejection_reason") == "no_test_files_touched"
        and int(item["merged_at"][:4]) >= MIN_MERGE_YEAR
    ]
    result = []
    for source in selected:
        item = dict(source)
        example_sources = [
            path for path in item.get("non_test_files", [])
            if path.startswith("examples/") and path.endswith(".py")
        ]
        item["phase1_source_files"] = list(item.get("source_files", []))
        item["source_files"] = sorted(set(item.get("source_files", [])) | set(example_sources))
        result.append(item)
    return result
