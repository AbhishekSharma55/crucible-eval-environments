"""Run Phase 3 B0/B1/B2 without overwriting any Phase 2 result."""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from collections import Counter
import json
from pathlib import Path
import re
import time
from typing import Any

from scripts.model_fixture import chat_completion, fixture_text, fixture_usage
from scripts.phase2_common import git, gold_patch
from scripts.phase3_common import (
    CASE_WALL_CAP_S, PHASE3, PHASE3_RESULTS, TEST_TIMEOUT_S, case_id, json_dump,
    phase3_candidate_pool, stub_authored_test,
)
from scripts.test_authoring_verifier import verify


DEFAULT_MODEL = "deepseek/deepseek-v4-flash"
TEMPERATURES = [0.0, 0.125, 0.25, 0.375, 0.5]
MAX_TOKENS = 1800
MAX_SOURCE_CHARS = 80_000
SPEND_CAP_USD = 6.0
INPUT_USD_PER_M = 0.09
OUTPUT_USD_PER_M = 0.18
SYSTEM_PROMPT = """You author missing pytest regression tests for real bug-fix commits. Return exactly one JSON object with string fields "path" and "content" and no markdown. The path must be a new file under tests/. The test must fail on the broken parent and pass on the fixed commit. Test externally observable behavior through APIs that already exist at the parent. Do not import, access, or assert the existence of identifiers introduced by the patch. Do not modify source, inspect files at runtime, invoke git, compare versions or source text, use unconditional failures, or weaken or skip the test. Keep the test focused and self-contained using only dependencies visible in the supplied source and metadata."""


def parent_source(candidate: dict[str, Any]) -> str:
    chunks = []
    used = 0
    for path in candidate["source_files"]:
        shown = git(candidate["repo"], "show", f"{candidate['parent_sha']}:{path}", check=False)
        if shown.returncode:
            continue
        chunk = f"\n--- {path} ---\n{shown.stdout}"
        remaining = MAX_SOURCE_CHARS - used
        if remaining <= 0:
            break
        chunks.append(chunk[:remaining])
        used += min(len(chunk), remaining)
    return "".join(chunks)


def user_prompt(candidate: dict[str, Any], patch: str) -> str:
    issues = "\n\n".join(
        f"Issue #{item['number']}:\n{item.get('body') or '(empty)'}" for item in candidate["linked_issues"]
    )
    return f"""Linked issue text:
{issues}

PR title:
{candidate['title']}

PR body:
{candidate.get('body') or '(empty)'}

Gold patch:
{patch}

Relevant source files at the broken parent:
{parent_source(candidate)}
"""


def request_payload(candidate: dict[str, Any], patch: str, temperature: float) -> dict[str, Any]:
    return {
        "model": DEFAULT_MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt(candidate, patch)},
        ],
        "temperature": temperature,
        "max_tokens": MAX_TOKENS,
        "reasoning": {"enabled": False},
    }


def parse_authored_test(text: str) -> tuple[dict[str, Any], dict[str, Any]]:
    raw = text.strip()
    fenced = re.fullmatch(r"```(?:json)?\s*(.*?)```", raw, re.DOTALL)
    if fenced:
        raw = fenced.group(1).strip()
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as exc:
        return {}, {"status": "fail", "reason": "invalid_json", "detail": str(exc)}
    if not isinstance(parsed, dict):
        return {}, {"status": "fail", "reason": "json_root_not_object"}
    authored = {"path": parsed.get("path"), "content": parsed.get("content")}
    valid = isinstance(authored["path"], str) and isinstance(authored["content"], str)
    return authored, {"status": "pass" if valid else "fail", "reason": None if valid else "missing_string_path_or_content"}


def model_attempt(candidate: dict[str, Any], patch: str, temperature: float, mode: str) -> dict[str, Any]:
    fixture = chat_completion(request_payload(candidate, patch, temperature), mode=mode)
    usage = fixture_usage(fixture)
    try:
        text = fixture_text(fixture)
    except RuntimeError as exc:
        return {
            "temperature": temperature, "raw_output": None, "authored_test": {},
            "parse": {"status": "fail", "reason": "model_error", "detail": str(exc)},
            "usage": usage,
        }
    authored, parse = parse_authored_test(text)
    return {
        "temperature": temperature, "raw_output": text, "authored_test": authored,
        "parse": parse, "usage": usage,
    }


