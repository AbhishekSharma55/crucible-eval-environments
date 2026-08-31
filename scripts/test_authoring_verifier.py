"""Sequential G1-G5 verifier for Phase 3 authored regression tests."""

from __future__ import annotations

import re
import time
from typing import Any

from scripts.leakage_detector import extract_added_identifiers, genuinely_new_identifiers
from scripts.phase2_common import gold_patch
from scripts.phase3_common import (
    changed_fix_lines, compact_run, fingerprint, run_phase3_test, validate_authored_test,
)


ANTI_CHEAT_EXCEPTIONS = ("ImportError", "AttributeError", "NameError", "ModuleNotFoundError")
EXCEPTION = re.compile(r"\b(ImportError|AttributeError|NameError|ModuleNotFoundError):\s*([^\n]+)")


def skipped(reason: str) -> dict[str, Any]:
    return {"status": "skipped", "reason": reason, "evidence": {}}


def gate3(candidate: dict[str, Any], parent_run: dict[str, Any], *, patch: str | None = None) -> dict[str, Any]:
    """Reject only missing-symbol failures that refer to a gold-introduced symbol."""
    text = "\n".join((parent_run.get("stdout_tail", ""), parent_run.get("stderr_tail", "")))
    failures = [{"exception": match.group(1), "message": match.group(2).strip()} for match in EXCEPTION.finditer(text)]
    patch = gold_patch(candidate, unified=0) if patch is None else patch
    introduced = genuinely_new_identifiers(candidate, extract_added_identifiers(candidate, patch))
    matches = []
    for failure in failures:
        for item in introduced:
            names = {item.name}
            if item.kind == "new_file_path":
                names.update({item.name.removesuffix(".py").replace("/", "."), item.name.rsplit("/", 1)[-1].removesuffix(".py")})
            if any(re.search(rf"(?<!\w){re.escape(name)}(?!\w)", failure["message"]) for name in names if name):
                matches.append({**failure, "introduced_symbol": item.name, "symbol_kind": item.kind, "gold_path": item.path})
    return {
        "status": "fail" if matches else "pass",
        "reason": "parent_failure_depends_on_gold_introduced_symbol" if matches else None,
        "evidence": {
            "anti_cheat_exception_types": list(ANTI_CHEAT_EXCEPTIONS),
            "parent_exceptions": failures, "introduced_symbols": [item.__dict__ for item in introduced],
            "matches": matches,
        },
    }


def gate1(parent_runs: list[dict[str, Any]]) -> dict[str, Any]:
    deterministic = len(parent_runs) == 2 and fingerprint(parent_runs[0]) == fingerprint(parent_runs[1])
    passed = deterministic and all(run["stage"] == "test" and run["exit_code"] != 0 for run in parent_runs)
    return {
        "status": "pass" if passed else "fail",
        "reason": None if passed else ("nondeterministic_parent" if not deterministic else "authored_test_did_not_fail_at_parent"),
        "evidence": {"deterministic": deterministic, "runs": parent_runs},
    }


def gate2(fix_runs: list[dict[str, Any]]) -> dict[str, Any]:
    deterministic = len(fix_runs) == 2 and fingerprint(fix_runs[0]) == fingerprint(fix_runs[1])
    passed = deterministic and all(run["stage"] == "test" and run["exit_code"] == 0 for run in fix_runs)
    return {
        "status": "pass" if passed else "fail",
        "reason": None if passed else ("nondeterministic_fix" if not deterministic else "authored_test_did_not_pass_at_fix"),
        "evidence": {"deterministic": deterministic, "runs": fix_runs},
    }


def gate4(candidate: dict[str, Any], coverage_run: dict[str, Any]) -> dict[str, Any]:
    changed = (
        candidate.get("phase3_prevalidation", {}).get("static", {}).get("changed_fix_lines")
        or changed_fix_lines(candidate)
    )
    executed = coverage_run.get("coverage", {})
    covered: dict[str, list[int]] = {}
    for path, lines in changed.items():
        hits = sorted(set(lines).intersection(executed.get(path, [])))
        if hits:
            covered[path] = hits
    total = sum(len(lines) for lines in changed.values())
    covered_total = sum(len(lines) for lines in covered.values())
    passed = coverage_run.get("stage") == "test" and coverage_run.get("exit_code") == 0 and covered_total > 0
    return {
        "status": "pass" if passed else "fail",
        "reason": None if passed else ("coverage_run_failed" if coverage_run.get("exit_code") != 0 else "no_gold_changed_line_executed"),
        "evidence": {
            "changed_lines": changed, "covered_changed_lines": covered,
            "changed_line_count": total, "covered_changed_line_count": covered_total,
            "changed_line_fraction": covered_total / total if total else 0.0,
            "coverage_run": coverage_run,
        },
    }


