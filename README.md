# Crucible

Manufactures verifiable evaluation environments for AI coding agents out of real
bug fixes, by writing the regression test the original fix never shipped.

```sh
make demo        # no API key, no network, under a minute
```

---

## Who needs this

An engineer building evaluation environments for coding agents. Public contractor
listings for that role pay $50–100/hour, output-based, against a weekly quota.
The job exists at every lab that trains or evaluates code models.

The work looks like this. Find a real bug fix in a real repository. Rebuild the
project at the commit *before* the fix, with the dependencies it had then. Confirm
there is a test that fails on the broken code and passes on the fixed code.
Confirm nothing else broke. Package it so someone else can run it.

**The bottleneck is that most candidates are unusable, and you find out last.**
Running the standard heuristic pipeline over 3,073 merged pull requests from seven
maintained Python libraries, **2,804 were discarded** — 91%. Every discard is
expert time already spent.

The largest single reason a candidate survives every other check and still gets
thrown away: the fix shipped **no regression test**. There is nothing to run. In
this corpus that is 167 candidates in the development repositories alone.

Writing that missing test is judgment work, which is why it is expensive. It is
also verifiable work, which is why an agent can be measured at it honestly.

## The result

| | Verified regression-test rate | Cost / candidate | Latency / candidate |
|---|---:|---:|---:|
| B0 — stub, no model | **0 / 80** (0.0%) | $0 | — |
| B1 — single prompt | 13 / 80 (16.25%) | $0.0011 | 13.9 s |
| B2 — best-of-5, gates as selector | 22 / 80 (27.5%) | $0.0041 | 63.7 s |
| **Crucible agent** | **26 / 80 (32.5%)** | $0.0054 | 90.6 s |

n = 80 development cases. The agent and B2 receive **the same five gate checks**,
so the difference is not bought with extra validation. It does cost 1.3× per
candidate and 3.5× the tokens; the accuracy-vs-cost plot is in
[`results/phase4/accuracy-vs-cost.svg`](results/phase4/accuracy-vs-cost.svg).

Tracking every one of B2's 58 failures through the agent: **11 recovered, 7 of
B2's passes lost, net +4.** The recoveries are concentrated exactly where the
design predicted — 5 of 24 broken tests and 4 of 9 misplaced ones.

### Held-out

`psf/black` and `PyCQA/flake8` were separated in the first hour and opened once,
at the end. All four arms, one pass, unchanged agent, zero selective reruns.

| | Development | Held-out | Drop |
|---|---:|---:|---:|
| B0 | 0/80 (0.00%) | 0/16 (0.00%) | 0.00 pp |
| B1 | 13/80 (16.25%) | **0/16 (0.00%)** | 16.25 pp |
| B2 | 22/80 (27.50%) | 3/16 (18.75%) | 8.75 pp |
| **Crucible agent** | 26/80 (32.50%) | **5/16 (31.25%)** | **1.25 pp** |

**The agent degrades least, and its lead over B2 is larger on held-out (+12.5 pp)
than on development (+5.0 pp).** It does not show the overfitting signature.

That is the reward-hacking check, and it is worth being precise about what it
does and does not show. At n=16 the differences are not statistically
established: treating each arm's development rate as the null, P(X ≤ observed) is
0.059 for B1, 0.320 for B2 and 0.576 for the agent. So this run does **not**
demonstrate a dev/held-out gap for any arm. What it demonstrates is the *absence
of a large one* for the agent — which is the claim worth making, and the weaker
of the two.

### Gate gaming

A scanner flags tests that look like they satisfy a gate without doing the work —
skips, expected-failure markers, assertions on incidental state.

On held-out, **zero accepted tests were flagged.** Six intermediate revisions
were, and all six were read by hand: two genuine evasion attempts, four false
positives, every one abandoned by the agent before validation in a case that went
on to fail.

On development, **8 of the 26 accepted tests are flagged** — marshmallow#2153,
click#1737, #1839, #1942, #2944, #3055, flask#4445 and #5242, with click#3055
carrying a `skip_or_expected_failure` marker.

A flag is not a verdict; the scanner is deliberately over-sensitive. But eight
flagged accepts is exactly why the five gates are treated as necessary and not
sufficient, and why nothing reaches `environments/approved/` without a person
looking at it. See below.

