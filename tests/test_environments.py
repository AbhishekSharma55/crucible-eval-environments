from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.export_environments import (
    GATES, build_metadata, environment_id, export, index_entry, new_file_diff,
    parse_new_file_diff, problem_statement, sha256, transition_kind,
)
from scripts.review_environments import (
    latest_verdicts, promote, promotion_decision, read_approvals,
)


def authored_test():
    return {"path": "tests/test_regression.py", "content": "def test_bug():\n    assert compute() == 2\n"}


def candidate():
    return {
        "case_id": "example/repo#7",
        "repo": "example/repo",
        "pr_number": 7,
        "url": "https://github.com/example/repo/pull/7",
        "title": "Fix off-by-one in compute",
        "merged_at": "2021-03-04T10:00:00Z",
        "parent_sha": "a" * 40,
        "merge_commit_sha": "b" * 40,
        "source_files": ["src/pkg/compute.py"],
        "linked_issues": [{"number": "6", "url": "https://github.com/example/repo/issues/6", "body": "compute() returns 1, expected 2.\r\n\r\nSee the trailing detail."}],
    }


def run(endpoint: str, outcome: str, exit_code: int, nodeid: str = "tests/test_regression.py::test_bug"):
    return {
        "endpoint": endpoint, "commit": "a" * 40 if endpoint == "parent" else "b" * 40,
        "exit_code": exit_code, "stage": "test", "duration_s": 0.5,
        "outcomes": {nodeid: outcome}, "stdout_tail": "", "stderr_tail": "", "coverage": {},
    }


def verification():
    parent = [run("parent", "failed", 1), run("parent", "failed", 1)]
    fix = [run("fix", "passed", 0), run("fix", "passed", 0)]
    return {
        "passed": True,
        "gates": {
            "g1": {"status": "pass", "reason": None, "evidence": {"deterministic": True, "runs": parent}},
            "g2": {"status": "pass", "reason": None, "evidence": {"deterministic": True, "runs": fix}},
            "g3": {"status": "pass", "reason": None, "evidence": {"parent_exceptions": [], "introduced_symbols": [], "matches": []}},
            "g4": {
                "status": "pass", "reason": None,
                "evidence": {
                    "changed_lines": {"src/pkg/compute.py": [10, 11]},
                    "covered_changed_lines": {"src/pkg/compute.py": [10]},
                    "changed_line_count": 2, "covered_changed_line_count": 1,
                    "changed_line_fraction": 0.5,
                    "coverage_run": {**run("fix", "passed", 0), "coverage": {"src/pkg/compute.py": [10]}},
                },
            },
            "g5": {
                "status": "pass", "reason": None,
                "evidence": {
                    "authored_patch_boundary": {"status": "pass", "reason": None, "path": "tests/test_regression.py"},
                    "selected_existing_tests": ["tests/test_existing.py::test_ok"],
                    "endpoints": {
                        "parent": {"deterministic": True, "passed": True, "runs": []},
                        "fix": {"deterministic": True, "passed": True, "runs": []},
                    },
                },
            },
        },
    }


def result():
    return {
        "case_id": "example/repo#7", "repo": "example/repo", "pr_number": 7, "passed": True,
        "authored_test": authored_test(), "verification": verification(),
        "accepted_gate_call": 1, "gate_calls": 1, "model_turns": 9, "tool_steps": 12,
        "stop_reason": "passed_all_gates", "rollout_seed": 1234, "gaming_flags": [],
    }


def rollout():
    return {
        "model": "deepseek/deepseek-v4-flash", "temperature": 0.2, "arm": "single_threaded_agent",
        "rollout": 0, "instruction_sha256": {"agents/phase4-system.md": "c" * 64},
        "limits": {"max_check_gates_calls": 5},
    }


def source():
    return {
        "split": "dev", "rollout": "results/phase5/task1/agent-rollout-0.json",
        "case_set": "data/phase3/case-set.json", "designated_by": "results/phase4/summary-run2.json",
    }


# --- export ---------------------------------------------------------------


def test_environment_id_is_owner_repo_pr():
    assert environment_id("pallets/click", 1737) == "pallets__click__1737"
    assert environment_id("marshmallow-code/marshmallow", "1631") == "marshmallow-code__marshmallow__1631"


