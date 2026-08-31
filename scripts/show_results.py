"""Print the published results table from committed runs.

Reads only committed JSON. No model calls, no network, no API key. Used by
`make demo` so a reviewer sees the headline numbers rather than a written file.
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def load(rel: str):
    path = ROOT / rel
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text())
    except (json.JSONDecodeError, OSError):
        return None


def rate(verified, n):
    if not n:
        return "-"
    return f"{verified}/{n} ({100.0 * verified / n:.2f}%)"


def arm_row(name, dev, heldout):
    dev_s = rate(*dev) if dev else "-"
    held_s = rate(*heldout) if heldout else "not run"
    if dev and heldout and dev[1] and heldout[1]:
        gap = (100.0 * dev[0] / dev[1]) - (100.0 * heldout[0] / heldout[1])
        gap_s = f"{gap:+.2f} pp"
    else:
        gap_s = "-"
    return f"  {name:<34} {dev_s:>18}   {held_s:>18}   {gap_s:>10}"


def baseline_counts(path):
    d = load(path)
    if not d:
        return None
    return d.get("verified_count"), d.get("n")


def main() -> int:
    print()
    print("  Verified regression-test rate")
    print("  " + "-" * 84)
    print(f"  {'arm':<34} {'development':>18}   {'held-out':>18}   {'gap':>10}")
    print("  " + "-" * 84)

    arms = [
        ("B0  stub, no model", "results/phase3/b0.json", "results/phase5/heldout/b0.json"),
        ("B1  single prompt", "results/phase3/b1.json", "results/phase5/heldout/b1.json"),
        ("B2  best-of-5, gates as selector", "results/phase3/b2.json", "results/phase5/heldout/b2.json"),
    ]
    for label, dev_path, held_path in arms:
        print(arm_row(label, baseline_counts(dev_path), baseline_counts(held_path)))

    # Agent: dev comes from the clean re-run; held-out from phase 5 if present.
    run2 = load("results/phase4/summary-run2.json")
    agent_dev = None
    if run2 and isinstance(run2.get("run2"), dict):
        agent_dev = (run2["run2"].get("verified_count"), run2["run2"].get("n"))
    agent_held = baseline_counts("results/phase5/heldout/summary.json") or baseline_counts(
        "results/phase5/heldout/agent.json"
    )
    print(arm_row("Crucible agent", agent_dev, agent_held))
    print("  " + "-" * 84)

    if run2 and isinstance(run2.get("run1"), dict):
        r1, r2 = run2["run1"], run2["run2"]
        print()
        print("  Measurement repair (whole arm re-run, zero selective reruns)")
        print(
            f"    run 1  {rate(r1.get('verified_count'), r1.get('n'))}"
            f"   infrastructure failures: {r1.get('infrastructure_failures')}"
        )
        print(
            f"    run 2  {rate(r2.get('verified_count'), r2.get('n'))}"
            f"   infrastructure failures: {r2.get('infrastructure_failures')}"
        )

    align = (run2 or {}).get("b2_alignment")
    if align:
        print()
        print("  Against B2, case by case")
        print(f"    recovered B2 failures : {align.get('recovered_b2_failures')}")
        print(f"    lost B2 passes        : {align.get('lost_b2_passes')}")
        print(f"    retained B2 passes    : {align.get('retained_b2_passes')}")

    if run2 and isinstance(run2.get("run2"), dict):
        fb = run2["run2"].get("first_failure_breakdown") or {}
        if fb.get("NO_GATE_CHECK"):
            n = run2["run2"].get("n") or 0
            reached = run2["run2"].get("gate_reached_count")
            print()
            print("  Main failure mode")
            print(
                f"    {fb['NO_GATE_CHECK']} of {n} cases never reached a gate check"
                f" ({reached} did)."
            )
            print("    The agent exhausts its step budget before validating.")

    print()
    print("  Numbers above are read from committed JSON in results/.")
    print("  Methodology: research/phase-*-report.md   How it evolved: CHANGELOG-IMPROVEMENT.md")
    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
