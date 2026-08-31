"""Shared helpers for the isolated Phase 3 test-authoring evaluation."""

from __future__ import annotations

import ast
import copy
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import subprocess
import tempfile
from typing import Any

from scripts.harvest import TEST_LAYOUTS
from scripts.phase2_common import ROOT, git


PHASE3 = ROOT / "data/phase3"
PHASE3_RESULTS = ROOT / "results/phase3"
MIN_MERGE_YEAR = 2019
SAMPLE_SEED = 63811
SAMPLE_TARGET = 80
TEST_TIMEOUT_S = 60
CASE_WALL_CAP_S = 360


def phase3_candidate_pool() -> list[dict[str, Any]]:
    """Load only the dev missing-test pool without opening held-out records."""
    rows: list[dict[str, Any]] = []
    for path in sorted((ROOT / "data/candidates/dev").glob("*.jsonl")):
        rows.extend(json.loads(line) for line in path.read_text(encoding="utf-8").splitlines())
    selected = [
        item for item in rows
        if item.get("rejection_reason") == "no_test_files_touched"
        and int(item["merged_at"][:4]) >= MIN_MERGE_YEAR
    ]
    result = []
    for item in selected:
        item = dict(item)
        # Phase 1 deliberately excluded examples from production source. For
        # test authoring, executable example applications are valid behavior
        # surfaces and remain coverable. Docs/conf.py and .pyi stubs are not.
        example_sources = [
            path for path in item.get("non_test_files", [])
            if path.startswith("examples/") and path.endswith(".py")
        ]
        item["phase1_source_files"] = list(item.get("source_files", []))
        item["source_files"] = sorted(set(item.get("source_files", [])) | set(example_sources))
        result.append(item)
    return result


def case_id(candidate: dict[str, Any]) -> str:
    return f"{candidate['repo']}#{candidate['pr_number']}"


def stable_rank(seed: int, value: str) -> str:
    return hashlib.sha256(f"{seed}:{value}".encode()).hexdigest()


