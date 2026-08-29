"""Probe every active corpus repository at its pinned head and old commit."""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import json
from pathlib import Path
import time
from typing import Any

from scripts.run_tests import run_tests


ROOT = Path(__file__).resolve().parents[1]


def probe_one(repo: dict[str, Any], revision: str, image: str) -> tuple[str, str, dict[str, Any]]:
    commit = repo["head_commit"] if revision == "head" else repo["old_commit"]
    result = run_tests(repo["repo"], commit, image=image)
    return repo["repo"], revision, result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--image", default="crucible-sandbox:phase1")
    parser.add_argument("--workers", type=int, default=3)
    parser.add_argument("--output", type=Path, default=ROOT / "data/probes")
    args = parser.parse_args()
    config = json.loads((ROOT / "config/repos.json").read_text(encoding="utf-8"))
    repos = [item for item in config["repos"] if item["status"] in {"accepted", "probe"}]
    started = time.monotonic()
    results: dict[tuple[str, str], dict[str, Any]] = {}
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = [pool.submit(probe_one, repo, revision, args.image) for repo in repos for revision in ("head", "old")]
        for future in as_completed(futures):
            name, revision, result = future.result()
            results[(name, revision)] = result
            output = args.output / name.replace("/", "--")
            output.mkdir(parents=True, exist_ok=True)
            (output / f"{revision}.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
            print(f"completed {name:<32} {revision:<4} exit={result['exit_code']} duration={result.get('duration_s', 0):.1f}s", flush=True)

    print("\nREPOSITORY                       HEAD  OLD   HEAD_S   OLD_S")
    print("-------------------------------- ----- ----- -------- --------")
    failures = 0
    for repo in repos:
        head = results[(repo["repo"], "head")]
        old = results[(repo["repo"], "old")]
        head_ok = head["exit_code"] == 0
        old_ok = old["exit_code"] == 0
        failures += int(not (head_ok and old_ok))
        print(f"{repo['repo']:<32} {'PASS' if head_ok else 'FAIL':<5} {'PASS' if old_ok else 'FAIL':<5} {head.get('duration_s', 0):8.1f} {old.get('duration_s', 0):8.1f}")
    elapsed = round(time.monotonic() - started, 3)
    (args.output / "summary.json").write_text(
        json.dumps({"wall_clock_s": elapsed, "repos": len(repos), "failures": failures}, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(f"\nwall_clock_s={elapsed}")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
