"""Mechanical problem-statement leakage detector for gold Python patches."""

from __future__ import annotations

import argparse
import ast
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import re
from typing import Any, Iterable

from scripts.phase2_common import git, gold_patch, json_dump, load_case_set


# Chosen a priori: eight lexical tokens is long enough to represent a code
# construction rather than an ordinary API name, while catching one copied
# expression or function call.  This constant must not be tuned on eval labels.
COPIED_CODE_TOKEN_THRESHOLD = 8
TOKEN = re.compile(r"[A-Za-z_]\w*|\d+(?:\.\d+)?|==|!=|<=|>=|:=|->|\*\*|//|[()[\]{}.,:;=+*/%<>|&~-]")
IDENTIFIER = re.compile(r"^[A-Za-z_]\w*$")
PATCH_SYNTAX = re.compile(r"(?m)^(?:diff --git |index [0-9a-f]+\.\.[0-9a-f]+|@@ |--- a/|\+\+\+ b/)")
PATH_LINE = re.compile(r"(?<![\w./-])(?:[\w.-]+/)*[\w.-]+\.py:\d+(?::\d+)?")
FIX_INSTRUCTION = re.compile(r"\b(?:add|change|replace|introduce|rename|remove)\b", re.IGNORECASE)
HUNK = re.compile(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,(\d+))? @@")
_NOVEL_CACHE: dict[tuple[str, str, str, str], list[AddedIdentifier]] = {}


@dataclass(frozen=True)
class AddedIdentifier:
    name: str
    kind: str
    path: str


def _patch_additions(patch: str) -> tuple[dict[str, set[int]], dict[str, list[str]], set[str]]:
    changed: dict[str, set[int]] = {}
    code: dict[str, list[str]] = {}
    added_files: set[str] = set()
    current: str | None = None
    next_line = 0
    remaining = 0
    new_file = False
    for line in patch.splitlines():
        if line.startswith("diff --git "):
            current = None
            new_file = False
        elif line.startswith("new file mode "):
            new_file = True
        elif line.startswith("+++ b/"):
            current = line[6:]
            changed.setdefault(current, set())
            code.setdefault(current, [])
            if new_file:
                added_files.add(current)
        elif (match := HUNK.match(line)):
            next_line = int(match.group(1))
            remaining = int(match.group(2) or "1")
        elif current is not None and remaining > 0 and not line.startswith("\\"):
            if line.startswith("+"):
                changed[current].add(next_line)
                code[current].append(line[1:])
                next_line += 1
                remaining -= 1
            elif not line.startswith("-"):
                next_line += 1
                remaining -= 1
    return changed, code, added_files


def _target_names(target: ast.expr) -> Iterable[str]:
    if isinstance(target, ast.Name):
        yield target.id
    elif isinstance(target, (ast.Tuple, ast.List)):
        for item in target.elts:
            yield from _target_names(item)


def extract_added_identifiers(candidate: dict[str, Any], patch: str | None = None) -> list[AddedIdentifier]:
    patch = gold_patch(candidate, unified=0) if patch is None else patch
    changed, added_code, added_files = _patch_additions(patch)
    found: set[AddedIdentifier] = set()
    for path in added_files:
        found.add(AddedIdentifier(path, "new_file_path", path))
    for path, lines in changed.items():
        shown = git(candidate["repo"], "show", f"{candidate['merge_commit_sha']}:{path}", check=False)
        if shown.returncode == 0 and path.endswith(".py"):
            try:
                tree = ast.parse(shown.stdout)
            except SyntaxError:
                tree = None
            if tree is not None:
                parents: dict[ast.AST, ast.AST] = {}
                for node in ast.walk(tree):
                    for child in ast.iter_child_nodes(node):
                        parents[child] = node
                for node in ast.walk(tree):
                    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.lineno in lines:
                        kind = "method" if isinstance(parents.get(node), ast.ClassDef) else "function"
                        found.add(AddedIdentifier(node.name, kind, path))
                    elif isinstance(node, ast.ClassDef) and node.lineno in lines:
                        found.add(AddedIdentifier(node.name, "class", path))
                    elif isinstance(node, ast.arg) and node.lineno in lines:
                        found.add(AddedIdentifier(node.arg, "parameter", path))
                    elif isinstance(node, ast.Attribute) and node.lineno in lines:
                        found.add(AddedIdentifier(node.attr, "attribute", path))
                    elif isinstance(node, (ast.Assign, ast.AnnAssign)) and node.lineno in lines:
                        targets = node.targets if isinstance(node, ast.Assign) else [node.target]
                        for target in targets:
                            for name in _target_names(target):
                                if name.isupper():
                                    found.add(AddedIdentifier(name, "constant", path))
        # Regex fallback covers partial/unparseable Python and attribute uses.
        for line in added_code.get(path, []):
            for name in re.findall(r"\.([A-Za-z_]\w*)", line):
                found.add(AddedIdentifier(name, "attribute", path))
            match = re.match(r"\s*(?:async\s+)?def\s+([A-Za-z_]\w*)", line)
            if match:
                found.add(AddedIdentifier(match.group(1), "function", path))
            match = re.match(r"\s*class\s+([A-Za-z_]\w*)", line)
            if match:
                found.add(AddedIdentifier(match.group(1), "class", path))
            match = re.match(r"\s*([A-Z][A-Z0-9_]*)\s*(?::[^=]+)?=", line)
            if match:
                found.add(AddedIdentifier(match.group(1), "constant", path))
    return sorted(found, key=lambda item: (item.name, item.kind, item.path))


