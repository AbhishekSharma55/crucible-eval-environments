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
