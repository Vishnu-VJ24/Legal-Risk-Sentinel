# LexAI

![LexAI banner placeholder](https://placehold.co/1200x400/0a0a0f/f1f0ff?text=LexAI+Banner)

LexAI is a production-style AI contract analysis app that extracts clauses, scores legal risk, and explains the highest-risk provisions in plain English.

[![React](https://img.shields.io/badge/React-18-61dafb?style=for-the-badge&logo=react&logoColor=white)](https://react.dev/)
[![TypeScript](https://img.shields.io/badge/TypeScript-Strict-3178c6?style=for-the-badge&logo=typescript&logoColor=white)](https://www.typescriptlang.org/)
[![Vite](https://img.shields.io/badge/Vite-Frontend-646cff?style=for-the-badge&logo=vite&logoColor=white)](https://vitejs.dev/)
[![FastAPI](https://img.shields.io/badge/FastAPI-Backend-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![Tailwind](https://img.shields.io/badge/Tailwind-v3-06b6d4?style=for-the-badge&logo=tailwindcss&logoColor=white)](https://tailwindcss.com/)

## Overview

LexAI is designed as a recruiter-facing capstone project that demonstrates full-stack engineering, AI product thinking, and clean API-first architecture. Version 1 uses a deterministic FastAPI mock backend so the frontend experience is stable, fast, and ready for demos. The backend contract is intentionally shaped so a real HuggingFace inference pipeline can replace the stub later without frontend changes.

## Architecture

```mermaid
flowchart LR
    A["User Uploads Contract"] --> B["React Frontend (Vite + TS)"]
    B --> C["FastAPI Mock API"]
    C --> D["Parser Service (PDF / DOCX / TXT)"]
    D --> E["Mock Clause Extractor"]
    E --> F["Mock Risk Scorer"]
    F --> G["Mock Explainer"]
    G --> H["Structured Results API"]
    H --> I["Results Dashboard + PDF Highlights"]
```

## Project Structure

```text
lexai/
├── frontend/
├── backend/
├── .github/workflows/deploy.yml
└── README.md
```

## Local Setup

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Set `VITE_API_BASE_URL` to your backend URL if it is not running at `http://localhost:8000`.

### Backend

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload
```

The backend accepts PDF, DOCX, and TXT uploads, parses basic metadata, simulates a multi-stage AI pipeline with realistic delays, and returns deterministic contract risk results.

## Screenshots

![Landing page placeholder](https://placehold.co/1200x700/111118/f1f0ff?text=Landing+Page)

Landing page with premium AI SaaS styling and upload CTA.

![Analyze flow placeholder](https://placehold.co/1200x700/111118/f1f0ff?text=Analyze+Flow)

Upload workflow with animated pipeline progress.

![Results dashboard placeholder](https://placehold.co/1200x700/111118/f1f0ff?text=Results+Dashboard)

Dashboard with risk overview, clause cards, PDF preview, and export actions.

## API Contract

### `POST /api/analyze`

Uploads a contract as multipart form-data with the `file` field and returns a session identifier plus initial progress metadata.

### `GET /api/results/{session_id}`

Returns a structured analysis payload with clause-level risk details, explanations, and a risk distribution summary.

## Deployment

Frontend deployment is handled through GitHub Actions and GitHub Pages.

Live demo placeholder: [https://your-username.github.io/lexai/](https://your-username.github.io/lexai/)

Backend deployment is intentionally separate and should point to a HuggingFace Space or other API host through `VITE_API_BASE_URL`.

## Dataset Credits

- [CUAD](https://www.atticusprojectai.org/cuad)
- [ContractNLI](https://stanfordnlp.github.io/contract-nli/)

## Future Work

- Replace the mock pipeline with task-specific LoRA or adapter-based models on HuggingFace.
- Add adapter hot-swap support for clause extraction, risk scoring, and explanation stages.
- Introduce authentication, saved sessions, and team review workflows.
- Export branded PDF reports with legal review summaries and audit logs.

## License

MIT
