"""Small pytest plugin that writes stable per-test outcomes as JSON."""

from __future__ import annotations

import json
import os
from pathlib import Path


_reports: dict[str, dict[str, str]] = {}


def outcome_for_phases(phases: dict[str, str]) -> str:
    if phases.get("collect") == "failed" or phases.get("setup") == "failed" or phases.get("teardown") == "failed":
        return "error"
    if phases.get("call") == "failed":
        return "failed"
    if "skipped" in set(phases.values()):
        return "skipped"
    return "passed"


def pytest_runtest_logreport(report):  # type: ignore[no-untyped-def]
    phases = _reports.setdefault(report.nodeid, {})
    phases[report.when] = report.outcome


def pytest_collectreport(report):  # type: ignore[no-untyped-def]
    if report.failed:
        _reports[f"collection::{report.nodeid}"] = {"collect": "failed"}


def pytest_sessionfinish(session, exitstatus):  # type: ignore[no-untyped-def]
    del session
    statuses = []
    for nodeid, phases in sorted(_reports.items()):
        outcome = outcome_for_phases(phases)
        statuses.append({"nodeid": nodeid, "outcome": outcome, "phases": phases})
    path = Path(os.environ["CRUCIBLE_STATUS_FILE"])
    path.write_text(
        json.dumps({"exit_code": int(exitstatus), "tests": statuses}, sort_keys=True),
        encoding="utf-8",
    )
