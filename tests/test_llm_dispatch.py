import tempfile
import time
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from src.config import StageConfig
from src.key_pool import NvidiaKeyPool
from src.llm_client import execute_with_fallback


class LlmDispatchTests(unittest.TestCase):
    def test_report_race_returns_first_completed_response(self):
        with tempfile.TemporaryDirectory() as out_dir:
            settings = SimpleNamespace(
                debug_traceflow=False,
                out_dir=out_dir,
                nvidia_api_key="slow",
                llm_timeout_sec=30,
                llm_max_retries=1,
                final_report_race_keys=2,
            )
            pool = NvidiaKeyPool(("slow", "fast"), 1, 0.01)

            def fake_call(_provider, key, *_args, **_kwargs):
                time.sleep(0.03 if key == "slow" else 0.001)
                return f"# {key} report"

            with patch("src.llm_client.get_nvidia_key_pool", return_value=pool), patch(
                "src.llm_client._execute_single_call", side_effect=fake_call
            ):
                raw, parsed = execute_with_fallback(
                    "final_report",
                    "race-test",
                    StageConfig(provider="nvidia", model="test-model"),
                    settings,
                    [{"role": "user", "content": "report"}],
                    race_nvidia_keys=True,
                )

        self.assertEqual(raw, "# fast report")
        self.assertIsNone(parsed)


if __name__ == "__main__":
    unittest.main()
