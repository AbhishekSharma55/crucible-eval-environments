"""Hash-addressed OpenRouter fixture transport; replay is the safe default."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from typing import Any

from scripts.phase2_common import ROOT, json_dump


ENDPOINT = "https://openrouter.ai/api/v1/chat/completions"
FIXTURE_DIR = Path(os.environ.get("CRUCIBLE_FIXTURE_DIR", ROOT / "fixtures/openrouter"))
WALL_CAP_S = 180
HTTP_CHILD = r'''
import os, sys
from urllib import request
payload = sys.stdin.buffer.read()
req = request.Request(
    "https://openrouter.ai/api/v1/chat/completions", data=payload, method="POST",
    headers={"Authorization": f"Bearer {os.environ['OPENROUTER_API_KEY']}", "Content-Type": "application/json"},
)
with request.urlopen(req, timeout=180) as response:
    sys.stdout.buffer.write(response.read())
'''


class FixtureMiss(RuntimeError):
    pass


def request_hash(payload: dict[str, Any]) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(canonical).hexdigest()


def chat_completion(payload: dict[str, Any], *, mode: str = "replay") -> dict[str, Any]:
    if mode not in {"replay", "record"}:
        raise ValueError("fixture mode must be replay or record")
    digest = request_hash(payload)
    path = FIXTURE_DIR / f"{digest}.json"
    if path.exists():
        fixture = json.loads(path.read_text(encoding="utf-8"))
        if fixture["request"] != payload:
            raise RuntimeError(f"fixture hash collision at {path}")
        return fixture
    if mode == "replay":
        raise FixtureMiss(
            f"OpenRouter fixture miss {digest}; replay never reaches the network. "
            "Run the same command explicitly with --fixture-mode record and OPENROUTER_API_KEY set."
        )
    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        raise RuntimeError("OPENROUTER_API_KEY is required only in record mode")
    started = time.monotonic()
    try:
        completed = subprocess.run(
            [sys.executable, "-c", HTTP_CHILD], input=json.dumps(payload), text=True,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=os.environ.copy(), timeout=WALL_CAP_S,
        )
    except subprocess.TimeoutExpired:
        fixture = {
            "schema_version": 1, "request_hash": digest, "request": payload,
            "response": {"error": {"type": "wall_clock_timeout", "message": f"request exceeded {WALL_CAP_S}s"}},
            "latency_s": WALL_CAP_S,
        }
        json_dump(path, fixture)
        return fixture
    if completed.returncode:
        error_type = "record_transport_error"
        if "ConnectionResetError" in completed.stderr:
            error_type = "connection_reset"
        fixture = {
            "schema_version": 1,
            "request_hash": digest,
            "request": payload,
            "response": {"error": {
                "type": error_type,
                "message": "The provider transport failed before a complete response; usage and any partial charge are unknown.",
            }},
            "latency_s": round(time.monotonic() - started, 3),
        }
        json_dump(path, fixture)
        return fixture
    body = json.loads(completed.stdout)
    fixture = {
        "schema_version": 1,
        "request_hash": digest,
        "request": payload,
        "response": body,
        "latency_s": round(time.monotonic() - started, 3),
    }
    json_dump(path, fixture)
    return fixture


def fixture_text(fixture: dict[str, Any]) -> str:
    response = fixture["response"]
    if "error" in response:
        raise RuntimeError(f"cached OpenRouter error: {response['error']}")
    try:
        content = response["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise RuntimeError(f"fixture has no chat message: {response}") from exc
    if not isinstance(content, str):
        raise RuntimeError("fixture chat content is not text")
    return content.strip()


def fixture_usage(fixture: dict[str, Any]) -> dict[str, Any]:
    usage = dict(fixture["response"].get("usage") or {})
    return {
        "prompt_tokens": int(usage.get("prompt_tokens") or 0),
        "completion_tokens": int(usage.get("completion_tokens") or 0),
        "total_tokens": int(usage.get("total_tokens") or 0),
        "cost_usd": float(usage.get("cost") or 0.0),
        "latency_s": float(fixture.get("latency_s") or 0.0),
        "request_hash": fixture["request_hash"],
    }