Full breakdown in [`research/phase-4-report.md`](research/phase-4-report.md) and
[`research/phase-5-report.md`](research/phase-5-report.md).

## What counts as success

A rescue passes only if all five gates hold. Each emits structured evidence, never
a bare pass/fail.

| Gate | Check |
|---|---|
| **G1** | The authored test **fails** at the parent commit. |
| **G2** | The same test **passes** at the fix commit. |
| **G3** | It fails for a behavioural reason — not merely because a symbol the fix introduces does not exist yet. |
| **G4** | It executes at least one line the fix actually changed, measured under coverage. |
| **G5** | It adds one test file and touches nothing else. No source edits, no changes to existing tests. |

G3 is the one that took the most care. The naive version — demand an assertion
failure at the parent — is wrong, because if the bug is a crash then the correct
regression test *errors* there, legitimately. So G3 rejects only when the parent
failure is a missing-symbol error naming something the fix introduced. A test
asserting `new_helper()` exists is testing the implementation, not the behaviour.

Every endpoint runs twice. Nondeterministic outcomes are rejected. Every test
container runs with `--network none`.

## Why the baselines are hard on purpose

**B0** emits a stub — import the module, `assert True`. It scores **0/80**, and
that zero is the point. In an earlier version of this project the null baseline
scored 88%, which is how I discovered the metric was measuring the absence of a
defect rather than the presence of quality. That story is in
[`CHANGELOG-IMPROVEMENT.md`](CHANGELOG-IMPROVEMENT.md); it cost eight hours and it
is the most useful thing here.

**B2** is deliberately strong. It samples five candidate tests across a temperature
ramp and runs every one through the full gate stack, accepting the first that
passes. It gets the same verification signal the agent gets. Published work on
agent evaluation shows plain retry frequently matches sophisticated architectures
at a fraction of the cost, and a comparison that skips it is not worth reporting.

The agent is capped at **the same five gate calls B2 receives**, so neither side
buys accuracy with extra compute. Cost and latency are reported alongside every
rate.

## What the agent does differently

B2 resamples blind. The agent looks.

It inspects where the repository actually keeps tests for the module in question
and what its existing fixtures look like, writes a test, runs it, reads the
failure, and revises.

The failure data says this is where the room is. Of B2's 58 failures, **24 were
tests that failed at both endpoints** — broken, and a single execution would have
shown it — and **17 passed at the parent**, meaning they never reproduced the bug.
Nine more wrote to the wrong place. All three are visible to something that runs
its own output and reads the result.

## The output, and the person who signs it off

The point of all this is not a results table. It is environments an eval engineer
can actually use.

```sh
make export-environments                        # 31 environments: 26 dev, 5 held-out
make review-environments REVIEWER='your name'   # a human decides, one at a time
make promote-environments                       # copies only explicit accepts
```

Each environment is self-contained: the linked issue as `problem_statement.md`,
the authored test as `test_patch.diff`, full gate evidence and coverage fraction
in `metadata.json`, and a `verify.sh` that re-checks all five gates. `verify.sh`
runs offline against recorded evidence by default, or `--mode live` to re-execute
both endpoints in the sandbox. All 31 pass both ways.

**Nothing reaches `environments/approved/` without a person typing an accept.**
`make promote-environments` refuses the lot until someone has reviewed them, and
refuses any accept whose test hash no longer matches. Approvals are recorded with
reviewer identity and a UTC timestamp in `environments/approvals.jsonl`.

That gate is not decoration. The five gates prove mechanical facts — fails before,
passes after, touches the changed lines, breaks nothing else. They cannot tell you
whether a test captures *the behaviour the issue describes* or merely something
the fix happened to alter.

### What the review actually found

**8 of the 31 environments were rejected by a human**, with reasons recorded in
`environments/approvals.jsonl`. Every one had already passed all five gates.

Three of the eight failed the same way, and it is the clearest illustration of the
gates' limit. When the fix deprecates something, the agent writes a test asserting
a `DeprecationWarning` fires — `click#1737`, `flask#4342`, `flask#4998`. That test
passes every gate honestly: the warning genuinely does not exist at the parent, it
does at the fix, and it touches the changed lines. It also tests the
*announcement* rather than any behaviour. No mechanical check catches this.

