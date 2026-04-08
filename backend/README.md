---
title: Legal Risk Sentinel API
sdk: docker
app_port: 7860
---

# Legal Risk Sentinel API

FastAPI backend for LexAI / Legal Risk Sentinel with a quality-first dynamic pipeline.

## Endpoints

- `POST /api/analyze`
- `GET /api/results/{session_id}`
- `GET /health`

## Pipeline Modes

- `LEXAI_PIPELINE_MODE=mock` uses the deterministic mock pipeline
- `LEXAI_PIPELINE_MODE=real` attempts only the dynamic model-backed pipeline
- `LEXAI_PIPELINE_MODE=hybrid` tries the dynamic pipeline first and falls back to mock results if needed

## Key Environment Variables

- `HF_TOKEN`
- `HF_EXTRACTOR_MODEL_ID`
- `HF_EXPLAINER_MODEL_ID`
- `CF_ACCOUNT_ID`
- `CF_API_TOKEN`
- `CF_RISK_BASE_MODEL` default: `@cf/mistral/mistral-7b-instruct-v0.2-lora`
- `CF_RISK_LORA_NAME` should be set to your immutable Cloudflare fine-tune ID, for example `bd08f996-1fa9-4c11-a512-c040ef90645f`
- `LANGCHAIN_TRACING_V2=true`
- `LANGSMITH_API_KEY`
- `LANGSMITH_PROJECT`

## Notes

- The frontend API contract remains unchanged.
- The backend now supports dynamic clause extraction, Cloudflare LoRA-backed scoring, and explanation assembly.
- If model inference is unavailable in hybrid mode, the service returns the existing mock-style output for demo reliability.
- To stay within Cloudflare's free Workers AI usage, the scorer uses a low-temperature, low-max-token JSON-only prompt and should only be invoked for clause-level scoring.
