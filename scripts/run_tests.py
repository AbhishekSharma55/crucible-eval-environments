"""Host-side interface to the network-disabled Docker test runner."""

from __future__ import annotations

import argparse
import json
import subprocess
from typing import Any


def run_tests(
    repo: str,
    commit: str,
    test_selector: list[str] | None = None,
    *,
    image: str = "crucible-sandbox:phase1",
    timeout_s: int = 1200,
) -> dict[str, Any]:
    """Run tests without network access and return the sandbox's JSON result."""
    command = [
        "docker",
        "run",
        "--rm",
        "--network",
        "none",
        image,
        repo,
        commit,
        *(test_selector or []),
    ]
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
    args = parser.parse_args()
    result = run_tests(args.repo, args.commit, args.test_selector, image=args.image, timeout_s=args.timeout)
    print(json.dumps(result, sort_keys=True))
    return int(result["exit_code"])


if __name__ == "__main__":
    raise SystemExit(main())
