"""Export gate-passing authored tests as self-contained evaluation environments.

This reads committed results only. It never calls a model, never re-runs the
agent, and never re-runs the gates. The `verify` subcommand re-checks an
exported environment through the unchanged Phase 3 gate stack.

Nothing exported here is usable until a human accepts it. See
`scripts/review_environments.py` and `environments/README.md`.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import stat
from typing import Any

from scripts.phase2_common import ROOT, slug
from scripts.phase3_common import json_dump
from scripts.test_authoring_verifier import EXCEPTION, gate1, gate2, gate3, gate4, gate5, verify
from scripts.validate_candidates import transition_tests


ENVIRONMENTS = ROOT / "environments"
CANDIDATE_ROOT = ENVIRONMENTS / "candidate"
APPROVED_ROOT = ENVIRONMENTS / "approved"
APPROVALS = ENVIRONMENTS / "approvals.jsonl"
INDEX = ENVIRONMENTS / "index.json"
GATES = ("g1", "g2", "g3", "g4", "g5")
PHASE3_IMAGE = "crucible-sandbox:phase3"

# The published agent arm. `results/phase4/summary-run2.json` designates
# `results/phase5/task1/agent-rollout-0.json` as the clean 80-case development
# re-run (26/80), which is the figure quoted in README.md and the Phase 5
# report. `results/phase4/agent-rollout-0.json` is the earlier run1 (23/80,
# 13 infrastructure failures) and is deliberately not the export source.
SOURCES = (
    {
        "split": "dev",
        "rollout": "results/phase5/task1/agent-rollout-0.json",
        "case_set": "data/phase3/case-set.json",
        "designated_by": "results/phase4/summary-run2.json",
    },
    {
        "split": "heldout",
        "rollout": "results/phase5/heldout/agent-rollout-0.json",
        "case_set": "data/phase5/heldout-case-set.json",
        "designated_by": "results/phase5/heldout/summary.json",
    },
)

GATE_TEXT = {
    "g1": "the authored test fails at the parent commit",
    "g2": "the same test passes at the fix commit",
    "g3": "the parent failure is behavioural, not a missing symbol the fix introduces",
    "g4": "the test executes at least one line the fix changed, measured under coverage",
    "g5": "the patch adds one test file and touches nothing else",
}

VERIFY_SH = """#!/usr/bin/env bash
# Re-check this environment through the unchanged Phase 3 gate stack (G1-G5).
# Exits non-zero if any gate fails.
#
#   ./verify.sh                 offline replay (default). Re-applies the
#                               committed gate functions to the recorded gate
#                               evidence and the committed candidate record.
#                               No Docker, no network, no API key.
#
#   ./verify.sh --mode live     re-executes both endpoints in the pinned
#                               sandbox container through the same verifier
#                               the agent was scored with. Needs Docker, the
#                               crucible-sandbox:phase3 image, and the local
#                               git mirror under cache/repos/.
set -euo pipefail
HERE="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "${HERE}/../../.." && pwd)"
cd "${REPO_ROOT}"
exec "${PYTHON:-python3}" -m scripts.export_environments verify --environment "${HERE}" "$@"
"""


def load_json(path: Path) -> Any:
    if not path.is_file():
        raise RuntimeError(f"missing committed input: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def environment_id(repo: str, pr_number: int | str) -> str:
    """`owner/repo` + PR number -> `owner__repo__pr` directory name."""
    return f"{repo.replace('/', '__')}__{pr_number}"


def new_file_diff(path: str, content: str) -> str:
    """Render an added-file unified diff that `git apply` accepts."""
    trailing = content.endswith("\n")
    body = content.split("\n")
    if trailing:
        body = body[:-1]
    lines = [
        f"diff --git a/{path} b/{path}",
        "new file mode 100644",
        "--- /dev/null",
        f"+++ b/{path}",
        f"@@ -0,0 +1,{len(body)} @@",
    ]
    lines.extend("+" + line for line in body)
    if not trailing:
        lines.append("\\ No newline at end of file")
    return "\n".join(lines) + "\n"


def parse_new_file_diff(diff: str) -> dict[str, str]:
    """Inverse of `new_file_diff`, so verification reads the exported artifact."""
    lines = diff.split("\n")
    path = None
    for line in lines:
        if line.startswith("+++ b/"):
            path = line[6:]
            break
    if path is None:
        raise RuntimeError("test_patch.diff has no '+++ b/<path>' header")
    try:
        start = next(index for index, line in enumerate(lines) if line.startswith("@@ "))
    except StopIteration as exc:
        raise RuntimeError("test_patch.diff has no hunk header") from exc
    body: list[str] = []
    trailing = True
    for line in lines[start + 1:]:
        if line.startswith("+"):
            body.append(line[1:])
        elif line.startswith("\\ No newline"):
            trailing = False
        elif line == "":
            continue
        else:
            raise RuntimeError(f"unexpected line in added-file diff: {line!r}")
    content = "\n".join(body) + ("\n" if trailing else "")
    return {"path": path, "content": content}


def sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def transition_kind(verification: dict[str, Any]) -> str | None:
    """Classify the parent->fix transition the authored test creates.

    Reuses the Phase 1/2 classifier so the label means the same thing it means
    for candidates that shipped their own test.
    """
    parent = verification["gates"]["g1"]["evidence"]["runs"][0]
    fix = verification["gates"]["g2"]["evidence"]["runs"][0]
    _, kind, _ = transition_tests(parent, fix)
    return kind


def problem_statement(candidate: dict[str, Any]) -> str:
    """Issue text verbatim, then a clearly separated reference block."""
    issues = candidate.get("linked_issues") or []
    parts = [f"# {candidate['case_id']}", ""]
    parts.append("## Problem statement")
    parts.append("")
    parts.append(
        "Verbatim text of the GitHub issue(s) this pull request closed. Nothing below "
        "this heading was written for this project."
    )
    parts.append("")
    for issue in issues:
        parts.append(f"### Issue #{issue.get('number')} — {issue.get('url')}")
        parts.append("")
        parts.append(issue.get("body") or "")
        parts.append("")
    parts.append("## Reference (not part of the problem statement)")
    parts.append("")
    parts.append(
        "Solution-adjacent metadata. Withhold this section from any agent under "
        "evaluation; it names the fixing pull request and its commits."
    )
    parts.append("")
    parts.append(f"- Repository: `{candidate['repo']}`")
    parts.append(f"- Pull request: {candidate['url']}")
    parts.append(f"- Pull request title: {candidate['title']}")
    parts.append(f"- Merged at: {candidate['merged_at']}")
    parts.append(f"- Parent commit (bug present): `{candidate['parent_sha']}`")
    parts.append(f"- Fix commit (bug absent): `{candidate['merge_commit_sha']}`")
    parts.append(f"- Changed source paths: {', '.join(candidate.get('source_files') or []) or '(none)'}")
    parts.append("")
    return "\n".join(parts)


def gate_block(verification: dict[str, Any]) -> dict[str, Any]:
    return {
        name: {
            "check": GATE_TEXT[name],
            "status": verification["gates"][name]["status"],
            "reason": verification["gates"][name]["reason"],
            "evidence": verification["gates"][name]["evidence"],
        }
        for name in GATES
    }


def build_metadata(
    result: dict[str, Any], candidate: dict[str, Any], rollout: dict[str, Any], source: dict[str, Any]
) -> dict[str, Any]:
    verification = result["verification"]
    coverage = verification["gates"]["g4"]["evidence"]
    return {
        "schema_version": 1,
        "environment_id": environment_id(candidate["repo"], candidate["pr_number"]),
        "case_id": result["case_id"],
        "split": source["split"],
        "repo": candidate["repo"],
        "pr_number": candidate["pr_number"],
        "pr_url": candidate["url"],
        "pr_title": candidate["title"],
        "merged_at": candidate["merged_at"],
        "parent_sha": candidate["parent_sha"],
        "fix_sha": candidate["merge_commit_sha"],
        "linked_issues": candidate.get("linked_issues") or [],
        "source_files": candidate.get("source_files") or [],
        "test_path": result["authored_test"]["path"],
        "test_patch_sha256": sha256(new_file_diff(result["authored_test"]["path"], result["authored_test"]["content"])),
        "transition_kind": transition_kind(verification),
        "coverage": {
            "changed_line_fraction": coverage["changed_line_fraction"],
            "changed_line_count": coverage["changed_line_count"],
            "covered_changed_line_count": coverage["covered_changed_line_count"],
            "changed_lines": coverage["changed_lines"],
            "covered_changed_lines": coverage["covered_changed_lines"],
        },
        "gates": gate_block(verification),
        "gate_status": {name: verification["gates"][name]["status"] for name in GATES},
        "gates_are_necessary_not_sufficient": (
            "The five gate verdicts above are necessary, not sufficient. They mean the test "
            "fails at the parent, passes at the fix, fails behaviourally, touches a changed "
            "line and edits nothing but one new test file. They do not mean the test captures "
            "the behaviour a user would recognise as the bug. That judgement belongs to the "
            "human reviewer and is recorded in environments/approvals.jsonl."
        ),
        "authored_by": {
            "model": rollout["model"],
            "temperature": rollout["temperature"],
            "arm": rollout["arm"],
            "rollout": rollout["rollout"],
            "rollout_seed": result["rollout_seed"],
            "accepted_gate_call": result["accepted_gate_call"],
            "gate_calls_spent": result["gate_calls"],
            "model_turns": result["model_turns"],
            "tool_steps": result["tool_steps"],
            "stop_reason": result["stop_reason"],
            "instruction_sha256": rollout["instruction_sha256"],
            "limits": rollout["limits"],
        },
        "gaming_flags": result.get("gaming_flags") or [],
        "provenance": {
            "rollout_result": source["rollout"],
            "case_set": source["case_set"],
            "designated_by": source["designated_by"],
            "verifier": "scripts/test_authoring_verifier.py",
            "sandbox_image": PHASE3_IMAGE,
            "note": "Exported from committed results. The agent and the gates were not re-run.",
        },
        "human_review": {
            "required": True,
            "status": "pending",
            "approvals_file": "environments/approvals.jsonl",
            "review_command": "make review-environments REVIEWER='your name'",
            "promote_command": "make promote-environments",
        },
    }


def write_environment(directory: Path, metadata: dict[str, Any], candidate: dict[str, Any], authored: dict[str, str]) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "problem_statement.md").write_text(problem_statement(candidate), encoding="utf-8")
    (directory / "test_patch.diff").write_text(new_file_diff(authored["path"], authored["content"]), encoding="utf-8")
    json_dump(directory / "metadata.json", metadata)
    script = directory / "verify.sh"
    script.write_text(VERIFY_SH, encoding="utf-8")
    script.chmod(script.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


def collect(source: dict[str, Any]) -> list[tuple[dict[str, Any], dict[str, Any], dict[str, Any]]]:
    rollout = load_json(ROOT / source["rollout"])
    cases = {case["case_id"]: case for case in load_json(ROOT / source["case_set"])["cases"]}
    collected = []
    for result in rollout["results"]:
        if not result.get("passed"):
            continue
        candidate = cases.get(result["case_id"])
        if candidate is None:
            raise RuntimeError(f"{result['case_id']} passed but is absent from {source['case_set']}")
        collected.append((result, candidate, rollout))
    return collected


def index_entry(metadata: dict[str, Any]) -> dict[str, Any]:
    return {
        "environment_id": metadata["environment_id"],
        "path": f"candidate/{metadata['environment_id']}",
        "case_id": metadata["case_id"],
        "split": metadata["split"],
        "repo": metadata["repo"],
        "pr_number": metadata["pr_number"],
        "merged_at": metadata["merged_at"],
        "parent_sha": metadata["parent_sha"],
        "fix_sha": metadata["fix_sha"],
        "test_path": metadata["test_path"],
        "transition_kind": metadata["transition_kind"],
        "changed_line_fraction": metadata["coverage"]["changed_line_fraction"],
        "gate_status": metadata["gate_status"],
        "gaming_flags": metadata["gaming_flags"],
        "model": metadata["authored_by"]["model"],
        "human_review_status": "pending",
    }


def export(root: Path = ENVIRONMENTS) -> dict[str, Any]:
    candidate_root = root / "candidate"
    entries: list[dict[str, Any]] = []
    for source in SOURCES:
        for result, candidate, rollout in collect(source):
            metadata = build_metadata(result, candidate, rollout, source)
            write_environment(candidate_root / metadata["environment_id"], metadata, candidate, result["authored_test"])
            entries.append(index_entry(metadata))
    entries.sort(key=lambda item: (item["split"], item["environment_id"]))
    counts = {"total": len(entries)}
    for source in SOURCES:
        counts[source["split"]] = sum(1 for item in entries if item["split"] == source["split"])
    index = {
        "schema_version": 1,
        "counts": counts,
        "sources": list(SOURCES),
        "selection": "every case whose agent rollout passed all five gates (G1-G5)",
        "human_review": {
            "required": True,
            "approved_count": 0,
            "note": (
                "No environment in candidate/ has been approved. Gate verdicts are "
                "necessary, not sufficient. Only environments a human explicitly accepts "
                "are promoted to approved/."
            ),
        },
        "environments": entries,
    }
    json_dump(root / "index.json", index)
    (root / "README.md").write_text(readme(counts), encoding="utf-8")
    approvals = root / "approvals.jsonl"
    if not approvals.exists():
        approvals.write_text("", encoding="utf-8")
    (root / "approved").mkdir(parents=True, exist_ok=True)
    (root / "approved" / ".gitkeep").write_text("", encoding="utf-8")
    return index


def readme(counts: dict[str, int]) -> str:
    return f"""# Environments

