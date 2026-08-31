"""Host-side interface to the network-disabled Docker test runner."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess
import tempfile
from typing import Any


def run_tests(
    repo: str,
    commit: str,
    test_selector: list[str] | None = None,
    *,
    image: str = "crucible-sandbox:phase1",
    timeout_s: int = 1200,
    test_patch_from: str | None = None,
    solution_patch: str | None = None,
) -> dict[str, Any]:
    """Run tests without network access and return the sandbox's JSON result."""
    with tempfile.TemporaryDirectory(prefix="crucible-solution-") as raw_tmp:
        sandbox_dir = Path(__file__).resolve().parents[1] / "sandbox"
        command = [
            "docker", "run", "--rm", "--network", "none",
            "-v", f"{sandbox_dir}:/opt/crucible/sandbox:ro",
        ]
        if solution_patch is not None:
            patch_path = Path(raw_tmp) / "solution.patch"
            patch_path.write_text(solution_patch, encoding="utf-8")
            command.extend(["-v", f"{patch_path}:/tmp/crucible-solution.patch:ro"])
        command.extend([image, repo, commit, *(test_selector or [])])
        if test_patch_from is not None:
            command.extend(["--test-patch-from", test_patch_from])
        if solution_patch is not None:
            command.extend(["--solution-patch", "/tmp/crucible-solution.patch"])
        try:
            completed = subprocess.run(
                command,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=timeout_s,
            )
        except subprocess.TimeoutExpired as exc:
            return {
                "repo": repo,
                "commit": commit,
                "exit_code": 124,
                "stdout": exc.stdout or "",
                "stderr": exc.stderr or "",
                "duration_s": timeout_s,
                "per_test_status": [],
                "stage": "timeout",
            }
    try:
        payload = json.loads(completed.stdout)
    except json.JSONDecodeError:
        payload = {
            "repo": repo,
            "commit": commit,
            "exit_code": completed.returncode,
            "stdout": completed.stdout,
            "stderr": completed.stderr,
            "duration_s": 0,
            "per_test_status": [],
            "stage": "runner",
        }
    if completed.stderr:
        payload["runner_stderr"] = completed.stderr
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("repo")
    parser.add_argument("commit")
    parser.add_argument("test_selector", nargs="*")
    parser.add_argument("--image", default="crucible-sandbox:phase1")
    parser.add_argument("--timeout", type=int, default=1200)
    parser.add_argument("--test-patch-from")
    parser.add_argument("--solution-patch", type=Path)
    args = parser.parse_args()
    result = run_tests(
        args.repo,
        args.commit,
        args.test_selector,
        image=args.image,
        timeout_s=args.timeout,
        test_patch_from=args.test_patch_from,
        solution_patch=args.solution_patch.read_text(encoding="utf-8") if args.solution_patch else None,
    )
    print(json.dumps(result, sort_keys=True))
    return int(result["exit_code"])


if __name__ == "__main__":
    raise SystemExit(main())
