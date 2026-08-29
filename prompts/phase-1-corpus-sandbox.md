# Codex Phase 1 — corpus and sandbox

Model: `gpt-5.6-sol`, high effort for the Dockerfile and the build-probe logic, medium for the rest.

---

## Context

We are building a system that manufactures verifiable evaluation environments for AI coding agents out of real bug-fix commits in open-source Python repos.

One environment is: a repo checked out at the commit *before* a fix, plus the issue text, plus a test that **fails** at that commit and **passes** at the fix commit. That fail→pass transition is the grading signal — no human, no LLM judge, just a test exit code.

The hard part, and the reason this is worth building, is that most candidate commits are unusable. The repo won't build at that commit, or the fix shipped no test, or the test is flaky, or it passes for an unrelated reason. SWE-bench's construction pipeline is heuristic and discards the large majority of candidates it examines. Each discard is wasted expert time, and that expert time is billed at $50–100/hour.

Later phases build an agent that tries to rescue the discards. **Phase 1 builds the ground the whole project stands on: a sandbox that can reliably check out and test these repos at arbitrary historical commits, and a corpus of candidate commits sorted into accepted and rejected with the reason recorded.**

Read `STRATEGY.md` and `CHALLENGE-FACTS.md` in the repo root before starting.

---

## Build four things

### 1. A pinned Docker sandbox

A single image that can check out any repo in our corpus at any commit and run its test suite.

- Base image pinned **by digest**, not tag.
- Python version pinned. If different repos need different Python versions, support that explicitly rather than hoping one version covers everything — a `python_version` field per repo in the corpus config is fine.
- Repos are cloned once into the image or into a mounted cache, so we are not re-cloning on every run.
- **After setup completes, the test run itself must work with networking disabled.** Anything a test needs must be installed at build time. This is a hard requirement: it makes runs reproducible and it stops a future agent from cheating by fetching things at eval time.
- Exposed as a single entrypoint, something like:
  `run_tests(repo, commit, test_selector) -> {exit_code, stdout, stderr, duration_s, per_test_status}`
- Per-test status matters. We need to know *which* tests passed and failed, not just the suite's exit code.

### 2. A repo corpus config

Start from this candidate list. **Do not assume any of these work — probe them.**

`encode/httpx`, `pallets/click`, `pallets/flask`, `python-attrs/attrs`, `Textualize/rich`, `agronholm/anyio`, `jd/tenacity`, `marshmallow-code/marshmallow`, `psf/black`, `tox-dev/tox`, `sqlfluff/sqlfluff`, `PyCQA/flake8`

Selection rules:

- **Pure Python only.** No compiled extensions, no Rust/C build steps. If `pip install -e .` triggers a compiler, drop the repo. (This is why `pydantic` v2, `scikit-learn`, `matplotlib`, `numpy` are excluded — do not add them.)
- Must have a real test suite runnable via `pytest`.
- Must build and test cleanly at HEAD *and* at a commit roughly 18–24 months old. The old-commit check is the one that actually matters and the one that will kill most candidates.
- **Time-box: 20 minutes per repo.** If it fights you longer than that, drop it, record why, and move on. Do not sink hours into making one stubborn repo work.
- **Target 6–10 repos that fully pass.** Fewer good repos beats more flaky ones. If you only get 5, say so — do not pad the list with repos you had to hack around.
- Prefer some repos that are *not* in SWE-bench's set (which is astropy, django, flask, matplotlib, pylint, pytest, requests, scikit-learn, seaborn, sphinx, sympy, xarray). Overlap risks memorization effects later. Flask is on both lists — keep it if it works, but don't lean on it.

Output a committed config file recording, per repo: clone URL, pinned Python version, install command, test command, a known-good old commit used for probing, and any repo-specific quirks.

### 3. A candidate harvest script

Deterministic, plain Python, **no LLM calls**. This is a script, not an agent task.

For each corpus repo, pull merged pull requests via the GitHub API and, for each, record:

- PR number, merge commit SHA, parent SHA
- linked issue number and issue body text (via closing keywords in the PR body, or the linked-issues API)
- files changed, split into test files and non-test files
- the PR title and body

Then apply the SWE-bench-style heuristic filter and sort every candidate into **accepted** or **rejected**, with a machine-readable reason code on every rejection. Reason codes should distinguish at minimum:

- no linked issue
- no test files touched
- no source files touched (test-only change)
- repo fails to build at the parent commit
- tests do not exhibit a clean fail→pass transition
- test outcome is nondeterministic across repeated runs
- other (with a free-text note)

**The rejected bucket with its reasons is the primary output of this phase.** It is the input our agent will later try to rescue, and the rejection-reason distribution is a number that goes in the final report. Do not treat rejections as errors to be swallowed — they are the data.

Cache all GitHub API responses to disk, committed to the repo, so the corpus does not drift and so the harvest can be re-run offline. Read the token from `GITHUB_TOKEN`; never write it to a file. Handle rate limits with backoff.

Aim for **at least 300 candidates total** across the corpus so that the rejected bucket is large enough to sample from later.

### 4. A dev / held-out split

Split the candidates **immediately**, before anything else touches them, and write them to separate directories.

- Split by **repo**, not by individual commit, so a repo's quirks can't leak across the boundary. Roughly 70/30.
- Write the split to disk with a fixed, committed seed. It must not be recomputed on each run.
- Make held-out awkward to read by accident: separate directory, a README in it saying what it is, and any loader that touches it should require an explicit flag.

We will not look at held-out again until the final evaluation. Treat that as a hard rule from now on.

---

## Definition of done

All of these must be literally true, verified by you running them, not asserted:

1. `make sandbox` builds the image from a clean state.
2. `make probe` runs each corpus repo's test suite at both HEAD and the old probe commit inside the sandbox, with **networking disabled during the test run**, and prints a pass/fail table.
3. `make harvest` reproduces the candidate corpus from the committed API cache **with no network access and no GitHub token**.
4. `make split` is deterministic — running it twice produces byte-identical output.
5. `data/candidates/dev/` and `data/candidates/heldout/` exist, are populated, and share no repo between them.
6. A summary file reports: repos attempted, repos accepted, repos dropped with reasons, total candidates, accepted vs rejected counts, and the rejection-reason histogram.

---

## Do not

- Do not write any agent, LLM call, or prompt in this phase. Phase 1 is deterministic code only.
- Do not silently work around a repo that won't build. Drop it and record why.
- Do not fabricate or hand-edit candidate data to make counts look better.
- Do not commit a GitHub token, and do not commit anything under a `.env`.
- Do not look at or load the held-out split for any purpose.
- Do not add a web UI, a dashboard, or a progress-bar library. CLI output is fine.

---

## Report back

When done, write `research/phase-1-report.md` with:

- Which repos passed the probe, which were dropped, and the specific reason for each drop.
- The rejection-reason histogram over all candidates.
- Actual wall-clock time for `make probe` and `make harvest`.
- Anything you had to work around, and anything you think is fragile.
- Your honest assessment: is this corpus good enough to build the rest of the project on, or should we reconsider the substrate?

That last question is real. If the answer is no, we want to know now, not in twenty hours.
