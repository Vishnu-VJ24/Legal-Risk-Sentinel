import os
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from src.config import get_settings
from src.server import app

EXPECTED_MODELS = [
    ("fast", "openai/gpt-oss-20b", "FAST", 1500),
]


class ChatModelConfigTests(unittest.TestCase):
    def test_chat_models_are_fixed_despite_environment_overrides(self):
        overrides = {
            "CHAT_MODELS": "unapproved/model,another/model",
            "CHAT_MODELS_ATTRIBUTES": "STANDARD,THINKING",
            "CHAT_MODELS_MAX_TOKENS": "9999,9999",
            "CHAT_MODEL": "legacy/model",
            "CHAT_MODEL_THINKING": "legacy/thinking-model",
        }

        with patch.dict(os.environ, overrides):
            models = get_settings().chat_models

        self.assertEqual(
            [(model.id, model.model, model.attribute, model.max_tokens) for model in models],
            EXPECTED_MODELS,
        )

    def test_llm_stages_default_to_nvidia_oss_20b_and_allow_overrides(self):
        with patch.dict(os.environ, {"LLM_PROVIDER": "nvidia", "LLM_MODEL": "openai/gpt-oss-20b", "EDGE_VERIFY_MODEL": "custom/model"}):
            settings = get_settings()
        self.assertEqual(settings.risk_analyzer.provider, "nvidia")
        self.assertEqual(settings.risk_analyzer.model, "openai/gpt-oss-20b")
        self.assertEqual(settings.edge_verify.model, "custom/model")

    def test_key_pool_supplies_legacy_default_for_embedding_and_chat_callers(self):
        with patch.dict(os.environ, {"NVIDIA_API_KEY": "", "NVIDIA_API_KEYS": "pool-one,pool-two"}):
            settings = get_settings()
        self.assertEqual(settings.nvidia_api_key, "pool-one")
        self.assertEqual(settings.nvidia_api_keys, ("pool-one", "pool-two"))


class ChatModelApiTests(unittest.TestCase):
    def test_chat_models_endpoint_exposes_only_the_fixed_catalog(self):
        response = TestClient(app).get("/api/chat/models")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["default_model_id"], "fast")
        self.assertEqual(
            [
                (model["id"], model["model"], model["attribute"], model["max_tokens"])
                for model in payload["models"]
            ],
            EXPECTED_MODELS,
        )


if __name__ == "__main__":
    unittest.main()