{counts['total']} candidate evaluation environments ({counts['dev']} development, {counts['heldout']} held-out),
one per bug-fix pull request whose missing regression test the Crucible agent
authored and whose authored test passed all five gates.

**Nothing in `candidate/` is approved.** These are proposals. A human reviewer
decides whether each authored test genuinely captures the bug's behaviour, and
only what a human explicitly accepts is copied into `approved/`.

## What an environment is

A directory named `<owner>__<repo>__<pr>` containing:

| File | Contents |
|---|---|
| `problem_statement.md` | The linked GitHub issue text, verbatim, plus a clearly separated reference block naming the repository, the pull request and both commits. |
| `test_patch.diff` | The regression test the agent authored, as an added-file unified diff that `git apply` accepts. |
| `metadata.json` | Repository, parent SHA, fix SHA, PR number, merge date, split, all five gate verdicts with their full evidence, the G4 coverage fraction, the authoring model, and the transition kind. |
| `verify.sh` | Re-checks the environment through the unchanged Phase 3 gate stack. Exits non-zero if any gate fails. |

`index.json` lists every environment with its gate statuses, coverage fraction
and review status.

## How to evaluate a coding agent with one

1. Check out `metadata.json:repo` at `metadata.json:parent_sha`. The bug is
   present at this commit.
