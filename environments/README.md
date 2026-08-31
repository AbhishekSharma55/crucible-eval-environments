# Environments

31 candidate evaluation environments (26 development, 5 held-out),
one per bug-fix pull request whose missing regression test the Crucible agent
authored and whose authored test passed all five gates.

**Nothing in `candidate/` is approved.** These are proposals. A human reviewer
decides whether each authored test genuinely captures the bug's behaviour, and
only what a human explicitly accepts is copied into `approved/`.

## What an environment is

A directory named `<owner>__<repo>__<pr>` containing:

| File | Contents |
|---|---|
| `problem_statement.md` | The linked GitHub issue text, verbatim, plus a clearly separated reference block naming the repository, the pull request and both commits. |
| `test_patch.diff` | The regression test the agent authored, as an added-file unified diff that `git apply` accepts. |
| `metadata.json` | Repository, parent SHA, fix SHA, PR number, merge date, split, all five gate verdicts with their full evidence, the G4 coverage fraction, the authoring model, and the transition kind. |
| `verify.sh` | Re-checks the environment through the unchanged Phase 3 gate stack. Exits non-zero if any gate fails. |

`index.json` lists every environment with its gate statuses, coverage fraction
and review status.

## How to evaluate a coding agent with one

1. Check out `metadata.json:repo` at `metadata.json:parent_sha`. The bug is
   present at this commit.
2. Give the agent everything above the `## Reference` heading in
   `problem_statement.md`. Withhold the reference block, `test_patch.diff` and
   `metadata.json:fix_sha` — each of them names or points at the fix.
3. Let the agent edit source files only.
4. Apply `test_patch.diff` on top of the agent's patch and run the test at
   `metadata.json:test_path`.
5. The agent succeeds if that test passes. It failed at `parent_sha` before the
   agent touched anything, which is what `verify.sh` re-establishes.

`metadata.json:gates.g5.evidence.selected_existing_tests` names existing tests
that pass at both endpoints; run them as the regression control.

## Re-checking an environment

```sh
environments/candidate/<id>/verify.sh              # offline replay, no Docker
environments/candidate/<id>/verify.sh --mode live  # re-executes both endpoints
```

Replay re-applies the committed gate functions to the recorded gate evidence and
the committed candidate record. It needs no network, no API key and no Docker.
Live mode re-runs both endpoints in the pinned `crucible-sandbox:phase3`
container through `scripts/test_authoring_verifier.py`, and needs Docker plus the
local git mirror under `cache/repos/`.

## The gates are necessary, not sufficient

All five gates passing means:

- **G1** the authored test fails at the parent commit
- **G2** the same test passes at the fix commit
- **G3** it fails for a behavioural reason, not because a symbol the fix
  introduces does not exist yet
- **G4** it executes at least one line the fix actually changed, under coverage
- **G5** it adds one test file and touches nothing else

It does **not** mean the test captures the behaviour a user of the library would
recognise as the bug. A test can satisfy every gate and still assert something
incidental that happens to correlate with the fix. That judgement is the human
reviewer's, and is the reason `approved/` exists.

`metadata.json:gaming_flags` carries the automated gate-gaming scanner's output
for the accepted revision. Flags are review evidence only; they never rejected or
selected anything. Read the test.

## Reviewing and promoting

```sh
make export-environments                          # rebuild candidate/ from committed results
make review-environments REVIEWER='your name'     # one environment at a time, resumable
make promote-environments                         # copies accepted environments into approved/
```

Review verdicts append to `approvals.jsonl` with the reviewer's identity, a UTC
timestamp, a free-text note and a hash of the reviewed artifact. Promotion
refuses any environment without an explicit `accept`, and refuses an accept whose
artifact hash no longer matches.

## Known limitations

The construction method is SWE-bench's. Remaining differences, stated so they are
not discovered:

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

Two further limitations specific to these environments:

- The regression test was written by a model, not by the maintainer who fixed the
  bug. That is the entire point of the project and also its main risk, which is
  why the human gate is not optional.
- Held-out environments come from `PyCQA/flake8` and `psf/black`, which were
  opened exactly once, at the end of the project. Development environments come
  from repositories the agent's design was iterated against.
