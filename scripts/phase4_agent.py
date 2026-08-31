"""Single-case Phase 4 agent tools and prompt-surface helpers."""

from __future__ import annotations

import ast
import fnmatch
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import time
from typing import Any

from scripts.harvest import TEST_LAYOUTS
from scripts.phase2_common import ROOT, git, gold_patch
from scripts.phase3_common import case_id, run_phase3_test, validate_authored_test
from scripts.test_authoring_verifier import verify


AGENT_DIR = ROOT / "agents"
MAX_READ_LINES = 160
MAX_SEARCH_MATCHES = 60
MAX_OBSERVATION_CHARS = 8_000
MAX_GATE_CALLS = 5
EXPECTED_TOOLS = {
    "list_tests", "read_file", "search", "write_test", "run_test", "check_gates",
}


def _read_instruction(name: str) -> str:
    path = AGENT_DIR / name
    if not path.is_file():
        raise RuntimeError(f"missing version-controlled agent instruction: {path}")
    return path.read_text(encoding="utf-8").strip()


def load_agent_instructions() -> tuple[str, str, list[dict[str, Any]]]:
    """Load every model-facing instruction from agents/*.md."""
    system = _read_instruction("phase4-system.md")
    task = _read_instruction("phase4-task.md")
    tools_text = _read_instruction("phase4-tools.md")
    match = re.search(r"```json\s*(.*?)\s*```", tools_text, re.DOTALL)
    if not match:
        raise RuntimeError("agents/phase4-tools.md must contain one fenced JSON tool list")
    tools = json.loads(match.group(1))
    names = {item.get("function", {}).get("name") for item in tools}
    if names != EXPECTED_TOOLS:
        raise RuntimeError(f"tool file defines {sorted(names)}; expected {sorted(EXPECTED_TOOLS)}")
    return system, task, tools


def _bounded(text: str, limit: int = MAX_OBSERVATION_CHARS) -> str:
    """Bound model-visible output with an unambiguous omission marker."""
    if len(text) <= limit:
        return text
    head = limit * 3 // 5
    tail = limit - head
    omitted = len(text) - limit
    return (
        text[:head]
        + f"\n...[TRUNCATED {omitted} CHARACTERS; narrow the query or read another window]...\n"
        + text[-tail:]
    )


def _safe_path(path: Any) -> tuple[PurePosixPath | None, str | None]:
    if not isinstance(path, str) or not path.strip():
        return None, "path must be a non-empty repository-relative string"
    pure = PurePosixPath(path)
    if pure.is_absolute() or ".." in pure.parts or ".git" in pure.parts:
        return None, "path must stay inside the repository and cannot address .git"
    return pure, None


def _show(candidate: dict[str, Any], path: str) -> str | None:
    shown = git(candidate["repo"], "show", f"{candidate['parent_sha']}:{path}", check=False)
    return shown.stdout if shown.returncode == 0 else None


def render_task(candidate: dict[str, Any], template: str) -> str:
    issues = "\n\n".join(
        f"Issue #{item['number']}:\n{item.get('body') or '(empty)'}"
        for item in candidate.get("linked_issues", [])
    ) or "(none)"
    values = {
        "CASE_ID": case_id(candidate),
        "REPO": candidate["repo"],
        "PARENT_SHA": candidate["parent_sha"],
        "FIX_SHA": candidate["merge_commit_sha"],
        "ISSUES": issues,
        "PR_TITLE": candidate.get("title") or "(empty)",
        "PR_BODY": candidate.get("body") or "(empty)",
        "GOLD_PATCH": gold_patch(candidate, unified=3) or "(empty)",
        "SOURCE_PATHS": "\n".join(f"- {path}" for path in candidate.get("source_files", [])) or "(none)",
    }
    rendered = template
    for key, value in values.items():
        rendered = rendered.replace("{{" + key + "}}", str(value))
    leftovers = sorted(set(re.findall(r"{{[A-Z_]+}}", rendered)))
    if leftovers:
        raise RuntimeError(f"unresolved phase4 task placeholders: {leftovers}")
    return rendered