2. Give the agent everything above the `## Reference` heading in
   `problem_statement.md`. Withhold the reference block, `test_patch.diff` and
   `metadata.json:fix_sha` — each of them names or points at the fix.
3. Let the agent edit source files only.
4. Apply `test_patch.diff` on top of the agent's patch and run the test at
   `metadata.json:test_path`.
5. The agent succeeds if that test passes. It failed at `parent_sha` before the
   agent touched anything, which is what `verify.sh` re-establishes.

`metadata.json:gates.g5.evidence.selected_existing_tests` names existing tests
that pass at both endpoints; run them as the regression control.

## Re-checking an environment

```sh
environments/candidate/<id>/verify.sh              # offline replay, no Docker
environments/candidate/<id>/verify.sh --mode live  # re-executes both endpoints
```

Replay re-applies the committed gate functions to the recorded gate evidence and
the committed candidate record. It needs no network, no API key and no Docker.
Live mode re-runs both endpoints in the pinned `crucible-sandbox:phase3`
container through `scripts/test_authoring_verifier.py`, and needs Docker plus the
local git mirror under `cache/repos/`.

## The gates are necessary, not sufficient

All five gates passing means:

- **G1** the authored test fails at the parent commit
- **G2** the same test passes at the fix commit
- **G3** it fails for a behavioural reason, not because a symbol the fix
  introduces does not exist yet