def test_new_file_diff_round_trips_including_missing_trailing_newline():
    for content in ("def test():\n    assert True\n", "def test():\n    assert True"):
        diff = new_file_diff("tests/test_x.py", content)
        assert diff.startswith("diff --git a/tests/test_x.py b/tests/test_x.py\nnew file mode 100644\n--- /dev/null\n")
        assert "@@ -0,0 +1,2 @@" in diff
        assert parse_new_file_diff(diff) == {"path": "tests/test_x.py", "content": content}
    assert "\\ No newline at end of file" in new_file_diff("tests/test_x.py", "x = 1")


def test_problem_statement_carries_issue_text_verbatim_and_separates_the_reference():
    text = problem_statement(candidate())
    body = candidate()["linked_issues"][0]["body"]
    assert body in text
    assert text.index("## Problem statement") < text.index(body) < text.index("## Reference")
    # the fixing commit must not appear above the reference heading
    assert "b" * 40 not in text[: text.index("## Reference")]
    assert "https://github.com/example/repo/pull/7" in text


def test_transition_kind_is_classified_with_the_committed_classifier():
    assert transition_kind(verification()) == "assertion_failure"
    collected = verification()
    for parent_run in collected["gates"]["g1"]["evidence"]["runs"]:
        parent_run["outcomes"] = {"collection::tests/test_regression.py": "error"}
    assert transition_kind(collected) == "collection_error"


def test_metadata_carries_every_required_field():
    metadata = build_metadata(result(), candidate(), rollout(), source())
    assert metadata["repo"] == "example/repo"
    assert metadata["parent_sha"] == "a" * 40
    assert metadata["fix_sha"] == "b" * 40
    assert metadata["pr_number"] == 7
    assert metadata["merged_at"] == "2021-03-04T10:00:00Z"
    assert metadata["split"] == "dev"
    assert metadata["transition_kind"] == "assertion_failure"
    assert metadata["coverage"]["changed_line_fraction"] == 0.5
    assert metadata["authored_by"]["model"] == "deepseek/deepseek-v4-flash"
    assert set(metadata["gates"]) == set(GATES)
    for name in GATES:
        assert metadata["gates"][name]["status"] == "pass"
        assert metadata["gates"][name]["evidence"]
    assert metadata["human_review"]["status"] == "pending"
    assert "necessary" in metadata["gates_are_necessary_not_sufficient"]


def test_export_writes_every_gate_passing_case_and_no_approvals(tmp_path):
    index = export(root=tmp_path)
    counts = index["counts"]
    assert counts["total"] == counts["dev"] + counts["heldout"]
    assert counts["dev"] == 26 and counts["heldout"] == 5
    assert len(index["environments"]) == counts["total"]
    for entry in index["environments"]:
        directory = tmp_path / entry["path"]
        for name in ("problem_statement.md", "test_patch.diff", "metadata.json", "verify.sh"):
            assert (directory / name).is_file(), f"{entry['environment_id']} missing {name}"
        assert (directory / "verify.sh").stat().st_mode & 0o111
        metadata = json.loads((directory / "metadata.json").read_text(encoding="utf-8"))
        assert all(metadata["gate_status"][name] == "pass" for name in GATES)
        assert metadata["test_patch_sha256"] == sha256((directory / "test_patch.diff").read_text(encoding="utf-8"))
        assert parse_new_file_diff((directory / "test_patch.diff").read_text(encoding="utf-8"))["path"] == metadata["test_path"]
    assert (tmp_path / "approvals.jsonl").read_text(encoding="utf-8") == ""
    assert read_approvals(tmp_path / "approvals.jsonl") == []
    assert index["human_review"]["approved_count"] == 0


def test_export_is_deterministic(tmp_path):
    first = export(root=tmp_path / "a")
    second = export(root=tmp_path / "b")
    assert first == second
    assert (tmp_path / "a/index.json").read_bytes() == (tmp_path / "b/index.json").read_bytes()


def test_committed_candidate_export_has_no_approval_records():
    approvals = Path("environments/approvals.jsonl")
    assert approvals.is_file()
    assert read_approvals(approvals) == [], "approval records must be typed by a human, never generated"