def gaming_flags(content: str) -> list[str]:
    """Conservative review flags, not a gate and never used to select outputs."""
    checks = {
        "runtime_source_or_file_inspection": r"inspect\.getsource|read_text\s*\(|read_bytes\s*\(|\bopen\s*\(",
        "runtime_version_or_environment_branch": r"sys\.version|platform\.|os\.environ|importlib\.metadata|pkg_resources|__version__",
        "runtime_git_or_commit_inspection": r"subprocess|\bgit\b|commit[_ -]?sha|rev-parse",
        "skip_or_expected_failure": r"pytest\.(?:skip|xfail)|@pytest\.mark\.(?:skip|xfail)",
        "unconditional_failure": r"assert\s+False\b|pytest\.fail\s*\(",
        "missing_symbol_probe": r"\b(?:hasattr|getattr)\s*\(|pytest\.raises\s*\(\s*(?:ImportError|AttributeError|NameError|ModuleNotFoundError)",
    }
    return [name for name, pattern in checks.items() if re.search(pattern, content, re.IGNORECASE)]


def _run_observation(result: dict[str, Any]) -> dict[str, Any]:
    stdout = result.get("stdout", "") or ""
    stderr = result.get("stderr", "") or ""
    stage = result.get("stage")
    code = result.get("exit_code")
    endpoint = result.get("endpoint")
    if stage != "test":
        action = (
            f"The {endpoint} checkout failed during {stage}, before pytest completed. "
            "Use the displayed output to correct imports or collection; if it is infrastructure-only, stop and report it."
        )
    elif code == 0 and endpoint == "fix":
        action = "The test passes at the fix. Run it at parent and confirm that the intended behavioral assertion fails there."
    elif code == 0 and endpoint == "parent":
        action = "The test also passes at parent, so it does not reproduce the bug. Tighten the assertion around the reported behavior."
    elif endpoint == "fix":
        action = "The test is broken at the fix. Read the failure below, inspect the referenced fixture/API, revise, and run fix again."
    else:
        action = "The test fails at parent. Confirm the failure is the intended behavioral assertion, then call check_gates."
    statuses = {
        item.get("nodeid", "<unknown>"): item.get("outcome", "unknown")
        for item in result.get("per_test_status", [])
    }
    return {
        "ok": stage == "test",
        "endpoint": endpoint,
        "stage": stage,
        "exit_code": code,
        "per_test_status": statuses,
        "duration_s": result.get("duration_s"),
        "action": action,
        "stdout": _bounded(stdout),
        "stderr": _bounded(stderr),
    }


def _compact_gate_run(run: dict[str, Any]) -> dict[str, Any]:
    return {
        "endpoint": run.get("endpoint"),
        "stage": run.get("stage"),
        "exit_code": run.get("exit_code"),
        "outcomes": run.get("outcomes", {}),
        "stdout": _bounded(run.get("stdout_tail", ""), 3_000),
        "stderr": _bounded(run.get("stderr_tail", ""), 3_000),
    }


def gate_observation(verification: dict[str, Any], calls: int) -> dict[str, Any]:
    summaries: dict[str, Any] = {}
    for name in ("g1", "g2", "g3", "g4", "g5"):
        gate = verification["gates"][name]
        item: dict[str, Any] = {"status": gate["status"], "reason": gate.get("reason")}
        evidence = gate.get("evidence") or {}
        if name in {"g1", "g2"}:
            item["runs"] = [_compact_gate_run(run) for run in evidence.get("runs", [])]
        elif name == "g3":
            item["parent_exceptions"] = evidence.get("parent_exceptions", [])
            item["introduced_symbol_matches"] = evidence.get("matches", [])
        elif name == "g4":
            item.update({
                "covered_changed_lines": evidence.get("covered_changed_lines", {}),
                "changed_line_fraction": evidence.get("changed_line_fraction", 0.0),
            })
            if evidence.get("coverage_run") and gate["status"] == "fail":
                item["coverage_run"] = _compact_gate_run(evidence["coverage_run"])
        elif name == "g5":
            item["authored_patch_boundary"] = evidence.get("authored_patch_boundary", {})
            item["selected_existing_tests"] = evidence.get("selected_existing_tests", [])
        summaries[name] = item
    failed = next((name for name in ("g1", "g2", "g3", "g4", "g5") if summaries[name]["status"] == "fail"), None)
    repairs = {
        "g1": "The test did not fail deterministically at parent. Tighten the behavioral assertion and confirm it with run_test(parent).",
        "g2": "The test does not pass deterministically at fix. Use the fix failure output above and nearby test conventions to repair it.",
        "g3": "The parent failure depends on a symbol introduced by the gold patch. Exercise an API that already exists at parent instead.",
        "g4": "The passing test did not execute a changed fix-side line. Drive the public behavior through the changed code path rather than only testing setup.",
        "g5": "The staged path is not one new test-only file or endpoint controls are unclean. Use an allowed new test path and avoid collateral edits.",
    }
    return {
        "ok": verification.get("passed", False),
        "passed": verification.get("passed", False),
        "gate_call": calls,
        "gate_calls_remaining": MAX_GATE_CALLS - calls,
        "gates": summaries,
        "action": "All gates passed; the case is complete." if failed is None else repairs[failed],
    }