- **G4** it executes at least one line the fix actually changed, under coverage
- **G5** it adds one test file and touches nothing else

It does **not** mean the test captures the behaviour a user of the library would
recognise as the bug. A test can satisfy every gate and still assert something
incidental that happens to correlate with the fix. That judgement is the human
reviewer's, and is the reason `approved/` exists.

`metadata.json:gaming_flags` carries the automated gate-gaming scanner's output
for the accepted revision. Flags are review evidence only; they never rejected or
selected anything. Read the test.

## Reviewing and promoting

```sh
make export-environments                          # rebuild candidate/ from committed results
make review-environments REVIEWER='your name'     # one environment at a time, resumable
make promote-environments                         # copies accepted environments into approved/
```

Review verdicts append to `approvals.jsonl` with the reviewer's identity, a UTC
timestamp, a free-text note and a hash of the reviewed artifact. Promotion
refuses any environment without an explicit `accept`, and refuses an accept whose
artifact hash no longer matches.

## Known limitations

The construction method is SWE-bench's. Remaining differences, stated so they are
not discovered:

- Seven pure-Python repositories and a single Python 3.11 sandbox, against
  SWE-bench's larger repository and environment matrix.
- Test selection is at changed-test-file granularity rather than project-specific
  target extraction.
- The fix endpoint is the cached merge commit and the parent is its first parent;
  no synthetic base-plus-gold checkout is reconstructed.
