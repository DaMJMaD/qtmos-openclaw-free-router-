#!/usr/bin/env python3
"""Route prompts across QTMoS-backed models ("subclaws")."""

from __future__ import annotations

import argparse
import json
import os
import re
import time
import urllib.error
import urllib.request


DEFAULT_FAST = "gpt-4.1-mini"
DEFAULT_REASONING = "claude-opus-4-6"
DEFAULT_CODING = "codestral-2508"
DEFAULT_DOCS = "gemini-2.5-pro"
DEFAULT_LOCAL = "ollama/llama3:latest"


def _post_json(base_url: str, path: str, payload: dict, timeout: int = 90) -> dict:
    url = base_url.rstrip("/") + path
    req = urllib.request.Request(
        url=url,
        method="POST",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", "Accept": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8", errors="replace"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace") if hasattr(e, "read") else ""
        return {"ok": False, "error": f"HTTP {e.code}", "detail": body}
    except Exception as e:
        return {"ok": False, "error": "request_failed", "detail": str(e)}


def _infer_task_class(task: str) -> str:
    t = task.lower()

    if re.search(r"\b(code|python|javascript|bug|stacktrace|function|refactor|compile|script|regex|api)\b", t):
        return "coding"
    if re.search(r"\b(image|pdf|scan|diagram|screenshot|document|doc)\b", t):
        return "docs"
    if re.search(r"\b(reason|analy[sz]e|proof|math|logic|plan|strategy|difficult|deep)\b", t):
        return "reasoning"
    return "fast"


def _auto_candidates(task: str) -> list[str]:
    cls = _infer_task_class(task)
    if cls == "coding":
        return [DEFAULT_CODING, DEFAULT_REASONING, DEFAULT_FAST, DEFAULT_LOCAL]
    if cls == "docs":
        return [DEFAULT_DOCS, DEFAULT_REASONING, DEFAULT_FAST, DEFAULT_LOCAL]
    if cls == "reasoning":
        return [DEFAULT_REASONING, DEFAULT_FAST, DEFAULT_LOCAL]
    return [DEFAULT_FAST, DEFAULT_REASONING, DEFAULT_LOCAL]


def _run_single(base_url: str, task: str, model: str | None) -> dict:
    payload = {
        "prompt": task,
        "model": model,
        "allow_local_fallback": True,
    }
    t0 = time.time()
    out = _post_json(base_url, "/ask", payload)
    out.setdefault("ok", False)
    out["elapsed_ms"] = int((time.time() - t0) * 1000)
    return out


def _run_with_fallbacks(base_url: str, task: str, models: list[str]) -> dict:
    attempts = []
    for m in models:
        out = _run_single(base_url, task, m)
        attempts.append({
            "model": m,
            "ok": bool(out.get("ok")),
            "provider": out.get("provider"),
            "elapsed_ms": out.get("elapsed_ms"),
            "error": out.get("error") or out.get("detail"),
        })
        if out.get("ok"):
            return {
                "ok": True,
                "model_used": out.get("model") or m,
                "provider": out.get("provider"),
                "reply": out.get("reply", ""),
                "fallback_used": m != models[0],
                "attempts": attempts,
            }

    return {
        "ok": False,
        "error": "all_candidates_failed",
        "attempts": attempts,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="QTMoS model router")
    parser.add_argument("task", help="Prompt or task text")
    parser.add_argument("--base-url", default=os.getenv("QTMOS_API_BASE_URL", "http://127.0.0.1:8010"))
    parser.add_argument("--mode", choices=["auto", "single", "compare"], default="auto")
    parser.add_argument("--model", default=None, help="Explicit model for single mode")
    parser.add_argument("--candidates", default=None, help="Comma-separated model list")
    parser.add_argument("--max-fanout", type=int, default=3, help="Max models in compare mode")
    args = parser.parse_args()

    if args.mode == "single":
        result = _run_single(args.base_url, args.task, args.model)
        print(json.dumps(result, indent=2, ensure_ascii=True))
        return 0 if result.get("ok") else 2

    if args.candidates:
        candidates = [x.strip() for x in args.candidates.split(",") if x.strip()]
    elif args.model:
        candidates = [args.model]
    else:
        candidates = _auto_candidates(args.task)

    if args.mode == "auto":
        result = _run_with_fallbacks(args.base_url, args.task, candidates)
        print(json.dumps(result, indent=2, ensure_ascii=True))
        return 0 if result.get("ok") else 2

    # compare mode
    fanout = max(1, min(args.max_fanout, len(candidates)))
    compare = []
    for model in candidates[:fanout]:
        out = _run_single(args.base_url, args.task, model)
        compare.append(
            {
                "ok": bool(out.get("ok")),
                "model": out.get("model") or model,
                "provider": out.get("provider"),
                "elapsed_ms": out.get("elapsed_ms"),
                "reply": out.get("reply", ""),
                "error": out.get("error") or out.get("detail"),
            }
        )

    best = next((x for x in compare if x.get("ok")), None)
    result = {
        "ok": bool(best),
        "mode": "compare",
        "winner": best,
        "results": compare,
    }
    print(json.dumps(result, indent=2, ensure_ascii=True))
    return 0 if result["ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
