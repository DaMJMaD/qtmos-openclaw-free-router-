import json
import os
import subprocess
from pathlib import Path

import requests

try:
    from dotenv import load_dotenv  # type: ignore
except Exception:  # pragma: no cover
    load_dotenv = None  # type: ignore

# Load project + llm env files so persisted Puter token works across restarts.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if load_dotenv:
    try:
        load_dotenv(PROJECT_ROOT / ".env", override=False)
    except Exception:
        pass
    try:
        load_dotenv(PROJECT_ROOT / "llm" / ".env", override=False)
    except Exception:
        pass


def _load_env_fallback(path: Path):
    """Lightweight .env loader used when python-dotenv is unavailable."""
    try:
        if not path.exists():
            return
        for line in path.read_text(encoding="utf-8").splitlines():
            s = line.strip()
            if not s or s.startswith("#") or "=" not in s:
                continue
            k, v = s.split("=", 1)
            key = k.strip()
            if not key:
                continue
            val = v.strip().strip("'\"")
            os.environ.setdefault(key, val)
    except Exception:
        return


_load_env_fallback(PROJECT_ROOT / ".env")
_load_env_fallback(PROJECT_ROOT / "llm" / ".env")

# ---------- MCP (local provider hub) ----------
MCP_BASE_URL = os.getenv("MCP_BASE_URL", "http://127.0.0.1:8000")
MCP_TIMEOUT = int(os.getenv("MCP_TIMEOUT", "20"))


def call_mcp_chat(prompt: str, model: str | None = None):
    """Call local MCP OpenAI proxy (POST /chat)."""
    try:
        r = requests.post(
            f"{MCP_BASE_URL}/chat",
            json={"content": prompt, "model": model},
            timeout=MCP_TIMEOUT,
        )
        r.raise_for_status()
        return (r.json() or {}).get("content")
    except Exception:
        return None


def call_mcp_gemini(prompt: str, model: str | None = None):
    """Call local MCP Gemini proxy (POST /gemini)."""
    try:
        r = requests.post(
            f"{MCP_BASE_URL}/gemini",
            json={"content": prompt, "model": model},
            timeout=MCP_TIMEOUT,
        )
        r.raise_for_status()
        return (r.json() or {}).get("content")
    except Exception:
        return None

# ---------- OLLAMA ----------
# Local-only adapter for an Ollama server running on this machine.
OLLAMA_BASE = "http://127.0.0.1:11434"

# Default model name; can be overridden by callers.
# Use llama3:latest as safer default across fresh installs.
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3:latest")
OLLAMA_TIMEOUT = int(os.getenv("OLLAMA_TIMEOUT", "20"))

# Minimal compatibility surface expected by core.cognitive_system
OLLAMA_MODELS = {
    "default": OLLAMA_MODEL,
}

def query_ollama(prompt, model: str | None = None):
    chosen = (model or OLLAMA_MODEL)
    try:
        r = requests.post(
            f"{OLLAMA_BASE}/api/generate",
            json={"model": chosen, "prompt": prompt, "stream": False},
            timeout=OLLAMA_TIMEOUT,
        )
        # Fallback when a migrated machine has only llama3:latest pulled.
        if r.status_code == 404 and chosen != "llama3:latest":
            r = requests.post(
                f"{OLLAMA_BASE}/api/generate",
                json={"model": "llama3:latest", "prompt": prompt, "stream": False},
                timeout=OLLAMA_TIMEOUT,
            )
        r.raise_for_status()
        return r.json().get("response")
    except Exception:
        return None


def chat_ollama(messages, model: str | None = None):
    """Compatibility helper.

    core.cognitive_system expects a chat-style function that takes a list of
    {role, content} messages. We keep it minimal and local-only by collapsing
    user content into a single prompt and calling /api/generate.
    """
    try:
        prompt = "\n".join(
            m.get("content", "") for m in (messages or []) if m.get("role") in ("user", "system")
        ).strip()
        if not prompt:
            return None
        return query_ollama(prompt, model=model)
    except Exception:
        return None