# --- promotion refusal ----------------------------------------------------


def exported(tmp_path) -> tuple[Path, Path, Path]:
    root = tmp_path / "environments"
    export(root=root)
    return root / "candidate", root / "approvals.jsonl", root / "approved"


def approval(directory: Path, verdict: str, **overrides):
    record = {
        "schema_version": 1, "environment_id": directory.name, "case_id": "x/y#1", "split": "dev",
        "verdict": verdict, "note": "", "reviewer": "A Human",
        "reviewed_at": "2026-08-31T00:00:00Z",
        "test_patch_sha256": sha256((directory / "test_patch.diff").read_text(encoding="utf-8")),
    }
    record.update(overrides)
    return record


def test_promotion_refuses_unreviewed_rejected_and_unsure(tmp_path):
    candidates, _, _ = exported(tmp_path)
    directory = sorted(candidates.iterdir())[0]
    allowed, why = promotion_decision(directory, None)
    assert not allowed and "no human review record" in why
    for verdict in ("reject", "unsure"):
        allowed, why = promotion_decision(directory, approval(directory, verdict))
        assert not allowed and "not 'accept'" in why
    allowed, why = promotion_decision(directory, approval(directory, "accept", reviewer=""))
    assert not allowed and "names no reviewer" in why


def test_promotion_refuses_an_accept_whose_artifact_changed(tmp_path):
    candidates, _, _ = exported(tmp_path)
    directory = sorted(candidates.iterdir())[0]
    record = approval(directory, "accept", test_patch_sha256="0" * 64)
    allowed, why = promotion_decision(directory, record)
    assert not allowed and "changed since it was accepted" in why


def test_promotion_accepts_only_an_explicit_accept(tmp_path):
    candidates, _, _ = exported(tmp_path)
    directory = sorted(candidates.iterdir())[0]
    allowed, why = promotion_decision(directory, approval(directory, "accept"))
    assert allowed and "accepted by A Human" in why


def test_promote_with_an_empty_approvals_file_promotes_nothing_and_exits_nonzero(tmp_path, capsys):
    candidates, approvals, destination = exported(tmp_path)
    assert approvals.read_text(encoding="utf-8") == ""
    assert promote(root=candidates, approvals=approvals, destination=destination) == 2
    assert not list(destination.glob("*/metadata.json"))
    assert "no environment carries an explicit human 'accept'" in capsys.readouterr().out


def test_promote_copies_only_accepted_environments(tmp_path):
    candidates, approvals, destination = exported(tmp_path)
    directories = sorted(candidates.iterdir())
    accepted, rejected = directories[0], directories[1]
    lines = [approval(accepted, "accept"), approval(rejected, "reject")]
    approvals.write_text("".join(json.dumps(item, sort_keys=True) + "\n" for item in lines), encoding="utf-8")
    assert promote(root=candidates, approvals=approvals, destination=destination) == 0
    promoted = sorted(path.name for path in destination.iterdir() if path.is_dir())
    assert promoted == [accepted.name]
    assert (destination / accepted.name / "approval.json").is_file()
    assert (destination / accepted.name / "verify.sh").is_file()
    index = json.loads((destination / "index.json").read_text(encoding="utf-8"))
    assert index["count"] == 1 and index["environments"][0]["reviewer"] == "A Human"


def test_a_later_verdict_supersedes_an_earlier_one(tmp_path):
    candidates, approvals, destination = exported(tmp_path)
    directory = sorted(candidates.iterdir())[0]
    lines = [approval(directory, "accept"), approval(directory, "reject")]
    approvals.write_text("".join(json.dumps(item, sort_keys=True) + "\n" for item in lines), encoding="utf-8")
    assert latest_verdicts(read_approvals(approvals))[directory.name]["verdict"] == "reject"
    assert promote(root=candidates, approvals=approvals, destination=destination) == 2
    assert not list(destination.glob("*/metadata.json"))


def test_promote_refuses_when_no_environments_were_exported(tmp_path):
    with pytest.raises(RuntimeError, match="make export-environments"):
        promote(root=tmp_path / "missing", approvals=tmp_path / "approvals.jsonl", destination=tmp_path / "approved")
