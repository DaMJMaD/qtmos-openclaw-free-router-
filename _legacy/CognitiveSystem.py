import os
import re
import json
import logging
import subprocess
import threading
from pathlib import Path
from queue import Queue
from llm_adapters import chat_ollama, query_ollama, OLLAMA_MODELS

# =========================
# OPTIONAL LLM ADAPTERS
# =========================

try:
    from llm_adapters import (
        chat_ollama,
        query_ollama,
        emit_mcp_chat,
        OLLAMA_MODELS,
        GeminiAdapter,
    )
except Exception as e:
    print(f"[LLM]: Adapters partially unavailable ({e})")
    chat_ollama = None
    query_ollama = None
    emit_mcp_chat = None
    GeminiAdapter = None
    OLLAMA_MODELS = {"default": "llama3.1:latest"}

# =========================
# PATHS
# =========================

BASE_DIR = Path(__file__).resolve().parent
META_DIR = BASE_DIR / "MetaDB"
PERSONA_DIR = META_DIR / "Personality Cortext'x"
CORE_PATH = META_DIR / "pack_core.json"
DEFAULT_EPI_PATH = PERSONA_DIR / "pack_empty.json"

# =========================
# SIMPLE MEMORY SYSTEM
# =========================

class LearningSystem:
    def __init__(self, core_file, epi_file):
        self.core_file = core_file
        self.epi_file = epi_file
        self.core_learning_history = []
        self.episodic_learning_history = []
        self._lock = threading.Lock()
        self.load_memory()

    def load_memory(self):
        if os.path.exists(self.core_file):
            self.core_learning_history = json.load(open(self.core_file))
        if os.path.exists(self.epi_file):
            self.episodic_learning_history = json.load(open(self.epi_file))

    def save_memory(self):
        os.makedirs(os.path.dirname(self.core_file), exist_ok=True)
        json.dump(self.core_learning_history, open(self.core_file, "w"), indent=2)
        json.dump(self.episodic_learning_history, open(self.epi_file, "w"), indent=2)

    def add_episodic(self, text):
        with self._lock:
            self.episodic_learning_history.append({"input": text})
            self.save_memory()

# =========================
# MAIN COGNITIVE SYSTEM
# =========================

class CognitiveSystem:
    def __init__(self):
        print("[MAIN]: Booting Cognitive System...")

        self.learning = LearningSystem(
            core_file=str(CORE_PATH),
            epi_file=str(DEFAULT_EPI_PATH),
        )

        self.preferred_llm = "auto"

        # Gemini (optional)
        if GeminiAdapter:
            try:
                self.gemini = GeminiAdapter()
            except Exception as e:
                print(f"[GEMINI]: Disabled ({e})")
                self.gemini = None
        else:
            self.gemini = None

        print("[MAIN]: System online.")

    # =========================
    # LLM ROUTING
    # =========================

    def route_llm(self, prompt):
        prompt = prompt.strip()
        if not prompt:
            return None

        # MCP
        if emit_mcp_chat:
            try:
                r = emit_mcp_chat(prompt)
                if r:
                    return r
            except Exception:
                pass

        # Gemini
        if self.gemini:
            try:
                r = self.gemini.ask(prompt)
                if r:
                    return r
            except Exception:
                pass

        # Ollama
        if query_ollama:
            try:
                return query_ollama(prompt)
            except Exception:
                pass

        return None

    # =========================
    # COMMANDS
    # =========================

    def command_chat(self, text):
        r = self.route_llm(text)
        if r:
            print("[CHAT]:", r)
        else:
            print("[CHAT]: No response from any engine.")

    def command_ollama(self, text):
        if not chat_ollama:
            print("[OLLAMA]: Adapter unavailable.")
            return
        model = OLLAMA_MODELS.get("default", "llama3.1:latest")
        reply = chat_ollama([{"role": "user", "content": text}], model=model)
        print(f"[OLLAMA:{model}]: {reply}")

    def command_gemini(self, text):
        if not self.gemini:
            print("[GEMINI]: Disabled.")
            return
        r = self.gemini.ask(text)
        print("[GEMINI]:", r if r else "No response.")

    def command_learn(self, text):
        self.learning.add_episodic(text)
        print(f"[LEARN]: Stored → \"{text}\"")

    def command_define(self, term):
        print("\n=== DEFINE RESULTS ===")
        found = False
        for i, m in enumerate(self.learning.episodic_learning_history, 1):
            if term.lower() in m["input"].lower():
                print(f"Epi {i}: {m['input']}")
                found = True
        if not found:
            print("[DEFINE]: No matches.")
        print("=====================")

    def command_recall(self):
        print("\n=== EPISODIC MEMORIES ===")
        for i, m in enumerate(self.learning.episodic_learning_history, 1):
            print(f"{i}: {m['input']}")
        print("========================")

    def command_state(self):
        print("\n=== STATE ===")
        print("Core memories   :", len(self.learning.core_learning_history))
        print("Episodic memory :", len(self.learning.episodic_learning_history))
        print("Status          : operational")
        print("================")

    # =========================
    # SINGLE COMMAND HANDLER
    # =========================

    def handle_command(self, line):
        try:
            if not line:
                return

            parts = line.split()
            cmd = parts[0].lower()
            rest = line[len(parts[0]):].strip()

            if cmd in ("chat", "ask"):
                self.command_chat(rest)

            elif cmd == "ollama":
                self.command_ollama(rest)

            elif cmd == "gemini":
                self.command_gemini(rest)

            elif cmd == "learn":
                self.command_learn(rest)

            elif cmd == "define":
                self.command_define(rest)

            elif cmd == "recall":
                self.command_recall()

            elif cmd == "state":
                self.command_state()

            elif cmd in ("exit", "quit"):
                raise SystemExit

            else:
                print(f"[UNKNOWN COMMAND]: '{line}'")

        except SystemExit:
            print("[MAIN]: Shutdown requested.")
            raise
        except Exception:
            print("[MAIN ERROR]: Unhandled exception.")
            logging.error("handle_command error", exc_info=True)

# =========================
# CLI LOOP
# =========================

def run_cli():
    system = CognitiveSystem()
    while True:
        try:
            line = input("> ").strip()
            system.handle_command(line)
        except (EOFError, KeyboardInterrupt):
            print("\n[MAIN]: Exiting.")
            break

if __name__ == "__main__":
    run_cli()
