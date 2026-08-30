# Crucible phase-one corpus and sandbox

This repository manufactures deterministic coding-agent evaluation inputs from
real Python bug-fix pull requests. Phase one contains no agent and no model
calls: it establishes the hermetic test substrate, cached GitHub evidence,
candidate rejection data, and a repo-level dev/held-out boundary.

## Reproduce

Requirements: Docker Desktop/Engine with BuildKit, GNU Make, and Python 3.11+.
No Python packages are required for the phase-one commands.

```sh
make sandbox
make probe
make harvest
make split
make test
```

`make sandbox` intentionally performs a clean build. The Python 3.11.9 base is
pinned by digest, OS packages and per-repo Python environments are pinned, and
the target repositories build without a compiler in the image. Repository git
mirrors are cloned once into the image.

Every test container is launched with `--network none`. The public interface is:

```sh
python3 -m scripts.run_tests OWNER/REPO COMMIT [PYTEST_SELECTOR ...]
```

It emits one JSON object containing `exit_code`, `stdout`, `stderr`,
`duration_s`, and `per_test_status`. The process exit code matches pytest.

`make harvest` never calls GitHub. It reconstructs 3,073 candidates from the
committed `data/github-api/` GraphQL snapshots and committed dynamic-validation
records, with `GITHUB_TOKEN` explicitly removed from its environment. Refreshing
the API cache is a separate, deliberate operation:

```sh
GITHUB_TOKEN=... python3 -m scripts.github_cache --pages 5
```

The refresh code applies bounded exponential backoff and never persists the
token. Do not commit `.env` files.

## Split boundary

The fixed seed and repo assignment live in `config/split.json`. Candidate files
are written directly into `data/candidates/dev/` and
`data/candidates/heldout/`; no persistent unsplit corpus exists. A loader refuses
held-out access unless passed `--allow-heldout`. Development work must not use
that flag.

`make split` replays the cache and verifies that no repository crosses the
boundary. The held-out directory is reserved for final evaluation.

## Online construction versus offline replay

The committed corpus is the reproducible artifact. API refresh is an explicit
online setup operation. Dynamic validation is offline: it builds a test-only
patch from the git mirror cached in the image, applies that patch to the PR's
first parent, and runs the same selected tests at the parent and merge commit.
Each endpoint is run twice. Per-test maps distinguish assertion failures from
setup or collection errors, and validation records clean transitions,
patch-application failures, build failures, and nondeterministic outcomes.

See `research/phase-1-report.md` for measured results, drops, limitations, and
the substrate recommendation.
