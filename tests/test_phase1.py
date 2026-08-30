from __future__ import annotations

import json
from pathlib import Path
import subprocess

import pytest

from sandbox.entrypoint import apply_patch, build_patch
from sandbox.pytest_status import outcome_for_phases
from scripts.harvest import PR_TOO_LARGE_THRESHOLD, complete_changed_paths, static_reason
from scripts.load_candidates import load_candidates
from scripts.validate_candidates import validate


ROOT = Path(__file__).resolve().parents[1]


def candidate(**overrides):
    value = {
        "linked_issues": [{"number": 1}],
        "test_files": ["tests/test_bug.py"],
        "source_files": ["src/pkg.py"],
        "files_truncated": False,
        "changed_file_count": 2,
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
        ({"changed_file_count": PR_TOO_LARGE_THRESHOLD + 1}, "pr_too_large"),
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
    assert summary["total_candidates"] >= 3000
    assert (
        summary["accepted_candidates"]
        + summary["rejected_candidates"]
        + summary["heldout_deferred_candidates"]
        + summary["validation_pending_candidates"]
        == summary["total_candidates"]
    )
    assert sum(summary["rejection_reason_histogram"].values()) == summary["rejected_candidates"]
    assert summary["validation_pending_candidates"] == 0
    assert summary["other_cases"] == []
    assert "other" not in summary["rejection_reason_histogram"]


@pytest.mark.parametrize(
    ("phases", "outcome"),
    [
        ({"call": "failed"}, "failed"),
        ({"setup": "failed"}, "error"),
        ({"collect": "failed"}, "error"),
        ({"call": "passed", "teardown": "failed"}, "error"),
    ],
)
def test_failure_and_error_outcomes_remain_distinct(phases, outcome):
    assert outcome_for_phases(phases) == outcome


def test_changed_paths_continue_past_first_api_page(tmp_path):
    pr = {"number": 7, "files": {"totalCount": 2, "nodes": [{"path": "src/pkg.py"}]}}
    supplemental = {
        "data": {
            "repository": {
                "pullRequest": {"files": {"nodes": [{"path": "tests/test_pkg.py"}]}}
            }
        }
    }
    (tmp_path / "pr-7-files-002.json").write_text(json.dumps(supplemental), encoding="utf-8")
    complete_changed_paths(tmp_path, "example/repo", pr)
    assert [node["path"] for node in pr["files"]["nodes"]] == ["src/pkg.py", "tests/test_pkg.py"]


def test_new_test_file_patch_applies_and_transition_is_detected(tmp_path, monkeypatch):
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=repo, check=True)
    (repo / "module.py").write_text("VALUE = 0\n", encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-qm", "parent"], cwd=repo, check=True)
    parent = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=repo, text=True).strip()
    (repo / "module.py").write_text("VALUE = 1\n", encoding="utf-8")
    (repo / "tests").mkdir()
    (repo / "tests/test_new.py").write_text(
        "from module import VALUE\n\ndef test_value():\n    assert VALUE == 1\n",
        encoding="utf-8",
    )
    subprocess.run(["git", "add", "."], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-qm", "fix with regression test"], cwd=repo, check=True)
    fix = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=repo, text=True).strip()
    subprocess.run(["git", "checkout", "-q", "--detach", parent], cwd=repo, check=True)

    patch_result = build_patch(repo, parent, fix, ["tests/test_new.py"])
    assert patch_result.returncode == 0
    assert apply_patch(repo, patch_result.stdout).returncode == 0
    assert (repo / "tests/test_new.py").is_file()
    assert (repo / "module.py").read_text(encoding="utf-8") == "VALUE = 0\n"

    calls = []

    def fake_run_tests(repo_name, commit, selector, *, image, test_patch_from=None):
        calls.append((commit, tuple(selector), test_patch_from))
        parent_run = commit == parent
        statuses = (
            [{"nodeid": "tests/test_new.py::test_value", "outcome": "failed"}]
            if parent_run
            else [{"nodeid": "tests/test_new.py::test_value", "outcome": "passed"}]
        )
        return {
            "exit_code": 1 if parent_run else 0,
            "stage": "test",
            "duration_s": 0.01,
            "per_test_status": statuses,
            "stdout": "",
            "stderr": "",
        }

    monkeypatch.setattr("scripts.validate_candidates.run_tests", fake_run_tests)
    result = validate(
        {
            "repo": "example/repo",
            "pr_number": 1,
            "parent_sha": parent,
            "merge_commit_sha": fix,
            "test_files": ["tests/test_new.py"],
        },
        "test-image",
    )
    assert result["rejection_reason"] is None
    assert result["transition_tests"] == [
        {"nodeid": "tests/test_new.py::test_value", "parent": "failed", "fix": "passed"}
    ]
    assert [call[2] for call in calls] == [fix, fix, None, None]
