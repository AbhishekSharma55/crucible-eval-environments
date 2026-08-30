"""Cache repeated fail-to-pass checks for statically eligible dev candidates."""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import json
from pathlib import Path
from typing import Any

from scripts.harvest import ROOT, build_candidate, cached_prs, static_reason
from scripts.run_tests import run_tests


def compact(result: dict[str, Any]) -> dict[str, Any]:
    return {
        "exit_code": result["exit_code"],
        "stage": result.get("stage"),
        "duration_s": result.get("duration_s"),
        "outcomes": {item["nodeid"]: item["outcome"] for item in result.get("per_test_status", [])},
        "stdout_tail": result.get("stdout", "")[-2000:],
        "stderr_tail": result.get("stderr", "")[-2000:],
    }


def fingerprint(result: dict[str, Any]) -> tuple[int, str | None, tuple[tuple[str, str], ...]]:
    return result["exit_code"], result.get("stage"), tuple(sorted(result["outcomes"].items()))


def transition_tests(parent: dict[str, Any], fix: dict[str, Any]) -> list[dict[str, str]]:
    """Return exact and collection-error tests that become passing."""
    changed: list[dict[str, str]] = []
    parent_outcomes = parent["outcomes"]
    fix_outcomes = fix["outcomes"]
    for nodeid, outcome in sorted(parent_outcomes.items()):
        if outcome in {"failed", "error"} and fix_outcomes.get(nodeid) == "passed":
            changed.append({"nodeid": nodeid, "parent": outcome, "fix": "passed"})
        if nodeid.startswith("collection::") and outcome == "error":
            path = nodeid.removeprefix("collection::")
            for fix_nodeid, fix_outcome in sorted(fix_outcomes.items()):
                if fix_outcome == "passed" and (fix_nodeid == path or fix_nodeid.startswith(f"{path}::")):
                    changed.append({"nodeid": fix_nodeid, "parent": "error", "fix": "passed"})
    return changed


def passing_regressed(parent: dict[str, Any], fix: dict[str, Any]) -> list[str]:
    return sorted(
        nodeid
        for nodeid, outcome in parent["outcomes"].items()
        if outcome == "passed" and fix["outcomes"].get(nodeid) != "passed"
    )


def validate(candidate: dict[str, Any], image: str) -> dict[str, Any]:
    selector = candidate["test_files"]
    parent_runs = [
        compact(
            run_tests(
                candidate["repo"],
                candidate["parent_sha"],
                selector,
                image=image,
                test_patch_from=candidate["merge_commit_sha"],
            )
        )
        for _ in range(2)
    ]
    fix_runs = [compact(run_tests(candidate["repo"], candidate["merge_commit_sha"], selector, image=image)) for _ in range(2)]
    reason = None
    note = None
    transitions: list[dict[str, str]] = []
    regressions: list[str] = []
    if any(run["stage"] in {"test_patch_apply", "test_patch_build"} for run in parent_runs):
        reason = "test_patch_does_not_apply"
        note = "test-only patch could not be built from cached commits or applied cleanly at the parent"
    elif any(run["stage"] == "build" and run["exit_code"] != 0 for run in parent_runs):
        reason = "repo_fails_to_build_at_parent"
    elif fingerprint(parent_runs[0]) != fingerprint(parent_runs[1]) or fingerprint(fix_runs[0]) != fingerprint(fix_runs[1]):
        reason = "nondeterministic_test_outcome"
    elif any(run["exit_code"] != 0 for run in fix_runs):
        reason = "tests_no_clean_fail_to_pass"
        note = "changed tests do not pass at the merge commit"
    elif any(run["exit_code"] == 0 for run in parent_runs):
        reason = "tests_no_clean_fail_to_pass"
        note = "selected tests also pass with the transplanted test patch at the parent commit"
    else:
        transitions = transition_tests(parent_runs[0], fix_runs[0])
        regressions = passing_regressed(parent_runs[0], fix_runs[0])
    if reason is None and regressions:
        reason = "tests_no_clean_fail_to_pass"
        note = "a test that passed at the parent did not remain passing at the fix"
    elif reason is None and not transitions:
        reason = "tests_no_clean_fail_to_pass"
        note = "no failing or erroring test at the parent became passing at the fix"
    return {
        "schema_version": 2,
        "repo": candidate["repo"],
        "pr_number": candidate["pr_number"],
        "test_selector": selector,
        "parent_sha": candidate["parent_sha"],
        "merge_commit_sha": candidate["merge_commit_sha"],
        "runs": {"parent": parent_runs, "fix": fix_runs},
        "transition_tests": transitions,
        "previously_passing_regressions": regressions,
        "rejection_reason": reason,
        "note": note,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--image", default="crucible-sandbox:phase1")
    parser.add_argument("--workers", type=int, default=3)
    parser.add_argument("--repo", action="append")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    corpus = json.loads((ROOT / "config/repos.json").read_text(encoding="utf-8"))
    split = json.loads((ROOT / "config/split.json").read_text(encoding="utf-8"))["assignment"]
    requested = set(args.repo or [])
    jobs: list[dict[str, Any]] = []
    for item in corpus["repos"]:
        repo = item["repo"]
        if item["status"] != "accepted" or (requested and repo not in requested):
            continue
        if split[repo] == "heldout":
            print(f"skipping held-out repo {repo}")
            continue
        for pr in cached_prs(repo):
            candidate = build_candidate(repo, pr, bucket=split[repo])
            if static_reason(candidate)[0] is None:
                output = ROOT / "data/validation" / repo.replace("/", "--") / f"pr-{candidate['pr_number']}.json"
                if args.force or not output.exists():
                    candidate["_output"] = output
                    jobs.append(candidate)
    print(f"validating {len(jobs)} statically eligible candidates")
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        future_jobs = {pool.submit(validate, candidate, args.image): candidate for candidate in jobs}
        for future in as_completed(future_jobs):
            candidate = future_jobs[future]
            result = future.result()
            output = candidate["_output"]
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
            status = "accepted" if result["rejection_reason"] is None else result["rejection_reason"]
            print(f"{candidate['repo']}#{candidate['pr_number']}: {status}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
