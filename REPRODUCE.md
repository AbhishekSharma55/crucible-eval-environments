# Reproduction guide

Written for someone starting from a clean machine with no API key and no
intention of spending money. That path works and reproduces every published
number.

## Requirements

| | Version |
|---|---|
| Docker | Engine or Desktop with BuildKit |
| GNU Make | any recent |
| Python (host) | 3.11+ |
| Python (sandbox) | 3.11.9, base image pinned **by digest** |
| Model under evaluation | `deepseek/deepseek-v4-flash` via OpenRouter, pinned |

No host Python packages are needed for the corpus commands. Development
dependencies for the test suite are in `requirements-dev.txt`.

Disk: the clone is about 290 MB, and the sandbox image plus cached git mirrors
add roughly 3 GB.

Most of the clone is `fixtures/` — 167 MB of recorded model responses. That is
the price of the offline path: because every call is committed, you can reproduce
every published number with no API key and no spend. It seemed a fair trade to
make the reviewer's cost a slow clone rather than a credit card.

## The short path

```sh
git clone <repo> && cd hacker-earth-challange
make sandbox     # ~3 min, needs network once, to build the image
make demo        # offline, no API key, reproduces the published table
```

`make demo` needs no `OPENROUTER_API_KEY` and reaches no network. If it tries to,
that is a bug — report it rather than working around it.

## What you can reproduce, and what it costs you

| Command | What it does | Runtime | Your cost |
|---|---|---:|---:|
| `make sandbox` | Clean image build, digest-pinned base, per-repo locked environments, git mirrors cloned in | 3 min | $0 |
| `make probe` | Every corpus repo's suite at HEAD and at a ~22-month-old commit, `--network none` | 36 s | $0 |
| `make harvest` | Rebuilds all 3,073 candidates from the committed API snapshot. `GITHUB_TOKEN` explicitly unset. | <1 s | $0 |
| `make split` | Replays the dev/held-out boundary; verifies no repo crosses it | <1 s | $0 |
| `make test` | 42 unit tests: gates, sampling, split invariants | 1 s | $0 |
| `make replay-c` | Phase 4 agent replay, 140 trajectories from 1,814 cached fixtures | ~30 min | $0 |
| `make report-c` | Final tables; refuses to run on incomplete rollouts | seconds | $0 |

Everything above runs from committed artifacts. **Total cost to reproduce the
entire submission: $0.**

## What it cost us to produce

API-reported, not estimated. Calls that failed without returning a usage object
are excluded and noted in the phase reports.

| Phase | Spend |
|---|---:|
| 1 and 1b — corpus and baseline | $0 (no model calls) |
| 2 — the removed experiment | $0.0862 |
| 3 — verifier and baselines | $0.3294 |
| 4 — agent, including the clean re-run | $0.8026 |
| **Total** | **$1.2182** + the held-out run |

Wall clock for the expensive steps: the full dev validation over 3,073 candidates
took 53 minutes on 3 workers; the Phase 4 agent arm took roughly 2¼ hours.

## Offline by construction

Every model call is hash-cached. The key covers model, messages, temperature and
token cap. **Replay is the default mode and hard-fails on a cache miss** — it will
not silently fall through to the network.

Every test container runs with `--network none`. The sandbox image is built with
all dependencies baked in, so nothing is fetched at evaluation time. This is both
a reproducibility property and an anti-gaming one: an agent cannot reach the
network to shortcut a verification.

Two operations are deliberately online and explicit:

```sh
GITHUB_TOKEN=... python3 -m scripts.github_cache --pages 5    # refresh corpus
OPENROUTER_API_KEY=... python3 -m scripts.run_phase4_agent \
  --fixture-mode record --rollout-plan subset --resume        # record fixtures
```

Neither is needed to reproduce anything. Both cost money. The token is never
persisted; only request hashes, responses, token counts and cost are versioned.

## What we do not promise

Bit-identical model outputs. That is not achievable over a hosted endpoint —
batch composition varies with server load and inference kernels are not
batch-invariant, so the same request can return different text.

What is guaranteed instead:

1. A byte-identical environment: digest-pinned base image, locked dependencies,
   pinned model snapshot asserted at startup.
2. A byte-identical **default** run, because replay serves committed fixtures.
3. Bounded variance on the live path, reported with intervals.
4. Full trajectories in `trajectories/` for every claim.

## The held-out boundary

`psf/black` and `PyCQA/flake8` were separated at Phase 1 under seed `41729`,
written to `data/candidates/heldout/`, and guarded by a loader that refuses access
without an explicit `--allow-heldout` flag. Every subsequent phase verified
byte-integrity of the boundary and of `config/split.json`.

They were opened exactly once, at the end. `make split` re-verifies that no
repository crosses the boundary.

If you re-run anything, do not develop against held-out results. The gap between
dev and held-out is the reward-hacking measurement; it is only meaningful once.

## Per-phase commands

```sh
# Phase 1 / 1b — corpus and sandbox
make sandbox && make probe && make harvest && make split

# Phase 2 — the removed experiment (kept for the changelog)
make sample
python3 -m scripts.run_baselines all --fixture-mode replay
make review-set                      # human labelling queue (labels not collected)
make solvability-set
python3 -m scripts.run_solvability --fixture-mode replay

# Phase 3 — five-gate verifier and baselines
make sample-b
python3 -m scripts.run_baselines_b all --fixture-mode replay

# Phase 4 / 5 — the agent, dev and held-out
make replay-c
make report-c
```

The public sandbox interface, if you want to run one repo at one commit:

```sh
python3 -m scripts.run_tests OWNER/REPO COMMIT [PYTEST_SELECTOR ...]
```

It emits one JSON object with `exit_code`, `stdout`, `stderr`, `duration_s` and
`per_test_status`, and exits with pytest's code.

## Expected output

`make report-c` prints the arm table: B0 0/80, B1 13/80, B2 22/80, agent 26/80 on
development cases, with cost, tokens and latency per candidate. Held-out figures
and the dev-minus-held-out gap are in `research/phase-5-report.md`.

If your numbers differ from the committed ones while in replay mode, something is
wrong with the fixture layer — that is a bug worth reporting, not variance.

## Troubleshooting

**`make demo` asks for an API key.** It should not. Confirm `LLM_MODE`/fixture
mode is `replay`; a miss is meant to hard-fail with the missing hash, not prompt.

**A repo fails to build.** The image bakes separate `head` and `old` locked
environments per repository because historical dependency ranges genuinely
conflict. Commits far outside the probed range may need another lock profile;
this is a stated limitation, not a transient failure.

**Docker permission errors.** The sandbox needs to create and remove containers
with `--rm` and `--network none`. Rootless Docker works; Podman is untested.
