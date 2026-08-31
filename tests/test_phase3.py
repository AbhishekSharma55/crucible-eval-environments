from __future__ import annotations

import json
from pathlib import Path

from scripts.leakage_detector import AddedIdentifier
from scripts.phase3_common import runtime_ast
from scripts.test_authoring_verifier import gate1, gate2, gate3, gate4, gate5


ROOT = Path(__file__).resolve().parents[1]


def run(exit_code: int, *, outcome: str, stage: str = "test", stdout: str = ""):
    return {
        "exit_code": exit_code, "stage": stage, "outcomes": {"tests/test_regression.py::test_bug": outcome},
        "stdout_tail": stdout, "stderr_tail": "", "coverage": {},
    }


def candidate():
    return {
        "repo": "example/repo", "pr_number": 1, "parent_sha": "a" * 40,
        "merge_commit_sha": "b" * 40, "source_files": ["pkg.py"],
    }


def test_g1_requires_repeatable_parent_failure():
    failed = run(1, outcome="failed")
    assert gate1([failed, failed])["status"] == "pass"
    assert gate1([failed, run(0, outcome="passed")])["reason"] == "nondeterministic_parent"


def test_g2_requires_repeatable_fix_pass():
    passed = run(0, outcome="passed")
    assert gate2([passed, passed])["status"] == "pass"
    assert gate2([passed, run(1, outcome="failed")])["reason"] == "nondeterministic_fix"


def test_g3_allows_legitimate_parent_error(monkeypatch):
    introduced = [AddedIdentifier("new_helper", "function", "pkg.py")]
    monkeypatch.setattr("scripts.test_authoring_verifier.extract_added_identifiers", lambda *args: introduced)
    monkeypatch.setattr("scripts.test_authoring_verifier.genuinely_new_identifiers", lambda *args: introduced)
    parent = run(1, outcome="error", stdout="E   ValueError: malformed public input")
    verdict = gate3(candidate(), parent, patch="diff --git a/pkg.py b/pkg.py")
    assert verdict["status"] == "pass"
    assert verdict["evidence"]["matches"] == []


def test_g3_rejects_error_caused_by_gold_symbol(monkeypatch):
    introduced = [AddedIdentifier("new_helper", "function", "pkg.py")]
    monkeypatch.setattr("scripts.test_authoring_verifier.extract_added_identifiers", lambda *args: introduced)
    monkeypatch.setattr("scripts.test_authoring_verifier.genuinely_new_identifiers", lambda *args: introduced)
    parent = run(1, outcome="error", stdout="E   AttributeError: module 'pkg' has no attribute 'new_helper'")
    verdict = gate3(candidate(), parent, patch="diff --git a/pkg.py b/pkg.py")
    assert verdict["status"] == "fail"
    assert verdict["evidence"]["matches"][0]["introduced_symbol"] == "new_helper"


def test_g4_requires_execution_of_a_changed_line():
    item = candidate()
    item["phase3_prevalidation"] = {"static": {"changed_fix_lines": {"pkg.py": [4, 7]}}}
    covered = run(0, outcome="passed")
    covered["coverage"] = {"pkg.py": [1, 7, 9]}
    verdict = gate4(item, covered)
    assert verdict["status"] == "pass"
    assert verdict["evidence"]["covered_changed_lines"] == {"pkg.py": [7]}
    assert verdict["evidence"]["changed_line_fraction"] == 0.5
    covered["coverage"] = {"pkg.py": [1, 9]}
    assert gate4(item, covered)["status"] == "fail"


def test_g5_requires_test_only_boundary_and_clean_repeated_controls():
    passed = run(0, outcome="passed")
    item = candidate()
    item["phase3_prevalidation"] = {
        "rejection_reason": None, "existing_test_selectors": ["tests/test_existing.py::test_smoke"],
        "endpoint_runs": {"parent": [passed, passed], "fix": [passed, passed]},
    }
    boundary = {"status": "pass", "path": "tests/test_regression.py"}
    assert gate5(item, boundary)["status"] == "pass"
    assert gate5(item, {**boundary, "status": "fail"})["status"] == "fail"


def test_runtime_ast_ignores_docs_and_annotations_but_not_behavior():
    before = 'def f(value: int) -> int:\n    """old"""\n    return value + 1\n'
    cosmetic = 'def f(value: str) -> str:\n    """new"""\n    return value + 1\n'
    behavior = 'def f(value: str) -> str:\n    """new"""\n    return value + 2\n'
    assert runtime_ast(before) == runtime_ast(cosmetic)
    assert runtime_ast(before) != runtime_ast(behavior)


def test_committed_phase3_case_set_is_dev_only_and_verified():
    payload = json.loads((ROOT / "data/phase3/case-set.json").read_text(encoding="utf-8"))
    assert payload["seed"] == 63811
    assert 80 <= len(payload["cases"]) <= 100
    assert {item["repo"] for item in payload["cases"]}.isdisjoint({"psf/black", "PyCQA/flake8"})
    assert all(item["phase3_prevalidation"]["rejection_reason"] is None for item in payload["cases"])