def genuinely_new_identifiers(candidate: dict[str, Any], identifiers: list[AddedIdentifier]) -> list[AddedIdentifier]:
    result: list[AddedIdentifier] = []
    for item in identifiers:
        if item.kind == "new_file_path":
            present = git(
                candidate["repo"], "cat-file", "-e", f"{candidate['parent_sha']}:{item.name}", check=False
            ).returncode == 0
        else:
            present = git(
                candidate["repo"], "grep", "-I", "-w", "-e", item.name,
                candidate["parent_sha"], "--", check=False,
            ).returncode == 0
        if not present:
            result.append(item)
    return result


def _copied_code_evidence(statement: str, patch: str) -> dict[str, Any] | None:
    _, code, _ = _patch_additions(patch)
    gold_shingles: set[tuple[str, ...]] = set()
    for lines in code.values():
        for line in lines:
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            tokens = TOKEN.findall(stripped)
            for index in range(len(tokens) - COPIED_CODE_TOKEN_THRESHOLD + 1):
                gold_shingles.add(tuple(tokens[index:index + COPIED_CODE_TOKEN_THRESHOLD]))
    statement_tokens = TOKEN.findall(statement)
    for index in range(len(statement_tokens) - COPIED_CODE_TOKEN_THRESHOLD + 1):
        shingle = tuple(statement_tokens[index:index + COPIED_CODE_TOKEN_THRESHOLD])
        if shingle in gold_shingles:
            return {
                "rule": "copied_gold_code",
                "threshold_tokens": COPIED_CODE_TOKEN_THRESHOLD,
                "tokens": list(shingle),
            }
    return None


def detect_leakage(candidate: dict[str, Any], statement: str, patch: str | None = None) -> dict[str, Any]:
    patch = gold_patch(candidate, unified=0) if patch is None else patch
    cache_key = (
        candidate["repo"], candidate["parent_sha"], candidate["merge_commit_sha"],
        hashlib.sha256(patch.encode()).hexdigest(),
    )
    novel = _NOVEL_CACHE.get(cache_key)
    if novel is None:
        extracted = extract_added_identifiers(candidate, patch)
        novel = genuinely_new_identifiers(candidate, extracted)
        _NOVEL_CACHE[cache_key] = novel
    evidence: list[dict[str, Any]] = []
    for item in novel:
        pattern = re.escape(item.name) if item.kind == "new_file_path" else rf"(?<!\w){re.escape(item.name)}(?!\w)"
        match = re.search(pattern, statement)
        if match:
            evidence.append({
                "rule": "new_gold_identifier", "identifier": item.name,
                "identifier_kind": item.kind, "gold_path": item.path,
            })
    if (match := PATCH_SYNTAX.search(statement)):
        evidence.append({"rule": "literal_patch_syntax", "matched": match.group(0).strip()})
    if (match := PATH_LINE.search(statement)):
        evidence.append({"rule": "file_path_with_line_number", "matched": match.group(0)})
    copied = _copied_code_evidence(statement, patch)
    if copied:
        evidence.append(copied)
    for sentence in re.split(r"(?<=[.!?])\s+|\n+", statement):
        verb = FIX_INSTRUCTION.search(sentence)
        if not verb:
            continue
        for item in novel:
            if re.search(rf"(?<!\w){re.escape(item.name)}(?!\w)", sentence):
                evidence.append({
                    "rule": "fix_instruction_with_new_identifier", "verb": verb.group(0).lower(),
                    "identifier": item.name, "identifier_kind": item.kind,
                })
    # Deduplicate evidence generated by repeated AST/regex discoveries.
    unique = list({json.dumps(item, sort_keys=True): item for item in evidence}.values())
    return {
        "schema_version": 1,
        "case_id": f"{candidate['repo']}#{candidate['pr_number']}",
        "verdict": "leaked" if unique else "leak_free",
        "evidence": unique,
        "new_gold_identifiers": [item.__dict__ for item in novel],
        "thresholds": {"copied_code_tokens": COPIED_CODE_TOKEN_THRESHOLD},
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case-set", type=Path)
    parser.add_argument("--statements", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    cases = {f"{item['repo']}#{item['pr_number']}": item for item in load_case_set(args.case_set)["cases"]}
    payload = json.loads(args.statements.read_text(encoding="utf-8"))
    results = []
    for item in payload["results"]:
        candidate = cases[item["case_id"]]
        results.append({**item, "leakage": detect_leakage(candidate, item["problem_statement"])})
    json_dump(args.output, {"schema_version": 1, "results": results})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
