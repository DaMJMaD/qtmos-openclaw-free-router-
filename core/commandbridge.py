from __future__ import annotations

import os
from pathlib import Path

# Canonical paths: keep aligned with modular core configuration.
BASE_DIR = Path(__file__).resolve().parents[1]  # systems modulation/
META_DIR = Path(os.getenv("QTMOS_META_DIR", str(BASE_DIR.parent / "MetaDB"))).expanduser()
PERSONA_DIR = META_DIR / "Personality Cortext'x"
PROFILE_DIR = META_DIR / "Profiles"
CORE_PATH = META_DIR / "pack_core.json"
DEFAULT_EPI_PATH = PERSONA_DIR / "pack_empty.json"


class CommandBridge:
    """Small command filter/router used by legacy helper paths.

    Intentionally lightweight: no hardcoded host paths, no stale flat-module imports.
    """

    def __init__(self, system, log_dir=None):
        self.system = system
        if log_dir is None:
            log_dir = META_DIR / "api_check"
        os.makedirs(log_dir, exist_ok=True)
        self.log_dir = Path(log_dir)

    def is_valid_command(self, line: str) -> bool:
        line = (line or "").strip()
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
