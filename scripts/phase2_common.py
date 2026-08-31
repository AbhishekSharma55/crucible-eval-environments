"""Shared, offline helpers for Phase 2 artifacts."""

from __future__ import annotations

import ast
import hashlib
import json
from pathlib import Path
import re
import subprocess
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[1]
PHASE2 = ROOT / "data/phase2"


def case_id(candidate: dict[str, Any]) -> str:
    return f"{candidate['repo']}#{candidate['pr_number']}"


def slug(repo: str) -> str:
    return repo.replace("/", "--")


def mirror(repo: str) -> Path:
    path = ROOT / "cache/repos" / f"{slug(repo)}.git"
    if not path.is_dir():
        raise RuntimeError(f"cached git mirror is missing: {path}")
    return path


def git(repo: str, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args], cwd=mirror(repo), check=check, text=True,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    )


def gold_patch(candidate: dict[str, Any], *, unified: int = 3) -> str:
    paths = candidate.get("non_test_files") or candidate.get("patches", {}).get("gold", {}).get("paths", [])
    if not paths:
        return ""
    return git(
        candidate["repo"], "diff", "--no-ext-diff", f"--unified={unified}",
        candidate["parent_sha"], candidate["merge_commit_sha"], "--", *paths,
    ).stdout


def load_dev_candidates() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for path in sorted((ROOT / "data/candidates/dev").glob("*.jsonl")):
        rows.extend(json.loads(line) for line in path.read_text(encoding="utf-8").splitlines())
    return rows


def load_case_set(path: Path | None = None) -> dict[str, Any]:
    target = path or PHASE2 / "case-set.json"
    return json.loads(target.read_text(encoding="utf-8"))


HUNK = re.compile(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,(\d+))? @@")


def _changed_lines_by_path(candidate: dict[str, Any]) -> dict[str, set[int]]:
    paths = candidate.get("test_files", [])
    if not paths:
        return {}
    patch = git(
        candidate["repo"], "diff", "--no-ext-diff", "--unified=0",
        candidate["parent_sha"], candidate["merge_commit_sha"], "--", *paths,
    ).stdout
    result: dict[str, set[int]] = {}
    current: str | None = None
    next_line = 0
    remaining = 0
    for line in patch.splitlines():
        if line.startswith("+++ b/"):
            current = line[6:]
            result.setdefault(current, set())
            continue
        match = HUNK.match(line)
        if match:
            next_line = int(match.group(1))
            remaining = int(match.group(2) or "1")
            continue
        if current is None or remaining <= 0 or line.startswith("\\"):
            continue
        if line.startswith("+"):
            result[current].add(next_line)
            next_line += 1
            remaining -= 1
        elif not line.startswith("-"):
            next_line += 1
            remaining -= 1
    return result


def touched_test_names(candidate: dict[str, Any]) -> set[str]:
    """Map changed fix-side lines to enclosing pytest functions where possible."""
    names: set[str] = set()
    for path, lines in _changed_lines_by_path(candidate).items():
        shown = git(candidate["repo"], "show", f"{candidate['merge_commit_sha']}:{path}", check=False)
        if shown.returncode:
            continue
        try:
            tree = ast.parse(shown.stdout)
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name.startswith("test"):
                end = getattr(node, "end_lineno", node.lineno)
                if any(node.lineno <= line <= end for line in lines):
                    names.add(node.name)
    return names


def narrow_collection_transitions(
    candidate: dict[str, Any] | None, transitions: list[dict[str, str]]
) -> tuple[list[dict[str, str]], str]:
    if not candidate:
        return transitions, "file_fanout_no_candidate"
    names = touched_test_names(candidate)
    if not names:
        return transitions, "file_fanout_no_test_symbol"
    narrowed = [
        item for item in transitions
        if any(re.search(rf"::{re.escape(name)}(?:\[|$)", item["nodeid"]) for name in names)
    ]
    if narrowed:
        return narrowed, "touched_test_symbols"
    return transitions, "file_fanout_no_nodeid_match"


def stable_rank(seed: int, value: str) -> str:
    return hashlib.sha256(f"{seed}:{value}".encode()).hexdigest()


def json_dump(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
