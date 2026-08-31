"""Tiny stdlib-only line tracer loaded only by the Phase 3 pytest runner."""

from __future__ import annotations

from collections import defaultdict
import json
import os
from pathlib import Path
import sys


_ROOT = Path(os.environ["CRUCIBLE_CHECKOUT"]).resolve()
_OUTPUT = Path(os.environ["CRUCIBLE_COVERAGE_FILE"])
_LINES: dict[str, set[int]] = defaultdict(set)


def _trace(frame, event, arg):
    if event == "line":
        try:
            path = Path(frame.f_code.co_filename).resolve().relative_to(_ROOT).as_posix()
        except (OSError, ValueError):
            return _trace
        _LINES[path].add(frame.f_lineno)
    return _trace


def pytest_sessionstart(session):
    sys.settrace(_trace)


def pytest_sessionfinish(session, exitstatus):
    sys.settrace(None)
    _OUTPUT.write_text(
        json.dumps({path: sorted(lines) for path, lines in sorted(_LINES.items())}, sort_keys=True),
        encoding="utf-8",
    )
