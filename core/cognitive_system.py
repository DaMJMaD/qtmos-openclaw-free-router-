import os
import json
import logging
import threading
import subprocess
import sys
import time
import shlex
import hashlib
import urllib.parse
import webbrowser
from pathlib import Path

from llm.llm_adapters import (
    chat_ollama,
    query_ollama,
    OLLAMA_MODELS,
    ask_router,
    GeminiAdapter,
    call_mcp_chat,
    call_mcp_gemini,
    call_puter_with_model,
    has_puter_auth,
    list_puter_models,
)

# Optional local-only helpers (avoid hard failures if modules move)
try:
    from cognition.synthesis import Synthesizer
except Exception:  # pragma: no cover
    Synthesizer = None  # type: ignore

try:
    from runtime.pulse import Pulse
except Exception:  # pragma: no cover
    Pulse = None  # type: ignore


# =========================
# PATHS
# =========================

PROJECT_ROOT = Path(__file__).resolve().parents[1]
LEGACY_V3_PATH = (PROJECT_ROOT.parent / "CognitiveSystems_V3.py").resolve()
LLM_ENV_PATH = PROJECT_ROOT / "llm" / ".env"

# MetaDB resolution order:
# 1) explicit override (QTMOS_META_DIR)
# 2) canonical Tenchin MetaDB (requested): ../MetaDB
# 3) migrated local copies under systems modulation
ENV_META_DIR = os.getenv("QTMOS_META_DIR")
CANONICAL_META_DIR = PROJECT_ROOT.parent / "MetaDB"
DEFAULT_META_DIR = PROJECT_ROOT / "memory" / "MetaDB"
FALLBACK_META_DIR = PROJECT_ROOT / "core" / "MetaDB"

if ENV_META_DIR:
    META_DIR = Path(ENV_META_DIR).expanduser()
elif CANONICAL_META_DIR.exists():
    META_DIR = CANONICAL_META_DIR
elif DEFAULT_META_DIR.exists():
    META_DIR = DEFAULT_META_DIR
else:
    META_DIR = FALLBACK_META_DIR

PERSONA_DIR = META_DIR / "Personality Cortext'x"
CORE_PATH = META_DIR / "pack_core.json"
DEFAULT_EPI_PATH = PERSONA_DIR / "pack_empty.json"


# =========================
# SIMPLE MEMORY SYSTEM
# =========================

class LearningSystem:
    """Minimal memory wrapper.

    Supports two on-disk formats seen in this repo:
    - list[dict] (legacy)
    - {"learning_history": list[dict], "last_saved": ...} (current)
    """

    def __init__(self, core_file: str, epi_file: str):
        self.core_file = core_file
        self.epi_file = epi_file
        self.core_learning_history: list[dict] = []
        self.episodic_learning_history: list[dict] = []
        self._lock = threading.Lock()
        self.load_memory()

    def _load_history(self, path: str) -> list[dict]:
        if not os.path.exists(path):
            return []
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list):
            return data
        if isinstance(data, dict) and isinstance(data.get("learning_history"), list):
            return data["learning_history"]
        return []

    def _save_history(self, path: str, history: list[dict]):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        payload = {
            "learning_history": history,
            "last_saved": __import__("time").time(),
        }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)

    def load_memory(self):
        self.core_learning_history = self._load_history(self.core_file)
        self.episodic_learning_history = self._load_history(self.epi_file)

    def save_memory(self):
        self._save_history(self.core_file, self.core_learning_history)
        self._save_history(self.epi_file, self.episodic_learning_history)

    def set_core_file(self, path: str):
        self.core_file = path
        self.load_memory()

    def set_epi_file(self, path: str):
        self.epi_file = path
        self.load_memory()

    def add_episodic(self, text: str):
        with self._lock:
            self.episodic_learning_history.append({"input": text})
            self.save_memory()

    def promote_to_core(self, text: str):
        with self._lock:
            self.core_learning_history.append({"input": text})
            self.save_memory()


# =========================
# MAIN COGNITIVE SYSTEM
# =========================

