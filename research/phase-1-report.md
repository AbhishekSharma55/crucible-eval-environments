# Phase 1 report: corpus and sandbox

Date: 2026-08-30 (Asia/Kolkata)

## Outcome

Phase 1 produced a compiler-free, digest-pinned Python 3.11.9 Docker sandbox,
seven passing repositories, a committed GitHub GraphQL snapshot containing 700
merged PR candidates, and a fixed five-repo/two-repo dev/held-out split.

The final clean verification run was:

| Command | Result | Wall clock |
|---|---:|---:|
| `make sandbox` | pass | 183.97 s |
| `make probe` | 7/7 repos pass at HEAD and old commit | 35.66 s |
| `make harvest` with `GITHUB_TOKEN` removed | pass, 700 candidates | 0.09 s |
| `make split`, twice | byte-identical; repo overlap 0 | <1 s each |

Every probe and candidate test container was launched with `--network none`.
The clean image build used the base image by digest, exact OS package versions,
and committed per-repo/per-revision Python lock files. No compiler is installed.

## Repository probe

The old revisions are dated 2024-08 through 2024-10, approximately 22 months
before the first probe date.

| Repository | Final result | Old probe commit | Detail |
|---|---|---|---|
| `pallets/click` | accepted | `9aeb586cbc62` | HEAD and old pass; `less` is installed because pager tests exercise it. |
| `pallets/flask` | accepted | `62c56e08c43f` | HEAD and old pass. Old env pins Click 8.1.7 and Werkzeug 3.1.3 to the compatible historical behavior. |
| `python-attrs/attrs` | accepted | `4580a74fc901` | HEAD and old pass. Separate environments make the pytest 9/8 revision boundary explicit. |
| `jd/tenacity` | accepted | `11af5c1397b6` | HEAD and old pass; typeguard, Tornado, and Trio tests are present. |
| `marshmallow-code/marshmallow` | accepted | `31d67b9c759a` | HEAD and old pass; simplejson compatibility tests are enabled. |
| `psf/black` | accepted | `53a219056d1a` | HEAD and old pass. Project builds pure Python with no compiler; old env pins Click 8.1.7 and pathspec 0.12.1. |
| `PyCQA/flake8` | accepted | `cf1542cefa3e` | HEAD and old pass. Old env resolves its declared Pyflakes `<3.3` range; HEAD uses 3.4. |
| `encode/httpx` | dropped | `83a85189c797` | Old passed after using the repo's exact tool pins. HEAD consistently failed `test_write_timeout[trio]` on an unraisable async-generator resource warning in three runs. |
| `Textualize/rich` | dropped | `46150cdbf614` | HEAD had three deterministic ANSI snapshot failures with Pygments 2.18; newer Pygments increased the failures. Too dependency-sensitive. |
| `agronholm/anyio` | dropped | `4d3dd2697a89` | Old had two Trio behavior failures. HEAD's sourceless-install test attempted nested package setup that is not compatible with the offline test boundary. |
| `tox-dev/tox` | dropped | `5d880fc93c22` | The suite required additional flaky/devpi plugins and nested environment machinery; it did not reach a clean suite inside the repo time-box. |
| `sqlfluff/sqlfluff` | dropped | `e63c337b17b1` | Old core suite had 158 Click/plugin compatibility failures; HEAD retained nine plugin/config snapshot failures. It was dropped rather than patched around. |

The final `make probe` table was:

```text
REPOSITORY                       HEAD  OLD   HEAD_S   OLD_S
-------------------------------- ----- ----- -------- --------
pallets/click                    PASS  PASS       3.9      1.8
pallets/flask                    PASS  PASS       2.0      2.1
python-attrs/attrs               PASS  PASS       7.0      7.2
jd/tenacity                      PASS  PASS       3.3      4.2
marshmallow-code/marshmallow     PASS  PASS       2.4      2.4
psf/black                        PASS  PASS      22.4     17.3
PyCQA/flake8                     PASS  PASS       2.1      2.1
```

Only Flask overlaps SWE-bench's repository set. Six of seven accepted repos do
not.

## Candidate corpus

The API cache contains the 100 most recently updated merged PRs for each of the
seven accepted repositories. GraphQL supplied PR title/body, merge commit and
parents, closing-issue bodies, and up to 100 changed paths in one response per
repo. The cached raw responses total roughly 4.4 MB and allow tokenless offline
replay.

| Metric | Count |
|---|---:|
| Repositories attempted | 12 |
| Repositories accepted | 7 |
| Repositories dropped | 5 |
| Candidates total | 700 |
| Accepted candidates | 1 |
| Rejected candidates | 699 |

Rejection-reason histogram:

| Reason | Count |
|---|---:|
| `no_linked_issue` | 551 |
| `tests_no_clean_fail_to_pass` | 74 |
| `no_test_files_touched` | 42 |
| `other` | 21 |
| `no_source_files_touched` | 7 |
| `nondeterministic_test_outcome` | 4 |

The one accepted transition is Flask PR #5630. This low automatic yield is not
being padded: it is the baseline signal and leaves a large, reason-labelled dev
rejection bucket for the rescue agent.

