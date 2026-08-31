# Codex Phase 5 — clean re-run, held-out evaluation, freeze

Model: `gpt-5.6-sol`. New session. **Roughly 9 hours to the deadline.** Do these in order and report after each. If you run out of time, a completed Task 1 and Task 2 with no Task 3 is far better than three half-finished tasks.

Read `research/phase-4-report.md` first.

---

## Task 1 — clean re-run of the agent arm (do this first)

Phase 4's headline is contaminated. 31 of 80 cases never reached a gate check and 12 model errors were connection resets clustered in Click during a network outage. The recovery table shows the agent fixed 11 of B2's 58 failures, yet the net was +1 — meaning it lost about 10 cases B2 passed, almost certainly to the outage rather than to capability.

**Re-run the entire 80-case agent arm.** Not the failures, not a subset — the whole arm, on a stable connection.

- Same case set, same seed, same caps: 5 gate checks, same step and wall limits, same pinned model.
- Change nothing about the agent, its prompt, or the gates. This is a measurement repair, not an improvement.
- If any case fails for an infrastructure reason again, record it explicitly and report how many.
- **Keep the original run.** Commit it as `results/phase4/summary-run1.json` (or equivalent) alongside the new one. Both go in the submission with the outage disclosed. Do not delete or overwrite the contaminated run — it is evidence that we did not quietly reroll a number we disliked.

Report: new pass@1, the recovery table against B2, cases lost that B2 passed, and infrastructure failure count. Then stop and report before continuing.

## Task 2 — held-out evaluation, once

**This is irreversible. Do it once, after Task 1, and do not repeat it under any circumstance.**

`psf/black` and `PyCQA/flake8` have been closed since Phase 1 under seed `41729`. Open them now.

- Build the held-out case set using the same filters, cutoff and sampling logic as the dev set. Report the pool size at each filter step.
- Run **B0, B1, B2 and the agent** on it. All four arms, one pass.
- Report each rate alongside the dev rate.

**Report the dev-minus-held-out gap for every arm.** That gap is the reward-hacking measurement and it is a headline number whichever way it falls. If the agent degrades more than the baselines do, say so plainly — that is a finding about the method, not a failure of the submission, and hiding it would be worse than reporting it.

Whatever comes out is what we publish. There is no second attempt and no tuning afterwards.

## Task 3 — freeze and package (only if Tasks 1 and 2 are done)

- `make demo` must run from a clean clone with **no API key, no network**, in under a minute, and reproduce the published table. Test it by actually doing that: fresh directory, unset every environment variable, disable networking. Do it twice.
- Export agent trajectories to `trajectories/`: one readable Markdown file per phase plus the raw JSONL. Include at least one **failing** trajectory with a retry, and the gate-evasive intermediate revision already flagged in Phase 4. Those are more valuable than clean successes.
- Regenerate the accuracy-vs-cost plot with the final numbers.
- Final `results/summary.json` covering every arm, dev and held-out, with cost, tokens, latency and n.

## Do not

- Do not modify the agent, its prompt, or the gates during any of this.
- Do not re-run held-out for any reason after the first pass.
- Do not delete the contaminated Phase 4 run.
- Do not rerun individual failed cases selectively. Whole arms only.
- Do not start any new capability work.

## Report back

Append to `research/phase-4-report.md` or write `research/phase-5-report.md`:

- Task 1: clean pass@1 vs the contaminated run, with the outage explained.
- Task 2: all four arms on held-out, dev-minus-held-out gap per arm, pool funnel.
- Final total project spend.
- Anything you would want a reviewer to know that the numbers alone do not show.
