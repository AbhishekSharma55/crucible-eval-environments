from __future__ import annotations

import json
from pathlib import Path
import subprocess

import pytest

from scripts.leakage_detector import detect_leakage
from scripts.model_fixture import FixtureMiss, chat_completion
from sandbox.entrypoint import apply_solution_patch


ROOT = Path(__file__).resolve().parents[1]


PATCH = """diff --git a/pkg.py b/pkg.py
index 1111111..2222222 100644
--- a/pkg.py
+++ b/pkg.py
@@ -1,0 +2,2 @@
+def novel_helper(value):
+    return existing_function(value)
"""


def _candidate():
    return {
        "repo": "example/repo",
        "pr_number": 7,
        "parent_sha": "a" * 40,
        "merge_commit_sha": "b" * 40,
        "non_test_files": ["pkg.py"],
    }


def _fake_git(repo, *args, check=True):
    if args[0] == "show":
        return subprocess.CompletedProcess(args, 0, "x = 1\ndef novel_helper(value):\n    return existing_function(value)\n", "")
    if args[0] == "grep":
        name = args[args.index("-e") + 1]
        return subprocess.CompletedProcess(args, 0 if name in {"existing_function", "value"} else 1, "", "")
    if args[0] == "cat-file":
        return subprocess.CompletedProcess(args, 1, "", "")
    raise AssertionError(args)


def test_preexisting_identifier_is_legitimate(monkeypatch):
    monkeypatch.setattr("scripts.leakage_detector.git", _fake_git)
    verdict = detect_leakage(
        _candidate(),
        "Calling existing_function with an invalid value raises an unexpected error.",
        patch=PATCH,
    )
    assert verdict["verdict"] == "leak_free"
    assert verdict["evidence"] == []


def test_new_gold_identifier_is_leakage_with_evidence(monkeypatch):
    monkeypatch.setattr("scripts.leakage_detector.git", _fake_git)
    verdict = detect_leakage(_candidate(), "Add novel_helper to handle the value.", patch=PATCH)
    assert verdict["verdict"] == "leaked"
    assert {item["rule"] for item in verdict["evidence"]} == {
        "new_gold_identifier", "fix_instruction_with_new_identifier"
    }


def test_hard_leakage_rules_do_not_depend_on_identifier_novelty(monkeypatch):
    monkeypatch.setattr("scripts.leakage_detector.git", _fake_git)
    verdict = detect_leakage(
        _candidate(),
        "pkg.py:42\n@@ -1,0 +2,2 @@\nreturn existing_function ( value ) + 1 + 2",
        patch=PATCH,
    )
    rules = {item["rule"] for item in verdict["evidence"]}
    assert "file_path_with_line_number" in rules
    assert "literal_patch_syntax" in rules


def test_fixture_replay_hard_fails_without_network(tmp_path, monkeypatch):
    monkeypatch.setattr("scripts.model_fixture.FIXTURE_DIR", tmp_path)
    with pytest.raises(FixtureMiss, match="replay never reaches the network"):
        chat_completion({"model": "deepseek/deepseek-v4-flash", "messages": []})


def test_committed_case_set_is_dev_only_and_verified():
    payload = json.loads((ROOT / "data/phase2/case-set.json").read_text(encoding="utf-8"))
    assert payload["seed"] == 82631
    assert 80 <= len(payload["cases"]) <= 120
    assert {item["repo"] for item in payload["cases"]}.isdisjoint({"psf/black", "PyCQA/flake8"})
    assert all(item["validation"]["valid_transition"] for item in payload["cases"])
    assert all(item["merge_year"] >= 2019 for item in payload["cases"])


def test_solver_patch_accepts_relative_paths_and_recounts_hunks(tmp_path):
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    target = tmp_path / "pkg.py"
    target.write_text("VALUE = 0\n", encoding="utf-8")
    patch = b"--- pkg.py\n+++ pkg.py\n@@ -1,9 +1,9 @@\n-VALUE = 0\n+VALUE = 1\n"
    result = apply_solution_patch(tmp_path, patch)
    assert result.returncode == 0, result.stderr.decode()
    assert target.read_text(encoding="utf-8") == "VALUE = 1\n"
