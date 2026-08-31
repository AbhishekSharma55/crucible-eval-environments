"""Run the measured single-threaded Phase 4 test-authoring agent."""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
import math
import os
from pathlib import Path
import signal
import subprocess
import sys
import time
from typing import Any

from scripts.model_fixture import (
    FIXTURE_DIR, FixtureMiss, chat_completion, fixture_usage, request_hash,
)
from scripts.phase2_common import ROOT
from scripts.phase3_common import PHASE3, TEST_TIMEOUT_S, case_id, json_dump, stable_rank
from scripts.phase4_agent import (
    MAX_GATE_CALLS, AgentWorkspace, load_agent_instructions, render_task,
)


MODEL = "deepseek/deepseek-v4-flash"
TEMPERATURE = 0.2
MAX_TOKENS = 2_200
MAX_TOOL_STEPS = 30
MAX_MODEL_TURNS = 16
CASE_WALL_CAP_S = 360
K3_SUBSET_SEED = 94721
K3_SUBSET_SIZE = 30
PHASE4_SPEND_CAP_USD = 8.0
INPUT_USD_PER_M = 0.09
OUTPUT_USD_PER_M = 0.18
PHASE4 = ROOT / "data/phase4"
RESULTS = Path(os.environ.get("CRUCIBLE_PHASE4_RESULTS_DIR", ROOT / "results/phase4"))
FIXTURE_CHILD = """
import json, sys
from scripts.model_fixture import chat_completion
payload = json.load(sys.stdin)
print(json.dumps(chat_completion(payload, mode='record')))
"""


class CaseWallClockExceeded(RuntimeError):
    pass


def bounded_chat_completion(
    payload: dict[str, Any], *, mode: str, remaining_s: float,
) -> dict[str, Any]:
    """Use the shared fixture layer, hard-killing an in-flight record call at the case cap."""
    if remaining_s <= 0:
        raise CaseWallClockExceeded("case wall-clock limit exhausted before model call")
    if mode == "replay":
        return chat_completion(payload, mode=mode)
    started = time.monotonic()
    process = subprocess.Popen(
        [sys.executable, "-c", FIXTURE_CHILD],
        cwd=ROOT,
        env=os.environ.copy(),
        text=True,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        start_new_session=True,
    )
    try:
        stdout, stderr = process.communicate(json.dumps(payload), timeout=max(0.1, remaining_s))
    except subprocess.TimeoutExpired:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        process.wait()
        raise CaseWallClockExceeded("in-flight model call reached the case wall-clock limit")
    if process.returncode:
        digest = request_hash(payload)
        error_type = "record_transport_error"
        if "ConnectionResetError" in stderr:
            error_type = "connection_reset"
        fixture = {
            "schema_version": 1,
            "request_hash": digest,
            "request": payload,
            "response": {"error": {
                "type": error_type,
                "message": "The provider transport failed before a complete response; usage and any partial charge are unknown.",
            }},
            "latency_s": round(time.monotonic() - started, 3),
        }
        json_dump(FIXTURE_DIR / f"{digest}.json", fixture)
        return fixture
    return json.loads(stdout)


def _usage_total(items: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        key: sum(float(item.get(key) or 0) for item in items)
        for key in ("prompt_tokens", "completion_tokens", "total_tokens", "cost_usd", "latency_s")
    }


def _instruction_hashes() -> dict[str, str]:
    result = {}
    for name in ("phase4-system.md", "phase4-task.md", "phase4-tools.md"):
        content = (ROOT / "agents" / name).read_bytes()
        result[f"agents/{name}"] = hashlib.sha256(content).hexdigest()
    return result


def _rollout_seed(candidate: dict[str, Any], rollout: int) -> int:
    digest = hashlib.sha256(f"phase4:{case_id(candidate)}:{rollout}".encode()).hexdigest()
    return int(digest[:8], 16) % (2**31 - 1)


def request_payload(
    messages: list[dict[str, Any]], tools: list[dict[str, Any]], *, seed: int,
) -> dict[str, Any]:
    return {
        "model": MODEL,
        "messages": messages,
        "tools": tools,
        "tool_choice": "auto",
        "parallel_tool_calls": False,
        "temperature": TEMPERATURE,
        "seed": seed,
        "max_tokens": MAX_TOKENS,
        "reasoning": {"enabled": False},
    }


