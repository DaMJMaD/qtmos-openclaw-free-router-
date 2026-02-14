#!/usr/bin/env python3
"""QTMoS local HTTP tool backend for OpenClaw and other clients."""

from __future__ import annotations

import io
import json
import os
import shlex
import sys
import threading
import time
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.cognitive_system import CognitiveSystem  # noqa: E402
from llm.llm_adapters import (  # noqa: E402
    call_puter_with_model,
    has_puter_auth,
    list_puter_models,
    query_ollama,
)

APP_NAME = "qtmos-tool-api"
APP_VERSION = "1.0.0"

SAFE_COMMANDS = {
    "ask",
    "chat",
    "claw",
    "core-list",
    "gemini",
    "health",
    "ollama",
    "pack-list",
    "puter-chat",
    "puter-models",
    "pulse-now",
    "recall",
    "state",
    "synthesize",
    "wander",
    "whoami",
}

BLOCKED_COMMANDS = {
    "create-profile",
    "crawl",
    "define",
    "duel",
    "exit",
    "forget",
    "genesis-review",
    "ingest-api",
    "ingest-ollama",
    "ingest-url",
    "learn",
    "load-core",
    "load-pack",
    "new-profile",
    "promote",
    "pulse-start",
    "pulse-stop",
    "puter-login",
    "qtm",
    "qtm-shell",
    "quit",
    "run-script",
    "scan",
    "wslmenu",
}

SAFE_CLAW_SUBCOMMANDS = {"health", "help", "memory", "status"}

app = FastAPI(title="QTMoS Tool API", version=APP_VERSION)

cors_raw = os.getenv("QTMOS_API_CORS_ORIGINS", "http://localhost,http://127.0.0.1")
cors_origins = [x.strip() for x in cors_raw.split(",") if x.strip()]
if cors_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_methods=["GET", "POST"],
        allow_headers=["*"],
    )

_SYSTEM = CognitiveSystem()
_SYSTEM_LOCK = threading.Lock()


class AskRequest(BaseModel):
    prompt: str = Field(min_length=1, max_length=8000)
    model: str | None = Field(default=None, max_length=128)
    allow_local_fallback: bool = True


class CommandRequest(BaseModel):
    cmd: str = Field(min_length=1, max_length=512)


def _token_present() -> bool:
    return bool(
        (os.getenv("PUTER_API_KEY") or "").strip()
        or (os.getenv("PUTER_AUTH_TOKEN") or "").strip()
        or (os.getenv("puterAuthToken") or "").strip()
    )


def _normalize_model_reply(reply: str) -> str:
    """Normalize provider replies that may come wrapped as JSON text."""
    if not isinstance(reply, str):
        return str(reply)

    text = reply.strip()
    if not text:
        return text

    if text.startswith("{") and text.endswith("}"):
        try:
            payload = json.loads(text)
            if isinstance(payload, dict):
                msg = payload.get("message")
                if isinstance(msg, dict):
                    c = msg.get("content")
                    if isinstance(c, str) and c.strip():
                        return c.strip()

                c2 = payload.get("content")
                if isinstance(c2, str) and c2.strip():
                    return c2.strip()

                choices = payload.get("choices")
                if isinstance(choices, list) and choices:
                    c0 = choices[0] if isinstance(choices[0], dict) else None
                    if c0:
                        c0m = c0.get("message") if isinstance(c0.get("message"), dict) else None
                        if c0m and isinstance(c0m.get("content"), str) and c0m.get("content").strip():
                            return c0m.get("content").strip()
                        c0t = c0.get("text")
                        if isinstance(c0t, str) and c0t.strip():
                            return c0t.strip()
        except Exception:
            pass

    return reply


def _validate_safe_command(line: str) -> list[str]:
    try:
        parts = shlex.split(line.strip())
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Command parse error: {e}")

    if not parts:
        raise HTTPException(status_code=400, detail="Command is empty")

    cmd = parts[0].lower()

    if cmd in BLOCKED_COMMANDS:
        raise HTTPException(status_code=403, detail=f"Command blocked: {cmd}")

    if cmd not in SAFE_COMMANDS:
        raise HTTPException(status_code=403, detail=f"Command not allowlisted: {cmd}")

    if cmd == "claw":
        sub = parts[1].lower() if len(parts) > 1 else ""
        if sub not in SAFE_CLAW_SUBCOMMANDS:
            raise HTTPException(status_code=403, detail=f"Unsafe claw subcommand: {sub or '<empty>'}")

    return parts


