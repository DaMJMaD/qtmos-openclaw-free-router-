#!/usr/bin/env python3
"""Simple client for QTMoS HTTP endpoints."""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter


def _request(base_url: str, method: str, path: str, payload: dict | None = None) -> dict:
    url = base_url.rstrip("/") + path
    data = None
    headers = {"Accept": "application/json"}

    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"

    req = urllib.request.Request(url=url, method=method, data=data, headers=headers)

    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            body = resp.read().decode("utf-8", errors="replace")
            return json.loads(body) if body else {}
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace") if hasattr(e, "read") else ""
        raise SystemExit(f"HTTP {e.code}: {body}")
    except urllib.error.URLError as e:
        raise SystemExit(f"Connection error: {e}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--base-url",
        default=os.getenv("QTMOS_API_BASE_URL", "http://127.0.0.1:8010"),
        help="QTMoS API base URL",
    )

    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("health")

    p_models = sub.add_parser("models")
    p_models.add_argument("--provider", default=None)
    p_models.add_argument("--limit", type=int, default=40, help="Limit model rows shown (default: 40)")
    p_models.add_argument("--all", action="store_true", help="Show all model rows")
    p_models.add_argument("--ids-only", action="store_true", help="Return only model IDs")
    p_models.add_argument("--providers", action="store_true", help="Return provider counts only")

    p_ask = sub.add_parser("ask")
    p_ask.add_argument("prompt")
    p_ask.add_argument("--model", default=None)

    p_command = sub.add_parser("command")
    p_command.add_argument("command")

    sub.add_parser("state")

    args = parser.parse_args()

    if args.cmd == "health":
        out = _request(args.base_url, "GET", "/health")
    elif args.cmd == "models":
        query = ""
        if args.provider:
            query = "?" + urllib.parse.urlencode({"provider": args.provider})
        out = _request(args.base_url, "GET", "/models" + query)

        rows = out.get("models") if isinstance(out.get("models"), list) else []
        total = len(rows)

        if args.providers:
            counts = Counter((str(r.get("provider") or "unknown") for r in rows if isinstance(r, dict)))
            out = {
                "ok": bool(rows),
                "count": total,
                "provider_counts": [
                    {"provider": k, "count": v}
                    for k, v in sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))
                ],
            }
        elif args.ids_only:
            ids = [str(r.get("id", "")).strip() for r in rows if isinstance(r, dict)]
            ids = [x for x in ids if x]
            if not args.all:
                ids = ids[: max(0, args.limit)]
            out = {
                "ok": bool(rows),
                "count": total,
                "shown": len(ids),
                "ids": ids,
            }
        else:
            if not args.all:
                limit = max(0, args.limit)
                out["models"] = rows[:limit]
                out["shown"] = len(out["models"])
                out["truncated"] = total > limit
    elif args.cmd == "ask":
        out = _request(
            args.base_url,
            "POST",
            "/ask",
            {"prompt": args.prompt, "model": args.model},
        )
    elif args.cmd == "command":
        out = _request(args.base_url, "POST", "/command", {"cmd": args.command})
    elif args.cmd == "state":
        out = _request(args.base_url, "GET", "/state")
    else:
        raise SystemExit(f"Unknown command: {args.cmd}")

    print(json.dumps(out, indent=2, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
