from __future__ import annotations

import json

import pytest

from scripts.model_fixture import FixtureMiss, request_hash
from scripts.phase4_agent import (
    MAX_GATE_CALLS, AgentWorkspace, _bounded, gaming_flags, load_agent_instructions,
)
from scripts.report_phase4 import category
from scripts.run_phase4_agent import (
    first_failure, k3_subset, replay_recorded_case, request_payload, rollout_plan, run_case,
)


def candidate(index: int = 1):
    return {
        "repo": "example/repo",
        "pr_number": index,
        "parent_sha": "a" * 40,
        "merge_commit_sha": "b" * 40,
        "title": "Fix behavior",
        "body": "",
        "linked_issues": [{"number": index, "body": "Public behavior is wrong."}],
        "source_files": ["src/pkg.py"],
    }


def passing_verification():
    return {
        "passed": True,
        "gates": {
            name: {"status": "pass", "reason": None, "evidence": {}}
            for name in ("g1", "g2", "g3", "g4", "g5")
        },
        "wall_s": 0.1,
    }


def test_agent_instructions_and_native_tools_are_loaded_from_files():
    system, task, tools = load_agent_instructions()
    assert "single test-authoring agent" in system
    assert "{{GOLD_PATCH}}" in task
    assert [item["function"]["name"] for item in tools] == [
        "list_tests", "read_file", "search", "write_test", "run_test", "check_gates",
    ]
    check = tools[-1]["function"]
    assert "five" in check["description"]
    assert check["parameters"]["additionalProperties"] is False


def test_long_observation_has_explicit_truncation_marker():
    output = _bounded("a" * 10_000, 100)
    assert len(output) > 100
    assert "[TRUNCATED 9900 CHARACTERS" in output
    assert output.startswith("a" * 60)
    assert output.endswith("a" * 40)


def test_windowed_read_rejects_oversized_or_unsafe_ranges():
    workspace = AgentWorkspace(candidate(), image="unused", timeout_s=1, wall_cap_s=10)
    too_large = workspace.read_file("src/pkg.py", 1, 161)
    unsafe = workspace.read_file("../secret", 1, 2)
    assert too_large["ok"] is False
    assert "at most 160" in too_large["error"]
    assert unsafe["ok"] is False
    assert "inside the repository" in unsafe["error"]


def test_gate_check_cap_is_host_enforced(monkeypatch):
    calls = []
    monkeypatch.setattr("scripts.phase4_agent.verify", lambda *args, **kwargs: calls.append(1) or passing_verification())
    workspace = AgentWorkspace(candidate(), image="unused", timeout_s=1, wall_cap_s=30)
    workspace.staged = {"path": "tests/test_regression.py", "content": "def test_bug(): assert 1"}
    for expected in range(1, MAX_GATE_CALLS + 1):
        result = workspace.check_gates()
        assert result["gate_call"] == expected
    rejected = workspace.check_gates()
    assert rejected["ok"] is False
    assert rejected["gate_calls_remaining"] == 0
    assert len(calls) == MAX_GATE_CALLS


def test_premature_gate_calls_still_consume_budget(monkeypatch):
    calls = []
    monkeypatch.setattr("scripts.phase4_agent.verify", lambda *args, **kwargs: calls.append(1) or passing_verification())
    workspace = AgentWorkspace(candidate(), image="unused", timeout_s=1, wall_cap_s=30)
    for remaining in range(MAX_GATE_CALLS - 1, -1, -1):
        result = workspace.check_gates()
        assert result["ok"] is False
        assert result["gate_calls_remaining"] == remaining
    workspace.staged = {"path": "tests/test_regression.py", "content": "def test_bug(): assert 1"}
    assert workspace.check_gates()["ok"] is False
    assert calls == []


def test_write_surface_flags_gaming_without_using_it_as_a_gate(monkeypatch):
    monkeypatch.setattr(
        "scripts.phase4_agent.validate_authored_test",
        lambda *args: {"status": "pass", "reason": None, "bytes": 20},
    )
    workspace = AgentWorkspace(candidate(), image="unused", timeout_s=1, wall_cap_s=30)
    content = "import sys\ndef test_bug():\n    assert sys.version_info\n"
    result = workspace.write_test("tests/test_regression.py", content)
    assert result["ok"] is True
    assert result["review_flags"] == ["runtime_version_or_environment_branch"]
    assert workspace.staged["content"] == content


def test_gaming_review_patterns_cover_required_cheats():
    assert "runtime_source_or_file_inspection" in gaming_flags("def test_x(): open('pkg.py').read()")
    assert "runtime_git_or_commit_inspection" in gaming_flags("subprocess.run(['git', 'rev-parse'])")
    assert "skip_or_expected_failure" in gaming_flags("pytest.skip('not here')")
    assert "unconditional_failure" in gaming_flags("def test_x(): assert False")
    assert gaming_flags("def test_x(client): assert client.get('/').status_code == 200") == []


def test_rollout_subset_is_fixed_and_plan_is_k1_plus_two_subset_runs():
    cases = [candidate(index) for index in range(80)]
    first = [item["pr_number"] for item in k3_subset(cases)]
    second = [item["pr_number"] for item in k3_subset(list(reversed(cases)))]
    assert first == second
    assert len(first) == 30
    plan = rollout_plan(cases, "subset")
    assert [(rollout, len(items)) for rollout, items in plan] == [(0, 80), (1, 30), (2, 30)]


