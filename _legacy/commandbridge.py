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



class CommandBridge:
    def __init__(self, system, log_dir=None):
        self.system = system

        if log_dir is None:
            log_dir = META_DIR / "api_check"

        os.makedirs(log_dir, exist_ok=True)
        self.log_dir = log_dir


    def is_valid_command(self, line: str) -> bool:
        line = line.strip()
        if not line or line.startswith("#"):
            return False
        if "force-learn" in line or "admin-inject" in line:
            return False
        if line.startswith("ingest-api") and len(line.split()) < 2:
            return False
        return True

    def route_command(self, line: str):
        if not self.is_valid_command(line):
            return None
        return line
