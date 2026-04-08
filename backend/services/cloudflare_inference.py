from __future__ import annotations

import json
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
    ) -> dict[str, Any]:
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

        try:
            with urlopen(request, timeout=90) as response:
                body = json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            raise RuntimeError(f"Cloudflare scorer request failed with status {exc.code}.") from exc
        except URLError as exc:
            raise RuntimeError("Cloudflare scorer request could not reach the API.") from exc

        if body.get("success") is False:
            errors = body.get("errors", [])
            raise RuntimeError(f"Cloudflare scorer returned an error: {errors}")

        result = body.get("result")
        if isinstance(result, dict):
            if isinstance(result.get("response"), str):
                return extract_json_object(result["response"])
            if isinstance(result.get("result"), str):
                return extract_json_object(result["result"])
            return result
        if isinstance(result, str):
            return extract_json_object(result)
        raise RuntimeError("Cloudflare scorer response did not contain a parseable result.")