Dynamic validation ran only on the five dev repositories. It repeated the
changed-test selection twice at the parent and twice at the merge commit and
compared per-test outcome maps. The validator explicitly skipped the two
held-out repositories. Consequently, their 21 statically eligible candidates
are recorded as `other` with `dynamic validation result is not cached`; they
must only be resolved during final held-out evaluation. This is deliberate
boundary enforcement, not missing data hidden from the summary.

## Split

Seed `41729` produced five dev repositories and two held-out repositories. The
assignment is committed rather than recomputed. Candidate files are written
directly to their split directories; there is no persistent unsplit corpus.

The held-out directory has its own warning README, and the candidate loader
raises unless `--allow-heldout` is explicit. Development validation did not use
that flag. Two consecutive `make split` runs, compared against the pre-run
state, produced byte-identical files. Filename-based verification reports zero
repository overlap.

## Workarounds and fragility

- Historical dependency ranges genuinely conflict. A single environment could
  not satisfy, for example, current and old Flake8 or attrs. The image therefore
  bakes explicit `head` and `old` locked environments per repo. Candidate
  commits use the head environment; very old arbitrary commits beyond the probe
  point may need another explicit lock profile.
- Target projects are built from source with no compiler. Some third-party
  dependencies arrive as platform wheels. The locks pin versions but not wheel
  hashes, so package-index compromise is outside the current threat model.
- The current heuristic runs test files present at each revision. It does not
  transplant a newly added test from the fix commit onto the parent. New/moved
  tests therefore become `tests_no_clean_fail_to_pass` instead of false
  acceptances. A later rescue system should reconstruct that test patch
  explicitly.
- GraphQL caches at most 100 changed paths per PR. Larger PRs are rejected with
  `other` rather than processed from incomplete data.
- The clean image build needs network access to clone mirrors and download
  locked packages. Test execution does not. A fully air-gapped image build would
  additionally require committing or publishing a wheelhouse and git bundle.
- Black is the slowest retained suite (roughly 17–22 seconds per full run) but
  remains well inside the 20-minute repo budget.

## Substrate assessment

Yes, with a qualification: this is good enough to build the dev-side rescue
agent on. Seven repos pass at both time points, six are outside SWE-bench, the
offline execution contract is real, and 699 honest rejections provide more than
enough dev material. The rejection distribution also validates the premise:
static PR heuristics have very low clean-transition yield.

It is not yet a finished benchmark substrate. Before final evaluation, the
held-out dynamic checks must be run exactly once under the explicit held-out
gate, and the verifier should learn to apply a fix PR's test patch to its parent
instead of rejecting newly introduced tests at collection time. If the next
phase cannot implement that test-patch reconstruction without weakening the
offline boundary, the substrate should be reconsidered then. There is no reason
to reconsider the seven-repo Docker sandbox itself.

## Phase 1b: corrected SWE-bench-style baseline

Date: 2026-08-30 (Asia/Kolkata)

Phase 1b supersedes the candidate-construction limitations described above.
The validator now partitions every cached changed-path list using an explicit
per-repository test layout, materializes the test-only diff from the cached git
mirror, applies it with `git apply` at the first parent, and runs the same test
files twice at the transplanted parent and twice at the merge commit. The gold
path partition is recorded but never applied at the parent. Test containers
remain `--network none`; no API or git network access occurs during validation.

The configured test roots are `tests/**` for all seven repositories, plus
`typing_tests/**` for attrs. This is configuration, not a hard-coded assumption
that every repository uses `tests/`.

### Controlled before/after comparison

The following comparison uses exactly the original 700 PR keys and the same
seven repository assignments. All 700 old candidates were still present after
pagination, so there is no sampling mismatch in this table.

| Outcome | Phase 1 (no transplant) | Phase 1b (test transplant) |
|---|---:|---:|
| Accepted | 1 | 57 |
| Rejected | 699 | 622 |
| Held-out deferred, not rejected | 0 | 21 |
| Total | 700 | 700 |

| Rejection reason | Before | After |
|---|---:|---:|
| `no_linked_issue` | 551 | 551 |
| `no_test_files_touched` | 42 | 42 |
| `tests_no_clean_fail_to_pass` | 74 | 17 |
| `no_source_files_touched` | 7 | 7 |
| `nondeterministic_test_outcome` | 4 | 5 |
| `test_patch_does_not_apply` | 0 | 0 |
| `pr_too_large` | 0 | 0 |
| `other` | 21 | 0 |

Exactly 56 candidates changed rejection/acceptance status specifically because
of the transplant: all moved from `tests_no_clean_fail_to_pass` to accepted.
One additional candidate remained rejected but moved from
`tests_no_clean_fail_to_pass` to `nondeterministic_test_outcome`. The 21 old
`other` records did not change because of transplant; they were the held-out
deferrals and are now represented as `heldout_deferred` outside the rejection
histogram.

### Deeper harvest and final Phase 1b corpus

