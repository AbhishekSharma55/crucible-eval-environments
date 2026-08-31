# Phase 3 report — test-authoring verifier and baselines

Date: 2026-08-31

## Outcome

The test-authoring task has a useful quality metric. The mandatory null baseline
passed **0/161** candidates in the post-cutoff raw pool, so the phase continued.
On the fixed 80-case set, B0 passed **0/80**, B1 passed **13/80 (16.25%)**, and
B2 passed **22/80 (27.5%)**.

B2 therefore leaves **72.5 percentage points of headroom to 100%**, or 58 of
the 80 cases. This is enough room for a repo-exploring, failure-revising agent to
demonstrate a real improvement. B2 is nowhere near the roughly 85% stop-and-
reconsider level; it is 57.5 points below it.

No rescue agent was built in this phase.

## B0 was run first

Before the remaining Phase 3 machinery or case set was built, the mechanical B0
stub was run against all 161 dev `no_test_files_touched` candidates at or after
the 2019 cutoff. Each stub imported a touched module and unconditionally asserted
`True`. The result was:

| pool | n | verified | rate | first failure |
|---|---:|---:|---:|---|
| raw post-cutoff dev pool | 161 | 0 | 0.0% | G1 101; G2 60 |
| final case set | 80 | 0 | 0.0% | G1 74; G2 6 |

The raw check took 289.611 seconds. Most stubs did not fail at the parent and
therefore died at G1. The remainder imported unsuccessfully at both endpoints:
they satisfied G1 only by erroring, then failed G2 because the fix endpoint also
errored. None could pass the transition. This is the desired contrast with Phase
2: the null output scores zero, so the metric measures a demonstrated behavioral
transition rather than merely the absence of a defect.

The raw result is in `results/phase3/b0-preflight.json`; the final-case result is
in `results/phase3/b0.json`.

## Verifier

A rescue passes only when all five structured gates pass:

1. **G1, parent failure.** The authored test is run twice at the parent and must
   fail deterministically.
2. **G2, fix pass.** The same test is run twice at the fix and must pass
   deterministically.
3. **G3, behavioral failure.** Parent errors are allowed. The gate rejects only
   `ImportError`, `AttributeError`, `NameError`, or `ModuleNotFoundError` evidence
   that names an identifier introduced by the gold patch and proven absent at
   the parent. It directly reuses Phase 2's added-identifier extraction and
   parent-existence checks.
4. **G4, fix exercised.** A small pytest tracing plugin records executed source
   lines at the fix. At least one nonblank, non-comment fix-side line added by
   the gold patch must execute. The result records the changed lines, covered
   changed lines, and covered fraction.
5. **G5, no collateral damage.** The authored patch must add one new file in the
   repository's configured test layout and cannot alter an existing test or any
   source file. A deterministically selected nearby existing test must pass twice
   at both endpoints.

Every run emits endpoint, commit, stage, exit code, test outcomes, bounded output
tails, duration, and (for G4) line coverage. A 60-second test-run timeout, a
360-second case cap, and six parallel workers bound execution. One B2 case,
`pallets/click#1587`, hit the case cap; it was retained with
`case_wall_clock_exceeded` and a measured teardown-inclusive duration of 360.541
seconds. It was not dropped.

Each endpoint checkout is a fresh clone inside an ephemeral, network-disabled
Docker container. The runner checks out the historical commit, installs only
from pinned offline environments, writes the proposed test after installation,
runs pytest, emits JSON evidence, and exits under Docker `--rm`. This is why a
baseline run creates and removes many short-lived containers: endpoint repeats,
coverage, controls, and B2 attempts must not share mutable checkout state.

Historical Flask, Marshmallow, and Tenacity dependency profiles were added to
avoid treating modern dependency incompatibilities as project failures. The
profiles are selected from merge year and are fixed independently of baseline
outcomes.

### Gate tests

`tests/test_phase3.py` tests G1–G5 and sampling invariants. In particular:

- a parent test that errors with the bug's `ValueError` passes G3;
- a parent `AttributeError` naming gold-added `new_helper` fails G3;
- G1 and G2 reject endpoint nondeterminism;
- G4 requires an actually covered changed line and reports a fraction;
- G5 requires both the test-only boundary and repeated clean controls.

The Phase 3 test file passes 8/8 tests, and the full repository suite passes
30/30.

## Case construction

Only dev candidate JSONL files were loaded. Held-out repositories were not read.
The linked-issue assumption was checked rather than inferred from pipeline order:
all 161 post-cutoff candidates had at least one linked issue, while one failed
the fixed usable-text rule (at least 40 characters and 20 alphabetic characters).

The filter funnel was:

| filter | remaining | excluded at step |
|---|---:|---:|
| dev `no_test_files_touched`, merge year 2019+ | 161 | — |
| linked issue present | 161 | 0 |
| linked issue text usable | 160 | 1 |
| changed Python source or executable example present | 112 | 48 |
| verified runtime AST behavior change; not rename-labelled | 89 | 23 |
| at least one coverable fix-side changed line | 85 | 4 |
| parent builds | 84 | 1 |
| selected existing test passes twice at both endpoints | 81 | 3 |

