#!/usr/bin/env python3
"""
claw_live_bridge.py

Non-invasive bridge between QTMoS core (main.py --once) and a live Claw-style operator loop.

Goals:
- Keep your existing core untouched.
- Provide a lightweight TUI-ish live loop.
- Add an "inferstructured" monitoring mode for steady real-time state snapshots.
- Write a local JSONL event stream for tooling/lacing.

Run:
  python3 claw_live_bridge.py

Optional env:
  BRIDGE_TICK_SECONDS=1.5
  BRIDGE_LOG_PATH=<path>
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import threading
import time
from datetime import datetime
from pathlib import Path
from queue import Queue, Empty

CORE_DIR = Path(__file__).resolve().parent
CORE_MAIN = CORE_DIR / "main.py"
PROJECT_ROOT = CORE_DIR.parent
DEFAULT_LOG = PROJECT_ROOT / "runtime" / "bridge" / "clawbus.jsonl"

TICK = float(os.getenv("BRIDGE_TICK_SECONDS", "1.5"))
LOG_PATH = Path(os.getenv("BRIDGE_LOG_PATH", str(DEFAULT_LOG)))


def now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def emit(event: dict):
    event = {"ts": now_iso(), **event}
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with LOG_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(event, ensure_ascii=False) + "\n")


def run_once(command: str) -> tuple[int, str, str]:
    proc = subprocess.run(
        [sys.executable, str(CORE_MAIN), "--once", command],
        cwd=str(CORE_DIR),
        text=True,
        capture_output=True,
    )
    return proc.returncode, proc.stdout.strip(), proc.stderr.strip()


def try_json(text: str):
    try:
        return json.loads(text)
    except Exception:
        return None


class Bridge:
    def __init__(self):
        self.running = True
        self.inferstructured = False
        self.input_q: Queue[str] = Queue()
        self.last_status = {}

    def start(self):
        emit({"kind": "bridge.start", "core": str(CORE_MAIN)})
        print("[BRIDGE] claw_live_bridge online")
        print("[BRIDGE] commands: /infer on|off, /status, /map, /help, /quit")
        print("[BRIDGE] pass-through: any QTMoS core command (e.g., state, claw status --json)")

        t_in = threading.Thread(target=self._input_loop, daemon=True)
        t_in.start()

        while self.running:
            self._tick()
            self._drain_input()
            time.sleep(TICK)

        emit({"kind": "bridge.stop"})
        print("[BRIDGE] shutdown")

    def _input_loop(self):
        while self.running:
            try:
                line = input("bridge> ").strip()
            except (EOFError, KeyboardInterrupt):
                self.input_q.put("/quit")
                break
            self.input_q.put(line)

    def _drain_input(self):
        while True:
            try:
                line = self.input_q.get_nowait()
            except Empty:
                return

            if not line:
                continue

            if line in ("/quit", "quit", "exit"):
                self.running = False
                return

            if line in ("/help", "help", "?"):
                print("[BRIDGE HELP] /infer on|off, /status, /map, /quit")
                print("[BRIDGE HELP] pass core commands like: state, claw status --json, pack-list epi")
                continue

            if line.lower() == "live":
                self.inferstructured = True
                emit({"kind": "infer.mode", "enabled": True, "alias": "live"})
                print("[INFERSTRUCTURED] ON (alias: live)")
                continue

            if line.startswith("/infer"):
                parts = line.split()
                if len(parts) >= 2 and parts[1].lower() in ("on", "off"):
                    self.inferstructured = parts[1].lower() == "on"
                    emit({"kind": "infer.mode", "enabled": self.inferstructured})
                    print(f"[INFERSTRUCTURED] {'ON' if self.inferstructured else 'OFF'}")
                else:
                    print("usage: /infer on|off")
                continue

            if line == "/status":
                self._status_snapshot(print_out=True)
                continue

            if line == "/map":
                rc, out, err = run_once("claw map --json")
                emit({"kind": "map", "rc": rc, "stdout": out, "stderr": err})
                print(out if out else f"[ERR] rc={rc} {err}")
                continue

            # prevent shell confusion inside bridge prompt
            if line.lower().startswith("python "):
                print("[BRIDGE]: this prompt is not a shell. Run core commands directly (e.g., state, claw status --json).")
                print("[BRIDGE]: or exit with /quit and run shell commands in PowerShell.")
                continue

            # pass-through command to QTMoS core
            rc, out, err = run_once(line)
            emit({"kind": "cmd", "cmd": line, "rc": rc, "stdout": out, "stderr": err})
            if out:
                print(out)
            elif err:
                print(f"[ERR] rc={rc} {err}")
            else:
                print(f"[OK] rc={rc}")

    def _status_snapshot(self, print_out=False):
        rc, out, err = run_once("claw status --json")
        data = try_json(out) if out else None
        if data:
            self.last_status = data
            emit({"kind": "status", "data": data})
            if print_out:
                mem = data.get("memory", {})
                print(
                    "[STATUS] "
                    f"core={mem.get('core_count','?')} epi={mem.get('epi_count','?')} "
                    f"llm={data.get('preferred_llm','?')}"
                )
        else:
            emit({"kind": "status.error", "rc": rc, "stdout": out, "stderr": err})
            if print_out:
                print(f"[STATUS ERROR] rc={rc} {err or out}")

    def _tick(self):
        if not self.inferstructured:
            return

        self._status_snapshot(print_out=True)

        rc, out, err = run_once("claw memory epi 2 --json")
        data = try_json(out) if out else None
        if data and isinstance(data, dict):
            tail = (((data.get("tail") or {}).get("items")) or [])
            preview = (tail[-1][:120] + "…") if tail and len(tail[-1]) > 120 else (tail[-1] if tail else "")
            emit({"kind": "infer.epi", "tail": tail})
            if preview:
                print(f"[INFER] epi_tail: {preview}")
        else:
            emit({"kind": "infer.error", "rc": rc, "stdout": out, "stderr": err})


if __name__ == "__main__":
    Bridge().start()