def empty_verification(parse: dict[str, Any]) -> dict[str, Any]:
    return {
        "passed": False, "abort_reason": "model_output_parse_failed", "parse": parse,
        "gates": {name: {"status": "skipped", "reason": "model_output_parse_failed", "evidence": {}} for name in ("g1", "g2", "g3", "g4", "g5")},
        "wall_s": 0,
    }


def usage_total(attempts: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        key: sum(float(item["usage"].get(key) or 0) for item in attempts)
        for key in ("prompt_tokens", "completion_tokens", "total_tokens", "cost_usd", "latency_s")
    }


def run_case(baseline: str, candidate: dict[str, Any], mode: str, image: str, timeout_s: int, case_cap_s: int) -> dict[str, Any]:
    started = time.monotonic()
    attempts: list[dict[str, Any]] = []
    accepted = None
    abort_reason = None
    patch = gold_patch(candidate, unified=3)
    temperatures = [] if baseline == "b0" else ([0.0] if baseline == "b1" else TEMPERATURES)
    if baseline == "b0":
        authored = stub_authored_test(candidate)
        verification = verify(
            candidate, authored, image=image, timeout_s=timeout_s,
            wall_cap_s=max(1, case_cap_s - (time.monotonic() - started)),
        )
        attempts.append({
            "temperature": None, "raw_output": None, "authored_test": authored,
            "parse": {"status": "pass", "reason": None}, "verification": verification,
            "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0, "cost_usd": 0.0, "latency_s": 0.0},
        })
        if verification["passed"]:
            accepted = 0
    else:
        for temperature in temperatures:
            if time.monotonic() - started >= case_cap_s:
                abort_reason = "case_wall_clock_exceeded"
                break
            attempt = model_attempt(candidate, patch, temperature, mode)
            if attempt["parse"]["status"] == "pass":
                attempt["verification"] = verify(
                    candidate, attempt["authored_test"], image=image, timeout_s=timeout_s,
                    wall_cap_s=max(1, case_cap_s - (time.monotonic() - started)),
                )
            else:
                attempt["verification"] = empty_verification(attempt["parse"])
            attempts.append(attempt)
            if attempt["verification"]["passed"]:
                accepted = len(attempts) - 1
                break
    final = attempts[accepted if accepted is not None else -1]
    return {
        "case_id": case_id(candidate), "repo": candidate["repo"], "pr_number": candidate["pr_number"],
        "passed": accepted is not None, "accepted_attempt_index": accepted,
        "abort_reason": abort_reason, "authored_test": final["authored_test"],
        "verification": final["verification"], "attempts": attempts,
        "usage": usage_total(attempts), "wall_s": round(time.monotonic() - started, 3),
    }


def first_failure(result: dict[str, Any]) -> str:
    verification = result["verification"]
    if verification.get("abort_reason") == "model_output_parse_failed":
        return "OUTPUT_PARSE"
    return next(
        (name.upper() for name in ("g1", "g2", "g3", "g4", "g5") if verification["gates"][name]["status"] == "fail"),
        "CASE_CAP" if result.get("abort_reason") else "NONE",
    )


def load_cases(raw_pool: bool, case_set: Path | None = None) -> tuple[list[dict[str, Any]], int | None]:
    if raw_pool:
        return sorted(phase3_candidate_pool(), key=case_id), None
    path = case_set or (PHASE3 / "case-set.json")
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload["cases"], payload["seed"]


