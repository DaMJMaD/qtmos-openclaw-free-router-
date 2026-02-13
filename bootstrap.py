from pathlib import Path
import os
import time

from pathlib import Path
import os

BASE_DIR = Path(__file__).resolve().parent
os.chdir(BASE_DIR)

# --- Core directory layout ---
META_DIR = BASE_DIR / "MetaDB"
PERSONA_DIR = META_DIR / "Personality Cortext'x"
PROFILE_DIR = META_DIR / "Profiles"

# Ensure directories exist
META_DIR.mkdir(exist_ok=True)
PERSONA_DIR.mkdir(parents=True, exist_ok=True)
PROFILE_DIR.mkdir(parents=True, exist_ok=True)
import sys
from pathlib import Path

import sys
sys.path.append("/home/aa/qtmos.com")


import os
import re
import json
import time
import threading
import logging
import traceback
import sys
import urllib.request
import urllib.error
import html
import urllib.parse
import subprocess


from collections import Counter
from datetime import datetime
from queue import Queue
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor


import requests
import os

from cognition_math import V0Formula
from emotionalbinary import EmotionalBinary
from persona_db import PersonalityDB


import os

from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
META_DIR = BASE_DIR / "MetaDB"
PERSONA_DIR = META_DIR / "Personality Cortext'x"
PROFILE_DIR = META_DIR / "Profiles"
from llm_adapters import GeminiAdapter
from recursiveLearning import RecursiveLearning
# --- Core memory paths ---
CORE_PATH = META_DIR / "pack_core.json"

# --- Episodic memory paths ---
DEFAULT_EPI_PATH = PERSONA_DIR / "pack_empty.json"
BASE_EMPTY_PACK = DEFAULT_EPI_PATH
from synthesis import Synthesizer
from tonesequencer import ToneSequencer






def find_qtm_boot_script() -> Path | None:
    candidates: list[Path] = []

    # 1) Explicit environment override
    env_path = os.getenv("QTM_BOOT_PATH")
    if env_path:
        candidates.append(Path(env_path))

    # 2) Repo-relative layout
    BASE_DIR = Path(__file__).resolve().parent

    # 3) Native Windows workspace path
    candidates.append(Path(r"C:\Projects\Daves Desktop Buddies\QTMoS\qtmos_boot.py"))

    # 4) WSL-native install (THIS WAS MISSING)
    candidates.append(
        Path.home() / "qtmos.com" / "QTMoS" / "qtmos_boot.py"
    )

    # 5) UNC (Windows-only, lowest priority)
    candidates.append(
        Path(r"\\wsl.localhost\Ubuntu\home\aa\qtmos.com\QTMoS\qtmos_boot.py")
    )

    for path in candidates:
        try:
            if path.is_file():
                return path.resolve()
        except OSError:
            continue

    return None
    
    # --- Safety block: disable external review, network eval, or auto-introspection ---
SAFE_MODE = False

if SAFE_MODE:
    import builtins, urllib, sys

    # Block web/network requests (this is fine)
    def _blocked_request(*a, **k):
        raise RuntimeError("[SECURITY]: External network access blocked.")

    urllib.request.urlopen = _blocked_request
    urllib.request.Request = _blocked_request

    # DO NOT globally kill eval/exec; they are used by Python internals.
    # If you need controlled exec, use safe_exec() below instead.

    _orig_open = builtins.open

    def _safe_open(path, *a, **k):
        p = str(path)
        if p.startswith("http") or "://" in p:
            raise RuntimeError(f"[SECURITY]: Attempted network file access ({p})")
        return _orig_open(path, *a, **k)

    builtins.open = _safe_open

    print("[SECURITY]: External introspection and network calls blocked.")

# Allow internal alchemy exec safely
SAFE_EXEC_ALLOWED = ["AlchemicalEquations.py"]

def safe_exec(source, context=None):
    import inspect
    frame = inspect.stack()[1]
    caller = frame.filename
    if any(allowed in caller for allowed in SAFE_EXEC_ALLOWED):
        exec(source, context or {})
    else:
        raise RuntimeError("[SECURITY]: exec() blocked outside of safe modules.")


# --- Ensure working dir = script dir ---
BASE_DIR = Path(__file__).resolve().parent
os.chdir(BASE_DIR)

# --- Optional Dwrapper stub/import ---
try:
    sys.path.append(str(BASE_DIR / "Modular" / "Cognition"))
    from NaviinaDwrapper import Dwrapper
except Exception:
    class Dwrapper:
        def __init__(self, *a, **k): pass
        def log(self, *a, **k): pass
        def speak(self, *a, **k): pass

# --- Color utility ---
class C:
    RESET = "\033[0m"
    @staticmethod
    def rgb(r,g,b): return f"\033[38;2;{r};{g};{b}m"
    @staticmethod
    def hex(h):
        try:
            h = h.strip("#")
            return f"\033[38;2;{int(h[0:2],16)};{int(h[2:4],16)};{int(h[4:6],16)}m"
        except Exception:
            return C.RESET

ROLE = {
    "SYSTEM": C.hex("#80DEEA"),
    "MEMORY": C.hex("#FFD54F"),
    "VOICE":  C.hex("#E91E63"),
    "DEBUG":  C.hex("#90CAF9"),
    "ERROR":  C.hex("#F44336"),
    "PACK":   C.hex("#8BC34A"),
    "DWRAP":  C.hex("#FF9800"),
}

def color_print(role, message):
    color = ROLE.get(role.upper(), "")
    print(f"{color}[{role.upper()}]: {message}{C.RESET}")






# --- Persona / Pack Layout ---
META_DIR = BASE_DIR / "MetaDB"
PERSONA_DIR = META_DIR / "Personality Cortext'x"   # episodic & persona packs live here
PROFILE_DIR = META_DIR / "Profiles"               # per-entity profiles (Willow, Caleb, Mem, etc.)

META_DIR.mkdir(exist_ok=True)
PERSONA_DIR.mkdir(parents=True, exist_ok=True)
PROFILE_DIR.mkdir(parents=True, exist_ok=True)

CORE_DIR = Path(os.getenv("QTMOS_CORE_DIR", META_DIR))
CORE_FILE = os.getenv("QTMOS_CORE_FILE", "pack_core.json")
CORE_PATH = CORE_DIR / CORE_FILE

BASE_EMPTY_PACK = PERSONA_DIR / "pack_empty.json"

# Ensure base empty episodic pack exists
if not BASE_EMPTY_PACK.exists():
    BASE_EMPTY_PACK.write_text(
        json.dumps(
            {
                "learning_history": [],
                "last_saved": time.time(),
                "_meta": {
                    "kind": "episodic",
                    "name": "base_empty",
                    "tags": ["empty", "reset"],
                },
            },
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

DEFAULT_EPI_PATH = BASE_EMPTY_PACK