class AgentWorkspace:
    """Stateful, deliberately tiny capability surface for one agent rollout."""

    def __init__(
        self, candidate: dict[str, Any], *, image: str, timeout_s: int,
        wall_cap_s: float, started: float | None = None,
    ) -> None:
        self.candidate = candidate
        self.image = image
        self.timeout_s = timeout_s
        self.wall_cap_s = wall_cap_s
        self.started = time.monotonic() if started is None else started
        self.staged: dict[str, str] | None = None
        self.staged_revision = 0
        self.gate_calls = 0
        self.gate_attempts: list[dict[str, Any]] = []

    def remaining_s(self) -> float:
        return self.wall_cap_s - (time.monotonic() - self.started)

    def _execution_timeout(self) -> int:
        remaining = self.remaining_s()
        if remaining <= 0:
            return 0
        return max(1, min(self.timeout_s, int(remaining)))

    def list_tests(self, module_or_path: Any) -> dict[str, Any]:
        if not isinstance(module_or_path, str) or not module_or_path.strip():
            return {"ok": False, "error": "module_or_path must be non-empty; pass a changed source path or public API term"}
        if len(module_or_path) > 300:
            return {"ok": False, "error": "module_or_path is too long; use one concise source path, module, or behavior term"}
        listed = git(
            self.candidate["repo"], "ls-tree", "-r", "--name-only", self.candidate["parent_sha"]
        ).stdout.splitlines()
        configured = TEST_LAYOUTS.get(self.candidate["repo"], [])
        tests = []
        for path in listed:
            pure = PurePosixPath(path)
            looks_like_test = (
                pure.name == "conftest.py"
                or pure.name.startswith("test_")
                or any(part in {"test", "tests", "testing", "typing_tests"} for part in pure.parts[:-1])
            )
            if path.endswith(".py") and (
                looks_like_test or any(fnmatch.fnmatchcase(path, pattern) for pattern in configured)
            ):
                tests.append(path)
        query_tokens = {
            token.lower() for token in re.split(r"[^A-Za-z0-9]+", module_or_path)
            if len(token) >= 2 and token.lower() not in {"src", "py", "python", "test", "tests"}
        }

        content_matches: set[str] = set()
        if query_tokens:
            expression = "|".join(re.escape(token) for token in sorted(query_tokens))
            found = git(
                self.candidate["repo"], "grep", "-l", "-I", "-E", "-e", expression,
                self.candidate["parent_sha"], "--", *tests, check=False,
            )
            prefix = self.candidate["parent_sha"] + ":"
            content_matches = {
                line[len(prefix):] if line.startswith(prefix) else line
                for line in found.stdout.splitlines()
            }

        def score(path: str) -> tuple[int, str]:
            lowered = path.lower()
            exact = sum(6 for token in query_tokens if re.search(rf"(?<![a-z0-9]){re.escape(token)}(?![a-z0-9])", lowered))
            partial = sum(2 for token in query_tokens if token in lowered)
            in_content = 4 if path in content_matches else 0
            return -(exact + partial + in_content), path

        ranked = sorted(tests, key=score)[:8]
        details = []
        for path in ranked:
            source = _show(self.candidate, path) or ""
            names: list[str] = []
            fixtures: list[str] = []
            try:
                tree = ast.parse(source)
                for node in ast.walk(tree):
                    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        if node.name.startswith("test") and len(names) < 12:
                            names.append(node.name)
                        for decorator in node.decorator_list:
                            if "fixture" in ast.unparse(decorator) and len(fixtures) < 8:
                                fixtures.append(node.name)
            except (SyntaxError, ValueError):
                pass
            excerpt_lines = source.splitlines()[:36]
            excerpt = "\n".join(f"{index:4d} | {line}" for index, line in enumerate(excerpt_lines, 1))
            if len(source.splitlines()) > len(excerpt_lines):
                excerpt += f"\n...[TRUNCATED; use read_file({path!r}, start, end) for another window]..."
            details.append({"path": path, "test_names": names, "fixtures": fixtures, "opening_excerpt": excerpt})
        return {
            "ok": True,
            "query": module_or_path,
            "allowed_new_test_layouts": configured,
            "ranked_test_files": details,
            "total_test_python_files": len(tests),
            "action": "Read a focused window from the closest test or search for a relevant fixture/API before staging a new file.",
        }

    def read_file(self, path: Any, start: Any, end: Any) -> dict[str, Any]:
        pure, error = _safe_path(path)
        if error:
            return {"ok": False, "error": error + "; pass a tracked repository-relative path from list_tests or search"}
        if not isinstance(start, int) or not isinstance(end, int) or isinstance(start, bool) or isinstance(end, bool):
            return {"ok": False, "error": "start and end must be one-based integers"}
        if start < 1 or end < start:
            return {"ok": False, "error": "use a valid inclusive range with 1 <= start <= end"}
        if end - start + 1 > MAX_READ_LINES:
            return {"ok": False, "error": f"window is {end - start + 1} lines; request at most {MAX_READ_LINES} lines"}
        source = _show(self.candidate, str(pure))
        if source is None:
            return {"ok": False, "error": f"{pure} does not exist at the broken parent; use search or list_tests to find a parent-side path"}
        lines = source.splitlines()
        if start > len(lines) and lines:
            return {"ok": False, "error": f"start line {start} is past EOF ({len(lines)} lines); request an earlier window"}
        selected = lines[start - 1:end]
        numbered = "\n".join(f"{line_no:4d} | {line}" for line_no, line in enumerate(selected, start))
        notices = []
        if start > 1:
            notices.append(f"{start - 1} earlier lines omitted")
        if end < len(lines):
            notices.append(f"{len(lines) - end} later lines omitted")
        if notices:
            numbered += "\n...[WINDOWED READ; " + "; ".join(notices) + "]..."
        return {"ok": True, "path": str(pure), "start": start, "end": min(end, len(lines)), "total_lines": len(lines), "content": _bounded(numbered)}

    def search(self, pattern: Any) -> dict[str, Any]:
        if not isinstance(pattern, str) or not pattern.strip():
            return {"ok": False, "error": "pattern must be a non-empty regular expression; try a public API, fixture, or error phrase"}
        if len(pattern) > 300 or "\n" in pattern:
            return {"ok": False, "error": "pattern must be one concise line no longer than 300 characters"}
        try:
            re.compile(pattern)
        except re.error as exc:
            return {"ok": False, "error": f"invalid regular expression: {exc}; simplify or escape metacharacters"}
        found = git(
            self.candidate["repo"], "grep", "-n", "-I", "-E", "-e", pattern,
            self.candidate["parent_sha"], "--", check=False,
        )
        if found.returncode not in {0, 1}:
            return {"ok": False, "error": "search engine rejected the expression; simplify it to an extended regular expression", "detail": _bounded(found.stderr, 1_000)}
        raw = found.stdout.splitlines()
        matches = []
        prefix = self.candidate["parent_sha"] + ":"
        for line in raw[:MAX_SEARCH_MATCHES]:
            if line.startswith(prefix):
                line = line[len(prefix):]
            matches.append(_bounded(line, 500))
        marker = None
        if len(raw) > len(matches):
            marker = f"[TRUNCATED {len(raw) - len(matches)} MATCHES; narrow the pattern]"
        return {
            "ok": True, "pattern": pattern, "matches": matches,
            "match_count_returned": len(matches), "more_matches": marker,
            "action": "Read a focused window around a relevant match." if matches else "No parent-side matches; try a less specific API or behavior term.",
        }

    def write_test(self, path: Any, content: Any) -> dict[str, Any]:
        authored = {"path": path, "content": content}
        boundary = validate_authored_test(self.candidate, authored)
        if boundary["status"] != "pass":
            reasons = {
                "authored_output_requires_string_path_and_content": "provide both path and complete content as strings",
                "unsafe_path": "use a repository-relative path without parent traversal",
                "path_is_not_in_configured_test_layout": f"use one of the allowed layouts: {boundary.get('allowed_patterns', [])}",
                "authored_patch_must_add_a_new_test_file": "choose a new filename; existing tests cannot be edited",
                "empty_test_file": "provide a focused pytest regression test",
            }
            reason = boundary.get("reason")
            return {"ok": False, "error": reason, "action": reasons.get(reason, "correct the staged test and try again"), "boundary": boundary}
        self.staged = {"path": str(path), "content": str(content)}
        self.staged_revision += 1
        digest = hashlib.sha256(str(content).encode()).hexdigest()
        flags = gaming_flags(str(content))
        return {
            "ok": True, "staged_revision": self.staged_revision, "path": path,
            "bytes": boundary["bytes"], "content_sha256": digest,
            "review_flags": flags,
            "action": (
                "Review flags indicate possible gate gaming; replace runtime checkout detection with a genuine behavioral assertion before execution."
                if flags else "Run the staged test at fix first."
            ),
        }

    def run_test(self, endpoint: Any) -> dict[str, Any]:
        if endpoint not in {"parent", "fix"}:
            return {"ok": False, "error": "endpoint must be exactly 'parent' or 'fix'"}
        if self.staged is None:
            return {"ok": False, "error": "no test is staged; call write_test with one new test file first"}
        timeout = self._execution_timeout()
        if timeout <= 0:
            return {"ok": False, "error": "case wall-clock limit is exhausted; stop without claiming success"}
        result = run_phase3_test(
            self.candidate, self.staged, endpoint, image=self.image, timeout_s=timeout
        )
        return _run_observation(result)

    def check_gates(self) -> dict[str, Any]:
        if self.gate_calls >= MAX_GATE_CALLS:
            return {
                "ok": False,
                "error": f"the hard cap of {MAX_GATE_CALLS} check_gates calls is exhausted",
                "action": "Stop and return the best already checked candidate; no further validation signal is available.",
                "gate_calls_remaining": 0,
            }
        self.gate_calls += 1
        if self.staged is None:
            return {"ok": False, "error": "no test is staged; this call still consumed validation budget, so write and run a candidate before calling again", "gate_calls_remaining": MAX_GATE_CALLS - self.gate_calls}
        timeout = self._execution_timeout()
        if timeout <= 0:
            return {"ok": False, "error": "case wall-clock limit is exhausted; this call consumed validation budget but the gate stack was not run", "gate_calls_remaining": MAX_GATE_CALLS - self.gate_calls}
        authored = dict(self.staged)
        verification = verify(
            self.candidate, authored, image=self.image, timeout_s=timeout,
            wall_cap_s=max(1, self.remaining_s()),
        )
        record = {
            "gate_call": self.gate_calls,
            "staged_revision": self.staged_revision,
            "authored_test": authored,
            "verification": verification,
            "gaming_flags": gaming_flags(authored["content"]),
        }
        self.gate_attempts.append(record)
        return gate_observation(verification, self.gate_calls)

    def call(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        if name not in EXPECTED_TOOLS:
            return {"ok": False, "error": f"unknown tool {name!r}; use one of {sorted(EXPECTED_TOOLS)}"}
        if not isinstance(arguments, dict):
            return {"ok": False, "error": "tool arguments must decode to a JSON object"}
        try:
            if name == "list_tests":
                return self.list_tests(arguments.get("module_or_path"))
            if name == "read_file":
                return self.read_file(arguments.get("path"), arguments.get("start"), arguments.get("end"))
            if name == "search":
                return self.search(arguments.get("pattern"))
            if name == "write_test":
                return self.write_test(arguments.get("path"), arguments.get("content"))
            if name == "run_test":
                return self.run_test(arguments.get("endpoint"))
            return self.check_gates()
        except Exception as exc:  # Tool failures must become model-recoverable observations.
            return {
                "ok": False,
                "error": f"{name} could not complete: {type(exc).__name__}: {_bounded(str(exc), 1_000)}",
                "action": "Correct the arguments or use a narrower inspection step. If the failure is infrastructure-only, stop and report it.",
            }
