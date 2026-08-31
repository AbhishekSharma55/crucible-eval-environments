# Codex Phase 3 — test-authoring verifier and baselines

Model: `gpt-5.6-sol`, high effort on the gate design. New session. Read `research/phase-1-report.md`, `research/phase-2-report.md`, and `STRATEGY.md`, then read the existing code in `scripts/` before changing anything.

**No agent in this phase.** Verifier and baselines only.

**Do not delete or modify any Phase 2 artifact.** The Phase 2 results are evidence for a documented removed experiment that goes in the final submission. They stay exactly as they are.

---

## Why we pivoted

Phase 2 targeted `no_linked_issue` candidates by synthesizing problem statements. The primary metric was "leak-free validated rescue rate." It failed, for a structural reason worth understanding before you build anything here.

The metric had two gates. Gate one — does the environment still validate — was **pre-satisfied by the sampling criterion**, because we only sampled candidates that already had a working transition. Gate two — does the text avoid leaking the fix — is rarely tripped by a short PR title. So the null baseline, copying the PR title verbatim with no model at all, scored **88%**. The best baseline scored 95%. Five points of headroom, and no way to tell a good problem statement from a useless one, because "Fix bug" passes both gates.

The lesson, which this phase institutionalizes: **a metric where the do-nothing baseline scores high is not measuring quality.** It measures the absence of a defect. Check the null baseline before building anything on top of a metric.

## The new task

Target the **`no_test_files_touched`** pool: PRs that fix a real bug and have a linked issue, but shipped no regression test. There are 167 in the dev repos, 161 after the 2019 cutoff.

The rescue is: **author the missing regression test.** This cannot be faked. A test either fails on the broken code and passes on the fixed code, or it does not.

The agent authoring the test **does see the gold patch.** That is the realistic task — a contractor building an eval environment has the fix in front of them. It also creates a specific cheat we must defend against: writing a test that checks the implementation rather than the behavior. The gates below exist for that.

---

## Task 0 — the null baseline, first, before anything else

Build **B0** and run it before you build the rest of the phase.

B0 emits a trivial stub for every candidate: import the touched module, `assert True`. No model call.

Run it through the gates. **Expected result: at or near 0%.**

If B0 scores meaningfully above zero, stop, do not proceed, and report immediately — it means a gate is not doing its job and the whole phase is built on sand. This check costs twenty minutes and would have saved Phase 2.

---

## Task 1 — the gates

A candidate rescue passes only if **all** hold. Each gate emits structured evidence, never a bare boolean.

**G1 — fails at the parent.** Apply only the authored test file to the parent checkout. The test must fail.

**G2 — passes at the fix.** Apply the same authored test to the fix commit. It must pass.

**G3 — fails for a behavioural reason, not a missing symbol.** This is the anti-cheat gate and the one to get right.

A legitimate regression test can fail at the parent with an *error* rather than an assertion — if the bug is an uncaught exception, the correct test triggers that exception. So do not require assertion failures.

What we reject is a test that fails only because the fix's new API does not exist yet. Concretely: reject when the parent failure is an `ImportError`, `AttributeError`, `NameError`, or `ModuleNotFoundError` whose referenced symbol is **introduced by the gold patch** (reuse the parent-existence check from the Phase 2 leakage detector — that logic is sound and directly transferable). A test asserting `new_helper()` exists is testing implementation, not behaviour.

**G4 — exercises the fix.** Run the authored test at the fix commit under coverage. It must execute at least one line changed by the gold patch. Record which lines and what fraction of changed lines were covered.

**G5 — no collateral damage.** The repo's existing selected tests still pass at both endpoints, and the authored patch adds only test files — it must not modify source.

Run each endpoint twice and reject nondeterministic outcomes, consistent with Phase 1b.

## Task 2 — the case set

Sample from the dev `no_test_files_touched` pool.

- Apply the 2019+ cutoff established in Phase 2.
- Require: a linked issue with usable text, at least one changed source file, the repo builds at the parent, and the gold patch is a real behaviour change rather than a rename, docs edit, or type annotation. Verify each rather than assuming.
- **Verify the linked-issue assumption explicitly.** These candidates should have issues because `no_linked_issue` is checked first in the pipeline, but confirm it rather than trusting the ordering.
- Stratify by repo and merge year. Target **80–100 cases**. Committed seed, deterministic, byte-identical on rerun.
- Held-out repos stay closed.

Report the pool size at each filter step so we can see what was excluded and why.

## Task 3 — baselines

All three see the same inputs: issue text, PR title and body, gold patch, and the relevant source files at the parent.

- **B0 — stub.** Task 0. Expected ~0%.
- **B1 — single prompt.** One call, temperature 0, no execution, no tools, no retry. First output is the answer.
- **B2 — best-of-N with the gate as selector.** Same prompt at temperatures 0, 0.125, 0.25, 0.375, 0.5. Run each output through the full gate stack. Accept the first that passes; up to 5 attempts.

**B2 is deliberately strong.** It gets the same external signal the Phase 4 agent will use. Do not weaken it. Published work shows plain retry frequently matches sophisticated agent architectures at a fraction of the cost, and if our agent cannot beat best-of-5-with-a-perfect-selector, that is a real finding we will report rather than hide.

The Phase 4 agent's intended edge is different in kind: exploring the repo for existing test conventions, fixtures and helpers, and *reading the failure output to revise* rather than resampling blind. Keep that distinction clean by giving B2 no repo exploration and no revision.

Same pinned model and hash-fixture layer as Phase 2. Replay is the default and hard-fails on a miss.

## Task 4 — cost and time discipline

Path B is compute-heavy and token-light, but the test runs add up: roughly 100 cases × 3 baselines × up to 5 attempts × 3 runs each.

- Per-test-run timeout, per-case wall-clock cap, parallel workers.
- Any case hitting a cap is recorded with the reason, never silently dropped.
- Log tokens and API cost per call. Spend so far is $0.086 of a ~$20 budget; state the new total.

---

## Primary metric

**Verified regression-test rate** — of the sampled candidates, the fraction where the authored test passes all five gates.

Report per baseline with n, plus cost and latency per candidate, and the G1–G5 failure breakdown so we can see *where* each baseline dies.

## Definition of done

1. B0 runs first and scores at or near zero. If not, phase halted and reported.
2. All five gates have unit tests, including: a legitimate test that errors at the parent because the bug raises an exception (must **pass** G3), and a test that errors only because a gold-patch symbol is missing (must **fail** G3).
3. `make sample-b` deterministic, byte-identical on rerun.
4. B0, B1, B2 run over the full case set, emitting `results/`.
5. Keyless replay reproduces all three rates.
6. Held-out untouched, `config/split.json` unchanged, all Phase 2 artifacts intact.

## Do not

- Do not build the rescue agent.
- Do not weaken B2.
- Do not tune gate thresholds against the case set.
- Do not let an authored test modify source files.
- Do not sample from held-out repos.
- Do not delete or edit Phase 2 results.

## Report back

Write `research/phase-3-report.md`: B0 result and what it proves about the gates, pool size at each filter step, the three baseline rates with n and cost, the G1–G5 failure breakdown per baseline, total spend, and wall clock.

Then answer directly: **how much headroom is there between B2 and 100%, and is it enough for an agent to demonstrate a real improvement?** If B2 is above roughly 85%, say so plainly and we will reconsider before building the agent rather than after. That question is the reason this phase exists.
