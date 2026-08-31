"""Single JSON-emitting entrypoint for hermetic test execution."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time


CONFIG = Path("/opt/crucible/config/repos.json")


def slug(name: str) -> str:
    return name.replace("/", "--")


def invoke(args: list[str], cwd: Path, env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, cwd=cwd, env=env, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)


def build_patch(checkout: Path, parent: str, fix: str, paths: list[str]) -> subprocess.CompletedProcess[bytes]:
    """Build one path-partitioned PR patch entirely from the cached git mirror."""
    return subprocess.run(
        ["git", "diff", "--binary", "--no-ext-diff", parent, fix, "--", *paths],
        cwd=checkout,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


def apply_patch(checkout: Path, patch: bytes) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(
        ["git", "apply", "--whitespace=nowarn", "-"],
        cwd=checkout,
        input=patch,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


def apply_solution_patch(checkout: Path, patch: bytes) -> subprocess.CompletedProcess[bytes]:
    """Apply common unified-diff variants without changing proposed content."""
    text = patch.decode(errors="replace")
    headers = [line for line in text.splitlines() if line.startswith(("--- ", "+++ "))]
    prefixed = any(line.startswith(("--- a/", "+++ b/")) for line in headers)
    command = ["git", "apply", "--whitespace=nowarn", "--recount"]
    if headers and not prefixed:
        command.extend(["-p", "0"])
    command.append("-")
    return subprocess.run(command, cwd=checkout, input=patch, stdout=subprocess.PIPE, stderr=subprocess.PIPE)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run pytest at a historical commit")
    parser.add_argument("repo")
    parser.add_argument("commit")
    parser.add_argument("test_selector", nargs="*", help="pytest node IDs or paths")
    parser.add_argument("--test-patch-from", help="fix commit used to build and transplant the selected test-only patch")
    parser.add_argument("--solution-patch", help="solver-produced patch file to apply after the test transplant")
    args = parser.parse_args()

    config = json.loads(CONFIG.read_text(encoding="utf-8"))
    repos = {item["repo"]: item for item in config["repos"] if item["status"] in {"accepted", "probe"}}
    if args.repo not in repos:
        print(json.dumps({"error": f"repo is not in the active corpus: {args.repo}"}, sort_keys=True))
        return 2

    item = repos[args.repo]
    name = slug(args.repo)
    mirror = Path("/opt/repos") / f"{name}.git"
    revision = "old" if args.commit == item["old_commit"] else "head"
    python = Path("/opt/venvs") / f"{name}--{revision}" / "bin/python"
    started = time.monotonic()
    with tempfile.TemporaryDirectory(prefix="crucible-") as raw_tmp:
        tmp = Path(raw_tmp)
        checkout = tmp / "repo"
        status_file = tmp / "status.json"
        clone = invoke(["git", "clone", "--quiet", str(mirror), str(checkout)], tmp, os.environ.copy())
        if clone.returncode:
            print(json.dumps({"exit_code": clone.returncode, "stdout": clone.stdout, "stderr": clone.stderr, "duration_s": time.monotonic() - started, "per_test_status": []}, sort_keys=True))
            return clone.returncode
        checkout_result = invoke(["git", "checkout", "--quiet", "--detach", args.commit], checkout, os.environ.copy())
        if checkout_result.returncode:
            print(json.dumps({"exit_code": checkout_result.returncode, "stdout": checkout_result.stdout, "stderr": checkout_result.stderr, "duration_s": time.monotonic() - started, "per_test_status": []}, sort_keys=True))
            return checkout_result.returncode

        if args.test_patch_from:
            patch_result = build_patch(checkout, args.commit, args.test_patch_from, args.test_selector)
            if patch_result.returncode:
                print(json.dumps({
                    "repo": args.repo,
                    "commit": args.commit,
                    "exit_code": patch_result.returncode,
                    "stdout": patch_result.stdout.decode(errors="replace"),
                    "stderr": patch_result.stderr.decode(errors="replace"),
                    "duration_s": round(time.monotonic() - started, 3),
                    "per_test_status": [],
                    "stage": "test_patch_build",
                }, sort_keys=True))
                return patch_result.returncode
            applied = apply_patch(checkout, patch_result.stdout)
            if applied.returncode:
                print(json.dumps({
                    "repo": args.repo,
                    "commit": args.commit,
                    "exit_code": applied.returncode,
                    "stdout": applied.stdout.decode(errors="replace"),
                    "stderr": applied.stderr.decode(errors="replace"),
                    "duration_s": round(time.monotonic() - started, 3),
                    "per_test_status": [],
                    "stage": "test_patch_apply",
                }, sort_keys=True))
                return applied.returncode

        if args.solution_patch:
            solution = Path(args.solution_patch).read_bytes()
            applied = apply_solution_patch(checkout, solution)
            if applied.returncode:
                print(json.dumps({
                    "repo": args.repo,
                    "commit": args.commit,
                    "exit_code": applied.returncode,
                    "stdout": applied.stdout.decode(errors="replace"),
                    "stderr": applied.stderr.decode(errors="replace"),
                    "duration_s": round(time.monotonic() - started, 3),
                    "per_test_status": [],
                    "stage": "solution_patch_apply",
                }, sort_keys=True))
                return applied.returncode

        env = os.environ.copy()
        env.update({
            "PATH": f"{python.parent}:{env.get('PATH', '')}",
            "PYTHONHASHSEED": "0",
            "PYTHONPATH": f"/opt/crucible/sandbox:{env.get('PYTHONPATH', '')}",
            "CRUCIBLE_STATUS_FILE": str(status_file),
        })
        install = [str(python) if part == "python" else part for part in item["install_command"]]
        installed = invoke(install, checkout, env)
        if installed.returncode:
            print(json.dumps({"exit_code": installed.returncode, "stdout": installed.stdout, "stderr": installed.stderr, "duration_s": time.monotonic() - started, "per_test_status": [], "stage": "build"}, sort_keys=True))
            return installed.returncode

        test = [str(python) if part == "python" else part for part in item["test_command"]]
        test.extend(["-p", "pytest_status"])
        test.extend(args.test_selector)
        result = invoke(test, checkout, env)
        statuses = []
        if status_file.exists():
            statuses = json.loads(status_file.read_text(encoding="utf-8"))["tests"]
        payload = {
            "repo": args.repo,
            "commit": args.commit,
            "test_selector": args.test_selector,
            "exit_code": result.returncode,
            "stdout": result.stdout,
            "stderr": installed.stderr + result.stderr,
            "duration_s": round(time.monotonic() - started, 3),
            "per_test_status": statuses,
            "stage": "test",
        }
        print(json.dumps(payload, sort_keys=True))
        return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
