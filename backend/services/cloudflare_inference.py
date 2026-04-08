from __future__ import annotations

import json
import time
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from config import Settings
from services.inference import extract_json_object


class CloudflareLoraScorer:
    def __init__(self, settings: Settings):
        self.settings = settings

    @property
    def available(self) -> bool:
        return bool(
            self.settings.cf_account_id
            and self.settings.cf_api_token
            and self.settings.cf_risk_lora_name
            and self.settings.cf_risk_base_model
        )

    def generate_json(
        self,
        *,
        prompt: str,
        max_tokens: int = 400,
        temperature: float = 0.05,
    ) -> tuple[dict[str, Any], float, dict[str, int], str]:
        if not self.available:
            raise RuntimeError("Cloudflare LoRA scorer is not configured.")

        url = (
            f"https://api.cloudflare.com/client/v4/accounts/"
            f"{self.settings.cf_account_id}/ai/run/{self.settings.cf_risk_base_model}"
        )
        payload = {
            "prompt": prompt,
            "raw": True,
            "lora": self.settings.cf_risk_lora_name,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
        request = Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.settings.cf_api_token}",
                "Content-Type": "application/json",
            },
            method="POST",
        )

        started = time.perf_counter()
        try:
            with urlopen(request, timeout=self.settings.cf_scorer_timeout_seconds) as response:
                body = json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            raise RuntimeError(f"Cloudflare scorer request failed with status {exc.code}.") from exc
        except URLError as exc:
            raise RuntimeError("Cloudflare scorer request could not reach the API.") from exc

        if body.get("success") is False:
            errors = body.get("errors", [])
            raise RuntimeError(f"Cloudflare scorer returned an error: {errors}")

        result = body.get("result")
        usage = body.get("result", {}).get("usage", {}) if isinstance(body.get("result"), dict) else {}
        normalized_usage = {
            "prompt_tokens": int(usage.get("prompt_tokens", 0) or 0),
            "completion_tokens": int(usage.get("completion_tokens", 0) or 0),
            "total_tokens": int(usage.get("total_tokens", 0) or 0),
        }
        if isinstance(result, dict):
            if isinstance(result.get("response"), str):
                raw_text = result["response"]
                return extract_json_object(raw_text), time.perf_counter() - started, normalized_usage, raw_text
            if isinstance(result.get("result"), str):
                raw_text = result["result"]
                return extract_json_object(raw_text), time.perf_counter() - started, normalized_usage, raw_text
            raw_text = json.dumps(result)
            return result, time.perf_counter() - started, normalized_usage, raw_text
        if isinstance(result, str):
            return extract_json_object(result), time.perf_counter() - started, normalized_usage, result
        raise RuntimeError("Cloudflare scorer response did not contain a parseable result.")