def preflight(candidates: list[dict[str, Any]], baselines: tuple[str, ...]) -> float:
    requests = {}
    for baseline in baselines:
        if baseline == "b0":
            continue
        temperatures = [0.0] if baseline == "b1" else TEMPERATURES
        for candidate in candidates:
            patch = gold_patch(candidate, unified=3)
            for temperature in temperatures:
                payload = request_payload(candidate, patch, temperature)
                requests[json.dumps(payload, sort_keys=True, separators=(",", ":"))] = payload
    estimated_input = sum(len(key) / 3 for key in requests)
    return estimated_input * INPUT_USD_PER_M / 1_000_000 + len(requests) * MAX_TOKENS * OUTPUT_USD_PER_M / 1_000_000


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("baseline", choices=("b0", "b1", "b2", "all"))
    parser.add_argument("--fixture-mode", choices=("replay", "record"), default="replay")
    parser.add_argument("--image", default="crucible-sandbox:phase3")
    parser.add_argument("--workers", type=int, default=6)
    parser.add_argument("--timeout", type=int, default=TEST_TIMEOUT_S)
    parser.add_argument("--case-cap", type=int, default=CASE_WALL_CAP_S)
    parser.add_argument("--raw-pool", action="store_true", help="only for the pre-case-set B0 null check")
    parser.add_argument("--case-set", type=Path, help="explicit fixed case set (used for held-out evaluation)")
    parser.add_argument("--results-dir", type=Path, default=PHASE3_RESULTS)
    parser.add_argument("--phase", type=int, default=3)
    args = parser.parse_args()
    baselines = ("b0", "b1", "b2") if args.baseline == "all" else (args.baseline,)
    if args.raw_pool and baselines != ("b0",):
        raise RuntimeError("raw-pool mode is restricted to B0")
    if args.raw_pool and args.case_set is not None:
        raise RuntimeError("--raw-pool and --case-set are mutually exclusive")
    candidates, seed = load_cases(args.raw_pool, args.case_set)
    estimate = preflight(candidates, baselines)
    if estimate > SPEND_CAP_USD:
        raise RuntimeError(f"baseline preflight estimate ${estimate:.2f} exceeds ${SPEND_CAP_USD:.2f} cap")
    for baseline in baselines:
        started = time.monotonic()
        indexed = {}
        with ThreadPoolExecutor(max_workers=args.workers) as pool:
            futures = {
                pool.submit(run_case, baseline, item, args.fixture_mode, args.image, args.timeout, args.case_cap): index
                for index, item in enumerate(candidates)
            }
            for future in as_completed(futures):
                index = futures[future]
                indexed[index] = future.result()
                result = indexed[index]
                print(f"{baseline.upper()} {result['case_id']}: {'PASS' if result['passed'] else first_failure(result)}", flush=True)
        results = [indexed[index] for index in range(len(candidates))]
        passed = sum(item["passed"] for item in results)
        breakdown = Counter(first_failure(item) for item in results if not item["passed"])
        totals = {
            key: sum(float(item["usage"].get(key) or 0) for item in results)
            for key in ("prompt_tokens", "completion_tokens", "total_tokens", "cost_usd", "latency_s")
        }
        wall = round(time.monotonic() - started, 3)
        payload = {
            "schema_version": 1, "phase": args.phase, "baseline": baseline.upper(),
            "model": None if baseline == "b0" else DEFAULT_MODEL, "fixture_mode": args.fixture_mode,
            "case_set_seed": seed, "n": len(results), "verified_count": passed,
            "verified_rate": passed / len(results) if results else 0.0,
            "first_failure_breakdown": dict(sorted(breakdown.items())),
            "totals": totals, "cost_per_candidate_usd": totals["cost_usd"] / len(results) if results else 0,
            "model_latency_per_candidate_s": totals["latency_s"] / len(results) if results else 0,
            "wall_clock_s": wall, "wall_clock_per_candidate_s": wall / len(results) if results else 0,
            "limits": {"per_test_run_s": args.timeout, "per_case_wall_s": args.case_cap, "workers": args.workers},
            "results": results,
        }
        name = "b0-preflight" if args.raw_pool else baseline
        json_dump(args.results_dir / f"{name}.json", payload)
        print(f"{baseline.upper()}: {passed}/{len(results)} ({payload['verified_rate']:.1%}); ${totals['cost_usd']:.6f}; wall={wall:.1f}s")
        if args.raw_pool and passed:
            return 3
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