def json_dump(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def source_module(path: str) -> str | None:
    """Map the retained repositories' Python layouts to an importable module."""
    if not path.endswith(".py"):
        return None
    parts = list(PurePosixPath(path).with_suffix("").parts)
    if parts and parts[0] == "src":
        parts.pop(0)
    if parts and parts[-1] == "__init__":
        parts.pop()
    if not parts or any(not re.fullmatch(r"[A-Za-z_]\w*", part) for part in parts):
        return None
    return ".".join(parts)


def stub_authored_test(candidate: dict[str, Any]) -> dict[str, str]:
    modules = [module for path in candidate.get("source_files", []) if (module := source_module(path))]
    module = modules[0] if modules else "builtins"
    repo_slug = candidate["repo"].replace("/", "_").replace("-", "_")
    path = f"tests/test_crucible_phase3_{repo_slug}_{candidate['pr_number']}.py"
    content = (
        "# Mechanical null baseline: deliberately tests no behavior.\n"
        "import importlib\n\n"
        f"importlib.import_module({module!r})\n\n"
        "def test_crucible_null_stub():\n"
        "    assert True\n"
    )
    return {"path": path, "content": content}


def validate_authored_test(candidate: dict[str, Any], authored: dict[str, Any]) -> dict[str, Any]:
    """Enforce the test-only, new-file patch boundary before Docker execution."""
    path = authored.get("path")
    content = authored.get("content")
    evidence: dict[str, Any] = {
        "status": "fail", "path": path, "allowed_patterns": TEST_LAYOUTS.get(candidate["repo"], [])
    }
    if not isinstance(path, str) or not isinstance(content, str):
        evidence["reason"] = "authored_output_requires_string_path_and_content"
        return evidence
    pure = PurePosixPath(path)
    if pure.is_absolute() or ".." in pure.parts:
        evidence["reason"] = "unsafe_path"
        return evidence
    import fnmatch
    if not any(fnmatch.fnmatchcase(path, pattern) for pattern in evidence["allowed_patterns"]):
        evidence["reason"] = "path_is_not_in_configured_test_layout"
        return evidence
    exists = {}
    for endpoint, sha in (("parent", candidate["parent_sha"]), ("fix", candidate["merge_commit_sha"])):
        exists[endpoint] = git(candidate["repo"], "cat-file", "-e", f"{sha}:{path}", check=False).returncode == 0
    evidence["exists_at_endpoints"] = exists
    if any(exists.values()):
        evidence["reason"] = "authored_patch_must_add_a_new_test_file"
        return evidence
    if not content.strip():
        evidence["reason"] = "empty_test_file"
        return evidence
    evidence.update({"status": "pass", "reason": None, "bytes": len(content.encode())})
    return evidence


def run_phase3_test(
    candidate: dict[str, Any], authored: dict[str, str] | None, endpoint: str,
    *, selectors: list[str] | None = None, coverage: bool = False,
    image: str = "crucible-sandbox:phase1", timeout_s: int = TEST_TIMEOUT_S,
    build_only: bool = False,
) -> dict[str, Any]:
    """Run the dedicated Phase 3 runner without changing the Phase 1/2 runner."""
    if endpoint not in {"parent", "fix"}:
        raise ValueError("endpoint must be parent or fix")
    commit = candidate["parent_sha"] if endpoint == "parent" else candidate["merge_commit_sha"]
    sandbox_dir = ROOT / "sandbox"
    with tempfile.TemporaryDirectory(prefix="crucible-phase3-host-") as raw_tmp:
        command = [
            "docker", "run", "--rm", "--network", "none",
            "-v", f"{sandbox_dir}:/opt/crucible/sandbox:ro",
        ]
        if authored is not None:
            authored_path = Path(raw_tmp) / "authored.json"
            authored_path.write_text(json.dumps(authored), encoding="utf-8")
            command.extend(["-v", f"{authored_path}:/tmp/crucible-authored.json:ro"])
        command.extend([
            "--entrypoint", "python", image,
            "/opt/crucible/sandbox/phase3_runner.py", candidate["repo"], commit,
        ])
        if authored is not None:
            command.extend(["--authored", "/tmp/crucible-authored.json"])
        if coverage:
            command.append("--coverage")
        if build_only:
            command.append("--build-only")
        command.extend(selectors or ([authored["path"]] if authored else []))
        try:
            completed = subprocess.run(
                command, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=timeout_s
            )
        except subprocess.TimeoutExpired as exc:
            return {
                "endpoint": endpoint, "commit": commit, "exit_code": 124, "stage": "timeout",
                "duration_s": timeout_s, "stdout": exc.stdout or "", "stderr": exc.stderr or "",
                "per_test_status": [], "coverage": {},
            }
    try:
        result = json.loads(completed.stdout)
    except json.JSONDecodeError:
        result = {
            "exit_code": completed.returncode, "stage": "runner", "duration_s": 0,
            "stdout": completed.stdout, "stderr": completed.stderr, "per_test_status": [], "coverage": {},
        }
    result["endpoint"] = endpoint
    if completed.stderr:
        result["runner_stderr"] = completed.stderr
    return result


def compact_run(result: dict[str, Any]) -> dict[str, Any]:
    return {
        "endpoint": result.get("endpoint"), "commit": result.get("commit"),
        "exit_code": result.get("exit_code"), "stage": result.get("stage"),
        "duration_s": result.get("duration_s"),
        "outcomes": {item["nodeid"]: item["outcome"] for item in result.get("per_test_status", [])},
        "stdout_tail": result.get("stdout", "")[-4000:],
        "stderr_tail": result.get("stderr", "")[-4000:],
        "coverage": result.get("coverage", {}),
    }


def fingerprint(result: dict[str, Any]) -> tuple[Any, ...]:
    return (
        result.get("exit_code"), result.get("stage"),
        tuple(sorted(result.get("outcomes", {}).items())),
    )


class _RuntimeAst(ast.NodeTransformer):
    """Remove documentation and annotations before comparing runtime syntax."""

    @staticmethod
    def _without_docstring(body: list[ast.stmt]) -> list[ast.stmt]:
        if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant) and isinstance(body[0].value.value, str):
            return body[1:]
        return body

    def visit_Module(self, node: ast.Module):
        node.body = self._without_docstring(node.body)
        return self.generic_visit(node)

    def visit_ClassDef(self, node: ast.ClassDef):
        node.body = self._without_docstring(node.body)
        return self.generic_visit(node)

    def visit_FunctionDef(self, node: ast.FunctionDef):
        node.returns = None
        node.type_comment = None
        node.body = self._without_docstring(node.body)
        return self.generic_visit(node)

    visit_AsyncFunctionDef = visit_FunctionDef

    def visit_arg(self, node: ast.arg):
        node.annotation = None
        node.type_comment = None
        return node

    def visit_AnnAssign(self, node: ast.AnnAssign):
        if node.value is None:
            return None
        return self.visit(ast.Assign(targets=[node.target], value=node.value))


def runtime_ast(source: str) -> str | None:
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return None
    cleaned = _RuntimeAst().visit(copy.deepcopy(tree))
    ast.fix_missing_locations(cleaned)
    return ast.dump(cleaned, include_attributes=False)


