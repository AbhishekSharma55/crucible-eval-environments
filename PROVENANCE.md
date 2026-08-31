# Provenance

Ground Rule 02 asks for a clear statement of what existed before the competition
and what was added during it. This is that statement.

## What existed before

Nothing in this repository. There is no prior codebase, no library of mine reused
here, and no project this was adapted from. The first commit was made after
kickoff.

The only pre-existing material is third-party and public: the open-source
repositories the corpus is built from, and the published research the design
draws on. Both are cited below.

## Timeline

| When (IST) | What |
|---|---|
| Aug 29, evening | Read the challenge PDF. Background research on evaluation design, verification, and reproducibility. No code. |
| Aug 30, morning | Repo created. Docker sandbox, corpus harvest, dev/held-out split. |
| Aug 30, midday | Baseline correctness fix — test-patch transplant. Corpus deepened to 3,073 PRs. |
| Aug 30, afternoon | Problem-statement rescue attempt. Measured, then removed. |
| Aug 30, evening | Pivot to test authoring. Five-gate verifier and three baselines. |
| Aug 30–31, overnight | The agent, ablations, held-out evaluation. |
| Aug 31 | Writing, trajectories, video, submission. |

## Coding agents used

Agent use is required by the rules and disclosed here in full. Representative
trajectories for each are in `trajectories/`.

**Claude Code (Opus 5)** — research, strategy, evaluation design, review of
generated code before its results became claims, and the written deliverables
(this file, `README.md`, `CHANGELOG-IMPROVEMENT.md`, `REPRODUCE.md`). It also
wrote the phase specifications in `prompts/`, which are the instructions the
implementation agent worked from.

**OpenAI Codex (gpt-5.6-sol)** — nearly all implementation: the Docker sandbox,
corpus harvest, the five-gate verifier, the baselines, the fixture layer, and the
rescue agent. Each phase was run as a separate session against a written spec, so
one trajectory maps to one phase.

**deepseek/deepseek-v4-flash via OpenRouter** — the model *under evaluation*. It
is the actor inside every baseline and inside the rescue agent. It is not a
development tool.

The separation is deliberate and worth noting: the model that builds the harness
is not the model being measured by it, and neither is the same family as the
other. Nothing here grades its own homework.

## Human work

The problem choice, the decision to fix the baseline rather than benefit from its
error, the diagnosis that killed the Phase 2 metric, the pivot, and the fairness
constraint capping the agent to the same number of validation calls the strongest
baseline receives.

The human review tool for leakage labelling was built (`make review-labels`) and
a 50-item queue was prepared, but **the labels were never collected** — there was
not enough time before the deadline. The leakage detector in Phase 2 is therefore
unvalidated against human judgement, and no agreement statistic is reported for
it. This matters because Phase 2's 95% figure rests on that detector; it is
reported as a measurement that motivated abandoning the approach, not as a
validated result. See `CHANGELOG-IMPROVEMENT.md`.

## Third-party material

**Repositories.** Corpus built from public commits in `pallets/click`,
`pallets/flask`, `python-attrs/attrs`, `jd/tenacity`,
`marshmallow-code/marshmallow` (development) and `psf/black`, `PyCQA/flake8`
(held out). Used under their own licences. No repository content is redistributed
here — only commit SHAs, cached public GitHub API metadata, and derived patches.

**Method.** The construction pipeline follows the approach established by
SWE-bench: split a fix PR into a gold patch and a test patch, transplant the test
patch onto the parent commit, and validate the fail→pass transition. This project
does not claim that method as novel. What is added is the rescue step for
candidates the method discards, and the gate stack that decides whether a rescue
is genuine. `README.md` lists the specific ways this pipeline still differs from
SWE-bench's.

**Research.** Design decisions draw on published work on baseline fairness in
agent evaluation, the limits of self-correction without an external signal, and
reward hacking under held-out evaluation. Cited at the point of use in
`README.md` and the phase reports.

## Credentials

No API keys, tokens, or personal data are committed. `.env` is gitignored, and
recorded model fixtures store request hashes, responses, token counts and cost —
never authorization headers.