def gate5(candidate: dict[str, Any], patch_boundary: dict[str, Any]) -> dict[str, Any]:
    prevalidation = candidate.get("phase3_prevalidation") or {}
    endpoint_runs = prevalidation.get("endpoint_runs") or {}
    endpoint_evidence = {}
    controls_pass = True
    for endpoint in ("parent", "fix"):
        runs = endpoint_runs.get(endpoint) or []
        deterministic = len(runs) == 2 and fingerprint(runs[0]) == fingerprint(runs[1])
        passed = deterministic and all(run.get("stage") == "test" and run.get("exit_code") == 0 for run in runs)
        controls_pass &= passed
        endpoint_evidence[endpoint] = {"deterministic": deterministic, "passed": passed, "runs": runs}
    patch_pass = patch_boundary.get("status") == "pass"
    passed = patch_pass and controls_pass and prevalidation.get("rejection_reason") is None
    return {
        "status": "pass" if passed else "fail",
        "reason": None if passed else ("authored_patch_modified_non_test_or_existing_file" if not patch_pass else "existing_endpoint_controls_not_clean"),
        "evidence": {
            "authored_patch_boundary": patch_boundary,
            "selected_existing_tests": prevalidation.get("existing_test_selectors", []),
            "endpoints": endpoint_evidence,
        },
    }


def verify(
    candidate: dict[str, Any], authored: dict[str, Any], *, image: str = "crucible-sandbox:phase1",
    timeout_s: int = 60, wall_cap_s: float | None = None,
) -> dict[str, Any]:
    started = time.monotonic()

    def execute(endpoint: str, *, coverage: bool = False) -> dict[str, Any]:
        remaining = None if wall_cap_s is None else wall_cap_s - (time.monotonic() - started)
        if remaining is not None and remaining <= 0:
            return compact_run({
                "endpoint": endpoint, "commit": candidate["parent_sha"] if endpoint == "parent" else candidate["merge_commit_sha"],
                "exit_code": 124, "stage": "case_wall_clock_exceeded", "duration_s": 0,
                "per_test_status": [], "stdout": "", "stderr": "", "coverage": {},
            })
        run_timeout = timeout_s if remaining is None else max(1, min(timeout_s, int(remaining)))
        return compact_run(run_phase3_test(
            candidate, authored, endpoint, coverage=coverage, image=image, timeout_s=run_timeout
        ))

    patch_boundary = validate_authored_test(candidate, authored)
    gates = {name: skipped("not_reached") for name in ("g1", "g2", "g3", "g4", "g5")}
    if patch_boundary["status"] != "pass":
        gates["g5"] = {"status": "fail", "reason": "authored_patch_boundary", "evidence": patch_boundary}
        return {"passed": False, "gates": gates, "patch_boundary": patch_boundary, "wall_s": round(time.monotonic() - started, 3)}

    parent_runs = [execute("parent") for _ in range(2)]
    gates["g1"] = gate1(parent_runs)
    if gates["g1"]["status"] != "pass":
        return {"passed": False, "gates": gates, "patch_boundary": patch_boundary, "wall_s": round(time.monotonic() - started, 3)}

    fix_runs = [execute("fix") for _ in range(2)]
    gates["g2"] = gate2(fix_runs)
    gates["g3"] = gate3(candidate, parent_runs[0])
    if gates["g2"]["status"] != "pass" or gates["g3"]["status"] != "pass":
        return {"passed": False, "gates": gates, "patch_boundary": patch_boundary, "wall_s": round(time.monotonic() - started, 3)}

    coverage_run = execute("fix", coverage=True)
    gates["g4"] = gate4(candidate, coverage_run)
    gates["g5"] = gate5(candidate, patch_boundary)
    passed = all(gates[name]["status"] == "pass" for name in ("g1", "g2", "g3", "g4", "g5"))
    return {"passed": passed, "gates": gates, "patch_boundary": patch_boundary, "wall_s": round(time.monotonic() - started, 3)}
