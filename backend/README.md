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
- `CF_RISK_BASE_MODEL` default: `@cf/meta/llama-3.1-8b-instruct`
- `CF_RISK_LORA_NAME`
- `LANGCHAIN_TRACING_V2=true`
- `LANGSMITH_API_KEY`
- `LANGSMITH_PROJECT`

## Notes

- The frontend API contract remains unchanged.
- The backend now supports dynamic clause extraction, Cloudflare LoRA-backed scoring, and explanation assembly.
- If model inference is unavailable in hybrid mode, the service returns the existing mock-style output for demo reliability.
