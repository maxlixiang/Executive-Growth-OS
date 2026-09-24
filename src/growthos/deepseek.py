import json
from typing import Any
import requests
from .config import Config

class DeepSeekError(RuntimeError): pass

def ask_json(config: Config, system: str, user: str, required: set[str], retries: int = 2) -> dict[str, Any]:
    if not config.api_key: raise DeepSeekError("DEEPSEEK_API_KEY is required for AI commands. Copy .env.example to .env.")
    url = config.base_url.rstrip("/") + "/chat/completions"
    for attempt in range(retries + 1):
        try:
            response = requests.post(url, headers={"Authorization": f"Bearer {config.api_key}", "Content-Type": "application/json"}, json={"model": config.model, "messages": [{"role":"system","content":system}, {"role":"user","content":user}], "response_format":{"type":"json_object"}, "temperature":0.3}, timeout=90)
            response.raise_for_status(); payload = json.loads(response.json()["choices"][0]["message"]["content"])
            if not required.issubset(payload): raise ValueError("Response misses required fields")
            return payload
        except (requests.RequestException, KeyError, ValueError, json.JSONDecodeError) as exc:
            if attempt == retries: raise DeepSeekError(f"AI response could not be safely validated: {exc}") from exc
    raise AssertionError("unreachable")