def behavior_change_evidence(candidate: dict[str, Any]) -> dict[str, Any]:
    """Verify that gold Python files change runtime AST, not only docs/types."""
    files = []
    runtime_changed = False
    for path in candidate.get("source_files", []):
        parent = git(candidate["repo"], "show", f"{candidate['parent_sha']}:{path}", check=False)
        fix = git(candidate["repo"], "show", f"{candidate['merge_commit_sha']}:{path}", check=False)
        if parent.returncode or fix.returncode:
            status = "file_added_or_deleted"
            changed = True
        else:
            before = runtime_ast(parent.stdout)
            after = runtime_ast(fix.stdout)
            if before is None or after is None:
                status = "unparseable_python"
                changed = False
            else:
                changed = before != after
                status = "runtime_ast_changed" if changed else "docs_or_annotations_only"
        runtime_changed |= changed
        files.append({"path": path, "status": status, "runtime_changed": changed})
    title = candidate.get("title", "")
    rename_claim = bool(re.search(r"\brename(?:d|s|ing)?\b", title, re.IGNORECASE))
    # A rename-labelled PR is not accepted merely because identifiers alter
    # the AST. This is deliberately conservative and fixed before baselines.
    passed = runtime_changed and not rename_claim
    return {
        "status": "pass" if passed else "fail",
        "reason": None if passed else ("rename_only_claim" if rename_claim else "no_verified_runtime_ast_change"),
        "title_rename_signal": rename_claim, "files": files,
    }


_DIFF_HUNK = re.compile(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,(\d+))? @@")


def changed_fix_lines(candidate: dict[str, Any]) -> dict[str, list[int]]:
    """Return nonblank, non-comment source lines added by the gold patch."""
    paths = candidate.get("source_files", [])
    if not paths:
        return {}
    patch = git(
        candidate["repo"], "diff", "--no-ext-diff", "--unified=0",
        candidate["parent_sha"], candidate["merge_commit_sha"], "--", *paths,
    ).stdout
    result: dict[str, set[int]] = {}
    current = None
    next_line = remaining = 0
    for line in patch.splitlines():
        if line.startswith("+++ b/"):
            current = line[6:]
            result.setdefault(current, set())
        elif (match := _DIFF_HUNK.match(line)):
            next_line = int(match.group(1))
            remaining = int(match.group(2) or "1")
        elif current is not None and remaining > 0 and not line.startswith("\\"):
            if line.startswith("+"):
                code = line[1:].strip()
                if code and not code.startswith("#"):
                    result[current].add(next_line)
                next_line += 1
                remaining -= 1
            elif not line.startswith("-"):
                next_line += 1
                remaining -= 1
    return {path: sorted(lines) for path, lines in sorted(result.items()) if lines}


def existing_test_selectors(candidate: dict[str, Any], *, limit: int = 20) -> list[str]:
    """Select the nearest existing test node without using authored output."""
    listed = git(candidate["repo"], "ls-tree", "-r", "--name-only", candidate["parent_sha"]).stdout.splitlines()
    tests = [
        path for path in listed
        if path.endswith(".py") and (
            PurePosixPath(path).name.startswith("test_") or PurePosixPath(path).name == "test.py"
        )
        and PurePosixPath(path).name != "conftest.py"
    ]
    source_tokens = set()
    for path in candidate.get("source_files", []):
        pure = PurePosixPath(path)
        source_tokens.update(part.lower() for part in pure.with_suffix("").parts if part not in {"src", "__init__"})
        if pure.stem != "__init__":
            source_tokens.add(pure.stem.lower())
    def score(path: str) -> tuple[int, str]:
        lowered = path.lower()
        value = sum(4 for token in source_tokens if re.search(rf"(?<![a-z0-9]){re.escape(token)}(?![a-z0-9])", lowered))
        value += sum(1 for token in source_tokens if token in lowered)
        return value, path
    ranked = sorted(tests, key=lambda path: (-score(path)[0], path))
    nodes: list[str] = []
    for path in ranked:
        shown = git(candidate["repo"], "show", f"{candidate['parent_sha']}:{path}", check=False)
        if shown.returncode:
            continue
        try:
            tree = ast.parse(shown.stdout)
        except SyntaxError:
            continue
        for node in tree.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name.startswith("test"):
                nodes.append(f"{path}::{node.name}")
            elif isinstance(node, ast.ClassDef) and node.name.startswith("Test"):
                for child in node.body:
                    if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)) and child.name.startswith("test"):
                        nodes.append(f"{path}::{node.name}::{child.name}")
    return nodes[:limit]