- Arbitrary historical commits run against the modern pinned dependency set, which
  is why candidates before 2019 are excluded — that cutoff was fixed before any
  generated output was inspected.
- Issue linkage comes from GitHub's closing references; textual mentions that
  create no closing relationship count as unlinked.

Two further limitations specific to these environments:

- The regression test was written by a model, not by the maintainer who fixed the
  bug. That is the entire point of the project and also its main risk, which is
  why the human gate is not optional.
- Held-out environments come from `PyCQA/flake8` and `psf/black`, which were
  opened exactly once, at the end of the project. Development environments come
  from repositories the agent's design was iterated against.
"""


def replay_gate3(parent_run: dict[str, Any], introduced: list[dict[str, Any]]) -> dict[str, Any]:
    """Re-apply the G3 decision rule to recorded evidence.

    Used only when the git mirror is absent, since recomputing the introduced
    symbols needs the gold patch, which an environment deliberately does not
    ship. The exception regex and the match rule are the verifier's own.
    """
    text = "\n".join((parent_run.get("stdout_tail", ""), parent_run.get("stderr_tail", "")))
    failures = [{"exception": match.group(1), "message": match.group(2).strip()} for match in EXCEPTION.finditer(text)]
    matches = []
    for failure in failures:
        for item in introduced:
            names = {item["name"]}
            if item.get("kind") == "new_file_path":
                names.update({
                    item["name"].removesuffix(".py").replace("/", "."),
                    item["name"].rsplit("/", 1)[-1].removesuffix(".py"),
                })
            if any(re.search(rf"(?<!\w){re.escape(name)}(?!\w)", failure["message"]) for name in names if name):
                matches.append({**failure, "introduced_symbol": item["name"]})
    return {
        "status": "fail" if matches else "pass",
        "reason": "parent_failure_depends_on_gold_introduced_symbol" if matches else None,
        "evidence": {"parent_exceptions": failures, "introduced_symbols": introduced, "matches": matches},
    }


def candidate_for(metadata: dict[str, Any]) -> dict[str, Any]:
    source = next(item for item in SOURCES if item["split"] == metadata["split"])
    cases = load_json(ROOT / source["case_set"])["cases"]
    for case in cases:
        if case["case_id"] == metadata["case_id"]:
            return case
    raise RuntimeError(f"{metadata['case_id']} is not in {source['case_set']}")


def replay(metadata: dict[str, Any], candidate: dict[str, Any]) -> dict[str, Any]:
    recorded = metadata["gates"]
    gates = {
        "g1": gate1(recorded["g1"]["evidence"]["runs"]),
        "g2": gate2(recorded["g2"]["evidence"]["runs"]),
        "g4": gate4(candidate, recorded["g4"]["evidence"]["coverage_run"]),
        "g5": gate5(candidate, recorded["g5"]["evidence"]["authored_patch_boundary"]),
    }
    if (ROOT / "cache/repos" / f"{slug(candidate['repo'])}.git").is_dir():
        gates["g3"] = gate3(candidate, recorded["g1"]["evidence"]["runs"][0])
        method = "g3_recomputed_from_gold_patch"
    else:
        gates["g3"] = replay_gate3(recorded["g1"]["evidence"]["runs"][0], recorded["g3"]["evidence"]["introduced_symbols"])
        method = "g3_reapplied_to_recorded_evidence"
    return {
        "mode": "replay",
        "method": method,
        "passed": all(gates[name]["status"] == "pass" for name in GATES),
        "gates": gates,
    }


def run_verify(directory: Path, mode: str, image: str) -> int:
    metadata = load_json(directory / "metadata.json")
    authored = parse_new_file_diff((directory / "test_patch.diff").read_text(encoding="utf-8"))
    candidate = candidate_for(metadata)
    print(f"environment : {metadata['environment_id']}  ({metadata['split']})")
    print(f"case        : {metadata['case_id']}")
    print(f"test        : {authored['path']}")
    print(f"mode        : {mode}")
    if authored["path"] != metadata["test_path"]:
        print(f"FAIL: test_patch.diff adds {authored['path']}, metadata says {metadata['test_path']}")
        return 1
    if mode == "live":
        result = verify(candidate, authored, image=image)
        result = {"mode": "live", "method": "phase3_verifier", "passed": result["passed"], "gates": result["gates"]}
    else:
        result = replay(metadata, candidate)
    print(f"method      : {result['method']}")
    print("")
    failed = []
    for name in GATES:
        gate = result["gates"][name]
        recorded_status = metadata["gate_status"][name]
        agrees = gate["status"] == recorded_status
        marker = "ok  " if gate["status"] == "pass" and agrees else "FAIL"
        detail = gate["reason"] or GATE_TEXT[name]
        print(f"  [{marker}] {name.upper()}  {gate['status']:<5} (recorded {recorded_status})  {detail}")
        if gate["status"] != "pass" or not agrees:
            failed.append(name.upper())
    fraction = result["gates"]["g4"]["evidence"].get("changed_line_fraction")
    print("")
    print(f"  G4 changed-line coverage: {fraction}")
    print(f"  transition kind         : {metadata['transition_kind']}")
    if failed:
        print(f"\nFAIL: {', '.join(failed)}")
        return 1
    print("\nPASS: all five gates hold. Gates are necessary, not sufficient — a human")
    print("still decides whether this test captures the bug. See environments/README.md.")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command")
    sub.add_parser("export", help="write environments/ from committed results")
    verify_parser = sub.add_parser("verify", help="re-check one exported environment")
    verify_parser.add_argument("--environment", type=Path, required=True)
    verify_parser.add_argument("--mode", choices=("replay", "live"), default="replay")
    verify_parser.add_argument("--image", default=PHASE3_IMAGE)
    args = parser.parse_args(argv)
    if args.command == "verify":
        return run_verify(args.environment, args.mode, args.image)
    index = export()
    counts = index["counts"]
    print(f"exported {counts['total']} environments to {CANDIDATE_ROOT.relative_to(ROOT)}")
    for source in SOURCES:
        print(f"  {source['split']:<8} {counts[source['split']]:>3}  from {source['rollout']}")
    print(f"index    : {INDEX.relative_to(ROOT)}")
    print(f"approvals: {APPROVALS.relative_to(ROOT)} ({sum(1 for _ in APPROVALS.read_text(encoding='utf-8').splitlines() if _.strip())} records)")
    print("None are approved. Run: make review-environments REVIEWER='your name'")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
