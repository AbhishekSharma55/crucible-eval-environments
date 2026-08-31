# Codex Phase 1b — make the baseline honest

Model: `gpt-5.6-sol`, high effort. This phase is short but it is the most correctness-sensitive work in the project.

Read `research/phase-1-report.md` first — it is your own report from Phase 1 and it names the main issue in the "Workarounds and fragility" section.

---

## Why we are doing this before Phase 2

Our project's headline claim will be "an agent rescues candidates that the standard heuristic pipeline rejects." That claim is only worth anything if the heuristic pipeline we compare against is the *real* one, implemented properly.

Right now it isn't. Phase 1 accepted 1 candidate out of 700 — a 0.14% yield. SWE-bench's published construction pipeline yields in the low single-digit percent on comparable repos. The gap is not because our repos are harder. It is because of the limitation you already identified:

> "The current heuristic runs test files present at each revision. It does not transplant a newly added test from the fix commit onto the parent."

Most good bug-fix PRs *add* the regression test. At the parent commit that test does not exist, so it cannot fail, so the transition never validates. SWE-bench's pipeline splits each PR diff into a **gold patch** (source changes) and a **test patch** (test changes), applies the *test patch* to the parent commit, and only then evaluates the fail→pass transition. That is not an enhancement to their method — it is their method.

If we ship a comparison against a pipeline missing this step, we are beating a strawman, and judges who build benchmarks professionally will spot it immediately. Fix the baseline first, then let the agent beat it honestly.

---

## Task 1 — test-patch transplant (the important one)

For every candidate, split the PR diff into two patches by path:

- **test patch** — changes to test files (use each repo's actual test layout; do not assume `tests/`)
- **gold patch** — everything else

Then evaluate the transition as:

1. Check out the **parent** commit.
2. Apply **only the test patch**. If it does not apply cleanly, that is a distinct, recorded outcome — not a generic failure.
3. Run the selected tests. Record per-test status.
4. Check out the **merge/fix** commit (test patch already present there).
5. Run the same selected tests. Record per-test status.
6. The candidate has a clean transition if some non-empty set of tests goes fail→pass, and the previously-passing tests stay passing at both points.

Notes:

- Distinguish **fail** from **error/collection-failure** in the per-test status map. A test that errors because of a missing import at the parent is a different signal from a test that runs and asserts false. Both can be legitimate fail→pass, but we want to be able to tell them apart in the histogram.
- Keep the existing repeated-run nondeterminism check. Run the transition twice at each end as you already do.
- Preserve the offline boundary. The transplant is a `git apply` of a patch we already have cached — it must not require network at test time.

## Task 2 — deepen and de-bias the harvest

The current corpus is the 100 most recently updated merged PRs per repo. That sample is biased: recent traffic in mature libraries skews to dependency bumps, CI fixes, typing and docs — exactly the PRs with no linked issue. That inflates `no_linked_issue` and starves us of real bug fixes.

- Draw **substantially more PRs per repo — target 400–600 each, roughly 3,000+ total**, subject to API budget and cache size.
- Sample **across time**, not just the most recent window. Paginate back through merge history rather than taking a single recent slice.
- Keep everything cached to disk and committed so `make harvest` still reproduces offline with no token.
- If cache size becomes a problem, store the fields we actually use rather than raw responses, and say so in the report.

Also fix the 100-changed-paths truncation: if a PR exceeds the page limit, paginate rather than rejecting it as `other`. If a PR is genuinely too large to be a useful environment, reject it with an explicit `pr_too_large` code and a size threshold we can state in the report.

## Task 3 — clean the rejection histogram

The histogram is going into the final report, so every bucket must be a real reason.

- All 21 current `other` entries are held-out candidates deferred by design. Deferral is not a rejection. Give it its own status, `heldout_deferred`, and **exclude it from the rejection histogram** — report it as a separate line.
- Add `test_patch_does_not_apply` as its own code.
- Add `pr_too_large` as its own code.
- After this, `other` should be near-empty. If anything remains in it, list those cases individually in the report so we can name them.

---

## Definition of done

Verified by running, not asserted:

1. `make harvest` reproduces the enlarged corpus offline, with no `GITHUB_TOKEN` set.
2. The transition check applies the test patch to the parent commit and this is covered by a unit test — including one case where a PR adds a brand-new test file and the transition is correctly detected.
3. `make split` remains deterministic and the dev/held-out repo boundary is unchanged. **Do not re-roll the split.** Same seed, same repo assignment as `config/split.json` today.
4. Held-out candidates remain untouched by dynamic validation.
5. Every rejection bucket is a real reason; `heldout_deferred` is reported separately.
6. A before/after comparison is recorded: old accept count and histogram vs new, on the same repos.

## Do not

- Do not re-roll or change the dev/held-out split.
- Do not run dynamic validation on held-out candidates.
- Do not loosen the offline test-execution boundary.
- Do not tune any threshold to make the accept rate look better. If the honest yield after the fix is still low, that is the number we report. We want the baseline as strong as it truthfully is — no stronger, no weaker.
- Do not start any agent or LLM work. Still deterministic code only.

---

## Report back

Append a "Phase 1b" section to `research/phase-1-report.md` with:

- Accept count and rejection histogram **before and after** the transplant fix, on the same repo set, so the delta is explicit.
- Corpus size before and after the deeper harvest.
- How many candidates changed status specifically because of the test-patch transplant.
- Wall clock for the full harvest and validation.
- Whether you think the resulting baseline is now a fair representation of the SWE-bench-style heuristic, and where it still differs. Be specific about the remaining differences — we intend to state them in the README, so an honest list here is worth more than a clean-sounding one.
