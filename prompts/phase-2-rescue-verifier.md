# Codex Phase 2 — rescue verifier, leakage detection, and baselines

Model: `gpt-5.6-sol`, high effort on the leakage detector and the solvability harness. New session. Read `research/phase-1-report.md` (both sections) and `STRATEGY.md` first, then read the code in `scripts/` before changing it.

**No rescue agent in this phase.** We build the thing that judges a rescue before we build the thing that performs one, for the same reason we built the transition verifier before the harvest filter: if the judge is wrong, every number downstream is wrong.

---

## Background

Phase 1b established an honest baseline. Its reject pool is dominated by one reason:

| Reject reason | Count | Share |
|---|---:|---:|
| `no_linked_issue` | 2,430 | 86.7% |
| `no_test_files_touched` | 219 | 7.8% |
| `tests_no_clean_fail_to_pass` | 116 | 4.1% |
| `no_source_files_touched` | 34 | 1.2% |
| `nondeterministic_test_outcome` | 5 | 0.2% |

We are going after `no_linked_issue`. Those PRs have a valid fail→pass transition available but no issue text, and SWE-bench-style construction uses the linked issue as the **problem statement** — the text a solver agent reads to know what to fix. No issue, no environment, candidate discarded.

The rescue is to synthesize a problem statement from the PR title, body, and diff. The obvious failure is **leakage**: describing the fix instead of the symptom. "Add a `None` guard in `parser.py` line 42" is leaked; a solver passing it has demonstrated nothing. A rescued environment is only valid if it validates, is leak-free, and is still genuinely solvable.

---

## Task 0 — two corrections from the Phase 1b review

**0a. Collection-error fan-out.** Seven accepted candidates hit collection errors at the parent and fan out to 804 passing fix node IDs, against 393 from the other 146. So 4.6% of accepted candidates generate 67% of all transitioned node IDs. Keep these candidates, but:

- Flag them with `transition_kind: collection_error` vs `assertion_failure`.
- Exclude collection-only transitions from any per-test statistic we report.
- Where possible, narrow the credited transition set to tests actually touched by the test patch, rather than every test in the newly-collectable file.

This is also an exploit channel for a later agent — break collection at the parent, get credited for the whole file. Note it in the report.

**0b. Yield by year.** The corpus spans 2014-12 to 2026-08, but arbitrary historical commits run against the *modern* pinned dependency set. A 2015 PR can fail for environment reasons unrelated to the PR. Produce a table of candidate count, accept count, and accept rate **bucketed by merge year**. If yield collapses before some cutoff, we need to know before sampling cases, because otherwise PR age confounds every downstream comparison.

---

## Task 1 — the evaluation case set

Sample the cases we will use for all Phase 2+ measurement.

- Draw from `no_linked_issue` candidates **in the dev repos only**.
- **Stratify by repo and by merge year**, informed by Task 0b. Exclude year buckets where the environment confound makes results uninterpretable, and say which you excluded and why.
- Only sample candidates that have a **valid fail→pass transition available** — i.e. they would have been accepted but for the missing issue. Verify this, don't assume it. A candidate with no recoverable transition is not rescuable by writing text, and including it would just add noise.
- **Target 80–120 cases.** Large enough for a stable rate, small enough to run repeatedly.
- Write the sample to disk with a committed seed. Deterministic, same discipline as `make split`.
- Held-out repos (Black, Flake8) remain closed. Do not sample from them.

---

## Task 2 — the leakage detector

Mechanical, deterministic, no LLM. This is the external signal the whole project rests on.

**Core rule:** an identifier mentioned in the problem statement is leakage **only if it does not exist at the parent commit**. Naming a function that already exists is describing where the symptom appears, which is legitimate and appears in real issues constantly. Naming a function, parameter, class, or constant *introduced by the gold patch* is describing the solution.

So:

1. Parse the gold patch. Extract added identifiers — functions, classes, methods, parameters, constants, attribute names, new file paths.
2. Determine which of those are genuinely new by checking their presence in the parent checkout.
3. Scan the problem statement for those new identifiers.
4. Separately flag hard leakage regardless of identifier novelty:
   - literal diff hunks or patch syntax
   - file-path-plus-line-number references (`parser.py:42`)
   - contiguous code spans copied from the gold patch above a stated token threshold
   - explicit fix instructions ("add", "change X to Y", "replace") combined with a gold-patch identifier

Emit a structured verdict per candidate: `leak_free | leaked`, with the specific triggering evidence. Never a bare boolean — we need to show a judge *why*.

