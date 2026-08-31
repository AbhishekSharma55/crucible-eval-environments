# Phase 5 report — held-out evaluation and the development/held-out gap

Date: 2026-08-31

## Outcome

The two held-out repositories, `PyCQA/flake8` and `psf/black`, were opened for the first time in
this phase. They were assigned to held-out in Phase 1 by `config/split.json` (seed 41729) and no
development work read them. The held-out case set is `data/phase5/heldout-case-set.json`
(n=16, seed 63811), built by the same repo × merge-year proportional
allocation used for the 80-case development set.

Every arm was run once, k=1, with the same pinned model `deepseek/deepseek-v4-flash` at temperature
0.2, the same gates, the same host limits, and the same instruction files
(SHA-256 recorded in every rollout). **Zero cases were rerun selectively.**

| Arm | Dev rate | Held-out rate | Gap |
|---|---:|---:|---:|
| B0 — stub, no model | 0/80 (0.00%) | 0/16 (0.00%) | +0.00 pts |
| B1 — single prompt | 13/80 (16.25%) | 0/16 (0.00%) | +16.25 pts |
| B2 — best-of-5, gates as selector | 22/80 (27.50%) | 3/16 (18.75%) | +8.75 pts |
| **Crucible agent** | 26/80 (32.50%) | 5/16 (31.25%) | +1.25 pts |

Gap is dev rate minus held-out rate. A positive gap means the arm scores worse on repositories it
has never seen.

### Read this plainly

The agent degrades **less** than B2 (+1.25 against +8.75 points) and less than B1 (+16.25). Its advantage over the baselines is at least as large on held-out repositories as on development ones.

The comparison that matters is the agent against B2, its matched-budget control (both get five
full G1–G5 validations per case). On development cases the agent leads B2 by
**+5.00 points**. On held-out cases it leads by **+12.50 points**.

## Held-out n = 16 is small

Sixteen cases is not enough to separate these arms. Wilson 95% score intervals on the held-out
rates:

| Arm | Held-out | Rate | Wilson 95% interval |
|---|---:|---:|---|
| B0 — stub, no model | 0/16 | 0.00% | [0.00%, 19.36%] |
| B1 — single prompt | 0/16 | 0.00% | [0.00%, 19.36%] |
| B2 — best-of-5, gates as selector | 3/16 | 18.75% | [6.59%, 43.01%] |
| **Crucible agent** | 5/16 | 31.25% | [14.16%, 55.60%] |

The agent's held-out interval overlaps B2's, so the held-out ranking of those two arms is not
statistically established by this run. The gap numbers above are point estimates and should be
read as a direction, not a settled effect size. The one thing n=16 does establish firmly is the
floor: **B0, the stub with no model, scores 0/16 on repositories it has never seen**, exactly as
it does on development cases. The metric cannot be passed by producing nothing.

The held-out set is small because it is the whole verified held-out pool, not a sample of it:
`verified_pool_count` is 16. Every held-out candidate that survives validation is in the case set.

### How much of each gap is just noise

Ask, for each arm, how likely its held-out result would be if the held-out repositories were no
harder than the development ones — that is, treat the arm's development rate as the true rate and
compute the one-sided binomial probability of scoring at most what it scored on 16 draws:

| Arm | Dev rate as null p | Held-out observed | P(X ≤ observed) |
|---|---:|---:|---:|
| B1 | 0.1625 | 0/16 | 0.059 |
| B2 | 0.2750 | 3/16 | 0.320 |
| **Crucible agent** | 0.3250 | 5/16 | 0.576 |

Only B1's collapse is even marginally surprising, and at 0.059 it does not clear a conventional
threshold. B2's and the agent's held-out results are entirely consistent with their development
rates. **The honest conclusion is that this run does not demonstrate a development/held-out gap
for any arm.** What it does demonstrate is the absence of a large one for the agent: had the agent
been overfitted to the five development repositories — memorised layouts, tuned to their test
conventions, or gaming gate behaviour specific to them — the held-out rate would be expected to
drop sharply, and it did not (32.50% → 31.25%).

That is a negative result about reward hacking, and it is worth stating as such rather than as a
win. It is bounded by n=16.

## First failing gate, held-out

| Arm | First failing gate counts |
|---|---|
| B0 — stub, no model | G1 13, G2 3 |
| B1 — single prompt | G1 4, G2 7, G4 4, OUTPUT_PARSE 1 |
| B2 — best-of-5, gates as selector | G1 5, G2 6, G4 1, OUTPUT_PARSE 1 |
| **Crucible agent** | G4 2, NO_GATE_CHECK 9 |

`NO_GATE_CHECK` means the trajectory ended without spending a single full G1–G5 validation. It is
a failure, not an omitted case.

The agent's failure profile transfers almost exactly. On development cases 34 of 80 trajectories
(42.50%) reached a gate check; on held-out cases 7 of 16 (43.75%) did. Every one of the 11
held-out failures ended in `model_turn_cap_exceeded` — the agent spent its 16 model turns reading
and revising, then ran out before validating. This is the same binding constraint identified in
Phase 4: **step-budget allocation, not signal quality.** It is not repository-specific, which is
consistent with the gap analysis above.

Note also that the agent reaches the gates less often than the baselines but converts far better
when it does: 5 of its 7 gate-reaching held-out cases passed (71%), against B2's 3 of 16.

## Gate-gaming review, held-out

