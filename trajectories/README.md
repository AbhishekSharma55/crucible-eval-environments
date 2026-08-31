# Trajectories

Every agent that took part in this project, and the raw record of what it did.

Two different agents are involved, and they must not be confused:

| Directory | Agent | Role |
|---|---|---|
| `crucible/` | **Crucible rescue agent** — `deepseek/deepseek-v4-flash`, temperature 0.2 | The agent **under evaluation**. It is the subject of the measurement, not an author of this repository. |
| `codex/` | **Codex implementation agent** — OpenAI Codex CLI 0.151.0, model `gpt-5.6-sol` | The agent that **built** this repository: the sandbox, the corpus, the gates, the baselines, and the evaluated agent itself. |

---

## `crucible/` — the agent under evaluation

A single-threaded, execution-grounded test-authoring agent. Given a real bug-fix pull request,
it must author a *new* test that fails at the parent commit and passes at the fix commit, and
that survives all five gates G1–G5. It is the thing the whole project measures.

Its instructions are version-controlled at the repository root and are **not** duplicated here,
so there is exactly one authoritative copy:

- system prompt — [`agents/phase4-system.md`](../agents/phase4-system.md)
- task template — [`agents/phase4-task.md`](../agents/phase4-task.md)
- native tool schemas — [`agents/phase4-tools.md`](../agents/phase4-tools.md)

The SHA-256 hash of each of those three files is recorded inside every rollout result, and each
exported trajectory reprints the hashes for the run it came from.

Its only capabilities are `list_tests`, windowed `read_file`, bounded `search`, test-only
`write_test`, one-endpoint `run_test`, and `check_gates`. It cannot write source, existing tests,
or gate code. Host-side limits per case: 30 tool steps, 16 model turns, 360 seconds, and 5 full
G1–G5 validations.

### The three exported cases

Chosen to be representative rather than flattering — one of the three is a failure and one
contains a genuine gate-evasion attempt.

| File | Case | Outcome | Why this one |
|---|---|---|---|
| `marshmallow-code-marshmallow-1631.md` | `marshmallow-code/marshmallow#1631` | **PASS** | Clean success. One staged test, no revision, one gate call, all five gates pass. |
| `marshmallow-code-marshmallow-2141.md` | `marshmallow-code/marshmallow#2141` | **FAIL** | Failure *with a retry*. Gate call 1 fails G4, the agent reads more source and revises, gate call 2 fails G4 again, it stages a third revision and runs out of model turns. Shows the execution-feedback loop retrying and not recovering. |
| `pallets-flask-5242.md` | `pallets/flask#5242` | **PASS** | The gate-evasive intermediate revision flagged in the Phase 4 report. Listed in `gaming_flagged_case_ids` in [`results/phase4/summary.json`](../results/phase4/summary.json). Staged revision 1 hid its assertions behind `if recorded:`, which would also have passed at the parent; the agent replaced it with an unconditional `pytest.warns` before ever gate-checking it, and that unconditional version is what passed. Both revisions are reproduced in full. |

All three come from `results/phase4/agent-rollout-0.json` (Phase 4, rollout 0).

### Format

Each Markdown file has: run identity and limits, the instruction hashes, then the trajectory as
numbered steps. Every step shows the agent's reasoning before the call, the tool call arguments,
the tool response, and what the agent did next and why. Long tool output is shortened with an
explicit `[truncated: N of M chars]` marker — the untruncated record is always available in the
raw JSON.

### `crucible/raw/`

The unmodified JSON object for each of the three cases, extracted verbatim from the rollout
file. Nothing is redacted or reformatted beyond pretty-printing. The complete set of all 80
Phase 4 trajectories, and the held-out trajectories, remain in `results/phase4/` and
`results/phase5/`.

---

## `codex/` — the implementation agent

Raw Codex CLI session logs (JSONL) for the sessions that built this repository, copied from
`~/.codex/sessions/2026/08/`. Eight session files across three day-directories; six carry real
implementation work and two are near-empty aborted starts.

`codex/INDEX.md` maps each session file to the phase it implemented (1, 1b, 2, 3, 4, 5), with
timestamps and line counts.

**Secrets:** every file was scanned for `sk-`, `OPENROUTER`, and `GITHUB_TOKEN` patterns before
copying. One live `OPENROUTER_API_KEY` was found in the Phase 2 session and replaced with
`[REDACTED_API_KEY]` (6 occurrences). A post-copy re-scan reports 0 residual matches. Details and
the machine-readable check are in `codex/INDEX.md` and `codex/.redaction-check.json`.

---

## Also disclosed: the finishing session

The Codex Phase 5 session (file 8) hit its usage limit before the held-out agent arm finished.
A **Claude Code session (Opus)** carried out the remaining execution: it resumed the same
checkpointed `results/phase5/heldout/agent-rollout-0.json` rollout under the identical command,
wrote `results/phase5/heldout/summary.json` and `research/phase-5-report.md`, and produced this
`trajectories/` export. It changed no agent, prompt, gate, or split configuration, and it reran
no individual case. Its own session log is not exported here; its effect on the repository is
visible entirely in the git history and in the artifacts named above.
