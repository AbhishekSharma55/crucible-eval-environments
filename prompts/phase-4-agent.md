# Codex Phase 4 — the rescue agent

Model: `gpt-5.6-sol`, high effort. New session. Read `research/phase-3-report.md` and `STRATEGY.md`, then read `scripts/` before changing anything.

**Time is short.** Roughly 22 hours to the deadline as this is written. Prefer a working, measured, honest result over an elaborate one. If you must cut, cut scope, not measurement.

---

## What we know

Phase 3 established the task and a strong baseline. B0 (stub) 0/80, B1 (single prompt) 13/80, B2 (best-of-5 with the full gate stack as selector) 22/80 = 27.5%. Ample headroom.

B2's 58 failures, by first failing gate:

| Gate | Count |
|---|---:|
| G2 — test fails at the fix too (simply broken) | 24 |
| G1 — test passes at the parent (doesn't reproduce) | 17 |
| G5 — collateral damage / wrong file placement | 9 |
| G4 — passes but doesn't exercise the fix | 5 |
| parse or model error | 3 |

Every one of the top three is addressable by execution feedback and repo inspection. B2 resamples blind. The agent should look and revise.

## What to build

A single-threaded agent. **No multi-agent architecture.** One measured multi-agent experiment comes later, in Phase 5, as an ablation.

Give it a small, explicit tool surface:

- `list_tests(module_or_path)` — where do this repo's tests for this area live, what do they look like
- `read_file(path, start, end)` — **windowed reads, not whole files**
- `search(pattern)` — grep over the repo at the parent checkout
- `write_test(path, content)` — stage the authored test
- `run_test(endpoint)` — run the staged test at `parent` or `fix`, returning exit code, per-test status, and **the actual failure output**
- `check_gates()` — run the full G1–G5 stack, returning structured per-gate evidence

Design the tool returns as a prompt surface. Error messages must be **actionable** — say what went wrong and what would fix it, not a raw traceback. Truncate long output with an explicit marker rather than dumping it.

The intended loop: inspect the repo's test conventions and existing fixtures for the module → write a test → run at fix → if broken, read the error and revise → run at parent → if it passes there, tighten it → check gates → revise → stop.

## Fairness — this matters more than the score

B2 gets 5 attempts. **Cap the agent at 5 `check_gates()` calls** so neither side gets more validation signal than the other, and cap total steps and wall clock per case.

Then report cost, tokens, and latency per candidate for the agent and every baseline, and plot accuracy against cost. If the agent wins only by spending 20× the tokens, that is a much weaker result than a smaller win at comparable cost, and we will say so in the submission. Do not hide the cost.

## Agent instructions as files

The system prompt and any tool descriptions live in `agents/*.md`, version controlled. The submission requires "the instructions that shape each agent," and the git history of those files is itself evidence for the changelog. Do not embed prompts as string literals in Python.

## Measurement

Same 80-case set. Same fixture layer, replay default, hard-fail on miss. Same pinned model.

Primary metric unchanged: **verified regression-test rate**, the fraction passing all five gates.

Report the G1–G5 failure breakdown for the agent alongside the baselines, so we can see which failure modes the loop actually fixed and which it did not. That table is the core evidence of the whole submission.

Run **k=3 rollouts** on the full case set if time allows. If it does not, run k=3 on a fixed 30-case subset and k=1 on the rest, and say exactly what you did. Report mean and spread, and pass^k alongside pass@1.

## Do not

- Do not touch held-out repos. Phase 5 only, once.
- Do not modify Phase 2 or Phase 3 artifacts or `config/split.json`.
- Do not let the agent edit source files, existing tests, or the gate code.
- Do not give the agent more gate calls than B2 gets attempts.
- Do not tune anything against the case set beyond what the changelog records.

## Report back

Write `research/phase-4-report.md`:

- Agent rate with n, k, mean and spread, pass@1 and pass^k.
- Full G1–G5 breakdown, agent vs B1 vs B2, so the deltas per failure mode are visible.
- Cost, tokens, latency per candidate for all four arms, plus the accuracy-vs-cost comparison.
- Which failure modes the loop fixed, and which it did not touch. Be specific — the ones it did not fix are the honest material for the final writeup.
- Any case where the agent appeared to game a gate rather than write a genuine test. Look for this actively and report it even if it is unflattering.
- Total project spend.