def test_run_case_executes_native_tool_loop_and_stops_on_gate_pass(monkeypatch):
    turn = iter([
        {
            "role": "assistant", "content": None,
            "tool_calls": [{"id": "call-write", "type": "function", "function": {
                "name": "write_test", "arguments": json.dumps({
                    "path": "tests/test_regression.py", "content": "def test_bug(): assert True",
                }),
            }}],
        },
        {
            "role": "assistant", "content": None,
            "tool_calls": [{"id": "call-gates", "type": "function", "function": {
                "name": "check_gates", "arguments": "{}",
            }}],
        },
    ])

    def fake_chat(payload, mode):
        message = next(turn)
        tool_messages = [item for item in payload["messages"] if item["role"] == "tool"]
        if message["tool_calls"][0]["function"]["name"] == "check_gates":
            assert tool_messages[-1]["tool_call_id"] == "call-write"
        return {
            "request_hash": f"hash-{len(tool_messages)}",
            "latency_s": 0.25,
            "response": {
                "choices": [{"message": message, "finish_reason": "tool_calls"}],
                "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15, "cost": 0.001},
            },
        }

    monkeypatch.setattr("scripts.run_phase4_agent.chat_completion", fake_chat)
    monkeypatch.setattr("scripts.run_phase4_agent.render_task", lambda *args: "measured task")
    monkeypatch.setattr(
        "scripts.phase4_agent.validate_authored_test",
        lambda *args: {"status": "pass", "reason": None, "bytes": 28},
    )
    monkeypatch.setattr("scripts.phase4_agent.verify", lambda *args, **kwargs: passing_verification())
    result = run_case(
        candidate(), 0, "replay", image="unused", timeout_s=1,
        case_cap_s=30, max_tool_steps=5, max_model_turns=5, cost_budget_usd=1.0,
    )
    assert result["passed"] is True
    assert result["stop_reason"] == "passed_all_gates"
    assert result["tool_counts"] == {"check_gates": 1, "write_test": 1}
    assert result["model_turns"] == 2
    assert result["usage"]["total_tokens"] == 30


def test_fixture_miss_propagates_as_a_hard_failure(monkeypatch):
    monkeypatch.setattr("scripts.run_phase4_agent.render_task", lambda *args: "measured task")
    monkeypatch.setattr(
        "scripts.run_phase4_agent.chat_completion",
        lambda *args, **kwargs: (_ for _ in ()).throw(FixtureMiss("missing")),
    )
    with pytest.raises(FixtureMiss):
        run_case(
            candidate(), 0, "replay", image="unused", timeout_s=1,
            case_cap_s=30, max_tool_steps=5, max_model_turns=5, cost_budget_usd=1.0,
        )


def test_recorded_transcript_replay_uses_exact_tool_observation(monkeypatch):
    call = {
        "id": "call-read", "type": "function",
        "function": {"name": "read_file", "arguments": '{"path":"src/pkg.py","start":1,"end":2}'},
    }
    assistant1 = {"role": "assistant", "content": None, "tool_calls": [call]}
    assistant2 = {"role": "assistant", "content": "done"}
    observation = {"ok": True, "duration_s": 1.234, "stdout": "/tmp/random-address-0xffff"}
    monkeypatch.setattr(
        "scripts.run_phase4_agent.load_agent_instructions",
        lambda: ("system", "task", []),
    )
    monkeypatch.setattr("scripts.run_phase4_agent.render_task", lambda *args: "rendered")
    monkeypatch.setattr("scripts.run_phase4_agent._rollout_seed", lambda *args: 123)
    messages1 = [{"role": "system", "content": "system"}, {"role": "user", "content": "rendered"}]
    payload1 = request_payload(messages1, [], seed=123)
    tool_message = {
        "role": "tool", "tool_call_id": "call-read",
        "content": json.dumps(observation, sort_keys=True),
    }
    payload2 = request_payload(messages1 + [assistant1, tool_message], [], seed=123)
    fixtures = {
        request_hash(payload1): {
            "request_hash": request_hash(payload1), "latency_s": 0.1,
            "response": {"choices": [{"message": assistant1, "finish_reason": "tool_calls"}]},
        },
        request_hash(payload2): {
            "request_hash": request_hash(payload2), "latency_s": 0.1,
            "response": {"choices": [{"message": assistant2, "finish_reason": "stop"}]},
        },
    }
    monkeypatch.setattr(
        "scripts.run_phase4_agent.chat_completion",
        lambda payload, mode: fixtures[request_hash(payload)],
    )
    result = {
        "case_id": "example/repo#1", "model_turns": 2,
        "events": [
            {"kind": "model", "turn": 1, "request_hash": request_hash(payload1),
             "content": None, "finish_reason": "tool_calls", "tool_names": ["read_file"]},
            {"kind": "tool", "step": 1, "name": "read_file",
             "arguments": {"path": "src/pkg.py", "start": 1, "end": 2}, "observation": observation},
            {"kind": "model", "turn": 2, "request_hash": request_hash(payload2),
             "content": "done", "finish_reason": "stop", "tool_names": []},
        ],
    }
    assert replay_recorded_case(candidate(), result, 0)["fixtures_checked"] == 2


def test_failure_category_preserves_gate_and_no_check_outcomes():
    failed = passing_verification()
    failed["passed"] = False
    failed["gates"]["g2"] = {"status": "fail", "reason": "broken", "evidence": {}}
    result = {"passed": False, "verification": failed, "gate_calls": 1, "rollout": 0}
    assert category(result) == "G2"
    assert first_failure(result) == "G2"
    no_check = {"passed": False, "verification": {"gates": {}}, "gate_calls": 1, "gate_attempts": [], "rollout": 0}
    assert category(no_check) == "NO_GATE_CHECK"
