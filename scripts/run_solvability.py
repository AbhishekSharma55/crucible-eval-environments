"""Run a one-step, cost-bounded solver without exposing the gold source patch."""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import json
from pathlib import Path
import re
import time
from typing import Any

from scripts.model_fixture import chat_completion, fixture_text, fixture_usage
from scripts.phase2_common import PHASE2, git, json_dump
from scripts.run_baselines import DEFAULT_MODEL
from scripts.run_tests import run_tests


MAX_CONTEXT_CHARS = 50_000
STEP_CAP = 1
TEST_WALL_CAP_S = 600
SPEND_CAP_USD = 12.0


def parent_context(case: dict[str, Any]) -> str:
    chunks = []
    used = 0
    for path in case["source_files"]:
        shown = git(case["repo"], "show", f"{case['parent_sha']}:{path}", check=False)
        if shown.returncode:
            continue
        chunk = f"\n--- {path} ---\n{shown.stdout}"
        remaining = MAX_CONTEXT_CHARS - used
        if remaining <= 0:
            break
        chunks.append(chunk[:remaining])
        used += min(len(chunk), remaining)
    return "".join(chunks)


def payload(case: dict[str, Any], model: str) -> dict[str, Any]:
    return {
        "model": model,
        "messages": [
            {"role": "system", "content": "You are a software repair agent. Produce a minimal unified diff that fixes the reported behavior. Return only the diff. You have one step and cannot use the network."},
            {"role": "user", "content": f"Problem statement:\n{case['problem_statement']}\n\nParent source files:{parent_context(case)}"},
        ],
        "temperature": 0.0,
        "max_tokens": 2000,
        "reasoning": {"enabled": False},
    }


def clean_patch(text: str) -> str:
    match = re.search(r"```(?:diff)?\s*\n(.*?)```", text, re.DOTALL)
    return (match.group(1) if match else text).strip() + "\n"


def patched_paths(patch: str) -> set[str]:
    return {line[6:] for line in patch.splitlines() if line.startswith("+++ b/")}


def solve(case: dict[str, Any], model: str, mode: str, image: str) -> dict[str, Any]:
    started = time.monotonic()
    usage: dict[str, Any] = {"cost_usd": 0, "latency_s": 0}
    try:
        fixture = chat_completion(payload(case, model), mode=mode)
        usage = fixture_usage(fixture)
        patch = clean_patch(fixture_text(fixture))
    except Exception as exc:
        return {"case_id": case["case_id"], "group": case["group"], "solved": False,
                "abort_reason": f"model_error:{type(exc).__name__}", "detail": str(exc), "usage": usage,
                "wall_s": round(time.monotonic() - started, 3)}
    forbidden = patched_paths(patch).intersection(case["test_files"])
    if forbidden:
        return {
            "case_id": case["case_id"], "group": case["group"], "solved": False,
            "abort_reason": "solver_modified_hidden_tests", "forbidden_paths": sorted(forbidden),
            "usage": usage, "wall_s": round(time.monotonic() - started, 3), "solution_patch": patch,
        }
    result = run_tests(
        case["repo"], case["parent_sha"], case["test_files"], image=image,
        timeout_s=TEST_WALL_CAP_S, test_patch_from=case["hidden_test_patch_sha"], solution_patch=patch,
    )
    outcomes = {item["nodeid"]: item["outcome"] for item in result.get("per_test_status", [])}
    transitioned_pass = all(outcomes.get(item["nodeid"]) == "passed" for item in case["transition_tests"])
    solved = result.get("exit_code") == 0 and transitioned_pass
    abort = None
    if not solved:
        stage = result.get("stage")
        if stage == "test":
            abort = "tests_failed" if result.get("exit_code") != 0 else "transition_check_failed"
        else:
            abort = stage or "transition_check_failed"
    return {
        "case_id": case["case_id"], "group": case["group"], "solved": solved,
        "abort_reason": abort, "usage": usage, "wall_s": round(time.monotonic() - started, 3),
        "test_result": {"exit_code": result.get("exit_code"), "stage": result.get("stage"),
                        "duration_s": result.get("duration_s"), "transitioned_tests_pass": transitioned_pass,
                        "stderr_tail": result.get("stderr", "")[-1000:]},
        "solution_patch": patch,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--set", type=Path, default=PHASE2 / "solvability-set.json")
    parser.add_argument("--output", type=Path, default=Path("results/solvability.json"))
    parser.add_argument("--fixture-mode", choices=("replay", "record"), default="replay")
    parser.add_argument("--image", default="crucible-sandbox:phase1")
    parser.add_argument("--max-spend", type=float, default=SPEND_CAP_USD)
    parser.add_argument("--workers", type=int, default=3)
    args = parser.parse_args()
    case_set = json.loads(args.set.read_text(encoding="utf-8"))
    # The pinned model is priced far below this bound, but preflight the whole
    # concurrent batch so parallel submission cannot race past the spend cap.
    requests = [payload(case, DEFAULT_MODEL) for case in case_set["cases"]]
    conservative_tokens = sum(len(json.dumps(item)) / 3 + 2000 for item in requests)
    conservative_cost = conservative_tokens * 0.66 / 1_000_000
    if conservative_cost > args.max_spend:
        raise RuntimeError(
            f"solver preflight estimate ${conservative_cost:.2f} exceeds ${args.max_spend:.2f} cap"
        )
    indexed_results: dict[int, dict[str, Any]] = {}
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = {
            pool.submit(solve, case, DEFAULT_MODEL, args.fixture_mode, args.image): (index, case)
            for index, case in enumerate(case_set["cases"])
        }
        for future in as_completed(futures):
            index, case = futures[future]
            result = future.result()
            indexed_results[index] = result
            print(f"{case['group']} {case['case_id']}: {'SOLVED' if result['solved'] else result['abort_reason']}", flush=True)
    results = [indexed_results[index] for index in range(len(case_set["cases"]))]
    spend = sum(float(item["usage"].get("cost_usd") or 0) for item in results)
    groups = {}
    for group in ("rescued", "control"):
        group_results = [item for item in results if item["group"] == group]
        attempted = [item for item in group_results if item["abort_reason"] != "project_spend_cap"]
        groups[group] = {
            "n": len(group_results), "attempted": len(attempted),
            "solved": sum(item["solved"] for item in attempted),
            "solve_rate": sum(item["solved"] for item in attempted) / len(attempted) if attempted else None,
        }
    json_dump(args.output, {
        "schema_version": 1, "model": DEFAULT_MODEL, "fixture_mode": args.fixture_mode,
        "single_attempt": True, "step_cap": STEP_CAP,
        "test_wall_cap_s": TEST_WALL_CAP_S, "spend_cap_usd": args.max_spend,
        "total_spend_usd": spend, "groups": groups, "results": results,
    })
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
