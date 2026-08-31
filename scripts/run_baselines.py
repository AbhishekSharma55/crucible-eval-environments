"""Run B0/B1/B2 problem-statement baselines on the committed case set."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from scripts.leakage_detector import detect_leakage
from scripts.model_fixture import chat_completion, fixture_text, fixture_usage
from scripts.phase2_common import PHASE2, case_id, gold_patch, json_dump, load_case_set


DEFAULT_MODEL = "deepseek/deepseek-v4-flash"
TEMPERATURES = [0.0, 0.125, 0.25, 0.375, 0.5]
SPEND_CAP_USD = 6.0
# Conservative preflight rates for the pinned model. Actual charged cost from
# every response remains authoritative and is stored in the fixture.
INPUT_USD_PER_M = 0.09
OUTPUT_USD_PER_M = 0.18
SYSTEM_PROMPT = """You write software bug reports. Given a pull request title, body, and patch, write a concise problem statement that describes only the externally observable bug or missing behavior. Do not reveal the implementation, new identifiers, exact code, patch syntax, file-and-line locations, or instructions for how to fix it. Return only the problem statement."""


def user_prompt(candidate: dict[str, Any], patch: str) -> str:
    return f"""PR title:
{candidate['title']}

PR body:
{candidate.get('body') or '(empty)'}

Gold patch (use only to infer the symptom; do not quote or describe the fix):
{patch}
"""


def request_payload(candidate: dict[str, Any], patch: str, model: str, temperature: float) -> dict[str, Any]:
    return {
        "model": model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt(candidate, patch)},
        ],
        "temperature": temperature,
        "max_tokens": 300,
        "reasoning": {"enabled": False},
    }


def _call(candidate: dict[str, Any], patch: str, model: str, temperature: float, mode: str) -> dict[str, Any]:
    fixture = chat_completion(request_payload(candidate, patch, model, temperature), mode=mode)
    return {"problem_statement": fixture_text(fixture), "usage": fixture_usage(fixture), "temperature": temperature}


def run_one(baseline: str, candidate: dict[str, Any], model: str, mode: str) -> dict[str, Any]:
    patch = gold_patch(candidate, unified=3)
    detector_patch = gold_patch(candidate, unified=0)
    attempts: list[dict[str, Any]] = []
    if baseline == "b0":
        statement = candidate["title"]
    elif baseline == "b1":
        attempt = _call(candidate, patch, model, 0.0, mode)
        attempts.append(attempt)
        statement = attempt["problem_statement"]
    else:
        statement = ""
        for temperature in TEMPERATURES:
            attempt = _call(candidate, patch, model, temperature, mode)
            attempt["leakage"] = detect_leakage(candidate, attempt["problem_statement"], patch=detector_patch)
            attempts.append(attempt)
            statement = attempt["problem_statement"]
            if attempt["leakage"]["verdict"] == "leak_free":
                break
    leakage = detect_leakage(candidate, statement, patch=detector_patch)
    usage = {
        "prompt_tokens": sum(item["usage"]["prompt_tokens"] for item in attempts),
        "completion_tokens": sum(item["usage"]["completion_tokens"] for item in attempts),
        "total_tokens": sum(item["usage"]["total_tokens"] for item in attempts),
        "cost_usd": sum(item["usage"]["cost_usd"] for item in attempts),
        "latency_s": sum(item["usage"]["latency_s"] for item in attempts),
    }
    return {
        "case_id": case_id(candidate), "repo": candidate["repo"], "pr_number": candidate["pr_number"],
        "problem_statement": statement, "leakage": leakage, "attempts": attempts,
        "validation": {"valid_transition": True, "transition_kind": candidate["validation"]["transition_kind"]},
        "usage": usage,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("baseline", choices=("b0", "b1", "b2", "all"))
    parser.add_argument("--case-set", type=Path)
    parser.add_argument("--fixture-mode", choices=("replay", "record"), default="replay")
    args = parser.parse_args()
    baselines = ("b0", "b1", "b2") if args.baseline == "all" else (args.baseline,)
    case_set = load_case_set(args.case_set)
    planned: dict[str, dict[str, Any]] = {}
    for baseline in baselines:
        if baseline == "b0":
            continue
        temperatures = [0.0] if baseline == "b1" else TEMPERATURES
        for candidate in case_set["cases"]:
            patch = gold_patch(candidate, unified=3)
            for temperature in temperatures:
                request = request_payload(candidate, patch, DEFAULT_MODEL, temperature)
                key = json.dumps(request, sort_keys=True, separators=(",", ":"))
                planned[key] = request
    conservative_input_tokens = sum(len(key) / 3 for key in planned)
    worst_case_cost = (
        conservative_input_tokens * INPUT_USD_PER_M / 1_000_000
        + len(planned) * 300 * OUTPUT_USD_PER_M / 1_000_000
    )
    if worst_case_cost > SPEND_CAP_USD:
        raise RuntimeError(
            f"baseline preflight upper estimate ${worst_case_cost:.2f} exceeds ${SPEND_CAP_USD:.2f} cap"
        )
    for baseline in baselines:
        results = [run_one(baseline, candidate, DEFAULT_MODEL, args.fixture_mode) for candidate in case_set["cases"]]
        clean = sum(item["leakage"]["verdict"] == "leak_free" for item in results)
        payload = {
            "schema_version": 1, "baseline": baseline.upper(), "model": None if baseline == "b0" else DEFAULT_MODEL,
            "fixture_mode": args.fixture_mode, "case_set_seed": case_set["seed"], "n": len(results),
            "leak_free_validated_rescue_count": clean,
            "leak_free_validated_rescue_rate": clean / len(results) if results else 0,
            "totals": {
                "cost_usd": sum(item["usage"]["cost_usd"] for item in results),
                "latency_s": sum(item["usage"]["latency_s"] for item in results),
                "prompt_tokens": sum(item["usage"]["prompt_tokens"] for item in results),
                "completion_tokens": sum(item["usage"]["completion_tokens"] for item in results),
            },
            "results": results,
        }
        json_dump(Path("results") / f"{baseline}.json", payload)
        print(f"{baseline.upper()}: {clean}/{len(results)} leak-free; ${payload['totals']['cost_usd']:.4f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
