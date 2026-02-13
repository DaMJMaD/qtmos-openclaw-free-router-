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



class MetaReflectionLogger:
    def __init__(self, base_dir=str(META_DIR)):
        self.log_dir = Path(base_dir) / "stage_raw"
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.path = self.log_dir / "meta_reflections.jsonl"
        self.gpu_log_path = self.log_dir / "gpu_performance.jsonl"  # New path for GPU logs
        self.quantum_log_path = self.log_dir / "quantum_simulation.jsonl"  # New path for Quantum logs

    def save_reflection(self, emotion, synthesis, keywords=None, source="pulse"):
        entry = {
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "emotion": emotion,
            "keywords": keywords or [],
            "synthesis": synthesis,
            "source": source,
            "stage": "raw",
        }
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    def log_gpu_performance(self, gpu_data):
        """Log GPU performance data"""
        entry = {
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "gpu_data": gpu_data
        }
        with self.gpu_log_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    def log_quantum_simulation(self, quantum_data):
        """Log quantum simulation results"""
        entry = {
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "quantum_data": quantum_data
        }
        with self.quantum_log_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    def recent(self, n=3):
        if not self.path.exists():
            return []
        with self.path.open("r", encoding="utf-8") as f:
            lines = f.readlines()[-n:]
        return [json.loads(x) for x in lines]

    def print_recent(self, n=3):
        records = self.recent(n)
        print(f"=== Last {len(records)} Reflections ===")
        for e in records:
            print(f"[{e['timestamp']}] ({e['emotion']}) {e['synthesis'][:120]}...")


    def make_synthesis_packet(emotion, synthesis, keywords=None, source="pulse"):
        return {
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "emotion": emotion,
            "synthesis": synthesis,
            "keywords": keywords or [],
            "source": source,
            "stage": "raw",
        }