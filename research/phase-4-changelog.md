# Phase 4 changelog

Date: 2026-08-31

The initial choices below were made before measurement so later changes can be
distinguished from case-set tuning. Rows explicitly labeled post-measurement did
not alter prompts, tools, limits, cases, model outputs, or gate outcomes.

| revision | evidence | change | reason |
|---|---|---|---|
| Initial implementation | Phase 3 B2 breakdown only | Added one sequential native-tool loop with parent-side inspection, one staged new test file, endpoint execution, and the unchanged G1–G5 verifier. | Directly targets the already reported G1, G2, and G5 failure modes with external evidence. |
| Fairness limits | Code/unit tests, no model output | Fixed 30 tool calls, 16 model turns, 360 seconds, and five `check_gates` invocations per case. Premature or invalid gate calls consume budget. | B2 receives five full-stack selections; the agent may not receive more full-stack validation calls. |
| Prompt provenance | File-load test | Put the system prompt, task template, and native tool schemas in `agents/*.md`; request fixtures store hashes of all three. | Makes every instruction change visible in source history and fixture hashes. |
| Historical test discovery fix | Parent-side smoke test on the first fixed case, Tenacity #236 | Broadened `list_tests` discovery beyond configured *new-file* layouts after it initially returned zero tests for historical `tenacity/tests/`. The write boundary remains unchanged at `tests/**`. | `list_tests` must describe where tests actually lived at the parent; configured authored-file placement and historical layout are different concepts. No authored model output was inspected. |
| k=3 subset freeze | Repository composition only, no model output | Replaced an initially generated global 30-case hash rank (which contained 18 Flask cases) with repository-proportional allocation plus within-repository SHA-256 rank: Flask 12, Click 11, Marshmallow 4, Tenacity 2, attrs 1. Seed 94721. | Avoids a visibly unrepresentative rollout subset without using labels, baseline outcomes, or agent outcomes. Exact IDs are frozen in `data/phase4/k3-subset.json`. |
| Hard record limits | Unit/smoke tests, no model output | Run record-mode model calls in a killable process group bounded by remaining case time; added a conservative per-request budget preflight and $8 Phase 4 executed-cost ceiling. | Enforces the declared wall-clock and project-cost constraints even during an in-flight provider request. |
| Reporting | Baseline artifacts only | Report generator refuses any incomplete rollout, computes case-aligned B2-to-agent transitions, strict pass^k and pass@k, flags possible gate gaming without selecting on it, and derives a four-arm SVG plot. | Prevents partial-case denominators, failure displacement, or hidden cost from being presented as improvement. |
| Provider transport recovery | The same unrecorded request reset its TLS connection on two resume attempts during pass@1 case 33 | Cache a structured zero-usage model-error fixture when the record subprocess exits without a complete provider response, matching the shared layer's existing timeout-fixture behavior. Continue from the deterministic checkpoint. | A persistent transport failure must count as a model error instead of aborting the entire fixed case set. Prompts, tools, limits, selection, and G1–G5 are unchanged. The two failed attempts may have unknown partial provider charges and must be disclosed. |
| Post-measurement replay audit | The first keyless re-execution produced a fixture miss because pytest output changed temporary directory names, memory addresses, and durations | Replay each hash-addressed model fixture against the exact measured tool observation stored in the trajectory, while checking the recorded tool names and arguments. Write a separate replay audit instead of overwriting measured results. | The recorded observation is the actual prompt surface. Re-running a semantically identical test cannot reproduce incidental process text byte-for-byte. This change validates all 1,814 model requests across 140 trajectories without changing any measured request or outcome. |
| Post-measurement human gaming review | Automated review flags plus all 23 accepted pass@1 tests | Added case-specific dispositions to the report. | Reporting only: makes false positives, structural attempts, and the Flask #5242 gate-evasive intermediate conditional explicit. No result was accepted, rejected, or rerun based on this review. |

The only model-facing content is the three files under `agents/`. Further
changes to those files, tool behavior, limits, subset membership, or metric
definitions after fixtures are recorded must be appended here with the evidence
used to motivate them.
