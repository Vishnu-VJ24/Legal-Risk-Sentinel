---
title: Legal Risk Sentinel
emoji: ⚖️
colorFrom: blue
colorTo: indigo
sdk: docker
app_port: 7860
---

# Legal Sentinel

Legal Sentinel is a contract analysis workspace that:

- uploads and parses a PDF contract
- maps clause relationships as a graph
- flags risks with grounded evidence
- generates an executive review
- supports follow-up contract questions with retrieval-backed chat

## Deploying On Free Hugging Face Spaces

This repo is configured for a single-container Docker Space on Hugging Face CPU Basic.

### 1. Create the Space

- Create a new Hugging Face Space
- Choose `Docker` as the SDK
- Push this repository to the Space

### 2. Add secrets

In the Hugging Face Space settings, add:

- `NVIDIA_API_KEY`
- `OCR_SPACE_API_KEY` when OCR fallback is required

Optional runtime variables:

- `MAX_UPLOAD_MB`
- `RUN_TTL_HOURS`
- `RISK_ANALYZER_CONCURRENCY`
- `EDGE_VERIFY_CONCURRENCY`

Use [.env.example](.env.example) as the local template. Do not commit real secrets.

All LLM stages use NVIDIA's OpenAI-compatible endpoint and `openai/gpt-oss-20b` by default. Individual stages may override this in environment configuration.

### 3. What the deployment does

- Builds the React frontend in a Node stage
- Installs the Python backend in a slim Python runtime
- Serves the built SPA and API from one FastAPI process on port `7860`
- Stores uploads and generated artifacts under `APP_DATA_DIR`

### 4. Optional: auto-deploy from GitHub `main`

If you want Hugging Face to update every time you push to GitHub `main`, this repo includes:

- [.github/workflows/deploy-hf-space.yml](.github/workflows/deploy-hf-space.yml)

Set these GitHub repository secrets:

- `HF_SPACE_REPO`
  Example: `bored26/legal-sentinel`
- `HF_USERNAME`
  Example: `bored26`
- `HF_TOKEN`
  A Hugging Face write token with access to the Space

What the workflow does:

- runs on every push to GitHub `main`
- creates a clean deploy snapshot without local/runtime artifacts or sample PDFs
- force-pushes that snapshot to the Hugging Face Space `main` branch

This is the recommended long-term flow if your source of truth is GitHub `main`.

## Local Development

### Backend

```bash
cp .env.example .env
uv run python main.py
```

The backend uses `HOST` and `PORT`. For local Vite development, the default backend URL is `http://127.0.0.1:8000`.

### Frontend

```bash
cd frontend
npm ci
npm run dev
```

The frontend talks to `/api` by default. To point it at a different backend, set `VITE_API_BASE_URL`.

## Runtime Notes

- `GET /healthz` is available for host health checks.
- Run state is persisted to per-run manifest files while the container is alive.
- Free hosting filesystems are ephemeral, so this deployment is demo-grade rather than durable production infrastructure.
- Stale runs are cleaned automatically after `RUN_TTL_HOURS`.
