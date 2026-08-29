from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.harvest import static_reason
from scripts.load_candidates import load_candidates


ROOT = Path(__file__).resolve().parents[1]


def candidate(**overrides):
    value = {
        "linked_issues": [{"number": 1}],
        "test_files": ["tests/test_bug.py"],
        "source_files": ["src/pkg.py"],
        "files_truncated": False,
        "parent_sha": "a" * 40,
    }
    value.update(overrides)
    return value


@pytest.mark.parametrize(
    ("overrides", "reason"),
    [
        ({"linked_issues": []}, "no_linked_issue"),
        ({"test_files": []}, "no_test_files_touched"),
        ({"source_files": []}, "no_source_files_touched"),
        ({"files_truncated": True}, "other"),
        ({"parent_sha": None}, "other"),
        ({}, None),
    ],
)
def test_static_reason_codes(overrides, reason):
    assert static_reason(candidate(**overrides))[0] == reason


def test_heldout_loader_requires_explicit_flag():
    with pytest.raises(PermissionError):
        load_candidates("heldout")


def test_config_has_only_passing_final_corpus():
    config = json.loads((ROOT / "config/repos.json").read_text(encoding="utf-8"))
    accepted = [repo for repo in config["repos"] if repo["status"] == "accepted"]
    assert 6 <= len(accepted) <= 10
    assert all(repo["python_version"] and repo["old_commit"] for repo in accepted)


def test_every_active_revision_has_a_lock():
    config = json.loads((ROOT / "config/repos.json").read_text(encoding="utf-8"))
    for repo in config["repos"]:
        if repo["status"] != "accepted":
            continue
        slug = repo["repo"].replace("/", "--")
        for revision in ("head", "old"):
            assert (ROOT / "config/locks" / f"{slug}--{revision}.txt").is_file()


def test_summary_is_internally_consistent():
    summary = json.loads((ROOT / "data/candidates/summary.json").read_text(encoding="utf-8"))
    assert summary["total_candidates"] >= 300
    assert summary["accepted_candidates"] + summary["rejected_candidates"] == summary["total_candidates"]
    assert sum(summary["rejection_reason_histogram"].values()) == summary["rejected_candidates"]
