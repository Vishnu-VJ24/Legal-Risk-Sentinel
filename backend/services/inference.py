from __future__ import annotations

import json
from json import JSONDecodeError
from typing import Any

from config import Settings

try:
    from huggingface_hub import InferenceClient
except ImportError:  # pragma: no cover - installed in deployment
    InferenceClient = None  # type: ignore[assignment]


def extract_json_object(payload: str) -> dict[str, Any]:
    start = payload.find("{")
    end = payload.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise ValueError("Model response did not contain a JSON object.")

    candidate = payload[start : end + 1]
    try:
        parsed = json.loads(candidate)
    except JSONDecodeError as exc:  # pragma: no cover - defensive parsing
        raise ValueError("Model response contained invalid JSON.") from exc

    if not isinstance(parsed, dict):
        raise ValueError("Model response JSON was not an object.")
    return parsed


class HuggingFaceTextGenerator:
    def __init__(self, settings: Settings):
        self.settings = settings
        self._client = InferenceClient(token=settings.hf_token) if InferenceClient else None

    @property
    def available(self) -> bool:
        return self._client is not None and bool(self.settings.hf_token)

    def generate_json(
        self,
        *,
        model_id: str,
        prompt: str,
        max_new_tokens: int = 512,
        temperature: float = 0.1,
    ) -> dict[str, Any]:
        if not self.available or self._client is None:
            raise RuntimeError("Hugging Face inference client is not configured.")

        response = self._client.text_generation(
            prompt,
            model=model_id,
            max_new_tokens=max_new_tokens,
            temperature=temperature,
            return_full_text=False,
        )
        return extract_json_object(str(response))