class CognitiveSystem:
    def __init__(self):
        self.learning = LearningSystem(
            core_file=str(CORE_PATH),
            epi_file=str(DEFAULT_EPI_PATH),
        )

        self.preferred_llm = "auto"

        # Gemini (optional; external) — keep initialization optional.
        self.gemini = None
        if GeminiAdapter:
            try:
                self.gemini = GeminiAdapter()
            except Exception as e:
                print(f"[GEMINI]: Disabled ({e})")
                self.gemini = None

        # Synthesis/pulse (local)
        self.synthesizer = None
        if Synthesizer:
            try:
                self.synthesizer = Synthesizer(self.learning, formula=None, encoder=None)
            except Exception as e:
                print(f"[SYNTHESIZER]: Disabled ({e})")

        # Optional logger expected by runtime.pulse.Pulse
        self.reflection_logger = None

        self._pulse = None

    # =========================
    # COMMANDS (implemented)
    # =========================

    def command_chat(self, text: str):
        """OpenAI chat via local MCP server (explicit user intent)."""
        if not text:
            print("[CHAT]: missing text")
            return
        resp = call_mcp_chat(text)
        if resp:
            print(f"[CHAT:OPENAI]: {resp}")
        else:
            print("[CHAT]: no response (is MCP running at $MCP_BASE_URL and OPENAI_API_KEY set?)")

    def command_ollama(self, text: str):
        if not chat_ollama:
            print("[OLLAMA]: Adapter unavailable.")
            return
        model = OLLAMA_MODELS.get("default", "llama3.3:70b")
        reply = chat_ollama([{"role": "user", "content": text}], model=model)
        print(f"[OLLAMA:{model}]: {reply}")

    def command_gemini(self, text: str):
        """Gemini via local MCP server (explicit user intent)."""
        if not text:
            print("[GEMINI]: missing text")
            return

        # Preferred path: local MCP proxy
        resp = call_mcp_gemini(text)
        if resp:
            print(f"[GEMINI]: {resp}")
            return

        # Fallback to direct adapter if available
        if self.gemini:
            r = self.gemini.ask(text)
            if r:
                print(f"[GEMINI]: {r}")
                return

        # Actionable diagnostics (instead of generic "No response")
        mcp_ok = False
        mcp_gemini = None
        try:
            req = Request("http://127.0.0.1:8000/health", headers={"accept": "application/json"})
            with urlopen(req, timeout=2) as h:
                data = json.loads(h.read().decode("utf-8") or "{}")
                if isinstance(data, dict):
                    mcp_ok = bool(data.get("status") == "ok")
                    mcp_gemini = data.get("gemini")
        except Exception:
            pass

        has_key = bool(os.getenv("GEMINI_API_KEY"))

        if not mcp_ok:
            print("[GEMINI]: unavailable (MCP server is down on 127.0.0.1:8000).")
            print("[GEMINI]: start MCP or relaunch core with autostart enabled.")
            return

        if mcp_gemini is False or not has_key:
            print("[GEMINI]: unavailable (GEMINI_API_KEY missing or google-genai not installed).")
            print("[GEMINI]: set GEMINI_API_KEY and install dependency: pip install google-genai")
            return

        print("[GEMINI]: no response (provider reachable but returned empty output).")

    def _parse_puter_chat_args(self, rest: str):
        try:
            tokens = shlex.split(rest or "")
        except ValueError as e:
            print(f"[PUTER]: parse error: {e}")
            return None, None

        model = None
        prompt_tokens = []
        i = 0
        while i < len(tokens):
            tok = tokens[i]
            if tok in ("--model", "-m"):
                if i + 1 >= len(tokens):
                    print("[PUTER]: missing value after --model")
                    return None, None
                model = tokens[i + 1]
                i += 2
                continue
            prompt_tokens.append(tok)
            i += 1

        return " ".join(prompt_tokens).strip(), model

    def command_puter_chat(self, rest: str):
        prompt, model = self._parse_puter_chat_args(rest)
        if prompt is None:
            return
        if not prompt:
            print("[PUTER]: usage: puter-chat <text> [--model <id>]")
            return

        reply, used_model = call_puter_with_model(prompt, model=model)
        if reply:
            label = used_model or model or os.getenv("PUTER_DEFAULT_MODEL", "claude-opus-4-6")
            print(f"[PUTER:{label}]: {reply}")
            return

        if not has_puter_auth():
            print("[PUTER]: no auth set (use PUTER_API_KEY or puterAuthToken)")
            print("[PUTER]: for keyless Puter.js in Node, install: npm i @heyputer/puter.js")
        else:
            print("[PUTER]: no response (check model id / Puter endpoint availability)")

    def command_puter_models(self, rest: str):
        provider = (rest or "").strip() or None
        rows = list_puter_models(provider=provider)
        if not rows:
            print("[PUTER]: model list unavailable right now")
            print("Try: puter-models claude")
            if not has_puter_auth():
                print("[PUTER]: no auth set (use PUTER_API_KEY or puterAuthToken)")
            return

        print("=== PUTER MODELS ===")
        shown = 0
        for item in rows:
            if not isinstance(item, dict):
                continue
            mid = str(item.get("id", "")).strip()
            if not mid:
                continue
            prov = str(item.get("provider", "")).strip() or "unknown"
            aliases = item.get("aliases") if isinstance(item.get("aliases"), list) else []
            alias_text = f" aliases={','.join(str(a) for a in aliases[:3])}" if aliases else ""
            print(f"- {mid} (provider={prov}){alias_text}")
            shown += 1
            if shown >= 40:
                break

        if shown == 0:
            print("[PUTER]: no models matched your filter")
        print("====================")

    def _extract_puter_token(self, text: str) -> str | None:
        raw = (text or "").strip()
        if not raw:
            return None

        # Accept direct KEY=VALUE pastes.
        if "=" in raw and "http" not in raw:
            k, v = raw.split("=", 1)
            if k.strip() in ("PUTER_AUTH_TOKEN", "puterAuthToken", "token", "authToken"):
                t = "".join(v.strip().split())
                return t or None
            # Not a known key=value token format; fall through.

        # Direct token paste (no URL).
        if "http" not in raw and "puterAuthToken=" not in raw and "PUTER_AUTH_TOKEN=" not in raw and "token=" not in raw:
            t = "".join(raw.split())
            return t or None

        parsed = urllib.parse.urlparse(raw)

        # Query params: ?puterAuthToken=... or ?token=...
        q = urllib.parse.parse_qs(parsed.query or "")
        for key in ("puterAuthToken", "token", "authToken"):
            if key in q and q[key]:
                t = urllib.parse.unquote(str(q[key][0]))
                t = "".join(t.split())
                return t or None

        # Hash params: #...&puterAuthToken=... or #...&token=...
        frag = urllib.parse.parse_qs((parsed.fragment or "").lstrip("#"))
        for key in ("puterAuthToken", "token", "authToken"):
            if key in frag and frag[key]:
                t = urllib.parse.unquote(str(frag[key][0]))
                t = "".join(t.split())
                return t or None

        return None

    def _upsert_env_var(self, env_path: Path, key: str, value: str):
        env_path.parent.mkdir(parents=True, exist_ok=True)
        lines = []
        if env_path.exists():
            try:
                lines = env_path.read_text(encoding="utf-8").splitlines()
            except Exception:
                lines = []

        out = []
        replaced = False
        for line in lines:
            s = line.strip()
            if s.startswith(f"{key}="):
                out.append(f"{key}={value}")
                replaced = True
            else:
                out.append(line)

        if not replaced:
            out.append(f"{key}={value}")

        env_path.write_text("\n".join(out).rstrip() + "\n", encoding="utf-8")

    def _token_sha256(self, token: str) -> str:
        return hashlib.sha256((token or "").encode("utf-8")).hexdigest()

    def _get_puter_token_via_node_sdk(self) -> str | None:
        """Try Puter.js browser auth flow in Node and return token.

        Uses llm/puter_node_bridge.cjs first (better SDK resolution + JSON output),
        then falls back to direct SDK require.
        """
        if os.getenv("PUTER_LOGIN_DISABLE_SDK", "0") == "1":
            return None

        # Keep SDK wait short so login doesn't feel stuck; manual paste fallback is immediate after timeout.
        timeout_s = int(os.getenv("PUTER_LOGIN_TIMEOUT", "12"))
        if timeout_s < 8:
            timeout_s = 8
        if timeout_s > 30:
            timeout_s = 30

        # Preferred: bridge helper
        bridge = PROJECT_ROOT / "llm" / "puter_node_bridge.cjs"
        if bridge.exists():
            try:
                proc = subprocess.run(
                    ["node", str(bridge), "auth-token"],
                    cwd=str(PROJECT_ROOT),
                    capture_output=True,
                    text=True,
                    timeout=timeout_s,
                )
                out = (proc.stdout or "").strip()
                if out:
                    # Parse last JSON-like line first.
                    candidates = [ln.strip() for ln in out.splitlines() if ln.strip()]
                    for c in reversed(candidates):
                        if c.startswith("{") and c.endswith("}"):
                            try:
                                payload = json.loads(c)
                            except Exception:
                                payload = None
                            if isinstance(payload, dict) and payload.get("ok") and payload.get("token"):
                                return "".join(str(payload.get("token") or "").split())
                            if isinstance(payload, dict) and payload.get("error"):
                                d = payload.get("detail")
                                msg = f"[PUTER LOGIN]: SDK auth error: {payload.get('error')}"
                                if d:
                                    msg += f" ({d})"
                                print(msg)
                                break
            except subprocess.TimeoutExpired:
                print("[PUTER LOGIN]: SDK auth timed out waiting for browser completion.")
            except FileNotFoundError:
                print("[PUTER LOGIN]: Node.js not found; skipping SDK auth")
                return None
            except Exception as e:
                print(f"[PUTER LOGIN]: SDK auth failed to launch: {e}")

        # Fallback: direct SDK require
        js = (
            "const { getAuthToken } = require('@heyputer/puter.js/src/init.cjs');"
            "getAuthToken().then(t=>{process.stdout.write(String(t||''));})"
            ".catch(e=>{console.error(e && e.message ? e.message : String(e)); process.exit(1);});"
        )
        try:
            proc = subprocess.run(
                ["node", "-e", js],
                cwd=str(PROJECT_ROOT),
                capture_output=True,
                text=True,
                timeout=timeout_s,
            )
        except FileNotFoundError:
            print("[PUTER LOGIN]: Node.js not found; skipping SDK auth")
            return None
        except subprocess.TimeoutExpired:
            print("[PUTER LOGIN]: SDK auth timed out waiting for browser completion.")
            return None
        except Exception as e:
            print(f"[PUTER LOGIN]: SDK auth failed to launch: {e}")
            return None

        out = (proc.stdout or "").strip()
        if proc.returncode == 0 and out:
            return "".join(out.split())

        err = (proc.stderr or "").strip()
        if err:
            print(f"[PUTER LOGIN]: SDK auth error: {err}")
            if "Cannot find module '@heyputer/puter.js" in err or "Cannot find module" in err:
                print("[PUTER LOGIN]: install once in project dir: npm i @heyputer/puter.js")
        return None

    def command_puter_login(self, rest: str = ""):
        """
        puter-login [<callback-url-or-token>]

        - Tries official Puter.js Node auth flow first (getAuthToken)
        - Falls back to opening Puter auth page in browser
        - Accepts pasted localhost callback URL containing puterAuthToken or token
        - Saves PUTER_AUTH_TOKEN to llm/.env
        """
        raw = (rest or "").strip()
        manual_mode = False
        for flag in ("--manual", "--no-sdk"):
            if raw == flag:
                manual_mode = True
                raw = ""
                break
            prefix = flag + " "
            if raw.startswith(prefix):
                manual_mode = True
                raw = raw[len(prefix):].strip()
                break

        # Reuse existing static credentials to avoid browser auth.
        if not raw:
            existing_token = "".join(str(os.getenv("PUTER_AUTH_TOKEN") or os.getenv("puterAuthToken") or "").split())
            if not existing_token and LLM_ENV_PATH.exists():
                try:
                    for line in LLM_ENV_PATH.read_text(encoding="utf-8").splitlines():
                        s = line.strip()
                        if not s or s.startswith("#") or "=" not in s:
                            continue
                        k, v = s.split("=", 1)
                        if k.strip() in ("PUTER_AUTH_TOKEN", "puterAuthToken"):
                            existing_token = "".join(v.strip().strip("'\"").split())
                            if existing_token:
                                os.environ["PUTER_AUTH_TOKEN"] = existing_token
                                os.environ["puterAuthToken"] = existing_token
                                break
                except Exception:
                    pass
            if existing_token:
                token = existing_token
            elif os.getenv("PUTER_API_KEY"):
                print("[PUTER LOGIN]: PUTER_API_KEY is already set; interactive login is not required.")
                print("[PUTER LOGIN]: try: puter-chat \"hey\" --model claude-opus-4-6")
                return
            else:
                token = None
        else:
            token = self._extract_puter_token(raw)

        if not token and not manual_mode:
            print("[PUTER LOGIN]: trying official Puter SDK auth flow...")
            token = self._get_puter_token_via_node_sdk()
        elif manual_mode and not token:
            print("[PUTER LOGIN]: manual mode enabled; skipping SDK auth flow.")

        if not token:
            login_url = os.getenv("PUTER_LOGIN_URL", "https://puter.com")
            print(f"[PUTER LOGIN]: opening {login_url}")
            print(f"[PUTER LOGIN]: if it does not open automatically, visit: {login_url}")
            try:
                opened = webbrowser.open(login_url)
                if not opened:
                    print("[PUTER LOGIN]: browser open returned false; open URL manually if needed")
            except Exception as e:
                print(f"[PUTER LOGIN]: could not open browser automatically: {e}")
                print(f"[PUTER LOGIN]: open manually: {login_url}")

            print("[PUTER LOGIN]: after auth, paste either:")
            print("- full localhost callback URL containing puterAuthToken=... or token=...")
            print("- or raw token value")
            print("[PUTER LOGIN]: waiting for token input...")
            pasted = input("PUTER token/url> ").strip()
            token = self._extract_puter_token(pasted)

        if not token:
            print("[PUTER LOGIN]: could not parse token")
            return

        token_hash = self._token_sha256(token)
        existing_hash = (os.getenv("PUTER_TOKEN_SHA256") or "").strip()
        if existing_hash and existing_hash == token_hash:
            print(f"[PUTER LOGIN]: token fingerprint unchanged ({token_hash[:12]}...), reusing session")

        os.environ["PUTER_AUTH_TOKEN"] = token
        os.environ["puterAuthToken"] = token
        os.environ["PUTER_TOKEN_SHA256"] = token_hash

        try:
            self._upsert_env_var(LLM_ENV_PATH, "PUTER_AUTH_TOKEN", token)
            self._upsert_env_var(LLM_ENV_PATH, "PUTER_TOKEN_SHA256", token_hash)
            # Keep default model pinned unless user changed it explicitly elsewhere.
            if "PUTER_DEFAULT_MODEL" not in os.environ:
                self._upsert_env_var(LLM_ENV_PATH, "PUTER_DEFAULT_MODEL", "claude-opus-4-6")
            print(f"[PUTER LOGIN]: token saved -> {LLM_ENV_PATH}")
            print(f"[PUTER LOGIN]: token sha256={token_hash}")
        except Exception as e:
            print(f"[PUTER LOGIN]: token set for current session, but failed to save env file: {e}")

        # Immediate handshake after token capture.
        model = os.getenv("PUTER_DEFAULT_MODEL", "claude-opus-4-6")
        print(f"[PUTER LOGIN]: handshaking with model={model} ...")
        try:
            reply, used_model = call_puter_with_model("handshake check", model=model)
        except Exception as e:
            reply, used_model = None, None
            print(f"[PUTER LOGIN]: handshake error: {e}")

        if reply:
            label = used_model or model
            snippet = str(reply).strip().replace("\n", " ")[:180]
            print(f"[PUTER LOGIN]: handshake OK via {label}")
            print(f"[PUTER LOGIN]: reply={snippet}")
        else:
            print("[PUTER LOGIN]: token saved, but handshake failed.")
            print("[PUTER LOGIN]: retry with: puter-chat \"ping\" --model claude-opus-4-6")

    def command_learn(self, text: str):
        self.learning.add_episodic(text)
        print(f"[LEARN]: Stored → \"{text}\"")

    def command_define(self, term: str):
        print("\n=== DEFINE RESULTS ===")
        found = False
        for i, m in enumerate(self.learning.episodic_learning_history, 1):
            if term.lower() in (m.get("input", "").lower()):
                print(f"Epi {i}: {m.get('input','')}")
                found = True
        if not found:
            print("[DEFINE]: No matches.")
        print("=====================")

    def command_recall(self):
        print("\n=== CORE MEMORIES ===")
        for i, m in enumerate(self.learning.core_learning_history, 1):
            print(f"{i}: {m.get('input','')}")
        print("=====================")

        print("\n=== EPISODIC MEMORIES ===")
        for i, m in enumerate(self.learning.episodic_learning_history, 1):
            print(f"{i}: {m.get('input','')}")
        print("========================")

    def command_state(self):
        print("\n=== STATE ===")
        print("Core memories   :", len(self.learning.core_learning_history))
        print("Episodic memory :", len(self.learning.episodic_learning_history))
        print("Core pack file  :", self.learning.core_file)
        print("Epi pack file   :", self.learning.epi_file)
        print("Status          : operational")
        print("================")

    def command_synthesize(self):
        if not self.synthesizer:
            print("[SYNTHESIZE]: Synthesizer unavailable.")
            return
        s = self.synthesizer.synthesize()
        print("[SYNTHESIS]:", s if s else "(no synthesis)")

    def command_pulse_now(self):
        if not Pulse:
            print("[PULSE]: Pulse service unavailable.")
            return
        p = Pulse(self, interval=999999)
        p.run_once()

    def command_pulse_start(self, seconds: str | None = None):
        if not Pulse:
            print("[PULSE]: Pulse service unavailable.")
            return
        if self._pulse and getattr(self._pulse, "is_alive", lambda: False)():
            print("[PULSE]: already running")
            return
        interval = 300
        if seconds:
            try:
                interval = int(seconds)
            except ValueError:
                pass
        self._pulse = Pulse(self, interval=interval)
        self._pulse.start()
        print(f"[PULSE]: started interval={interval}s")

    def command_pulse_stop(self):
        if self._pulse:
            try:
                self._pulse.stop()
            except Exception:
                pass
            self._pulse = None
            print("[PULSE]: stopped")
        else:
            print("[PULSE]: not running")

    def command_health(self):
        # Minimal local health summary.
        self.command_state()
        print("\n=== HEALTH ===")
        print("Synthesizer     :", "ok" if self.synthesizer else "disabled")
        print("Ollama adapter   :", "ok" if query_ollama else "disabled")
        print("===============")

    def command_wander(self):
        # Safe curiosity == pulse-now for now.
        self.command_pulse_now()

    def command_ingest_ollama(self, text: str):
        """Summarize text via local Ollama (if available) and store to episodic memory."""
        if not text:
            print("[INGEST-OLLAMA]: missing text")
            return
        if not query_ollama:
            print("[INGEST-OLLAMA]: adapter unavailable")
            return
        model = OLLAMA_MODELS.get("default")
        prompt = "Summarize briefly for memory storage:\n\n" + text
        summary = query_ollama(prompt, model=model)
        if not summary:
            print("[INGEST-OLLAMA]: no response")
            return
        self.learning.add_episodic(summary)
        print("[INGEST-OLLAMA]: stored summary")

    def command_promote(self, text: str):
        if not text:
            print("[PROMOTE]: missing text")
            return
        self.learning.promote_to_core(text)
        print("[PROMOTE]: added to core")

    def command_whoami(self):
        print("\n=== WHOAMI ===")
        print("Core pack:", self.learning.core_file)
        print("Epi pack :", self.learning.epi_file)
        print("=============")

    def command_pack_list(self, kind: str | None = None):
        kind = (kind or "epi").strip().lower()
        if kind not in ("epi", "core", "profiles"):
            kind = "epi"

        if kind == "epi":
            base = PERSONA_DIR
            globs = ["pack_*.json", "pack*_episodic.json"]
        elif kind == "core":
            base = META_DIR
            globs = ["pack_*.json", "pack*_core.json"]
        else:
            base = META_DIR / "Profiles"
            globs = ["pack_*.json", "pack*_core.json"]

        if not base.exists():
            print(f"[PACK-LIST]: directory missing: {base}")
            return
        found = set()
        for g in globs:
            for p in base.glob(g):
                found.add(p.name)
        packs = sorted(found)
        print(f"[PACK-LIST:{kind}]: {len(packs)}")
        for p in packs:
            print(" -", p)

    def command_load_pack(self, name: str):
        if not name:
            print("[LOAD-PACK]: missing name")
            return
        # Accept either absolute file path or short name.
        cand_in = Path(name)
        candidates = []
        if cand_in.is_absolute():
            candidates.append(cand_in)
        elif cand_in.suffix:
            candidates.append((PERSONA_DIR / cand_in).resolve())
        else:
            n = name.strip()
            candidates += [
                (PERSONA_DIR / f"pack{n}_episodic.json").resolve(),
                (PERSONA_DIR / f"pack_{n}.json").resolve(),
                (PERSONA_DIR / f"pack{n}.json").resolve(),
            ]

        chosen = next((p for p in candidates if p.exists()), None)
        if not chosen:
            print(f"[LOAD-PACK]: not found for '{name}' in {PERSONA_DIR}")
            return
        self.learning.set_epi_file(str(chosen))
        print(f"[LOAD-PACK]: ok → {chosen.name}")

    def command_load_core(self, name: str):
        if not name:
            print("[LOAD-CORE]: missing name")
            return
        cand_in = Path(name)
        candidates = []
        if cand_in.is_absolute():
            candidates.append(cand_in)
        elif cand_in.suffix:
            candidates.append((META_DIR / cand_in).resolve())
        else:
            n = name.strip()
            candidates += [
                (META_DIR / f"pack{n}_core.json").resolve(),
                (META_DIR / f"pack_{n}.json").resolve(),
                (META_DIR / f"pack{n}.json").resolve(),
            ]

        chosen = next((p for p in candidates if p.exists()), None)
        if not chosen:
            print(f"[LOAD-CORE]: not found for '{name}' in {META_DIR}")
            return
        self.learning.set_core_file(str(chosen))
        print(f"[LOAD-CORE]: ok → {chosen.name}")

    def command_create_profile(self, name: str):
        """Create matching core + episodic packs for a new profile name."""
        raw = (name or "").strip()
        if not raw:
            print("[CREATE-PROFILE]: missing name")
            print("Usage: create-profile <name>")
            return

        safe = "".join(ch if ch.isalnum() else "_" for ch in raw).strip("_")
        if not safe:
            print("[CREATE-PROFILE]: invalid name")
            return

        PERSONA_DIR.mkdir(parents=True, exist_ok=True)
        META_DIR.mkdir(parents=True, exist_ok=True)

        core_main = META_DIR / f"pack{safe}_core.json"
        epi_main = PERSONA_DIR / f"pack{safe}_episodic.json"
        # compatibility aliases used by some commands/older scripts
        core_alias = META_DIR / f"pack_{safe}.json"
        epi_alias = PERSONA_DIR / f"pack_{safe}.json"

        ts = time.time()
        core_payload = {
            "learning_history": [
                {
                    "input": f"i am {safe} core",
                    "emotional_state": {"name": safe, "binary": "1111"},
                }
            ],
            "last_saved": ts,
        }
        epi_payload = {
            "learning_history": [],
            "last_saved": ts,
        }

        created = []
        for path, payload in (
            (core_main, core_payload),
            (epi_main, epi_payload),
            (core_alias, core_payload),
            (epi_alias, epi_payload),
        ):
            if path.exists():
                continue
            path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
            created.append(path.name)

        print(f"[CREATE-PROFILE]: name={safe}")
        if created:
            print("[CREATE-PROFILE]: created")
            for f in created:
                print(" -", f)
        else:
            print("[CREATE-PROFILE]: already exists (no new files written)")

        print(f"[TIP]: load-core {safe}")
        print(f"[TIP]: load-pack {safe}")

    def command_run_script(self, file_path: str):
        if not file_path:
            print("[RUN-SCRIPT]: missing file")
            return
        p = Path(file_path)
        if not p.is_absolute():
            p = (PROJECT_ROOT / p).resolve()
        if not p.exists():
            print(f"[RUN-SCRIPT]: not found: {p}")
            return
        print(f"[RUN-SCRIPT]: {p}")
        with p.open("r", encoding="utf-8") as f:
            for raw in f:
                line = raw.strip()
                if not line or line.startswith("#"):
                    continue
                print(f"> {line}")
                self.handle_command(line)

    def command_scan(self):
        # Minimal local scan: try compiling core modules.
        import compileall

        ok = compileall.compile_dir(str(PROJECT_ROOT / "core"), quiet=1)
        ok = compileall.compile_dir(str(PROJECT_ROOT / "llm"), quiet=1) and ok
        print("[SCAN]:", "ok" if ok else "issues")

    # =========================
    # LOCAL SHELL HELPERS / LOCAL-ONLY COMMANDS
    # =========================

    def _run_shell(self, cmd, label: str = "cmd"):
        """Run a local shell command and print output.

        cmd can be a list[str] (no shell) or a string (shell=True).
        """
        try:
            if isinstance(cmd, (list, tuple)):
                r = subprocess.run(cmd, text=True, capture_output=True)
            else:
                r = subprocess.run(cmd, shell=True, text=True, capture_output=True)
            out = (r.stdout or "").strip()
            err = (r.stderr or "").strip()
            if out:
                print(out)
            if err:
                print(f"[{label} stderr]:\n{err}")
            if r.returncode != 0:
                print(f"[{label}]: exit={r.returncode}")
        except FileNotFoundError:
            print(f"[{label}]: command not found")
        except Exception as e:
            print(f"[{label} ERROR]: {e}")

    def _find_qtmos_boot(self) -> Path | None:
        """Find QTMoS boot script (qtmos_boot.py) locally."""
        env_path = os.getenv("QTM_BOOT_PATH")
        if env_path:
            p = Path(env_path)
            if p.is_file():
                return p.resolve()

        # Walk up a few parents and look for QTMoS/qtmos_boot.py
        cur = PROJECT_ROOT
        for _ in range(8):
            p = cur / "QTMoS" / "qtmos_boot.py"
            try:
                if p.is_file():
                    return p.resolve()
            except OSError:
                pass
            if cur.parent == cur:
                break
            cur = cur.parent

        return None

    def command_qtm_shell(self, rest: str):
        """qtm / qtm-shell [custom_command]

        Default: launch QTMoS via qtmos_boot.py with the current Python.
        If extra text is provided, run it as a local shell command.
        """
        custom = (rest or "").strip()
        if custom:
            print(f"[QTM]: running custom command: {custom}")
            self._run_shell(custom, label="qtm")
            return

        script = self._find_qtmos_boot()
        if not script:
            print("[QTM ERROR]: Could not find qtmos_boot.py")
            print("  Expected at: <project>/QTMoS/qtmos_boot.py")
            print("  Or set QTM_BOOT_PATH to the full path.")
            return

        # QTMoS currently depends on numpy; check early so failures are clear.
        chk = subprocess.run([sys.executable, "-c", "import numpy"], capture_output=True)
        if chk.returncode != 0:
            print("[QTM ERROR]: Missing dependency: numpy")
            if os.getenv("VIRTUAL_ENV"):
                print("  Fix (venv):  python -m pip install numpy")
            else:
                print("  Fix (user):  python3 -m pip install --user numpy")
            return

        # Bridge SoftAdmin env into QTMoS OS launch (read-only; no behavior changes unless the env file exists).
        env = os.environ.copy()
        env_file = os.getenv("QTM_OS_ENV_FILE") or str(Path.home() / ".config" / "qtmos" / "qtmos_os.env")
        if env_file and os.path.exists(env_file):
            try:
                with open(env_file, "r", encoding="utf-8") as f:
                    for raw in f:
                        line = raw.strip()
                        if not line or line.startswith("#"):
                            continue
                        if "=" not in line:
                            continue
                        k, v = line.split("=", 1)
                        k = k.strip()
                        v = v.strip().strip('"').strip("'")
                        if k and k not in env:
                            env[k] = v
            except Exception:
                pass

        print(f"[QTM]: launching {script} using {sys.executable}")
        try:
            subprocess.run([sys.executable, str(script)], env=env)
        except Exception as e:
            print(f"[QTM ERROR]: Failed to launch QTMoS: {e}")

    def command_live(self):
        """Launch bridge TUI for live operator mode."""
        bridge = PROJECT_ROOT / "core" / "claw_live_bridge.py"
        if not bridge.exists():
            print(f"[LIVE ERROR]: bridge not found: {bridge}")
            print("Run manually: python claw_live_bridge.py")
            return

        print("[LIVE]: launching claw_live_bridge.py")
        try:
            subprocess.run([sys.executable, str(bridge)], cwd=str(PROJECT_ROOT / "core"))
        except Exception as e:
            print(f"[LIVE ERROR]: {e}")

    def command_wslmenu(self, args: str = ""):
        """WSL/Linux quick menu (ported minimally from CognitiveSystems_V3).

        wslmenu               - show menu
        wslmenu gpu           - nvidia-smi
        wslmenu envs          - list venv activate scripts under ~
        wslmenu dirs          - print quick dirs
        wslmenu peek <path>   - ls <path>
        wslmenu servers       - ps aux filtered
        """
        arg_str = (args or "").strip()
        parts = arg_str.split() if arg_str else []
        sub = parts[0].lower() if parts else ""

        if not sub:
            print("=== WSL/LINUX MENU ===")
            print("wslmenu gpu        - GPU peek (nvidia-smi)")
            print("wslmenu envs       - Show Python envs (~/*/bin/activate)")
            print("wslmenu dirs       - Quick peek directories")
            print("wslmenu peek <p>   - ls <p>")
            print("wslmenu servers    - ps aux filtered for common servers")
            print("======================")
            return

        if sub == "gpu":
            self._run_shell(["nvidia-smi"], label="gpu")
            return

        if sub == "envs":
            cmd = 'find ~ -type f -name "activate" -path "*/bin/activate" | awk -F"/" \'{print $(NF-2)}\''
            self._run_shell(cmd, label="envs")
            return

        if sub == "dirs":
            print("=== QUICK DIRS ===")
            dirs = [
                str(Path("~").expanduser()),
                str((Path("~") / "my-quantum-env").expanduser()),
                str((Path("~") / "qiskit-aer").expanduser()),
                str((Path("~") / "qubit-venv").expanduser()),
                str((Path("~") / "quantum310").expanduser()),
                "/mnt/c/Projects",
                "/mnt/c/Projects/Daves Desktop Buddies/Head/Tenchin",
                str(PROJECT_ROOT),
            ]
            for d in dirs:
                print(f"- {d}")
            return

        if sub == "peek":
            if len(parts) < 2:
                print("[wslmenu] Usage: wslmenu peek <path>")
                return
            path = " ".join(parts[1:])
            self._run_shell(["ls", path], label="peek")
            return

        if sub == "servers":
            cmd = r'ps aux | egrep "ollama|python|jupyter|code|node|gunicorn" | grep -v egrep'
            self._run_shell(cmd, label="servers")
            return

        print(f"[wslmenu] Unknown subcommand: {sub}")
        print("Try: wslmenu, wslmenu gpu, wslmenu envs, wslmenu dirs, wslmenu peek <path>, wslmenu servers")

    def command_local_only_block(self, name: str):
        print(f"[{name.upper()}]: disabled (local-only mode)")

    def command_not_migrated(self, name: str, hint: str | None = None):
        msg = f"[{name.upper()}]: not migrated in modular core yet"
        if hint:
            msg += f" ({hint})"
        print(msg)

    def command_compat_legacy(self, name: str, rest: str = ""):
        """Compatibility shim for V3 command names.

        We do not re-enable networked behavior by default.
        """
        cmd = (name or "").strip().lower()
        arg = (rest or "").strip()

        if cmd in ("qtm-status",):
            # Safe modern equivalent
            self.command_claw("status")
            return

        if cmd in ("qtm-mode", "rails", "qhace", "forget", "duel", "ingest-url", "ingest-api", "crawl", "genesis-review"):
            print(f"[{cmd.upper()}]: delegating to V3...")
            ok, out, err, rc = self._run_legacy_passthrough(f"{cmd} {arg}".strip(), timeout=90)
            if out.strip():
                print(out.rstrip())
            if err.strip():
                print(f"[{cmd.upper()} stderr]:")
                print(err.rstrip())
            if not ok:
                print(f"[{cmd.upper()}]: V3 execution failed (exit={rc})")
            return

        if cmd == "puter-chat":
            self.command_puter_chat(arg)
            return

        if cmd == "puter-models":
            self.command_puter_models(arg)
            return

        self.command_not_migrated(cmd)

    # =========================
    # LEGACY BRIDGE
    # =========================

    def _run_legacy_passthrough(self, legacy_command: str, timeout: int = 60):
        """Run a single command through CognitiveSystems_V3.py, then quit."""
        if not LEGACY_V3_PATH.exists():
            return False, "", f"Legacy V3 script not found: {LEGACY_V3_PATH}", 127

        legacy_py = os.getenv("QTM_LEGACY_PY") or os.getenv("LEGACY_V3_PY") or sys.executable

        env = os.environ.copy()
        env_file = os.getenv("QTM_LEGACY_ENV_FILE")
        if not env_file:
            cand = (PROJECT_ROOT / "llm" / ".env")
            if cand.exists():
                env_file = str(cand)

        if env_file and os.path.exists(env_file):
            try:
                with open(env_file, "r", encoding="utf-8") as f:
                    for raw in f:
                        line = raw.strip()
                        if not line or line.startswith("#") or "=" not in line:
                            continue
                        k, v = line.split("=", 1)
                        k = k.strip()
                        v = v.strip().strip('"').strip("'")
                        if k and k not in env:
                            env[k] = v
            except Exception:
                pass

        input_text = f"{legacy_command}\nquit\n"
        try:
            r = subprocess.run(
                [legacy_py, str(LEGACY_V3_PATH)],
                input=input_text,
                text=True,
                capture_output=True,
                timeout=timeout,
                cwd=str(LEGACY_V3_PATH.parent),
                env=env,
            )
            return r.returncode == 0, (r.stdout or ""), (r.stderr or ""), r.returncode
        except subprocess.TimeoutExpired:
            return False, "", "timeout running legacy command", 124
        except Exception as e:
            return False, "", str(e), 1

    def command_legacy(self, rest: str = ""):
        """legacy: read-only bridge to CognitiveSystems_V3.py via subprocess.

        No imports, no in-process coupling. This preserves legacy as-is.

        Usage:
          legacy status [--json]
        """
        arg_str = (rest or "").strip()
        parts = arg_str.split() if arg_str else []
        as_json = "--json" in parts
        if as_json:
            parts = [p for p in parts if p != "--json"]

        sub = parts[0].lower() if parts else "help"

        if sub in ("help", "-h", "--help"):
            if as_json:
                print(json.dumps({"kind": "legacy.help", "usage": ["legacy status [--json]"]}, indent=2))
                return
            print("=== LEGACY ===")
            print("legacy status [--json]  - run CognitiveSystems_V3.py and return its status output")
            print("=============")
            return

        if sub != "status":
            if as_json:
                print(json.dumps({"kind": "legacy.error", "error": {"message": f"unknown subcommand: {sub}"}}, indent=2))
                return
            print(f"[LEGACY]: unknown subcommand: {sub} (try: legacy help)")
            return

        if not LEGACY_V3_PATH.exists():
            msg = f"Legacy V3 script not found: {LEGACY_V3_PATH}"
            if as_json:
                print(json.dumps({"kind": "legacy.status", "ok": False, "error": {"message": msg}}, indent=2))
                return
            print("[LEGACY]:", msg)
            return

        # Attempt to run legacy CLI and ask it for state.
        # We do NOT assume legacy supports one-shot flags.
        # Prefer an explicit legacy venv python if provided.
        legacy_py = os.getenv("QTM_LEGACY_PY") or os.getenv("LEGACY_V3_PY")

        def _py_supports_google_genai(py_path: str) -> bool:
            try:
                r0 = subprocess.run(
                    [py_path, "-c", "from google import genai"],
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
                return r0.returncode == 0
            except Exception:
                return False

        if not legacy_py:
            # Best-effort auto-pick: prefer known venvs that can import google-genai.
            candidates = [
                str(Path.home() / "qtmos-venv" / "bin" / "python"),
                str(Path.home() / ".venvs" / "qtmos-v3" / "bin" / "python"),
            ]
            for c in candidates:
                if os.path.exists(c) and _py_supports_google_genai(c):
                    legacy_py = c
                    break

        cmd = [legacy_py or sys.executable, str(LEGACY_V3_PATH)]
        input_text = "state\nquit\n"

        # Environment bridging: load keys the same way QTMoS core does (dotenv), but without importing.
        # Default env file: <project_root>/llm/.env (if present). Override via QTM_LEGACY_ENV_FILE.
        env = os.environ.copy()
        env_file = os.getenv("QTM_LEGACY_ENV_FILE")
        if not env_file:
            cand = (PROJECT_ROOT / "llm" / ".env")
            if cand.exists():
                env_file = str(cand)

        if env_file and os.path.exists(env_file):
            try:
                with open(env_file, "r", encoding="utf-8") as f:
                    for raw in f:
                        line = raw.strip()
                        if not line or line.startswith("#"):
                            continue
                        if "=" not in line:
                            continue
                        k, v = line.split("=", 1)
                        k = k.strip()
                        v = v.strip().strip('"').strip("'")
                        # Only set if not already present in the current environment
                        if k and k not in env:
                            env[k] = v
            except Exception:
                pass

        try:
            r = subprocess.run(
                cmd,
                input=input_text,
                text=True,
                capture_output=True,
                timeout=20,
                cwd=str(LEGACY_V3_PATH.parent),
                env=env,
            )
        except subprocess.TimeoutExpired:
            if as_json:
                print(json.dumps({"kind": "legacy.status", "ok": False, "error": {"message": "timeout running legacy"}}, indent=2))
                return
            print("[LEGACY]: timeout running legacy")
            return
        except Exception as e:
            if as_json:
                print(json.dumps({"kind": "legacy.status", "ok": False, "error": {"message": str(e)}}, indent=2))
                return
            print(f"[LEGACY]: failed to run: {e}")
            return

        out = (r.stdout or "")
        err = (r.stderr or "")
        ok = r.returncode == 0

        if as_json:
            print(
                json.dumps(
                    {
                        "kind": "legacy.status",
                        "ok": ok,
                        "returncode": r.returncode,
                        "cmd": cmd,
                        "stdout": out,
                        "stderr": err,
                    },
                    indent=2,
                    ensure_ascii=False,
                )
            )
            return

        # Human output: show stdout primarily; stderr if present.
        if out.strip():
            print(out.rstrip())
        if err.strip():
            print("[LEGACY stderr]:")
            print(err.rstrip())
        if not ok:
            print(f"[LEGACY]: exit={r.returncode}")

    # =========================
    # INTROSPECTION / OPERATOR (claw)
    # =========================

    def command_claw(self, rest: str = ""):
        """claw: safe, local-only introspection.

        This command is intentionally read-only and should not change system behavior.

        Usage:
          claw help
          claw status [--json]
          claw map [--json]
          claw memory [core|epi] [n] [--json]
        """
        arg_str = (rest or "").strip()
        parts = arg_str.split() if arg_str else []

        # Flags (keep parsing minimal and non-invasive)
        as_json = "--json" in parts
        if as_json:
            parts = [p for p in parts if p != "--json"]

        sub = parts[0].lower() if parts else "help"

        def _dump_json(obj):
            # Machine-readable, single payload.
            print(json.dumps(obj, indent=2, ensure_ascii=False, default=str))

        if sub in ("help", "-h", "--help"):
            if as_json:
                _dump_json(
                    {
                        "command": "claw",
                        "usage": [
                            "claw status [--json]",
                            "claw map [--json]",
                            "claw memory [core|epi] [n] [--json]",
                        ],
                    }
                )
                return
            print("=== CLAW ===")
            print("claw status [--json]                - summary of subsystem state (read-only)")
            print("claw map [--json]                   - show important paths + components")
            print("claw memory [core|epi] [n] [--json] - summarize memory packs (optionally show last n)")
            print("==========")
            return

        if sub == "status":
            payload = {
                "kind": "claw.status",
                "project_root": str(PROJECT_ROOT),
                "meta_dir": str(META_DIR),
                "persona_dir": str(PERSONA_DIR),
                "preferred_llm": getattr(self, "preferred_llm", "(unset)"),
                "adapters": {
                    "synthesizer": bool(self.synthesizer),
                    "ollama": bool(query_ollama),
                    "gemini": bool(self.gemini),
                },
                "memory": {
                    "core_file": str(self.learning.core_file),
                    "epi_file": str(self.learning.epi_file),
                    "core_count": len(self.learning.core_learning_history),
                    "epi_count": len(self.learning.episodic_learning_history),
                },
            }
            if as_json:
                _dump_json(payload)
                return
            print("\n=== CLAW STATUS ===")
            print("Project root    :", PROJECT_ROOT)
            print("Meta dir        :", META_DIR)
            print("Persona dir     :", PERSONA_DIR)
            print("Preferred LLM   :", getattr(self, "preferred_llm", "(unset)"))
            print("Synthesizer     :", "ok" if self.synthesizer else "disabled")
            print("Ollama adapter  :", "ok" if query_ollama else "disabled")
            print("Gemini adapter  :", "ok" if self.gemini else "disabled")
            print("Core memories   :", len(self.learning.core_learning_history))
            print("Episodic memory :", len(self.learning.episodic_learning_history))
            print("===============" )
            return

        if sub == "map":
            payload = {
                "kind": "claw.map",
                "paths": {
                    "project_root": str(PROJECT_ROOT),
                    "meta_dir": str(META_DIR),
                    "core_path": str(CORE_PATH),
                    "default_epi_path": str(DEFAULT_EPI_PATH),
                    "active_core": str(self.learning.core_file),
                    "active_epi": str(self.learning.epi_file),
                },
                "components": {
                    "learning_system": True,
                    "synthesizer": bool(self.synthesizer),
                    "pulse": bool(Pulse),
                    "mcp": bool(call_mcp_chat or call_mcp_gemini),
                },
            }
            if as_json:
                _dump_json(payload)
                return
            print("\n=== CLAW MAP ===")
            print("PROJECT_ROOT:", PROJECT_ROOT)
            print("META_DIR     :", META_DIR)
            print("CORE_PATH    :", CORE_PATH)
            print("DEFAULT_EPI  :", DEFAULT_EPI_PATH)
            print("Active core  :", self.learning.core_file)
            print("Active epi   :", self.learning.epi_file)
            print("Components   :")
            print(" - LearningSystem")
            print(" - Synthesizer:", "enabled" if self.synthesizer else "disabled")
            print(" - Pulse     :", "available" if Pulse else "unavailable")
            print(" - MCP(OpenAI/Gemini):", "available" if (call_mcp_chat or call_mcp_gemini) else "unavailable")
            print("=============")
            return

        if sub == "memory":
            # memory [core|epi] [n]
            which = (parts[1].lower() if len(parts) >= 2 else "summary")
            n = None
            if len(parts) >= 3:
                try:
                    n = int(parts[2])
                except ValueError:
                    n = None

            def _tail(hist: list[dict], k: int):
                k = max(0, min(k, len(hist)))
                return hist[-k:] if k else []

            payload = {
                "kind": "claw.memory",
                "core_file": str(self.learning.core_file),
                "epi_file": str(self.learning.epi_file),
                "core_count": len(self.learning.core_learning_history),
                "epi_count": len(self.learning.episodic_learning_history),
            }

            if which in ("core", "epi") and n:
                hist = self.learning.core_learning_history if which == "core" else self.learning.episodic_learning_history
                payload["tail"] = {
                    "which": which,
                    "n": min(n, len(hist)),
                    "items": [m.get("input", "") for m in _tail(hist, n)],
                }
            elif which not in ("summary", "core", "epi"):
                payload["error"] = {"message": f"unknown memory target: {which}", "expected": ["summary", "core", "epi"]}

            if as_json:
                _dump_json(payload)
                return

            print("\n=== CLAW MEMORY ===")
            print("Core file:", self.learning.core_file)
            print("Epi  file:", self.learning.epi_file)
            print("Core count:", len(self.learning.core_learning_history))
            print("Epi  count:", len(self.learning.episodic_learning_history))

            if which in ("core", "epi") and n:
                hist = self.learning.core_learning_history if which == "core" else self.learning.episodic_learning_history
                print(f"\nLast {min(n, len(hist))} from {which}:")
                for i, m in enumerate(_tail(hist, n), 1):
                    print(f"- {m.get('input','')}")
            elif which not in ("summary", "core", "epi"):
                print(f"[CLAW]: unknown memory target: {which} (use: core|epi)")

            print("===================")
            return

        if as_json:
            _dump_json({"kind": "claw.error", "error": {"message": f"unknown subcommand: {sub}", "hint": "try: claw help"}})
            return
        print(f"[CLAW]: unknown subcommand: {sub} (try: claw help)")

    # =========================
    # SINGLE COMMAND HANDLER
    # =========================

    def handle_command(self, line: str):
        try:
            if not line:
                return

            parts = line.split()
            cmd = parts[0].lower()
            rest = line[len(parts[0]) :].strip()

            if cmd in ("chat", "ask"):
                self.command_chat(rest)

            elif cmd == "ollama":
                self.command_ollama(rest)

            elif cmd == "gemini":
                self.command_gemini(rest)

            elif cmd in ("puter-login", "puter-auth"):
                self.command_puter_login(rest)

            elif cmd == "learn":
                self.command_learn(rest)

            elif cmd == "define":
                self.command_define(rest)

            elif cmd == "recall":
                self.command_recall()

            elif cmd == "state":
                self.command_state()

            elif cmd == "health":
                self.command_health()

            elif cmd == "synthesize":
                self.command_synthesize()

            elif cmd == "pulse-now":
                self.command_pulse_now()

            elif cmd == "pulse-start":
                self.command_pulse_start(rest or None)

            elif cmd == "pulse-stop":
                self.command_pulse_stop()

            elif cmd == "wander":
                self.command_wander()

            elif cmd == "ingest-ollama":
                self.command_ingest_ollama(rest)

            elif cmd == "promote":
                self.command_promote(rest)

            elif cmd == "whoami":
                self.command_whoami()

            elif cmd == "pack-list":
                self.command_pack_list(rest or None)

            elif cmd == "core-list":
                self.command_pack_list("core")

            elif cmd == "load-pack":
                self.command_load_pack(rest)

            elif cmd == "load-core":
                self.command_load_core(rest)

            elif cmd in ("create-profile", "new-profile"):
                self.command_create_profile(rest)

            elif cmd == "run-script":
                self.command_run_script(rest)

            elif cmd == "scan":
                self.command_scan()

            elif cmd in ("qtm", "qtm-shell"):
                self.command_qtm_shell(rest)

            elif cmd == "live":
                self.command_live()

            elif cmd == "wslmenu":
                self.command_wslmenu(rest)

            elif cmd == "claw":
                self.command_claw(rest)

            elif cmd == "legacy":
                self.command_legacy(rest)

            # V3 compatibility shims
            elif cmd in (
                "qtm-status",
                "qtm-mode",
                "rails",
                "qhace",
                "forget",
                "duel",
                "ingest-url",
                "ingest-api",
                "crawl",
                "genesis-review",
                "puter-chat",
                "puter-models",
            ):
                self.command_compat_legacy(cmd, rest)

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
