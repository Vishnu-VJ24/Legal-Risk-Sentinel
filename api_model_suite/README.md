# API Model Suite

Standalone CLI checks for the Legal Sentinel backend and configured external model APIs.

The suite is intentionally separate from the Docker app. It lives under `api_model_suite/`, writes reports to `api_model_suite/reports/`, and does not need to be copied into the deployment container.

Progress bars are shown with `tqdm` while checks are running. If `tqdm` is not installed, the CLI falls back to simple progress lines.

For remote deployments, the default model inventory source is the deployed backend's `/api/chat/models` endpoint. Private Hugging Face Space variables such as `EDGE_VERIFY_MODEL` are not externally visible unless the app exposes them, so local `.env` stage models are excluded by default for remote `--base-url` runs. Use `--config-source hybrid` when you intentionally want to combine local `.env` with deployed backend chat models.

## Commands

```bash
python3 -m api_model_suite --help
python3 -m api_model_suite check-backend --base-url http://127.0.0.1:8000
python3 -m api_model_suite check-models --list
python3 -m api_model_suite check-models
python3 -m api_model_suite stress --requests 20 --concurrency 4
python3 -m api_model_suite all
```

Explicit model inventory source:

```bash
python3 -m api_model_suite --base-url https://your-space.hf.space check-models --list
python3 -m api_model_suite --base-url https://your-space.hf.space check-models --list --config-source hybrid
python3 -m api_model_suite check-models --list --config-source local
```

## Notes

- `check-models --list` only prints model inventory and makes no external API calls.
- Direct NVIDIA probes use `NVIDIA_API_KEY`.
- Direct OpenAI probes use `OPENAI_API_KEY`.
- Backend chat streaming requires `--run-id` for a completed run; otherwise it is skipped.
- Reports include `model_name`, `provider`, `api_surface`, `role`, and `source` for model-related rows.