The rest split between tests asserting an internal field instead of the
user-visible symptom (`flake8#1328` asserts `indent_size_str` rather than the E111
message the issue is about; `black#4541` asserts a constant's type rather than the
performance problem it was reported for) and tests unrelated to their issue —
`black#4447` is reported as dropped characters on M1 and tested by blocking Python
3.12.5, which is the mitigation the PR chose, not the bug.

A 26% human rejection rate on tests that passed every automated gate is the
strongest evidence in this project that the verifier is necessary and not
sufficient. It is also why the export refuses to promote anything a person has not
looked at.

## Reproducing this

`make demo` runs offline in under a minute with no API key and no network, and
reproduces the published table.

I do not promise bit-identical model outputs. That is not achievable over a hosted
endpoint: batch composition varies with server load and inference kernels are not
batch-invariant. What is promised instead:

1. A pinned environment — digest-pinned Docker base, Python 3.11.9, locked
   dependencies, and a pinned dated model snapshot asserted at startup.
2. A **byte-identical default run**. Every model call is hash-cached. Replay is
   the default mode and hard-fails on a cache miss rather than silently reaching
   the network. No key required.
3. Bounded live variance — k rollouts with intervals for the `--live` path.
4. Full trajectories for every claim.

Total API spend to produce every number in this repository: **$1.8080**, across
3,688 unique requests and 43.4M tokens. Figures are API-reported rather than
estimated, and deduplicated — 80 request hashes are shared between the Phase 4
agent run and the Phase 5 re-run, so they are charged once. Full accounting and
commands in [`REPRODUCE.md`](REPRODUCE.md).

## How this differs from SWE-bench

The construction method here is SWE-bench's and I make no claim otherwise: split
the fix PR into a gold patch and a test patch, transplant the test patch onto the
parent, validate the fail→pass transition. What is added is the rescue step for
candidates that method discards, and the gate stack that decides whether a rescue
is real.

Remaining differences, stated so they are not discovered:

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

## Main failure mode

**The agent runs out of budget before it validates.**

Of 80 cases, only 34 ever reached a gate check. The other 43 — more than half —
spent their step allowance inspecting the repository and revising, then stopped
before running the verifier at all. Three more died on infrastructure.

That reframes the result. The honest claim is not "execution feedback is worth
five points." It is that **when the agent reaches its verifier it does well, and it
fails to reach its verifier most of the time.** Every recovered case came from the
34 that got there. The binding constraint is how the agent spends its steps, not
the quality of the signal it eventually gets.

I did not fix this, and the reason matters: raising the step cap would have broken
the matched-budget comparison against B2, and a win bought with extra compute is
not a win. The right fix is teaching the agent to validate early and often rather
than exploring first — cheap to try, and the first thing I would do with another
day.

## Hot take

Self-correction is not a capability, it is a wiring diagram.

The same reflection loop gains roughly eight points with an external correctness
signal and loses up to thirty-eight without one. Most published positive results
either leaked oracle labels or compared against a deliberately weak first attempt.
So the question is never whether the agent should check its work. It is **what
non-model signal the check is made of.** If you cannot name it — a test exit code,
a coverage trace, a schema validator, a different model — you have built a loop
that will talk itself out of correct answers.

And once you can name it, the agent starts optimizing against it, which is why the
held-out repositories in this project were opened exactly once, at the end.

I got to say this the expensive way. My first metric had no such signal — it
checked that an output was *not bad* rather than that it was *good*, and a
zero-cost baseline scored 88% on it. The fix was not a better prompt. It was
changing the task to one where the verifier is an exit code.

## Repository map

```
README.md                  this file
CHANGELOG-IMPROVEMENT.md   how it evolved, including what was removed and why
REPRODUCE.md               clean-environment setup, commands, runtime, cost
PROVENANCE.md              what existed before the competition, tools disclosed
environments/              the product: 31 exported environments + the human approval gate
agents/                    agent system prompts and tool schemas, version controlled
scripts/                   harvest, verifier, baselines, agent runner
sandbox/                   Docker sandbox and test entrypoint
config/                    repo corpus, dev/held-out split, pinned model
data/                      candidate corpus, case sets, human leakage labels
results/                   every run, committed
fixtures/                  hash-cached model calls for offline replay
trajectories/              per-agent traces, including failures and human checkpoints
research/                  per-phase reports with full methodology and numbers
prompts/                   the phase specifications each implementation session worked from
tests/                     unit tests for gates, sampling, and split invariants
```