def _response_message(fixture: dict[str, Any]) -> tuple[dict[str, Any], str | None]:
    response = fixture.get("response") or {}
    if "error" in response:
        raise RuntimeError(f"cached OpenRouter error: {response['error']}")
    try:
        choice = response["choices"][0]
        message = choice["message"]
    except (KeyError, IndexError, TypeError) as exc:
        raise RuntimeError("fixture has no assistant message") from exc
    if not isinstance(message, dict):
        raise RuntimeError("fixture assistant message is not an object")
    normalized: dict[str, Any] = {"role": "assistant", "content": message.get("content")}
    if message.get("tool_calls") is not None:
        normalized["tool_calls"] = message["tool_calls"]
    return normalized, choice.get("finish_reason")


def _empty_verification(reason: str) -> dict[str, Any]:
    return {
        "passed": False,
        "abort_reason": reason,
        "gates": {
            name: {"status": "skipped", "reason": reason, "evidence": {}}
            for name in ("g1", "g2", "g3", "g4", "g5")
        },
        "wall_s": 0,
    }


def first_failure(result: dict[str, Any]) -> str:
    verification = result["verification"]
    for name in ("g1", "g2", "g3", "g4", "g5"):
        if verification["gates"][name]["status"] == "fail":
            return name.upper()
    if result.get("stop_reason") == "model_error":
        return "MODEL_ERROR"
    return "NO_GATE_CHECK" if not result.get("gate_attempts") else "CASE_LIMIT"


def run_case(
    candidate: dict[str, Any], rollout: int, mode: str, *, image: str,
    timeout_s: int, case_cap_s: int, max_tool_steps: int, max_model_turns: int,
    cost_budget_usd: float = PHASE4_SPEND_CAP_USD,
) -> dict[str, Any]:
    """Execute one sequential model/tool trajectory and select its last gate-checked test."""
    started = time.monotonic()
    system, task_template, tools = load_agent_instructions()
    messages: list[dict[str, Any]] = [
        {"role": "system", "content": system},
        {"role": "user", "content": render_task(candidate, task_template)},
    ]
    workspace = AgentWorkspace(
        candidate, image=image, timeout_s=timeout_s, wall_cap_s=case_cap_s, started=started,
    )
    usage_items: list[dict[str, Any]] = []
    events: list[dict[str, Any]] = []
    tool_counts: Counter[str] = Counter()
    tool_steps = 0
    model_turns = 0
    stop_reason: str | None = None
    seed = _rollout_seed(candidate, rollout)

    while model_turns < max_model_turns and tool_steps < max_tool_steps:
        if workspace.remaining_s() <= 0:
            stop_reason = "case_wall_clock_exceeded"
            break
        payload = request_payload(messages, tools, seed=seed)
        conservative_input_tokens = len(json.dumps(payload, ensure_ascii=False).encode("utf-8"))
        estimated_request_ceiling = (
            conservative_input_tokens * INPUT_USD_PER_M / 1_000_000
            + MAX_TOKENS * OUTPUT_USD_PER_M / 1_000_000
        )
        spent_so_far = sum(float(item.get("cost_usd") or 0) for item in usage_items)
        if spent_so_far + estimated_request_ceiling > cost_budget_usd:
            stop_reason = "phase4_spend_cap"
            break
        try:
            fixture = bounded_chat_completion(
                payload,
                mode=mode,
                remaining_s=workspace.remaining_s(),
            )
        except CaseWallClockExceeded:
            stop_reason = "case_wall_clock_exceeded"
            break
        usage = fixture_usage(fixture)
        usage_items.append(usage)
        model_turns += 1
        try:
            assistant, finish_reason = _response_message(fixture)
        except RuntimeError as exc:
            events.append({
                "kind": "model_error", "turn": model_turns,
                "request_hash": usage["request_hash"], "error": str(exc), "usage": usage,
            })
            stop_reason = "model_error"
            break
        messages.append(assistant)
        calls = assistant.get("tool_calls") or []
        events.append({
            "kind": "model",
            "turn": model_turns,
            "request_hash": usage["request_hash"],
            "finish_reason": finish_reason,
            "content": assistant.get("content"),
            "tool_names": [call.get("function", {}).get("name") for call in calls],
            "usage": usage,
        })
        if not calls:
            stop_reason = "model_stopped_without_passing_gate_check"
            break
        for index, call in enumerate(calls):
            if tool_steps >= max_tool_steps:
                stop_reason = "tool_step_cap_exceeded"
                break
            tool_steps += 1
            function = call.get("function") or {}
            name = function.get("name")
            raw_arguments = function.get("arguments", "{}")
            argument_error = None
            if isinstance(raw_arguments, dict):
                arguments = raw_arguments
            else:
                try:
                    arguments = json.loads(raw_arguments)
                except (json.JSONDecodeError, TypeError) as exc:
                    arguments = {}
                    argument_error = f"tool arguments are invalid JSON: {exc}; send one JSON object matching the tool schema"
            if argument_error:
                observation = {"ok": False, "error": argument_error}
            elif not isinstance(name, str):
                observation = {"ok": False, "error": "tool call has no function name; call one named tool from the supplied schema"}
            else:
                tool_counts[name] += 1
                observation = workspace.call(name, arguments)
            tool_call_id = call.get("id") or f"phase4-call-{model_turns}-{index}"
            tool_message = {
                "role": "tool", "tool_call_id": tool_call_id,
                "content": json.dumps(observation, sort_keys=True),
            }
            messages.append(tool_message)
            events.append({
                "kind": "tool", "step": tool_steps, "name": name,
                "arguments": arguments, "observation": observation,
            })
            if workspace.gate_attempts and workspace.gate_attempts[-1]["verification"]["passed"]:
                stop_reason = "passed_all_gates"
                break
            if workspace.remaining_s() <= 0:
                stop_reason = "case_wall_clock_exceeded"
                break
        if stop_reason:
            break

    if stop_reason is None:
        stop_reason = "model_turn_cap_exceeded" if model_turns >= max_model_turns else "tool_step_cap_exceeded"
    final_gate = workspace.gate_attempts[-1] if workspace.gate_attempts else None
    authored = final_gate["authored_test"] if final_gate else (workspace.staged or {})
    verification = final_gate["verification"] if final_gate else _empty_verification("no_gate_check")
    usage = _usage_total(usage_items)
    passed = bool(verification.get("passed"))
    return {
        "case_id": case_id(candidate),
        "repo": candidate["repo"],
        "pr_number": candidate["pr_number"],
        "rollout": rollout,
        "rollout_seed": seed,
        "passed": passed,
        "stop_reason": stop_reason,
        "authored_test": authored,
        "verification": verification,
        "gate_calls": workspace.gate_calls,
        "accepted_gate_call": final_gate["gate_call"] if passed and final_gate else None,
        "gate_attempts": workspace.gate_attempts,
        "gaming_flags": final_gate["gaming_flags"] if final_gate else [],
        "tool_steps": tool_steps,
        "model_turns": model_turns,
        "tool_counts": dict(sorted(tool_counts.items())),
        "usage": usage,
        "wall_s": round(time.monotonic() - started, 3),
        "events": events,
    }


