# Improvement Changelog

How this project actually went, including the eight hours I spent on an approach
that turned out to be unmeasurable.

Every row links to committed evidence. Where a number moved, the run that
produced it is in `results/` and the reasoning is in the phase report under
`research/`. Nothing in this table was reconstructed after the fact — each row
was written the same day the run finished.

---

## The arc in one paragraph

I started by reproducing a SWE-bench-style construction pipeline and measuring
how many real bug-fix PRs it converts into usable evaluation environments. It
converted almost none, which turned out to be my bug rather than a property of
the problem. After fixing it I tried to rescue the largest bucket of discards by
synthesizing missing problem statements, spent most of a day on it, and threw the
work away because the metric I chose could not distinguish a good output from a
useless one. The version that survived targets a different bucket and authors the
missing regression test instead — a task where the null baseline scores exactly
zero, because you cannot fake a test that fails on broken code and passes on
fixed code.

---

## Changelog

| # | Stage | What I tried and why | Evidence | Primary metric | Cost | Decision |
|---|---|---|---|---|---|---|
| 0 | **Baseline** | Reproduce the standard heuristic construction pipeline: merged PR closes an issue, touches tests, and shows a clean fail→pass transition. Run it over 700 merged PRs from 7 pinned pure-Python repos. | [`phase-1-report.md`](research/phase-1-report.md) · `data/candidates/summary.json` | **1 / 700 accepted (0.14%)** | $0 | Kept as the starting point, but the number looked wrong. |
| 1 | **Fix the baseline** | 0.14% is far below the low-single-digit yield published pipelines report. Diagnosis: most bug fixes *add* the regression test, so at the parent commit the test does not exist and cannot fail. The real pipeline splits the diff into a gold patch and a test patch and transplants **only the test patch** onto the parent. I had omitted that step. | [`phase-1-report.md` §Phase 1b](research/phase-1-report.md) | **57 / 700 (8.1%)** on the identical 700 PRs. 56 candidates flipped from rejected to accepted for this reason alone. | $0 | Kept. This was a correctness fix to my own baseline, not an improvement to my system. Reporting it any other way would have been a strawman comparison. |
| 2 | **Deepen the corpus** | The original sample was the 100 most recently updated PRs per repo, which skews to dependency bumps and CI chores. Paginated back through merge history instead. | `data/github-api/` · [`phase-1-report.md`](research/phase-1-report.md) | 3,073 PRs spanning 2014-12 to 2026-08. **153 accepted (6.72% of fully processed dev PRs)** | $0 | Kept. Yield is now in a defensible range. |
| 3 | **Rescue attempt: synthesize missing problem statements** | 2,430 of 2,804 discards (87%) fail for one reason: no linked issue, so no problem statement for a solver to read. Tried generating one from the PR title, body and diff. Built a mechanical leakage detector to catch statements that describe the fix rather than the symptom. | [`phase-2-report.md`](research/phase-2-report.md) · `results/b0.json`, `b1.json`, `b2.json` | B0 title-copy **88%** · B1 single prompt **89%** · B2 retry **95%** (n=100) | $0.086 | **Removed.** See below. |
| 4 | **Pivot: author the missing regression test** | Target a different bucket — 167 dev PRs that fix a real bug, have a linked issue, and shipped no test. Build a five-gate verifier, then measure. | [`phase-3-report.md`](research/phase-3-report.md) · `results/phase3/` | B0 stub **0 / 80** · B1 single prompt **13 / 80 (16.25%)** · B2 best-of-5 **22 / 80 (27.5%)** | $0.329 | Kept. 72.5 points of headroom and a null baseline at zero. |
| 5 | **Execution-grounded agent** | B2's failures are dominated by tests that break at both endpoints (24/58) or that never reproduce the bug (17/58) — both visible in a single test run. Gave the agent repo inspection plus the ability to run its test, read the failure, and revise. Capped at the same 5 gate checks B2 gets, so neither side buys accuracy with compute. | [`phase-4-report.md`](research/phase-4-report.md) · `agents/phase4-system.md` | **23 / 80 (28.75%)** vs B2 27.5% | 1.18× B2 | Kept, but the result was contaminated — see row 6. |
| 6 | **Measurement repair** | Row 5's run had 13 infrastructure failures, 12 of them connection resets clustered in Click during a network outage. Re-ran the **entire** 80-case arm on a stable connection. Nothing about the agent, its prompt, or the gates changed — verified by matching instruction SHA-256, seed, model, temperature and limits. | `results/phase4/summary-run2.json` · run 1 retained at `summary-run1.json` | **26 / 80 (32.5%)**, infrastructure failures 13 → 3 | $0.43 | Kept. Both runs ship. Zero selective reruns. |
| 7 | **Multi-agent split** | Planned ablation separating authoring from verification. | — | not run | — | **Cut for time.** Recorded here rather than quietly dropped. The Phase 2 removal below is the substantive negative result. |
| 8 | **Held-out evaluation** | Open `PyCQA/flake8` and `psf/black` for the first time and run all four arms on the entire verified held-out pool (n=16), unchanged agent, unchanged gates, k=1, zero selective reruns. | [`phase-5-report.md`](research/phase-5-report.md) · `results/phase5/heldout/` | B0 **0/16** · B1 **0/16** · B2 **3/16 (18.75%)** · agent **5/16 (31.25%)** | $0.182 | Kept. The agent's dev→held-out drop is **1.25 points**, against B2's 8.75 and B1's 16.25. |
| Final | | Execution-grounded single agent, 5 gate checks, unchanged from row 5. | `results/phase5/` | dev **32.5%** · held-out **31.25%** | **$1.808** total | The loop's contribution is real but bounded by step budget — see below. It does not appear to be overfitted to the development repositories. |