The on-disk GraphQL snapshot grew from 100 merged PRs per repository (700
active candidates) to five pages where history allowed. Five repositories have
500 PRs each; Tenacity exhausts its available merged history at 278 and Flake8
at 295. The resulting corpus is 3,073 PRs, up from 700. Its merge dates span
2014-12 through 2026-08 overall, instead of being only a recent traffic window.

The active raw API cache is about 9.1 MB (about 11 MB including the retained
probe-repository pages), so compacting away raw response fields was unnecessary.
All pages are committed and `make harvest` consumes only these files. Changed
paths are paginated in 100-path pages up to a stated 300-file threshold; PRs
above that threshold receive `pr_too_large`. No PR in this snapshot exceeded
100 changed paths, so neither the supplemental-path nor too-large bucket has a
non-zero corpus count.

| Final corpus outcome | Count |
|---|---:|
| Candidates | 3,073 |
| Accepted dev candidates | 153 |
| Rejected candidates | 2,804 |
| Held-out deferred, not dynamically validated | 116 |
| Pending validation | 0 |

| Final rejection reason | Count |
|---|---:|
| `no_linked_issue` | 2,430 |
| `no_test_files_touched` | 219 |
| `tests_no_clean_fail_to_pass` | 116 |
| `no_source_files_touched` | 34 |
| `nondeterministic_test_outcome` | 5 |
| `test_patch_does_not_apply` | 0 |
| `pr_too_large` | 0 |
| `other` | 0 |

Accepted candidates by dev repository are Click 85, attrs 34, Tenacity 14,
Flask 12, and Marshmallow 8. Dynamic validation was never run for Black or
Flake8: the validation cache contains zero files for both held-out repositories,
and the validator no longer exposes an override that can schedule them.

The first-run parent per-test map contains 525 assertion/test-call failures and
185 setup or collection errors, kept as distinct `failed` and `error` values.
Among accepted candidates, 146 have assertion-failure-to-pass transitions and
7 have collection/setup-error-to-pass transitions. Those seven collection
errors fan out to 804 passing fix node IDs, while ordinary failures account for
393 transitioned node IDs; this fan-out preserves the actual parent collection
signal while identifying the concrete fix-side tests it prevented from being
collected.

### Verification and timings

| Command/check | Result | Wall clock |
|---|---:|---:|
| `make harvest` with `GITHUB_TOKEN` removed | pass; 3,073 candidates, 0 pending | 0.23 s |
| full dev validation, 3 workers, two runs per endpoint | pass; 274 statically eligible candidates | 3,213.83 s (53m 33.83s) |
| `make test` | 16 passed, including a newly-added test-file transplant | 0.9 s |
| `make split`, twice | pass; byte-identical candidate outputs | <1 s each |

The new-file unit test creates a temporary git history in which the fix changes
source code and adds `tests/test_new.py`. It constructs and applies only the
test partition to the parent, verifies the source remains at the buggy parent
version, and verifies that the validator recognizes the repeated failed-to-pass
transition. The split remains seed `41729`, with the original five dev and two
held-out repository assignment unchanged and zero overlap.

### Baseline assessment and remaining differences

This is now a fair representation of the central SWE-bench-style heuristic for
the comparison we intend to make: source and test changes are separated, only
the regression test is transplanted to the parent, actual per-test transitions
are checked, collection errors are not conflated with assertions, repeated runs
screen nondeterminism, and all test execution is offline. The increase from 1
to 57 acceptances on the controlled original sample demonstrates that the old
baseline was materially incomplete. On the enlarged corpus the 153 observed
acceptances are 4.98% of all 3,073 PRs, although that denominator includes 116
held-out candidates deliberately left unresolved; among the 2,278 fully
processed dev PRs the observed yield is 6.72%.

It is not an exact reproduction of SWE-bench construction. Remaining
differences that should be disclosed in the README are:

- This corpus has seven pure-Python repositories and a Python 3.11 sandbox,
  rather than SWE-bench's larger repository and environment matrix.
- Selection is at changed-test-file granularity. It runs every test collected
  from those files, rather than relying on project-specific test-target
  extraction. Test helpers outside the configured roots would remain in the
  gold partition.
- The fix endpoint is the cached GitHub merge commit and the parent is its first
  parent. The pipeline does not reconstruct a synthetic base-plus-gold checkout
  independently of that merge topology.
- Arbitrary historical commits use the repository's pinned `head` environment,
  except for the two explicitly probed old revisions. Very old PRs can therefore
  be rejected because their fix tests are incompatible with the modern pinned
  dependency set.
- GitHub `closingIssuesReferences` supplies issue linkage. Textual references
  that do not create a GitHub closing relationship are classified
  `no_linked_issue`.
- Repository-specific marker exclusions established in Phase 1 still apply
  (for example Click stress tests and Black's mypyc-incompatible tests).
- The 300-changed-file cutoff is a local practicality threshold, and the
  two-run nondeterminism rule is stricter than a one-shot construction pass.
- Held-out dynamic outcomes remain intentionally unknown. Counts labelled
  accepted are dev-side observations, not claims about the deferred Black and
  Flake8 candidates.
