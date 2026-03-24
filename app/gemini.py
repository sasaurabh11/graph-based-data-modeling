from __future__ import annotations

import json
import urllib.error
import urllib.request

from .config import GEMINI_API_KEY, GEMINI_MODEL


class GeminiError(RuntimeError):
    pass


def _extract_text(payload: dict) -> str:
    parts: list[str] = []
    for candidate in payload.get("candidates", []):
        content = candidate.get("content", {})
        for part in content.get("parts", []):
            text = part.get("text")
            if text:
                parts.append(text)
    return "\n".join(parts).strip()


def generate_text(prompt: str, temperature: float = 0.1) -> str:
    if not GEMINI_API_KEY:
        raise GeminiError("Missing GEMINI_API_KEY in .env.")
    if not GEMINI_MODEL:
        raise GeminiError("Missing GEMINI_MODEL in .env.")

    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/"
        f"{GEMINI_MODEL}:generateContent?key={GEMINI_API_KEY}"
    )
    body = {
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": temperature,
            "topP": 0.95,
            "responseMimeType": "application/json",
        },
    }
    request = urllib.request.Request(
        url,
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="ignore")
        raise GeminiError(f"Gemini request failed: {detail or exc.reason}") from exc
    except Exception as exc:
        raise GeminiError("Gemini request failed.") from exc

    text = _extract_text(payload)
    if not text:
        raise GeminiError("Gemini returned no text.")
    return text
