FROM node:22-bookworm-slim AS frontend-build

WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build


FROM python:3.13-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    HOST=0.0.0.0 \
    PORT=7860 \
    APP_DATA_DIR=/tmp/legal-sentinel-data \
    HF_HOME=/tmp/huggingface

WORKDIR /app

COPY pyproject.toml README.md main.py ./
COPY src/ ./src/

RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir .

COPY --from=frontend-build /app/frontend/dist ./frontend/dist

EXPOSE 7860

CMD ["python", "main.py"]
# 