---

## What the agent actually contributed, and where it stalls

The aggregate rate hides the mechanism. Tracking every one of B2's 58 failures
through the agent shows what the execution loop fixed:

| B2's first failing gate | n | Agent recovered | Never reached a gate check |
|---|---:|---:|---:|
| G1 — test didn't reproduce the bug | 17 | 2 | 14 |
| G2 — test broken at both endpoints | 24 | **5** | 16 |
| G5 — collateral damage | 9 | **4** | 4 |
| G4 — didn't exercise the fix | 5 | 0 | 0 |
| output parse failure | 3 | 0 | 2 |

**11 recovered, 7 of B2's passes lost, net +4.** The recoveries land exactly where
the design predicted: broken tests and wrong-file-placement, both of which one
execution or one directory listing reveals. The loop works.

The interesting number is the right-hand column. **43 of 80 cases never reached a
gate check at all** — the agent spent its step budget inspecting the repository and
revising, then ran out before validating. Only 34 cases got that far.

So the honest reading is not "execution feedback gives +5 points." It is: *when
the agent reaches its verifier it does well, and it fails to reach its verifier
more than half the time.* The binding constraint is step budget allocation, not
the quality of the signal. That is a more useful thing to know than the headline,
and it is what I would fix first with another day.

I did not fix it here, because raising the cap would have broken the matched-budget
comparison with B2, and an unmatched win is not a win.

---

## Iteration 3, in full: the experiment I removed

This cost about eight hours and it is the most useful thing in this repository.

**The idea.** Most discarded candidates have no linked issue. A problem statement
can be synthesized from the PR diff. The obvious risk is leakage — describing the
fix instead of the symptom — so I built a deterministic detector for it. The rule
is defensible: an identifier in the problem statement counts as leakage only if it
does not exist at the parent commit. Naming a function that already exists is
describing where the symptom appears, which real issues do constantly. Naming
something the fix introduces is describing the answer.

**The metric.** "Leak-free validated rescue rate" — the fraction of candidates
converted into environments that still validate and pass the leakage detector.

