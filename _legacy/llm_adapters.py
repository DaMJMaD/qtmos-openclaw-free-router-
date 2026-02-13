# llm_adapters.py
import os
import requests

# =========================
# OLLAMA CONFIG
# =========================

OLLAMA_BASE = "http://127.0.0.1:11434"

OLLAMA_MODELS = {
    "default": "llama3.1:8b",
    "fast": "llama3.2:3b",
    "mistral": "mistral:7b",
}

def query_ollama(prompt: str, model=None, max_tokens=2048):
    model = model or OLLAMA_MODELS["default"]
    url = f"{OLLAMA_BASE}/api/generate"

    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {
            "num_predict": max_tokens
        }
    }

    try:
        r = requests.post(url, json=payload, timeout=120)
        r.raise_for_status()
        return r.json().get("response", "").strip()
    except Exception as e:
        print(f"[OLLAMA ERROR]: {e}")
        return None


def chat_ollama(messages, model=None):
    # simple wrapper: flatten messages
    prompt = "\n".join(m["content"] for m in messages if "content" in m)
    return query_ollama(prompt, model=model)


# =========================
# MCP (ChatGPT proxy)
# =========================

MCP_CHAT_URL = "http://localhost:8000/chat"

def emit_mcp_chat(text: str) -> str | None:
    try:
        r = requests.post(
            MCP_CHAT_URL,
            json={"content": text},
            timeout=30
        )
        r.raise_for_status()
        return r.json().get("content")
    except Exception as e:
        print(f"[MCP ERROR]: {e}")
        return None



# =========================
# GEMINI ADAPTER (SAFE)
# =========================

class GeminiAdapter:
    def __init__(self):
        self.enabled = False
        try:
            from google import genai
            api_key = os.getenv("GEMINI_API_KEY")
            if not api_key:
                raise RuntimeError("GEMINI_API_KEY missing")

            self.client = genai.Client(api_key=api_key)
            self.model = "models/gemini-flash-lite-latest"
            self.enabled = True
        except Exception as e:
            print(f"[GEMINI]: Disabled ({e})")

    def ask(self, prompt: str) -> str | None:
        if not self.enabled:
            return None
        try:
            r = self.client.models.generate_content(
                model=self.model,
                contents=prompt
            )
            return r.text.strip()
        except Exception as e:
            print(f"[GEMINI ERROR]: {e}")
            return None


# =========================
# ASK ROUTER (TEAM MODE)
# =========================

_gemini = GeminiAdapter()

def ask_router(prompt: str) -> tuple[str | None, str]:
    """
    Deterministic, team-based ask routing.
    Tries engines in order, never aborts early.
    Returns (response, engine_name).
    """

    # 1️⃣ Try Ollama first (local, fast, private)
    resp = query_ollama(prompt)
    if resp:
        return resp, "ollama"

    # 2️⃣ Fallback to MCP Chat (Puter / OpenAI / OpenRouter)
    resp = emit_mcp_chat(prompt)
    if resp:
        return resp, "chat"

    # 3️⃣ Fallback to Gemini (if enabled)
    resp = _gemini.ask(prompt)
    if resp:
        return resp, "gemini"

    # ❌ Nothing worked
    return None, "none"
