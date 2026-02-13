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

BASE_DIR = Path(__file__).resolve().parents[1]  # systems modulation/
META_DIR = Path(os.getenv("QTMOS_META_DIR", str(BASE_DIR.parent / "MetaDB"))).expanduser()
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





class Pulse(threading.Thread):
    def __init__(self, system, interval=300):
        super().__init__(daemon=True)
        self.system = system
        self.interval = max(5, int(interval))
        self._stop = threading.Event()
        self._paused = threading.Event()

    def run(self):
        while not self._stop.is_set():
            if self._paused.is_set():
                time.sleep(0.2)
                continue
            time.sleep(self.interval)
            if self._stop.is_set():
                break
            self.run_once()

    def run_once(self):
        ts = datetime.now().strftime("%H:%M:%S")
        print(f"\n[PACK PULSE {ts}]: Autonomous reflection...")

        # --- World state snapshots (GPU + Quantum) ---
        snapshot = gpu_log_snapshot()
        if snapshot:
            idx, total, used, free = snapshot
            # log to console only, do NOT store as episodic memory
            msg = (f"[GPU LOG]: device {idx} using {used}/{total} MiB "
                   f"(free {free} MiB)")
            print(msg)


        try:
            # Quantum status (will just print if stubbed)
            self.system.quantum_log_snapshot()
            # optionally also store
            # self.system.command_learn("[QUANTUM LOG] ...")
        except Exception:
            pass

        # --- Emotional / memory synthesis ---
        s = self.system.synthesizer.synthesize()
        if s:
            print(f"[PACK SYNTHESIZES]: {s}")
            if self.system.reflection_logger:
                pkt = make_synthesis_packet("auto", s, [], "pulse")
                self.system.reflection_logger.save_reflection(
                    pkt["emotion"], pkt["synthesis"], pkt["keywords"], pkt["source"]
                )
        print("="*40)



    def pause(self): self._paused.set()
    def resume(self): self._paused.clear()
    def stop(self):
        self._stop.set()
        self._paused.clear()