# ---------- PUTER (CLAUDE / GPT / GROK) ----------
PUTER_API = os.getenv("PUTER_CHAT_URL", "https://api.puter.com/v1/chat")
PUTER_KEY = os.getenv("PUTER_API_KEY")
PUTER_TIMEOUT = int(os.getenv("PUTER_TIMEOUT", "90"))
PUTER_DEFAULT_MODEL = os.getenv("PUTER_DEFAULT_MODEL", "claude-opus-4-6")
PUTER_FALLBACK_MODEL = os.getenv("PUTER_FALLBACK_MODEL", "claude-opus-4-6")
PUTER_MODELS_URL = os.getenv("PUTER_MODELS_URL", "https://api.puter.com/puterai/chat/models/details")
PUTER_NODE_BRIDGE = Path(__file__).resolve().with_name("puter_node_bridge.cjs")
PUTER_SDK_CHECK_ARG = "@heyputer/puter.js/src/init.cjs"
PUTER_AUTO_INSTALL_SDK = os.getenv("PUTER_AUTO_INSTALL_SDK", "1") == "1"
PUTER_AUTH_RETRY_ERRORS = {
    "MISSING_AUTH_TOKEN",
    "INVALID_TOKEN_PLACEHOLDER",
    "INIT_FAILED",
    "AUTH_BOOTSTRAP_FAILED",
}
PUTER_AUTH_RETRY_DETAIL_MARKERS = (
    "unauthorized",
    "forbidden",
    "invalid token",
    "invalid header value",
    "auth",
    "expired",
    "session",
    "401",
    "403",
)


def _ensure_puter_sdk() -> bool:
    """Ensure Puter.js Node SDK is resolvable for bridge calls.

    Auto-installs into the project (no-save) when missing.
    """
    if not PUTER_NODE_BRIDGE.exists():
        return False

    try:
        ok = subprocess.run(
            ["node", "-e", f"require.resolve('{PUTER_SDK_CHECK_ARG}')"],
            cwd=str(PROJECT_ROOT),
            capture_output=True,
            text=True,
            timeout=8,
        )
        if ok.returncode == 0:
            return True
    except Exception:
        pass

    if not PUTER_AUTO_INSTALL_SDK:
        return False

    try:
        subprocess.run(
            ["npm", "install", "--prefix", str(PROJECT_ROOT), "--no-save", "@heyputer/puter.js"],
            cwd=str(PROJECT_ROOT),
            capture_output=True,
            text=True,
            timeout=120,
            check=False,
        )
    except Exception:
        return False

    try:
        ok2 = subprocess.run(
            ["node", "-e", f"require.resolve('{PUTER_SDK_CHECK_ARG}')"],
            cwd=str(PROJECT_ROOT),
            capture_output=True,
            text=True,
            timeout=8,
        )
        return ok2.returncode == 0
    except Exception:
        return False


def _puter_token():
    token = os.getenv("puterAuthToken") or os.getenv("PUTER_AUTH_TOKEN") or ""
    # Strip accidental whitespace/newlines from pasted tokens.
    return "".join(str(token).split())


def _set_puter_token(token: str | None):
    clean = "".join(str(token or "").split())
    if not clean:
        return ""
    os.environ["puterAuthToken"] = clean
    os.environ["PUTER_AUTH_TOKEN"] = clean
    return clean


def _puter_headers():
    if PUTER_KEY:
        return {"Authorization": f"Bearer {PUTER_KEY}"}
    return {}


def _extract_chat_content(payload):
    if isinstance(payload, dict):
        content = payload.get("content")
        if isinstance(content, str) and content.strip():
            return content

        choices = payload.get("choices")
        if isinstance(choices, list) and choices:
            msg = choices[0].get("message") if isinstance(choices[0], dict) else None
            if isinstance(msg, dict):
                c = msg.get("content")
                if isinstance(c, str):
                    return c
                if isinstance(c, list):
                    text_bits = []
                    for bit in c:
                        if isinstance(bit, dict) and bit.get("type") == "text":
                            text_bits.append(str(bit.get("text", "")))
                    merged = "".join(text_bits).strip()
                    if merged:
                        return merged

    return None


def _run_puter_node_bridge(argv: list[str], require_token: bool = True):
    token = _puter_token()
    if require_token and not token:
        return None
    if not _ensure_puter_sdk():
        return None

    env = os.environ.copy()
    if token:
        env.setdefault("puterAuthToken", token)
        env.setdefault("PUTER_AUTH_TOKEN", token)

    try:
        r = subprocess.run(
            ["node", str(PUTER_NODE_BRIDGE), *argv],
            capture_output=True,
            text=True,
            timeout=max(15, PUTER_TIMEOUT + 10),
            env=env,
        )
    except Exception:
        return None

    out = (r.stdout or "").strip()
    if not out:
        return None

    # Prefer full payload parse, then last JSON-looking line as fallback.
    for candidate in [out] + [line.strip() for line in out.splitlines()[::-1]]:
        if not candidate:
            continue
        if not (candidate.startswith("{") and candidate.endswith("}")):
            continue
        try:
            return json.loads(candidate)
        except Exception:
            continue
    return None


def _bridge_error(payload):
    if not isinstance(payload, dict):
        return ""
    return str(payload.get("error") or "").strip().upper()


def _bridge_detail(payload):
    if not isinstance(payload, dict):
        return ""
    return str(payload.get("detail") or "").strip().lower()


