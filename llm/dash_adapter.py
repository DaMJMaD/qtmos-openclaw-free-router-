import requests

DASH_ENDPOINT = "https://dash.qtmos.com/api/chat"

def ask_dash(prompt: str, model="claude-opus-4-6"):
    payload = {
        "message": prompt,
        "model": model,
    }

    try:
        r = requests.post(DASH_ENDPOINT, json=payload, timeout=60)
        r.raise_for_status()
        data = r.json()

        # normalize response
        if isinstance(data, dict):
            return data.get("content") or data.get("message")
        return str(data)

    except Exception as e:
        print(f"[DASH ERROR]: {e}")
        return None