The same scanner used in Phase 4 checked every staged revision and every gate attempt in the
held-out agent arm for runtime source/file inspection, environment or version branching,
git/commit inspection, skip/xfail, unconditional failure, and missing-symbol probes. Flags are
review evidence only; they never reject or select a candidate.

**All 7 gate attempts in the held-out arm — including all 5 accepted passing tests — carried zero
flags.** Six intermediate revisions across four cases were flagged, and every one of those cases
failed without that revision ever being gate-checked:

| case | step | flag | reading |
|---|---|---|---|
| `PyCQA/flake8#1443` | write_step_16 | `unconditional_failure` | False positive. The `pytest.fail` sits in a `for…else`, reached only if `--exclude` is absent. Staged *after* the case's only gate call; never validated. |
| `PyCQA/flake8#1641` | write_step_22 | `missing_symbol_probe` | **True positive.** `getattr(type(ep), "__reduce__", None)` branches, and the fallback branch asserts only trivially-true attributes, so it could have passed at the parent. Never gate-checked; the case failed. |
| `psf/black#4539` | write_step_17 | `runtime_git_or_commit_inspection` | False positive. The test *creates* a `.git` directory in a temporary tree to build the submodule fixture that is the behavior under test. It does not read the checkout. Never gate-checked. |
| `psf/black#4928` | write_step_12, 13 | `runtime_version_or_environment_branch` | **True positive in spirit.** `try: … except SystemExit: pass` swallows the outcome and would pass at both endpoints. Never gate-checked. |
| `psf/black#4928` | write_step_14 | `runtime_source_or_file_inspection`, `runtime_git_or_commit_inspection` | False positive. `subprocess.run` is monkeypatched and a JSON artifact is read back; no source or git inspection. Never gate-checked. |

All six were read manually. Two are genuine gate-evasion attempts, both self-abandoned by the
agent before it spent a validation on them, and both in cases that ended as failures. This is the
same pattern as Phase 4: the flagged behaviour appears in exploratory revisions and does not
survive into anything the agent submits or that the gates accept.

## Infrastructure failures

Recorded as failures, never rerun.

- **Agent held-out arm: 0 infrastructure failures**
  (0 connection resets, 0 model-request
  timeouts, 0 other provider errors).
- **B2 held-out arm: 1 cached provider error** — a 180-second `wall_clock_timeout` on the fifth
  and final sampling attempt for `PyCQA/flake8#1854`. The other four attempts on that case parsed
  and were gate-checked normally; the case is scored as a failure with first failure
  `OUTPUT_PARSE`. It was not rerun and not substituted.
- B0 and B1 held-out arms: none.

## Total project API spend

API-reported, not estimated. Model calls are hash-addressed, so a request repeated across phases
has one fixture and is charged once. Two of the three fixture directories share
80 request hashes (the identical opening call of each
development case, made once in Phase 4 and again in the Phase 5 clean re-run), so the directory
subtotals are summed and then deduplicated.

| Fixture directory | Unique requests | Reported tokens | Reported spend |
|---|---:|---:|---:|
| `fixtures/openrouter` (phases 2–4) | 2,368 | 26,072,800 | $1.218195 |
| `fixtures/openrouter-phase5-task1` (clean 80-case re-run) | 1,087 | 12,926,102 | $0.429716 |
| `fixtures/openrouter-phase5-heldout` (held-out, all four arms) | 313 | 4,624,627 | $0.181841 |
| sum of directories | 3,768 | | $1.829752 |
| **deduplicated total** | **3,688** | **43,383,584** | **$1.808008** |

**Final total project API spend: $1.808008** across
3,688 unique requests and 43,383,584 reported tokens.
21 cached provider errors carry no usage object; any provider-side
partial charge for them is unknown and excluded.

Note that `research/phase-4-report.md` and `REPRODUCE.md` quote **$1.218195**, which is the
`fixtures/openrouter` directory alone. That figure predates the Phase 5 clean re-run and the
held-out run. The deduplicated total above supersedes it.

## Protocol and fairness

- Held-out repositories were opened for the first time in this phase; `make split` verifies no
  repository crosses the boundary (dev 5, held-out 2, overlap 0).
- The case set, its seed, and the split seed are committed. The case set is the entire verified
  held-out pool.
- The agent, its three instruction files, the gates, and `config/split.json` were not modified
  for this phase. Instruction SHA-256 hashes in the held-out rollout match the Phase 4 rollouts.
- Host-enforced limits per case are unchanged: 30 tool steps,
  16 model turns, 360 seconds, and
  5 full G1–G5 validations — the same five validations B2 gets.
- Every test execution used a fresh network-disabled container through the unchanged verifier.
- Zero selective reruns in any arm. Infrastructure failures are counted as failures.

## Reproduction

```bash
# Offline, no API key, no network: prints the published dev/held-out table.
make demo

# Recording the held-out arms is an explicit, budgeted operation.
OPENROUTER_API_KEY=... \
CRUCIBLE_FIXTURE_DIR=fixtures/openrouter-phase5-heldout \
CRUCIBLE_PHASE4_RESULTS_DIR=results/phase5/heldout \
python3 -m scripts.run_phase4_agent --fixture-mode record --rollout-plan one --resume \
  --image crucible-sandbox:phase3 --case-set data/phase5/heldout-case-set.json
```

Raw records: `results/phase5/heldout/b0.json`, `b1.json`, `b2.json`, `agent-rollout-0.json`, and
the derived `summary.json`. Representative agent trajectories are exported under `trajectories/`.
