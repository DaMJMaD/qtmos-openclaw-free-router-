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




class V0Formula:
    def __init__(self, weights): self.weights = weights
    def calculate(self, text: str):
        text = (text or "").lower()
        scores = {k:0 for k in ("time","meaning","reflection","gravity")}
        for cat in scores:
            for kw, val in self.weights.get(cat, {}).items():
                scores[cat] += text.count(kw) * val
        return scores