The runtime-AST comparison removes docstrings and type annotations before
comparison. Annotation-only, documentation-only, and rename-labelled changes
therefore cannot enter merely because textual Python changed. Executable Python
under `examples/` is accepted as a behavior surface; `docs/conf.py` and `.pyi`
stubs are not.

Four candidates failed runtime validation after the static filters: the rejected
2019 Tenacity transitions were incompatible with the pinned Python 3.11 runtime
(one build failure and three imports using removed `asyncio.coroutine`). These
were reported, not silently discarded.

The 81 eligible cases were stratified by repository and merge year. Seed 63811
uses a SHA-256 rank and proportional allocation with a minimum of one per stratum;
80 cases were selected. `make sample-b` produced a byte-identical
`data/phase3/case-set.json` on repeated runs.

Final repository composition is Flask 31, Click 30, Marshmallow 10, Tenacity 7,
and attrs 2. Merge-year composition is 2019: 1, 2020: 3, 2021: 27, 2022: 17,
2023: 17, 2024: 3, 2025: 5, and 2026: 7.

## Baselines

B1 and B2 receive exactly the linked issue text, PR title and body, gold patch,
and relevant parent source. Both use the Phase 2 pinned model,
`deepseek/deepseek-v4-flash`, through the same hash-addressed fixture layer.

- **B1:** one temperature-0 request; first output is final; no execution, tools,
  or retry is exposed to the model.
- **B2:** the same prompt at temperatures 0, 0.125, 0.25, 0.375, and 0.5; every
  output is evaluated by the complete gate stack; the first pass is accepted.
  It receives no repository exploration and cannot revise from failure output.

| baseline | n | verified | rate | executed API cost | cost/candidate | stored model latency/candidate | capped replay wall/candidate |
|---|---:|---:|---:|---:|---:|---:|---:|
| B0 stub | 80 | 0 | 0.0% | $0 | $0 | 0 s | 1.381 s |
| B1 single prompt | 80 | 13 | 16.25% | $0.084293 | $0.001054 | 13.881 s | 2.709 s |
| B2 best of five | 80 | 22 | 27.5% | $0.328362 | $0.004105 | 63.747 s | 18.935 s |

The replay wall times were 110.465 seconds for B0, 216.752 seconds for B1, and
1,514.801 seconds for B2: 1,842.018 seconds (30 minutes 42 seconds) over the full
case-set replay. Stored model latency is provider-call latency from the recorded
fixtures; replay wall time excludes API waiting and measures Docker verification.

B2 executed 330 attempts. Its 22 accepted tests were found at attempt indices
0: 13, 1: 4, 2: 1, 3: 3, and 4: 1. The passed tests covered at least one changed
line by construction; their changed-line fractions ranged from 0.1667 to 1.0.

## Failure breakdown

Counts below are the first failed gate per non-passing candidate. Output parsing
is shown separately because no gate ran for those outputs.

| baseline | failures | G1 | G2 | G3 | G4 | G5 | output parse/model error |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| B0 | 80 | 74 | 6 | 0 | 0 | 0 | 0 |
| B1 | 67 | 19 | 27 | 0 | 4 | 11 | 6 |
| B2 | 58 | 17 | 24 | 0 | 5 | 9 | 3 |

G3 has zero observed baseline rejections; its positive and negative behavior is
covered by unit tests. This is not evidence that G3 was disabled. It means no
final evaluated output had G3 as its earliest failing gate.

## Cost, fixtures, and replay

B1's temperature-0 fixtures are a subset of B2 and are not double-counted in
project spend. The 331 Phase 3 fixture files contain 3,313,438 reported tokens and
$0.329379503176 of API-reported cost. This includes a $0.001017 unused temperature-
0.5 fixture recorded to make the capped `click#1587` attempt boundary replay-
stable. Three provider timeouts contain no usage object, so any provider-side
partial charge for those calls is unknown and excluded.

Adding Phase 2's $0.086225 gives a new project total of **$0.415604503176**, far
below the approximately $20 budget.

Replay is the default and hard-fails on a fixture miss. With
`OPENROUTER_API_KEY` removed from the environment, B0, B1, and B2 reproduced
0/80, 13/80, and 22/80 respectively. Replay never reached the network.

## Preservation checks

SHA-256 manifests captured before Phase 3 were checked after the final replay.
Every Phase 2 case set, validation record, fixture, result, test, and report was
byte-identical. The five dev candidate JSONLs and `config/split.json` were also
byte-identical. The held-out repositories remain closed and absent from the Phase
3 case set.

The structured artifacts are under `data/phase3/` and `results/phase3/`. The
entry points are `make phase3-sandbox`, `make validate-b`, `make sample-b`,
`make baselines-b`, and keyless `make replay-b`.

## Decision for Phase 4

Proceeding to an agent evaluation is justified by the metric and baseline, not
guaranteed to succeed. The null baseline is 0%, while the deliberately strong
blind best-of-five selector reaches only 27.5%. The remaining **72.5-point** gap
is large enough for repository exploration, convention discovery, fixture reuse,
and failure-driven revision to produce a measurable improvement. If an agent
does not beat B2 here, that is a substantive negative result rather than a
ceiling effect.
