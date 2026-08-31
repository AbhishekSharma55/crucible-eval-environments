"""Isolated JSON runner for authored tests and stdlib-only line coverage."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path, PurePosixPath
import subprocess
import tempfile
import time


CONFIG = Path("/opt/crucible/config/repos.json")


def invoke(args: list[str], cwd: Path, env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, cwd=cwd, env=env, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)


def emit(payload: dict) -> int:
    print(json.dumps(payload, sort_keys=True))
    return int(payload.get("exit_code") or 0)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("repo")
    parser.add_argument("commit")
    parser.add_argument("selectors", nargs="*")
    parser.add_argument("--authored")
    parser.add_argument("--coverage", action="store_true")
    parser.add_argument("--build-only", action="store_true")
    args = parser.parse_intermixed_args()
    config = json.loads(CONFIG.read_text(encoding="utf-8"))
    repos = {item["repo"]: item for item in config["repos"] if item["status"] == "accepted"}
    if args.repo not in repos:
        return emit({"exit_code": 2, "stage": "config", "error": "repo is not active"})
    item = repos[args.repo]
    slug = args.repo.replace("/", "--")
    mirror = Path("/opt/repos") / f"{slug}.git"
    older_than_probe = subprocess.run(
        ["git", "merge-base", "--is-ancestor", args.commit, item["old_commit"]],
        cwd=mirror, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    ).returncode == 0
    revision = "old" if older_than_probe else "head"
    year = subprocess.check_output(
        ["git", "show", "-s", "--format=%ad", "--date=format:%Y", args.commit],
        cwd=mirror, text=True,
    ).strip()
    profiles = [Path("/opt/phase3-venvs") / f"{slug}--{year}"]
    if int(year) <= 2023:
        profiles.append(Path("/opt/phase3-venvs") / f"{slug}--phase3")
    profiles.append(Path("/opt/venvs") / f"{slug}--{revision}")
    venv = next(path for path in profiles if path.is_dir())
    python = venv / "bin/python"
    started = time.monotonic()
    with tempfile.TemporaryDirectory(prefix="crucible-phase3-") as raw_tmp:
        tmp = Path(raw_tmp)
        checkout = tmp / "repo"
        status_file = tmp / "status.json"
        coverage_file = tmp / "coverage.json"
        env = os.environ.copy()
        clone = invoke(["git", "clone", "--quiet", str(mirror), str(checkout)], tmp, env)
        if clone.returncode:
            return emit({"exit_code": clone.returncode, "stage": "clone", "stdout": clone.stdout, "stderr": clone.stderr, "duration_s": time.monotonic() - started, "per_test_status": [], "coverage": {}})
        checked = invoke(["git", "checkout", "--quiet", "--detach", args.commit], checkout, env)
        if checked.returncode:
            return emit({"exit_code": checked.returncode, "stage": "checkout", "stdout": checked.stdout, "stderr": checked.stderr, "duration_s": time.monotonic() - started, "per_test_status": [], "coverage": {}})
        authored_payload = None
        if args.authored:
            authored_payload = json.loads(Path(args.authored).read_text(encoding="utf-8"))
            pure = PurePosixPath(authored_payload["path"])
            if pure.is_absolute() or ".." in pure.parts:
                return emit({"exit_code": 2, "stage": "authored_patch", "error": "unsafe path", "per_test_status": [], "coverage": {}})
            authored_path = checkout.joinpath(*pure.parts)
            if authored_path.exists():
                return emit({"exit_code": 2, "stage": "authored_patch", "error": "path already exists", "per_test_status": [], "coverage": {}})
        env.update({
            "PATH": f"{python.parent}:{env.get('PATH', '')}", "PYTHONHASHSEED": "0",
            "PYTHONPATH": f"/opt/crucible/sandbox:{env.get('PYTHONPATH', '')}",
            "CRUCIBLE_STATUS_FILE": str(status_file), "CRUCIBLE_CHECKOUT": str(checkout),
            "CRUCIBLE_COVERAGE_FILE": str(coverage_file),
        })
        install = [str(python) if part == "python" else part for part in item["install_command"]]
        installed = invoke(install, checkout, env)
        if installed.returncode:
            return emit({"repo": args.repo, "commit": args.commit, "exit_code": installed.returncode, "stage": "build", "stdout": installed.stdout, "stderr": installed.stderr, "duration_s": round(time.monotonic() - started, 3), "per_test_status": [], "coverage": {}})
        if authored_payload is not None:
            authored_path.parent.mkdir(parents=True, exist_ok=True)
            authored_path.write_text(authored_payload["content"], encoding="utf-8")
        if args.build_only:
            return emit({
                "repo": args.repo, "commit": args.commit, "exit_code": 0, "stage": "build",
                "stdout": installed.stdout, "stderr": installed.stderr,
                "duration_s": round(time.monotonic() - started, 3), "per_test_status": [], "coverage": {},
            })
        test = [str(python) if part == "python" else part for part in item["test_command"]]
        test.extend(["-p", "pytest_status"])
        if args.coverage:
            test.extend(["-p", "pytest_phase3_coverage"])
        test.extend(args.selectors)
        result = invoke(test, checkout, env)
        statuses = json.loads(status_file.read_text(encoding="utf-8"))["tests"] if status_file.exists() else []
        coverage = json.loads(coverage_file.read_text(encoding="utf-8")) if coverage_file.exists() else {}
        return emit({
            "repo": args.repo, "commit": args.commit, "test_selector": args.selectors,
            "exit_code": result.returncode, "stage": "test", "stdout": result.stdout,
            "stderr": installed.stderr + result.stderr, "duration_s": round(time.monotonic() - started, 3),
            "per_test_status": statuses, "coverage": coverage,
        })


if __name__ == "__main__":
    raise SystemExit(main())
