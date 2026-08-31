"""Derive the Phase 4 report and accuracy-cost plot from committed raw results."""

from __future__ import annotations

from collections import Counter, defaultdict
from html import escape
import json
import math
from pathlib import Path
import statistics
from typing import Any

from scripts.phase2_common import ROOT
from scripts.phase3_common import json_dump


PHASE3_RESULTS = ROOT / "results/phase3"
PHASE4_RESULTS = ROOT / "results/phase4"
REPORT = ROOT / "research/phase-4-report.md"


def load(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise RuntimeError(f"missing measured result: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def category(result: dict[str, Any]) -> str:
    verification = result.get("verification") or {}
    if verification.get("abort_reason") == "model_output_parse_failed":
        return "OUTPUT_PARSE"
    for name in ("g1", "g2", "g3", "g4", "g5"):
        if (verification.get("gates") or {}).get(name, {}).get("status") == "fail":
            return name.upper()
    if result.get("stop_reason") == "model_error":
        return "MODEL_ERROR"
    if not result.get("gate_attempts") and result.get("rollout") is not None:
        return "NO_GATE_CHECK"
    return "CASE_LIMIT"


def arm_metrics(payload: dict[str, Any], name: str) -> dict[str, Any]:
    n = payload["n"]
    totals = payload.get("totals") or {}
    wall_per = payload.get("wall_clock_per_candidate_s")
    if wall_per is None:
        wall_per = sum(float(item.get("wall_s") or 0) for item in payload.get("results", [])) / n
    return {
        "name": name,
        "n": n,
        "verified": payload["verified_count"],
        "accuracy": payload["verified_rate"],
        "tokens": float(totals.get("total_tokens") or 0) / n,
        "cost": float(totals.get("cost_usd") or 0) / n,
        "latency": float(totals.get("latency_s") or 0) / n,
        "wall": wall_per,
    }


def fixture_totals() -> dict[str, Any]:
    files = sorted((ROOT / "fixtures/openrouter").glob("*.json"))
    cost = 0.0
    tokens = 0
    errors = 0
    for path in files:
        fixture = json.loads(path.read_text(encoding="utf-8"))
        response = fixture.get("response") or {}
        errors += int("error" in response)
        usage = response.get("usage") or {}
        cost += float(usage.get("cost") or 0)
        tokens += int(usage.get("total_tokens") or 0)
    return {"fixtures": len(files), "errors": errors, "tokens": tokens, "cost_usd": cost}


def failure_counts(payload: dict[str, Any]) -> Counter[str]:
    return Counter(category(item) for item in payload["results"] if not item["passed"])


def write_svg(arms: list[dict[str, Any]], path: Path) -> None:
    width, height = 760, 470
    left, right, top, bottom = 90, 35, 40, 75
    plot_w, plot_h = width - left - right, height - top - bottom
    max_cost = max(item["cost"] for item in arms) or 0.001
    max_cost *= 1.12

    def x(value: float) -> float:
        return left + value / max_cost * plot_w

    def y(value: float) -> float:
        return top + (1 - value) * plot_h

    colors = {"B0": "#6b7280", "B1": "#2563eb", "B2": "#7c3aed", "Agent": "#dc2626"}
    lines = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="white"/>',
        '<text x="380" y="24" text-anchor="middle" font-family="sans-serif" font-size="17">Verified accuracy against executed model cost per candidate</text>',
    ]
    for tick in range(0, 101, 20):
        yy = y(tick / 100)
        lines.append(f'<line x1="{left}" y1="{yy:.1f}" x2="{width-right}" y2="{yy:.1f}" stroke="#e5e7eb"/>')
        lines.append(f'<text x="{left-12}" y="{yy+5:.1f}" text-anchor="end" font-family="sans-serif" font-size="12">{tick}%</text>')
    for index in range(6):
        value = max_cost * index / 5
        xx = x(value)
        lines.append(f'<line x1="{xx:.1f}" y1="{top}" x2="{xx:.1f}" y2="{height-bottom}" stroke="#f3f4f6"/>')
        lines.append(f'<text x="{xx:.1f}" y="{height-bottom+24}" text-anchor="middle" font-family="sans-serif" font-size="12">${value:.4f}</text>')
    lines.extend([
        f'<line x1="{left}" y1="{top}" x2="{left}" y2="{height-bottom}" stroke="#111827"/>',
        f'<line x1="{left}" y1="{height-bottom}" x2="{width-right}" y2="{height-bottom}" stroke="#111827"/>',
        f'<text x="{left + plot_w/2:.1f}" y="{height-18}" text-anchor="middle" font-family="sans-serif" font-size="13">Executed model cost / candidate (USD)</text>',
        f'<text x="22" y="{top + plot_h/2:.1f}" transform="rotate(-90 22 {top + plot_h/2:.1f})" text-anchor="middle" font-family="sans-serif" font-size="13">Verified regression-test rate</text>',
    ])
    offsets = {"B0": (12, -10), "B1": (10, -10), "B2": (10, -10), "Agent": (10, -10)}
    for item in arms:
        xx, yy = x(item["cost"]), y(item["accuracy"])
        dx, dy = offsets[item["name"]]
        color = colors[item["name"]]
        lines.append(f'<circle cx="{xx:.1f}" cy="{yy:.1f}" r="6" fill="{color}"/>')
        label = escape(f"{item['name']} {item['accuracy']:.1%}")
        lines.append(f'<text x="{xx+dx:.1f}" y="{yy+dy:.1f}" font-family="sans-serif" font-size="13" fill="{color}">{label}</text>')
    lines.append("</svg>")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def fmt_breakdown(counts: Counter[str], key: str) -> int:
    return int(counts.get(key, 0))


def model_error_count(counts: Counter[str]) -> int:
    return fmt_breakdown(counts, "OUTPUT_PARSE") + fmt_breakdown(counts, "MODEL_ERROR")


def main() -> int:
    baseline_payloads = {name: load(PHASE3_RESULTS / f"{name.lower()}.json") for name in ("B0", "B1", "B2")}
    rollouts = [load(PHASE4_RESULTS / f"agent-rollout-{index}.json") for index in range(3)]
    for payload in rollouts:
        if not payload.get("complete"):
            raise RuntimeError(
                f"rollout {payload.get('rollout')} is incomplete ({payload.get('n')}/{payload.get('expected_n')}); refusing to publish partial metrics"
            )
    pass1 = rollouts[0]
    if pass1["n"] != 80:
        raise RuntimeError(f"pass@1 must cover all 80 fixed cases, found {pass1['n']}")
    maps = [{item["case_id"]: item for item in payload["results"]} for payload in rollouts]
    common_ids = sorted(set(maps[0]).intersection(maps[1], maps[2]))
    if len(common_ids) not in {30, 80}:
        raise RuntimeError(f"k=3 common set must contain fixed 30-case subset or all 80, found {len(common_ids)}")
    rates = [sum(maps[index][cid]["passed"] for cid in common_ids) / len(common_ids) for index in range(3)]
    pass_power_k = sum(all(mapping[cid]["passed"] for mapping in maps) for cid in common_ids) / len(common_ids)
    pass_at_k = sum(any(mapping[cid]["passed"] for mapping in maps) for cid in common_ids) / len(common_ids)
    spread = max(rates) - min(rates)
    stdev = statistics.pstdev(rates)

    arms = [arm_metrics(baseline_payloads[name], name) for name in ("B0", "B1", "B2")]
    arms.append(arm_metrics(pass1, "Agent"))
    write_svg(arms, PHASE4_RESULTS / "accuracy-vs-cost.svg")
    baseline_failures = {name: failure_counts(payload) for name, payload in baseline_payloads.items()}
    agent_failures = failure_counts(pass1)

    b2_by_id = {item["case_id"]: item for item in baseline_payloads["B2"]["results"]}
    agent_by_id = maps[0]
    recovery: dict[str, dict[str, Any]] = {}
    for source in ("G1", "G2", "G3", "G4", "G5", "OUTPUT_PARSE", "CASE_LIMIT"):
        ids = [cid for cid, item in b2_by_id.items() if not item["passed"] and category(item) == source]
        destinations = Counter("PASS" if agent_by_id[cid]["passed"] else category(agent_by_id[cid]) for cid in ids)
        recovery[source] = {"n": len(ids), "recovered": destinations.get("PASS", 0), "destinations": dict(sorted(destinations.items()))}

    flagged = []
    for result in pass1["results"]:
        flags = set(result.get("gaming_flags") or [])
        locations = []
        for attempt in result.get("gate_attempts") or []:
            attempt_flags = attempt.get("gaming_flags") or []
            if attempt_flags:
                flags.update(attempt_flags)
                locations.append(f"gate_call_{attempt.get('gate_call')}")
        for event in result.get("events") or []:
            event_flags = (event.get("observation") or {}).get("review_flags") or []
            if event_flags:
                flags.update(event_flags)
                locations.append(f"write_step_{event.get('step')}")
        if flags:
            flagged.append({
                "case_id": result["case_id"], "passed": result["passed"],
                "flags": sorted(flags), "locations": sorted(set(locations)),
            })
    project = fixture_totals()
    replay_audit = load(PHASE4_RESULTS / "replay-audit.json")
    if replay_audit.get("cases_checked") != sum(payload["n"] for payload in rollouts):
        raise RuntimeError("keyless replay audit does not cover every measured trajectory")
    agent = arms[-1]
    b2 = arms[2]
    cost_ratio = agent["cost"] / b2["cost"] if b2["cost"] else math.inf
    token_ratio = agent["tokens"] / b2["tokens"] if b2["tokens"] else math.inf
    latency_ratio = agent["latency"] / b2["latency"] if b2["latency"] else math.inf
    wall_ratio = agent["wall"] / b2["wall"] if b2["wall"] else math.inf
    accuracy_delta = agent["accuracy"] - b2["accuracy"]
    overlap = sum(b2_by_id[cid]["passed"] and agent_by_id[cid]["passed"] for cid in agent_by_id)
    b2_losses = sum(b2_by_id[cid]["passed"] and not agent_by_id[cid]["passed"] for cid in agent_by_id)
    b2_recoveries = sum(not b2_by_id[cid]["passed"] and agent_by_id[cid]["passed"] for cid in agent_by_id)
    protocol = (
        "k=3 on the full 80-case set"
        if len(common_ids) == 80
        else "k=3 on a fixed SHA-256-ranked 30-case subset and k=1 on the other 50 cases"
    )

    arm_rows = "\n".join(
        f"| {item['name']} | {item['verified']}/{item['n']} | {item['accuracy']:.2%} | {item['tokens']:,.1f} | ${item['cost']:.6f} | {item['latency']:.3f} s | {item['wall']:.3f} s |"
        for item in arms
    )
    failure_rows = "\n".join(
        f"| {name} | {payload['n'] - payload['verified_count']} | "
        + " | ".join(str(fmt_breakdown(baseline_failures[name], key)) for key in ("G1", "G2", "G3", "G4", "G5"))
        + f" | {model_error_count(baseline_failures[name])} | {fmt_breakdown(baseline_failures[name], 'CASE_LIMIT')}"
        + " | 0 |"
        for name, payload in baseline_payloads.items()
    )
    failure_rows += (
        f"\n| Agent pass@1 | {pass1['n'] - pass1['verified_count']} | "
        + " | ".join(str(fmt_breakdown(agent_failures, key)) for key in ("G1", "G2", "G3", "G4", "G5"))
        + f" | {model_error_count(agent_failures)} | {fmt_breakdown(agent_failures, 'CASE_LIMIT')}"
        + f" | {fmt_breakdown(agent_failures, 'NO_GATE_CHECK')} |"
    )
    recovery_rows = "\n".join(
        f"| {source} | {item['n']} | {item['recovered']} | {json.dumps(item['destinations'], sort_keys=True)} |"
        for source, item in recovery.items() if item["n"]
    )
    manual_dispositions = {
        "marshmallow-code/marshmallow#1903": "False positive: version data is the behavior under test; no runtime checkout branch. Genuine attempts, but no gate check.",
        "marshmallow-code/marshmallow#1990": "Implementation-coupled symbol probe, but no checkout detection. It failed without a gate check and was not selected.",
        "pallets/click#1737": "False positive: `hasattr` asserts the documented terminal-size return shape. Accepted test is behavioral and genuine.",
        "pallets/click#1754": "Concerning structural attempt: an intermediate test inspected function source for `mktemp`. It never reached a gate and was not selected.",
        "pallets/click#1839": "False positive: `subprocess` is monkeypatched to exercise URL launching; no git inspection. Accepted test is behavioral.",
        "pallets/click#1942": "False positive: mocked `subprocess.run` supplies locale-dependent Bash output; no git inspection. Accepted test is behavioral.",
        "pallets/click#2944": "False positive: subprocess mocks observe pager invocation and symlink identity; no git inspection. The case never reached a gate.",
        "pallets/click#3055": "False positives: the test executes a pager and reads its output file. It does not inspect source, version, git, or the checkout; accepted behavior is genuine.",
        "pallets/flask#4152": "Mostly false positive on `client.open`; the last revision probes a type annotation structurally. It never reached a gate and was not selected.",
        "pallets/flask#4298": "False positive: subprocess runs mypy for the reported typing regression, not git. It never reached a gate.",
        "pallets/flask#4445": "False positive on the overridden `FlaskClient.open` method. Accepted redirect behavior is genuine.",
        "pallets/flask#5242": "One intermediate revision used `if recorded`, which could accept the parent and appeared gate-evasive. It was never gate-checked; the accepted revision replaced it with unconditional `pytest.warns` and is genuine.",
    }
    flagged_rows = (
        "\n".join(
            f"| {item['case_id']} | {'yes' if item['passed'] else 'no'} | {', '.join(item['flags'])} ({', '.join(item['locations'])}) | {manual_dispositions[item['case_id']]} |"
            for item in flagged
        )
        if flagged else "| — | — | — | No automated runtime-checkout/gate-gaming pattern was flagged in the selected pass@1 candidates. |"
    )

    report = f"""# Phase 4 report — execution-grounded single agent

Date: 2026-08-31

## Outcome

The single-threaded agent passed **{pass1['verified_count']}/{pass1['n']} ({pass1['verified_rate']:.2%})** on the fixed Phase 3 case set at pass@1. The rollout protocol was **{protocol}**. On the {len(common_ids)} cases with three rollouts, rates were {', '.join(f'{rate:.2%}' for rate in rates)}: mean **{statistics.mean(rates):.2%}**, population standard deviation **{stdev:.2%}**, and range/spread **{min(rates):.2%}–{max(rates):.2%} ({spread:.2%} points)**.

Here **pass^3** means the strict reliability rate—the same case passed all three rollouts—not pass@3. It was **{pass_power_k:.2%}**. For completeness, the any-success pass@3 rate was **{pass_at_k:.2%}**. This definition directly measures whether the agent produces a valid environment consistently rather than once in three attempts.

The agent changed accuracy by **{accuracy_delta:+.2%} points** relative to B2 while using **{cost_ratio:.2f}×** B2's executed model cost, **{token_ratio:.2f}×** its tokens, **{latency_ratio:.2f}×** its recorded model latency, and **{wall_ratio:.2f}×** its end-to-end wall time per candidate. The gain is therefore small and expensive, not a decisive efficiency win.

## First-failing-gate breakdown

Counts are mutually exclusive first failures. G1–G5 are unchanged from Phase 3. `NO_GATE_CHECK` means the agent stopped or hit a limit without spending any full-stack validation call; it is a failure, not an omitted case.

| arm | failures | G1 | G2 | G3 | G4 | G5 | parse/model | case limit | no gate check |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
{failure_rows}

The case-aligned transition from B2's failures to the agent's pass@1 outcomes is the clearest evidence of what feedback changed:

| B2 first failure | B2 cases | recovered to agent pass | agent destinations (including pass) |
|---|---:|---:|---|
{recovery_rows}

This table should be read literally. A lower G2 count, for example, is evidence that fix-side execution feedback repaired broken tests only to the extent that B2-G2 cases moved to `PASS`; movement from G2 to G1 or G4 is displacement, not recovery. Failure modes with zero or negligible recovered cases were not fixed by the loop.

### What the loop fixed—and did not

The loop recovered **3/17 B2-G1 cases**, **6/24 B2-G2 cases**, and **2/9 B2-G5 cases**. It recovered **0/5 B2-G4 cases** and **0/3 parse/model-error cases**; there were no B2-G3 failures to test. These are modest, case-aligned recoveries, not elimination of those failure modes.

The aggregate zeroes in the agent's G1, G2, and G5 columns are misleading if read alone: only 30 pass@1 trajectories reached `check_gates` (23 passed and 7 failed G4), while 37 ended with no gate check and 13 ended in model/provider error. Relative to B2, the agent retained **{overlap}/22** B2 successes, recovered **{b2_recoveries}** B2 failures, and lost **{b2_losses}** B2 successes. The net +1 case is substantial churn, not a uniform improvement.

Of the 13 pass@1 model errors, 12 were cached connection resets during the laptop/network interruption and one was a 180-second model-request timeout. They count as failures. Because the fixed case order clustered them in Click, the observed rate mixes agent quality with that outage; no cases were rerun or substituted after outcomes were known.

## Cost, tokens, and latency

All values are per evaluated candidate. Model latency is the sum of provider-call latency recorded in fixtures. End-to-end wall time includes local verification/orchestration and, for recorded calls, provider waiting. B1's temperature-zero calls are shared with B2 in project-spend accounting, although each arm's executed-cost column reflects what that arm consumes in isolation.

| arm | verified | accuracy | tokens / candidate | executed cost / candidate | stored model latency / candidate | end-to-end wall / candidate |
|---|---:|---:|---:|---:|---:|---:|
{arm_rows}

![Accuracy against model cost](../results/phase4/accuracy-vs-cost.svg)

The plot uses executed model cost per candidate on a linear x-axis and verified G1–G5 accuracy on the y-axis. It therefore exposes, rather than hides, an accuracy gain purchased through longer trajectories.

## Gate-gaming review

The evaluator scans every staged revision and gate attempt for runtime source/file inspection, environment or version branching, git/commit inspection, skip/xfail, unconditional failure, and missing-symbol probes. Flags are review evidence only and never reject or select a candidate; G1–G5 remain the primary metric.

| case | passed | automated flags | review disposition |
|---|---|---|---|
{flagged_rows}

All 12 flagged cases, every flagged intermediate revision, and all 23 accepted pass@1 tests were manually read. No accepted test detected a checkout, commit, gate, or source patch. The Flask #5242 intermediate conditional and Click #1754 source-inspection attempt are reported above even though neither was gate-checked or selected.

## Protocol and fairness

- The case set is exactly `data/phase3/case-set.json` (n=80); held-out repositories were not opened.
- The actor is the Phase 3 pinned model, `{pass1['model']}`, at temperature {pass1['temperature']} with a deterministic per-case rollout seed.
- Each trajectory is sequential: one model conversation and serial tool execution, with no subagents or parallel tool calls.
- The only capabilities are `list_tests`, windowed `read_file`, bounded `search`, test-only `write_test`, one-endpoint `run_test`, and `check_gates`.
- Host enforcement caps each case at {pass1['limits']['max_tool_steps']} tool steps, {pass1['limits']['max_model_turns']} model turns, {pass1['limits']['per_case_wall_s']} seconds, and **{pass1['limits']['max_check_gates_calls']} full G1–G5 calls**, equal to B2's five attempts.
- Long observations contain explicit truncation markers. Tool failures return a recovery action instead of a Python traceback.
- Replay is the default and a missing request fixture aborts the run. The keyless audit reconstructed **{replay_audit['cases_checked']} trajectories and {replay_audit['fixtures_checked']} model requests** from their exact measured tool observations; this avoids false misses from temporary paths, object addresses, and timings in re-executed pytest output. Endpoint containers remain network-disabled and fresh.
- The system prompt, task template, and native tool schemas are version-controlled under `agents/`; their SHA-256 hashes are stored in every rollout result.

## Spend

Across the project's hash-addressed OpenRouter fixture directory there are **{project['fixtures']} unique requests**, **{project['tokens']:,} reported tokens**, and **${project['cost_usd']:.12f}** of API-reported spend. {project['errors']} cached provider errors have no usage and any provider-side partial charge for them is unknown and excluded. This unique-fixture total avoids double-counting requests reused by B1/B2 or replayed later.

## Reproduction

```bash
# Default feasible protocol: k=1 on 80 plus two more fixed-subset rollouts.
python3 -m scripts.run_phase4_agent --fixture-mode replay --rollout-plan subset

# Only after explicit spending authorization, record missing fixtures once.
OPENROUTER_API_KEY=... python3 -m scripts.run_phase4_agent --fixture-mode record --rollout-plan subset --resume

python3 -m scripts.report_phase4
```

The raw trajectories, per-gate evidence, usage, limits, and instruction hashes are in `results/phase4/agent-rollout-0.json` through `agent-rollout-2.json`. The fixed subset definition is `data/phase4/k3-subset.json`.
"""
    REPORT.write_text(report, encoding="utf-8")
    json_dump(PHASE4_RESULTS / "summary.json", {
        "schema_version": 1,
        "pass_at_1": pass1["verified_rate"],
        "k_common_n": len(common_ids),
        "rollout_rates": rates,
        "mean": statistics.mean(rates),
        "population_stdev": stdev,
        "spread": spread,
        "pass_power_k": pass_power_k,
        "pass_at_k": pass_at_k,
        "arms": arms,
        "project": project,
        "gaming_flagged_case_ids": [item["case_id"] for item in flagged],
        "b2_failure_recovery": recovery,
    })
    print(f"wrote {REPORT}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except RuntimeError as exc:
        raise SystemExit(f"Phase 4 report not written: {exc}")