def _run_core_command(line: str) -> dict[str, Any]:
    _validate_safe_command(line)

    out = io.StringIO()
    err = io.StringIO()
    t0 = time.time()

    with _SYSTEM_LOCK:
        with redirect_stdout(out), redirect_stderr(err):
            _SYSTEM.handle_command(line)

    elapsed_ms = int((time.time() - t0) * 1000)

    return {
        "ok": True,
        "command": line,
        "stdout": out.getvalue().strip(),
        "stderr": err.getvalue().strip(),
        "elapsed_ms": elapsed_ms,
    }


@app.get("/health")
def health() -> dict[str, Any]:
    return {
        "ok": True,
        "service": APP_NAME,
        "version": APP_VERSION,
        "token_present": _token_present(),
        "time": int(time.time()),
    }


@app.get("/models")
def models(provider: str | None = Query(default=None)) -> dict[str, Any]:
    rows = list_puter_models(provider=provider)
    return {
        "ok": bool(rows),
        "provider": provider,
        "count": len(rows or []),
        "models": rows or [],
    }


@app.post("/ask")
def ask(req: AskRequest) -> dict[str, Any]:
    raw_model = (req.model or "").strip()
    ollama_prefix = "ollama/"
    fallback_model = os.getenv("QTMOS_LOCAL_FALLBACK_MODEL", "llama3:latest")

    # Explicit ollama model path: model="ollama/llama3:latest"
    if raw_model.lower().startswith(ollama_prefix):
        local_model = raw_model[len(ollama_prefix) :].strip() or fallback_model
        local_reply = query_ollama(req.prompt, model=local_model)
        if not local_reply:
            raise HTTPException(status_code=503, detail="No response from local Ollama backend")
        return {
            "ok": True,
            "provider": "ollama",
            "model": local_model,
            "prompt": req.prompt,
            "reply": _normalize_model_reply(local_reply),
            "fallback_used": False,
        }

    # Default path: Puter first.
    # If we don't have Puter auth configured, don't try to bootstrap interactive login.
    # Go straight to local fallback when allowed.
    if req.allow_local_fallback and not has_puter_auth():
        local_model = fallback_model
        local_reply = query_ollama(req.prompt, model=local_model)
        if local_reply:
            return {
                "ok": True,
                "provider": "ollama",
                "model": local_model,
                "prompt": req.prompt,
                "reply": _normalize_model_reply(local_reply),
                "fallback_used": True,
            }

    reply, used_model = call_puter_with_model(req.prompt, model=req.model)
    if reply:
        return {
            "ok": True,
            "provider": "puter",
            "model": used_model or req.model,
            "prompt": req.prompt,
            "reply": _normalize_model_reply(reply),
            "fallback_used": False,
        }

    if req.allow_local_fallback:
        local_model = fallback_model
        local_reply = query_ollama(req.prompt, model=local_model)
        if local_reply:
            return {
                "ok": True,
                "provider": "ollama",
                "model": local_model,
                "prompt": req.prompt,
                "reply": _normalize_model_reply(local_reply),
                "fallback_used": True,
            }

    raise HTTPException(status_code=503, detail="No response from Puter or local Ollama backend")


@app.post("/command")
def command(req: CommandRequest) -> dict[str, Any]:
    return _run_core_command(req.cmd)


@app.get("/state")
def state() -> dict[str, Any]:
    status = _run_core_command("claw status --json")
    whoami = _run_core_command("whoami")
    health_out = _run_core_command("health")

    return {
        "ok": True,
        "status": status,
        "whoami": whoami,
        "health": health_out,
    }


if __name__ == "__main__":
    import uvicorn

    host = os.getenv("QTMOS_API_HOST", "127.0.0.1")
    port = int(os.getenv("QTMOS_API_PORT", "8010"))
    uvicorn.run("qtmos_server:app", host=host, port=port, reload=False)
