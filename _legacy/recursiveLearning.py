# recursiveLearning.py

import threading
import os
import json
import time
import logging


class RecursiveLearning:
    def __init__(self, core_file: str, epi_file: str):
        self.core_file = core_file
        self.epi_file = epi_file
        self.core_learning_history = []
        self.episodic_learning_history = []
        self._lock = threading.Lock()
        self._is_core_dirty = False
        self._is_episodic_dirty = False
        self.load_memory()

    def _load_file(self, path, target_attr):
        if not os.path.exists(path):
            return
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict) and "learning_history" in data:
            setattr(self, target_attr, data["learning_history"])
        elif isinstance(data, list):
            setattr(self, target_attr, data)

    def load_memory(self):
        try:
            self._load_file(self.core_file, "core_learning_history")
            self._load_file(self.epi_file, "episodic_learning_history")
            print(
                f"[MEMORY]: Loaded {len(self.core_learning_history)} core "
                f"and {len(self.episodic_learning_history)} episodic memories."
            )
        except Exception as e:
            print("[SYSTEM WARNING]: Could not load memory, starting blank.", e)
            self.core_learning_history = []
            self.episodic_learning_history = []

    def _save_file(self, path, data):
        with open(path, "w", encoding="utf-8") as f:
            json.dump(
                {"learning_history": data, "last_saved": time.time()},
                f,
                indent=2,
                ensure_ascii=False,
            )

    def save_memory(self):
        with self._lock:
            try:
                if self._is_core_dirty:
                    self._save_file(self.core_file, self.core_learning_history)
                    self._is_core_dirty = False
                if self._is_episodic_dirty:
                    self._save_file(self.epi_file, self.episodic_learning_history)
                    self._is_episodic_dirty = False
            except Exception:
                print("[SYSTEM CRITICAL ERROR]: FAILED TO SAVE MEMORY.")
                logging.error("Memory save failed", exc_info=True)

    def add_episodic_memory(self, packet):
        with self._lock:
            text = (packet.get("input") or "")
            if "SYNTHESIS:" in text:
                print("[MEMORY SAFETY]: Blocking recursive synthesis learn.")
                return
            self.episodic_learning_history.append(packet)
            if len(self.episodic_learning_history) > 900:
                self.episodic_learning_history.pop(0)
            self._is_episodic_dirty = True
        self.save_memory()

    def add_core_memory(self, packet):
        with self._lock:
            self.core_learning_history.append(packet)
            self._is_core_dirty = True
        self.save_memory()

    def reload_core(self, new_core_file: str):
        with self._lock:
            self.core_file = new_core_file
            self.core_learning_history = []
            self._load_file(self.core_file, "core_learning_history")
            self._is_core_dirty = False
