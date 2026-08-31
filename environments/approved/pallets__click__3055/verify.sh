#!/usr/bin/env bash
# Re-check this environment through the unchanged Phase 3 gate stack (G1-G5).
# Exits non-zero if any gate fails.
#
#   ./verify.sh                 offline replay (default). Re-applies the
#                               committed gate functions to the recorded gate
#                               evidence and the committed candidate record.
#                               No Docker, no network, no API key.
#
#   ./verify.sh --mode live     re-executes both endpoints in the pinned
#                               sandbox container through the same verifier
#                               the agent was scored with. Needs Docker, the
#                               crucible-sandbox:phase3 image, and the local
#                               git mirror under cache/repos/.
set -euo pipefail
HERE="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "${HERE}/../../.." && pwd)"
cd "${REPO_ROOT}"
exec "${PYTHON:-python3}" -m scripts.export_environments verify --environment "${HERE}" "$@"