def load_cases(path: Path | None = None) -> tuple[list[dict[str, Any]], int]:
    case_set_path = path or (PHASE3 / "case-set.json")
    payload = json.loads(case_set_path.read_text(encoding="utf-8"))
    cases = payload["cases"]
    if path is None and len(cases) != 80:
        raise RuntimeError(f"Phase 4 requires the fixed 80-case Phase 3 set, found {len(cases)}")
    return cases, payload["seed"]


def k3_subset(cases: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_repo: dict[str, list[dict[str, Any]]] = {}
    for item in cases:
        by_repo.setdefault(item["repo"], []).append(item)
    exact = {repo: K3_SUBSET_SIZE * len(items) / len(cases) for repo, items in by_repo.items()}
    counts = {repo: max(1, math.floor(value)) for repo, value in exact.items()}
    while sum(counts.values()) < K3_SUBSET_SIZE:
        choices = [repo for repo, items in by_repo.items() if counts[repo] < len(items)]
        chosen = max(choices, key=lambda repo: (exact[repo] - counts[repo], stable_rank(K3_SUBSET_SEED, repo)))
        counts[chosen] += 1
    while sum(counts.values()) > K3_SUBSET_SIZE:
        choices = [repo for repo in by_repo if counts[repo] > 1]
        chosen = max(choices, key=lambda repo: (counts[repo] - exact[repo], stable_rank(K3_SUBSET_SEED, repo)))
        counts[chosen] -= 1
    selected = []
    for repo, items in sorted(by_repo.items()):
        ranked = sorted(items, key=lambda item: stable_rank(K3_SUBSET_SEED, case_id(item)))
        selected.extend(ranked[:counts[repo]])
    return sorted(selected, key=case_id)


def write_subset(cases: list[dict[str, Any]], case_set_seed: int) -> None:
    subset = k3_subset(cases)
    json_dump(PHASE4 / "k3-subset.json", {
        "schema_version": 1,
        "phase": 4,
        "selection_rule": "proportional repository allocation with minimum one and SHA-256 seed:case_id rank",
        "seed": K3_SUBSET_SEED,
        "source_case_set_seed": case_set_seed,
        "n": len(subset),
        "repo_counts": dict(sorted(Counter(item["repo"] for item in subset).items())),
        "case_ids": [case_id(item) for item in subset],
    })


def rollout_plan(cases: list[dict[str, Any]], name: str) -> list[tuple[int, list[dict[str, Any]]]]:
    if name == "one":
        return [(0, cases)]
    if name == "full":
        return [(index, cases) for index in range(3)]
    subset = k3_subset(cases)
    return [(0, cases), (1, subset), (2, subset)]


def _checkpoint_payload(
    rollout: int, expected: list[dict[str, Any]], results: list[dict[str, Any]],
    *, mode: str, case_set_seed: int, limits: dict[str, Any], started: float,
) -> dict[str, Any]:
    passed = sum(item["passed"] for item in results)
    breakdown = Counter(first_failure(item) for item in results if not item["passed"])
    totals = _usage_total([item["usage"] for item in results])
    return {
        "schema_version": 1,
        "phase": 4,
        "arm": "single_threaded_agent",
        "model": MODEL,
        "temperature": TEMPERATURE,
        "fixture_mode": mode,
        "case_set_seed": case_set_seed,
        "rollout": rollout,
        "expected_n": len(expected),
        "expected_case_ids": [case_id(item) for item in expected],
        "n": len(results),
        "complete": len(results) == len(expected),
        "verified_count": passed,
        "verified_rate": passed / len(results) if results else 0.0,
        "first_failure_breakdown": dict(sorted(breakdown.items())),
        "totals": totals,
        "cost_per_candidate_usd": totals["cost_usd"] / len(results) if results else 0.0,
        "tokens_per_candidate": totals["total_tokens"] / len(results) if results else 0.0,
        "model_latency_per_candidate_s": totals["latency_s"] / len(results) if results else 0.0,
        "wall_clock_s": round(time.monotonic() - started, 3),
        "wall_clock_per_candidate_s": sum(item["wall_s"] for item in results) / len(results) if results else 0.0,
        "limits": limits,
        "instruction_sha256": _instruction_hashes(),
        "results": results,
    }


def _load_resume(
    path: Path, expected: list[dict[str, Any]], limits: dict[str, Any],
) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    payload = json.loads(path.read_text(encoding="utf-8"))
    expected_ids = [case_id(item) for item in expected]
    if payload.get("expected_case_ids") != expected_ids:
        raise RuntimeError(f"cannot resume {path}: expected case IDs changed")
    if payload.get("model") != MODEL or payload.get("temperature") != TEMPERATURE:
        raise RuntimeError(f"cannot resume {path}: pinned model configuration changed")
    if payload.get("instruction_sha256") != _instruction_hashes():
        raise RuntimeError(f"cannot resume {path}: agent instruction files changed")
    if payload.get("limits") != limits:
        raise RuntimeError(f"cannot resume {path}: execution limits changed")
    results = payload.get("results") or []
    if [item["case_id"] for item in results] != expected_ids[:len(results)]:
        raise RuntimeError(f"cannot resume {path}: completed prefix is not deterministic")
    return results


def _parsed_call_arguments(call: dict[str, Any]) -> dict[str, Any]:
    """Mirror the measured runner's argument parsing for transcript replay."""
    raw = (call.get("function") or {}).get("arguments", "{}")
    if isinstance(raw, dict):
        return raw
    try:
        parsed = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return {}
    return parsed if isinstance(parsed, dict) else {}


def replay_recorded_case(
    candidate: dict[str, Any], result: dict[str, Any], rollout: int,
) -> dict[str, Any]:
    """Replay model fixtures against the exact measured tool transcript.

    Test-process output contains nondeterministic temporary paths, object addresses,
    and timings. Re-executing tools would therefore create a different model request
    even when behavior is identical. The measured observations are the prompt
    surface, so fixture replay reconstructs requests from those observations and
    separately validates the recorded tool-call names and arguments.
    """
    system, task_template, tools = load_agent_instructions()
    messages: list[dict[str, Any]] = [
        {"role": "system", "content": system},
        {"role": "user", "content": render_task(candidate, task_template)},
    ]
    seed = _rollout_seed(candidate, rollout)
    current_calls: list[dict[str, Any]] = []
    call_index = 0
    checked = 0
    for event in result.get("events") or []:
        kind = event.get("kind")
        if kind in {"model", "model_error"}:
            payload = request_payload(messages, tools, seed=seed)
            digest = request_hash(payload)
            if digest != event.get("request_hash"):
                raise RuntimeError(
                    f"transcript hash mismatch for {result['case_id']} rollout {rollout} "
                    f"turn {event.get('turn')}: recorded {event.get('request_hash')}, reconstructed {digest}"
                )
            fixture = chat_completion(payload, mode="replay")
            checked += 1
            if kind == "model_error":
                if "error" not in (fixture.get("response") or {}):
                    raise RuntimeError(
                        f"recorded model error for {result['case_id']} rollout {rollout} "
                        f"turn {event.get('turn')} replays as a successful response"
                    )
                current_calls = []
                call_index = 0
                continue
            assistant, finish_reason = _response_message(fixture)
            calls = assistant.get("tool_calls") or []
            if assistant.get("content") != event.get("content"):
                raise RuntimeError(
                    f"assistant content mismatch for {result['case_id']} rollout {rollout} turn {event.get('turn')}"
                )
            if finish_reason != event.get("finish_reason"):
                raise RuntimeError(
                    f"finish reason mismatch for {result['case_id']} rollout {rollout} turn {event.get('turn')}"
                )
            if [call.get("function", {}).get("name") for call in calls] != event.get("tool_names"):
                raise RuntimeError(
                    f"tool-call list mismatch for {result['case_id']} rollout {rollout} turn {event.get('turn')}"
                )
            messages.append(assistant)
            current_calls = calls
            call_index = 0
            continue
        if kind != "tool":
            raise RuntimeError(f"unknown recorded event kind {kind!r} for {result['case_id']}")
        if call_index >= len(current_calls):
            raise RuntimeError(f"orphan tool observation for {result['case_id']} rollout {rollout}")
        call = current_calls[call_index]
        function = call.get("function") or {}
        if function.get("name") != event.get("name"):
            raise RuntimeError(f"tool name mismatch for {result['case_id']} rollout {rollout}")
        if _parsed_call_arguments(call) != event.get("arguments"):
            raise RuntimeError(f"tool arguments mismatch for {result['case_id']} rollout {rollout}")
        tool_call_id = call.get("id") or f"phase4-call-{event.get('step')}-{call_index}"
        messages.append({
            "role": "tool",
            "tool_call_id": tool_call_id,
            "content": json.dumps(event.get("observation"), sort_keys=True),
        })
        call_index += 1
    if checked != result.get("model_turns"):
        raise RuntimeError(
            f"model-turn count mismatch for {result['case_id']} rollout {rollout}: "
            f"recorded {result.get('model_turns')}, replayed {checked}"
        )
    return {"case_id": result["case_id"], "rollout": rollout, "fixtures_checked": checked}


def replay_recorded_plan(
    plan: list[tuple[int, list[dict[str, Any]]]], limits: dict[str, Any], case_set_seed: int,
) -> dict[str, Any]:
    """Hard-fail audit of every model fixture in the completed measured checkpoints."""
    audits: list[dict[str, Any]] = []
    for rollout, expected in plan:
        path = RESULTS / f"agent-rollout-{rollout}.json"
        results = _load_resume(path, expected, limits)
        if len(results) != len(expected):
            raise RuntimeError(
                f"cannot replay incomplete measured checkpoint {path}: {len(results)}/{len(expected)} cases"
            )
        for candidate, result in zip(expected, results):
            audits.append(replay_recorded_case(candidate, result, rollout))
    payload = {
        "schema_version": 1,
        "phase": 4,
        "fixture_mode": "replay",
        "method": "exact measured tool-transcript reconstruction",
        "case_set_seed": case_set_seed,
        "cases_checked": len(audits),
        "fixtures_checked": sum(item["fixtures_checked"] for item in audits),
        "instruction_sha256": _instruction_hashes(),
        "audits": audits,
    }
    json_dump(RESULTS / "replay-audit.json", payload)
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixture-mode", choices=("replay", "record"), default="replay")
    parser.add_argument("--rollout-plan", choices=("one", "subset", "full"), default="subset")
    parser.add_argument("--image", default="crucible-sandbox:phase3")
    parser.add_argument("--timeout", type=int, default=TEST_TIMEOUT_S)
    parser.add_argument("--case-cap", type=int, default=CASE_WALL_CAP_S)
    parser.add_argument("--max-tool-steps", type=int, default=MAX_TOOL_STEPS)
    parser.add_argument("--max-model-turns", type=int, default=MAX_MODEL_TURNS)
    parser.add_argument("--case", help="run one case ID for harness debugging")
    parser.add_argument("--case-set", type=Path, help="explicit fixed case set (used for held-out evaluation)")
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()
    if not 1 <= args.max_tool_steps <= MAX_TOOL_STEPS:
        raise RuntimeError(f"max tool steps must be between 1 and the fixed cap {MAX_TOOL_STEPS}")
    if not 1 <= args.max_model_turns <= MAX_MODEL_TURNS:
        raise RuntimeError(f"max model turns must be between 1 and the fixed cap {MAX_MODEL_TURNS}")
    if args.case_cap > CASE_WALL_CAP_S:
        raise RuntimeError(f"case cap cannot exceed the fairness limit of {CASE_WALL_CAP_S}s")
    if args.fixture_mode == "record" and not os.environ.get("OPENROUTER_API_KEY"):
        raise RuntimeError("OPENROUTER_API_KEY is required only for explicit record mode")

    cases, case_set_seed = load_cases(args.case_set)
    if args.case_set is None:
        write_subset(cases, case_set_seed)
    if args.case:
        cases = [item for item in cases if case_id(item) == args.case]
        if not cases:
            raise RuntimeError(f"case {args.case!r} is not in the fixed Phase 3 case set")
        plan = [(0, cases)]
    else:
        plan = rollout_plan(cases, args.rollout_plan)
    limits = {
        "workers": 1,
        "single_threaded": True,
        "max_check_gates_calls": MAX_GATE_CALLS,
        "max_tool_steps": args.max_tool_steps,
        "max_model_turns": args.max_model_turns,
        "per_test_run_s": args.timeout,
        "per_case_wall_s": args.case_cap,
        "phase4_executed_cost_cap_usd": PHASE4_SPEND_CAP_USD,
    }
    if args.fixture_mode == "replay" and not args.case:
        audit = replay_recorded_plan(plan, limits, case_set_seed)
        print(
            f"replay audit: {audit['cases_checked']} trajectories, "
            f"{audit['fixtures_checked']} model fixtures; no network access",
            flush=True,
        )
        return 0
    run_cost = 0.0
    for rollout, expected in plan:
        path = RESULTS / f"agent-rollout-{rollout}.json"
        results = _load_resume(path, expected, limits) if args.resume else []
        run_cost += sum(float(item["usage"].get("cost_usd") or 0) for item in results)
        started = time.monotonic()
        for candidate in expected[len(results):]:
            if run_cost >= PHASE4_SPEND_CAP_USD:
                raise RuntimeError(f"Phase 4 executed cost reached the hard ${PHASE4_SPEND_CAP_USD:.2f} cap")
            result = run_case(
                candidate, rollout, args.fixture_mode, image=args.image,
                timeout_s=args.timeout, case_cap_s=args.case_cap,
                max_tool_steps=args.max_tool_steps, max_model_turns=args.max_model_turns,
                cost_budget_usd=max(0.0, PHASE4_SPEND_CAP_USD - run_cost),
            )
            results.append(result)
            run_cost += float(result["usage"].get("cost_usd") or 0)
            checkpoint = _checkpoint_payload(
                rollout, expected, results, mode=args.fixture_mode,
                case_set_seed=case_set_seed, limits=limits, started=started,
            )
            json_dump(path, checkpoint)
            label = "PASS" if result["passed"] else first_failure(result)
            print(
                f"A{rollout} {result['case_id']}: {label}; "
                f"gates={result['gate_calls']} tools={result['tool_steps']} ${result['usage']['cost_usd']:.6f}",
                flush=True,
            )
        payload = _checkpoint_payload(
            rollout, expected, results, mode=args.fixture_mode,
            case_set_seed=case_set_seed, limits=limits, started=started,
        )
        json_dump(path, payload)
        print(
            f"A{rollout}: {payload['verified_count']}/{payload['n']} "
            f"({payload['verified_rate']:.1%}); ${payload['totals']['cost_usd']:.6f}",
            flush=True,
        )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except FixtureMiss as exc:
        raise SystemExit(f"fixture replay hard-failed: {exc}")