Tune nothing against the eval sample. Thresholds get set from first principles and stated in the report.

## Task 3 — validate the leakage detector against human labels

**This is the highest-value item in the phase and you must not do the labeling yourself.**

Build the tooling; a human supplies the ground truth. A detector validated against labels the same system generated is worthless, and claiming otherwise in the submission would be dishonest.

- Build a minimal CLI review tool that shows one problem statement at a time alongside the gold patch, and records a human verdict of `leak_free | leaked | unsure`, plus a free-text note.
- Store labels in a committed file with the labeler's identity and a timestamp.
- Pre-generate **50 problem statements to label**, drawn from a mix of baseline outputs (Task 4) so the set contains both clean and leaky examples. Do not balance it artificially — record the natural rate.
- Once labels exist, compute and report: 2×2 confusion matrix, TPR, TNR, **Cohen's κ** (not raw agreement), and the disagreement list with each case's evidence.
- Target TPR and TNR above 0.90; below 0.80 the detector is not fit for purpose and we revise the rules, not the labels.

Leave the labeling step as a documented manual command. The human running it is a real human-in-the-loop checkpoint and it goes in the trajectory.

## Task 4 — baselines

Three, all producing a problem statement from PR title + body + diff, all measured on the same case set.

- **B0 — template.** Use the PR title verbatim as the problem statement. Zero model cost. Honest floor.
- **B1 — single prompt.** One call, basic instructions, no tools, no verification, no retry. This is what the challenge PDF describes as a reasonable simple baseline.
- **B2 — prompt with retry-and-warming.** Same prompt, re-invoked up to 5 times with temperature ramped 0 → 0.5, accepting the first output that passes the leakage detector.

B2 matters: published work shows plain retry often matches sophisticated agent architectures at a fraction of the cost, and an evals-literate judge will ask whether we tested it. **B2 is the number our agent has to beat**, not B0.

Model for B1/B2: use a cheap high-capability model via OpenRouter; the total budget for this project is about $20, so log token counts and cost per call from the start. Route every model call through a hash-cache fixture layer now — `replay` as the default mode, hard-failing on a cache miss — so all of this reproduces offline later. Do not defer that layer; retrofitting it is far more expensive.

## Task 5 — solvability, on a sample, with a control group

A leak-free environment is still worthless if nobody can solve it, or if everybody can.

- Sample **30 rescued** environments and **30 accepted** environments (the real issue-backed ones from Phase 1b) as a control group.
- Run a solver agent on each, in the sandbox, network off, **with no access to the gold patch**. Score by the existing transition check.
- Report solve rate for both groups.

The comparison is the point. If rescued environments are solved at a substantially *higher* rate than real issue-backed ones, that is evidence of leakage the mechanical detector missed. If they are solved at a much lower rate, the statements are too vague to be useful. We want the bands to overlap.

Bound the cost hard: single attempt per environment, an explicit step and wall-clock cap per run, and abort with the reason recorded. State the total spend. If 60 runs is infeasible in time or budget, reduce N and say so plainly rather than quietly sampling less.

---

## Primary metric for the phase

**Leak-free validated rescue rate** — of the sampled `no_linked_issue` candidates, the fraction converted into environments that both still validate the fail→pass transition and pass the leakage detector.

Report it for B0, B1, B2 with n, and with cost and latency per candidate alongside.

---

## Definition of done

1. `make sample` is deterministic and produces the committed case set.
2. Leakage detector has unit tests, including a case where a legitimately pre-existing identifier is mentioned and correctly **not** flagged.
3. The human labeling tool runs, and the report states clearly that labels are pending until a human completes them.
4. B0, B1, B2 all run over the full case set and emit `results/*.json`.
5. All model calls go through the fixture layer; a second run in `replay` mode with no API key reproduces the results.
6. Held-out repos untouched; `config/split.json` unchanged.

## Do not

- Do not build the rescue agent. Phase 3.
- Do not label the leakage ground truth yourself.
- Do not tune detector thresholds against the eval sample.
- Do not let the solver see the gold patch or reach the network.
- Do not sample from held-out repos.
- Do not weaken B2 to make a later agent look better. It is supposed to be hard to beat.

## Report back

Write `research/phase-2-report.md`: the year-yield table and which buckets you excluded, case-set composition, leakage-detector rules and thresholds with rationale, B0/B1/B2 rates with n and cost, solvability rates for both groups, total spend so far, and your honest read on whether the leak-free rescue rate leaves enough headroom for an agent to demonstrate improvement. If B2 already scores near the ceiling, say so — we would rather redesign now than discover it in the final evaluation.
