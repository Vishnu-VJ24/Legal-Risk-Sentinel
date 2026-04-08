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
- `HF_RISK_MODEL_ID` default: `VJ24/llama-risk-tagger-merged`
- `HF_EXTRACTOR_MODEL_ID`
- `HF_EXPLAINER_MODEL_ID`
- `LANGCHAIN_TRACING_V2=true`
- `LANGSMITH_API_KEY`
- `LANGSMITH_PROJECT`

## Notes

- The frontend API contract remains unchanged.
- The backend now supports dynamic clause extraction, scoring, and explanation assembly.
- If model inference is unavailable in hybrid mode, the service returns the existing mock-style output for demo reliability.