**The result.**

| Baseline | Rate | Cost/candidate |
|---|---:|---:|
| B0 — copy the PR title verbatim, no model | **88.0%** | $0 |
| B1 — single prompt | 89.0% | $0.000177 |
| B2 — retry with temperature ramp | 95.0% | $0.000227 |

**What went wrong.** The metric had two gates and both were nearly free. Gate one
asked whether the environment still validates — but I had told the sampler to
draw only from candidates that already validated, so it passed 100% by
construction. Gate two asked whether the text leaks the fix, and a one-line PR
title almost never does. Copying the title scored 88%. There were five points of
headroom and no way to distinguish a good problem statement from a useless one,
because "Fix bug" passes both gates.

I had measured the *absence of a defect* and called it quality.

**The backstop failed too.** I had a solver attempt the environments, expecting
better statements to be more solvable. Rescued environments solved at 20.0%
(6/30), real issue-backed controls at 16.7% (5/30) — Wilson intervals 9.5–37.3%
and 7.3–33.6%, overlapping almost entirely. But 48 of the 60 failures were
solver-side mechanics: 26 proposed patches would not even apply. The instrument
was too weak to discriminate. Testing whether a map is useful by handing it to
someone who cannot walk.

**What I changed because of it.** Two things.

First, the Phase 3 spec makes the null baseline the *first* thing built and run,
before anything else. If a stub scores above zero, the gates are wrong and work
stops. That check takes twenty minutes and would have caught this on day one.

Second, I chose a task whose verification cannot be satisfied by omission. A test
that fails on broken code and passes on fixed code is a positive demonstration.
The stub baseline scores 0/80, not 88%.

**What I kept.** The leakage detector's parent-existence logic is reused in Phase
3's G3 gate to reject tests that fail only because a new symbol does not exist
yet. The human labeling set, the fixture layer, the case sampler and the
solvability harness all carried over. The dead end was in the metric, not the
machinery.

---

## Iteration 1, in full: why the baseline fix matters more than it looks

Fixing my own baseline from 0.14% to 8.1% made my eventual improvement look
*smaller*, and I did it anyway.

A pipeline that discards 99.86% of candidates would have been a flattering thing
to measure against. It was also wrong — and specifically wrong in a way that
inflates any system compared against it. The literature on agent evaluation is
blunt that a large fraction of reported gains dissolve when the baseline is given
the same resources as the proposed method. This one would have.

The number that matters is not how far my system is above the floor. It is how
far above a *correctly implemented* standard method it gets.

---

## Notes on measurement

- **Held-out repositories were never opened during development.** `psf/black` and
  `PyCQA/flake8` were split out at Phase 1 under seed `41729`, written to a
  separate directory behind an explicit `--allow-heldout` flag, and every phase
  verified byte-integrity of the boundary. They are evaluated once, at the end.
- **Every model call is hash-cached.** Replay is the default and hard-fails on a
  miss, so all reported numbers reproduce offline with no API key.
- **Total spend: $1.8080**, 3,688 unique requests, 43.4M tokens. API-reported, not
  estimated, and deduplicated: 80 request hashes are shared between the Phase 4
  agent run and the Phase 5 clean re-run, charged once. Summing the fixture
  directories naively gives $1.8298. Provider failures that returned no usage
  object are excluded and noted.
- The 2019 cutoff excluding 12 pre-2019 candidates was fixed **before** any
  generated output was inspected.
- **The Phase 2 leakage detector was never validated against human labels.** The
  review tool and a 50-item queue exist; the labels were not collected before the
  deadline. So Phase 2's 95% is reported as the measurement that led me to abandon
  the approach, not as a validated result. Since the approach was abandoned, this
  weakens nothing that is still standing — but it would be dishonest to present
  that detector as verified.
- Row 5's contaminated run is published alongside the clean one. A re-run that
  improves a number looks identical to a quiet reroll unless the original is kept.