def _is_bridge_auth_failure(payload):
    code = _bridge_error(payload)
    if code in PUTER_AUTH_RETRY_ERRORS:
        return True

    # Some providers only include auth/session hints in detail text.
    detail = _bridge_detail(payload)
    if detail and any(mark in detail for mark in PUTER_AUTH_RETRY_DETAIL_MARKERS):
        return True

    return False


def _bootstrap_puter_token(force: bool = False):
    if PUTER_KEY:
        return None
    if not PUTER_NODE_BRIDGE.exists():
        return None

    existing = _puter_token()
    if existing and not force:
        return existing

    payload = _run_puter_node_bridge(["auth-token"], require_token=False)
    if not isinstance(payload, dict):
        return None
    if not payload.get("ok"):
        return None
    return _set_puter_token(payload.get("token"))


def _run_puter_bridge_with_reauth(argv: list[str]):
    if not PUTER_NODE_BRIDGE.exists():
        return None

    if not _puter_token():
        _bootstrap_puter_token(force=False)

    payload = _run_puter_node_bridge(argv, require_token=True)
    if payload is None and not _puter_token():
        if _bootstrap_puter_token(force=True):
            return _run_puter_node_bridge(argv, require_token=True)
        return None

    if _is_bridge_auth_failure(payload):
        if _bootstrap_puter_token(force=True):
            retry = _run_puter_node_bridge(argv, require_token=True)
            if retry is not None:
                return retry

    return payload


def has_puter_auth():
    # Auth means we have a credential, not just a bridge binary.
    return bool(PUTER_KEY or _puter_token())


def call_puter_with_model(prompt: str, model: str | None = None):

    candidates = []
    selected = (model or PUTER_DEFAULT_MODEL or "").strip()
    if selected:
        candidates.append(selected)

    fallback = (PUTER_FALLBACK_MODEL or "").strip()
    if fallback and fallback not in candidates:
        candidates.append(fallback)

    if not candidates:
        candidates = ["claude-opus-4-6"]

    if PUTER_KEY:
        for chosen in candidates:
            try:
                r = requests.post(
                    PUTER_API,
                    headers=_puter_headers(),
                    json={
                        "model": chosen,
                        "messages": [{"role": "user", "content": prompt}],
                    },
                    timeout=PUTER_TIMEOUT,
                )
                r.raise_for_status()
                content = _extract_chat_content(r.json())
                if content:
                    return content, chosen
            except Exception:
                continue

    for chosen in candidates:
        payload = _run_puter_bridge_with_reauth(["chat", "--model", chosen, "--prompt", prompt])
        if not isinstance(payload, dict):
            continue
        if payload.get("ok") and payload.get("content"):
            return str(payload.get("content")), str(payload.get("model") or chosen)

    return None, None


def call_puter(prompt: str, model: str | None = None):
    content, _used_model = call_puter_with_model(prompt, model=model)
    return content


def list_puter_models(provider: str | None = None):
    endpoints = [
        PUTER_MODELS_URL,
        "https://puter.com/puterai/chat/models/details",
    ]

    params = {}
    if provider:
        params["provider"] = provider

    for url in endpoints:
        try:
            r = requests.get(url, params=params, headers=_puter_headers(), timeout=PUTER_TIMEOUT)
            if r.status_code in (401, 403):
                r = requests.get(url, params=params, timeout=PUTER_TIMEOUT)
            r.raise_for_status()
            data = r.json()
            if isinstance(data, list):
                return data
            if isinstance(data, dict):
                for key in ("models", "data", "result"):
                    v = data.get(key)
                    if isinstance(v, list):
                        return v
        except Exception:
            continue

    payload = _run_puter_bridge_with_reauth(
        ["list-models", "--provider", provider] if provider else ["list-models"]
    )
    if isinstance(payload, dict) and payload.get("ok") and isinstance(payload.get("models"), list):
        return payload["models"]

    return None

# ---------- GEMINI ----------
class GeminiAdapter:
    def __init__(self):
        try:
            from google import genai
            self.client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
            self.enabled = True
        except:
            self.enabled = False

    def ask(self, prompt):
        if not self.enabled:
            return None
        try:
            r = self.client.models.generate_content(
                model="models/gemini-2.5-flash",
                contents=prompt,
            )
            return r.text
        except:
            return None

_gemini = GeminiAdapter()

# ---------- ROUTER ----------
def ask_router(prompt):
    """Route a prompt to an available engine.

    Local-only mode:
      If QTM_LOCAL_ONLY=1 (default), skip external providers and only try Ollama.
    """

    local_only = os.getenv("QTM_LOCAL_ONLY", "1") == "1"

    if not local_only:
        resp = call_puter(prompt)
        if resp:
            return resp, "puter"

    resp = query_ollama(prompt)
    if resp:
        return resp, "ollama"

    if (not local_only) and _gemini.enabled:
        resp = _gemini.ask(prompt)
        if resp:
            return resp, "gemini"

    return None, "none"
