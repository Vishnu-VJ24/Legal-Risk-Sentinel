from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv


@dataclass
class StageConfig:
    provider: str
    model: str
    fallback_provider: Optional[str] = None
    fallback_model: Optional[str] = None
    use_response_format: bool = True


@dataclass(frozen=True)
class ChatModelConfig:
    id: str
    model: str
    attribute: str
    display_name: str
    assistant_name: str
    max_tokens: int


CHAT_MODELS: tuple[ChatModelConfig, ...] = (
    ChatModelConfig(
        id="fast",
        model="openai/gpt-oss-20b",
        attribute="FAST",
        display_name="gpt-oss-20b",
        assistant_name="gpt-oss-20b Fast Assistant",
        max_tokens=1500,
    ),
)


@dataclass
class Settings:
    pdf_path: str
    out_dir: str
    nvidia_api_key: str
    nvidia_api_keys: tuple[str, ...]

    edge_verify: StageConfig
    clause_repair: StageConfig
    risk_analyzer: StageConfig
    final_report: StageConfig
    ocr_space_api_key: str = ""

    max_ids_in_prompt: int = 600
    temperature: float = 0.0
    chat_models: tuple[ChatModelConfig, ...] = ()
    embedding_model: str = "nvidia/nv-embed-v1"
    fallback_embedding_model: str = "BAAI/bge-small-en-v1.5"
    embedding_batch_size: int = 64
    embedding_batch_max_chars: int = 120_000
    
    force_local_embeddings: bool = False
    debug_traceflow: bool = False
    risk_analyzer_concurrency: int = 3
    edge_verify_concurrency: int = 3
    app_data_dir: str = "/tmp/legal-sentinel-data"
    host: str = "127.0.0.1"
    port: int = 8000
    max_upload_mb: int = 25
    run_ttl_hours: float = 24.0
    cors_allow_origins: tuple[str, ...] = ()
    ocr_min_text_chars: int = 500
    ocr_enabled: bool = True
    clause_repair_enabled: bool = True
    clause_repair_min_words: int = 350
    clause_repair_timeout_sec: int = 25
    skip_retrieval_indexing: bool = False
    llm_timeout_sec: int = 30
    llm_max_in_flight_per_key: int = 1
    llm_max_retries: int = 1
    llm_cooldown_sec: float = 5.0
    final_report_race_keys: int = 0
    risk_group_max_chars: int = 18000


def _clean_env_value(raw: str) -> str:
    value = raw.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        return value[1:-1].strip()
    return value


def _env_str(name: str, default: str = "") -> str:
    raw = os.getenv(name)
    if raw is None:
        return default
    return _clean_env_value(raw)


def _env_int(name: str, default: int) -> int:
    raw = _env_str(name)
    if raw is None:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def _env_float(name: str, default: float) -> float:
    raw = _env_str(name)
    if raw is None:
        return default
    try:
        return float(raw)
    except ValueError:
        return default


def _env_csv(name: str, default: str) -> tuple[str, ...]:
    raw = _env_str(name, default)
    values = [_clean_env_value(item) for item in raw.split(",")]
    return tuple(item for item in values if item)


def _build_chat_models() -> tuple[ChatModelConfig, ...]:
    """Return the fixed chat API model catalog.

    Chat models intentionally are not environment-configurable: the API and UI
    must only expose the supported OpenAI OSS models.
    """
    return CHAT_MODELS


def _load_stage_config(prefix: str, default_provider: str, default_model: str) -> StageConfig:
    provider = _env_str(f"{prefix}_PROVIDER", default_provider).lower()
    model = _env_str(f"{prefix}_MODEL", default_model)

    fallback_provider = _env_str(f"{prefix}_FALLBACK_PROVIDER", "").lower()
    fallback_model = _env_str(f"{prefix}_FALLBACK_MODEL", "")
    use_format = _env_str(f"{prefix}_USE_RESPONSE_FORMAT", "true").lower() == "true"

    return StageConfig(
        provider=provider,
        model=model,
        fallback_provider=fallback_provider if fallback_provider else None,
        fallback_model=fallback_model if fallback_model else None,
        use_response_format=use_format
    )


def get_settings(
    pdf_path: str | None = None,
    out_dir: str | None = None,
) -> Settings:
    load_dotenv(override=False)

    app_data_dir = _env_str("APP_DATA_DIR", str(Path("/tmp/legal-sentinel-data")))
    default_out_dir = str(Path(app_data_dir) / "runs" / "adhoc")

    nvidia_api_key = _env_str("NVIDIA_API_KEY", "")
    configured_keys = _env_csv("NVIDIA_API_KEYS", "")
    nvidia_api_keys = configured_keys or ((nvidia_api_key,) if nvidia_api_key else ())
    # Older call sites accept one credential. Prefer the first configured pool key so
    # NVIDIA_API_KEYS works without requiring the legacy variable as well.
    if not nvidia_api_key and nvidia_api_keys:
        nvidia_api_key = nvidia_api_keys[0]
    if not nvidia_api_key:
        print("Warning: NVIDIA_API_KEY is not set!")

    default_provider = _env_str("LLM_PROVIDER", "nvidia").lower()
    default_model = _env_str("LLM_MODEL", "openai/gpt-oss-20b")
    edge_verify = _load_stage_config("EDGE_VERIFY", default_provider, default_model)
    clause_repair = _load_stage_config("CLAUSE_REPAIR", default_provider, default_model)
    risk_analyzer = _load_stage_config("RISK_ANALYZER", default_provider, default_model)
    final_report = _load_stage_config("FINAL_REPORT", default_provider, default_model)

    # The shared pool enforces per-key limits. Let stage concurrency use the
    # configured pool instead of silently stranding additional credentials.
    pool_capacity = max(1, len(nvidia_api_keys) * max(1, _env_int("LLM_MAX_IN_FLIGHT_PER_KEY", 1)))
    default_concurrency = min(10, pool_capacity)
    concurrency = _env_int("RISK_ANALYZER_CONCURRENCY", default_concurrency)
    risk_concurrency = min(pool_capacity, max(1, concurrency))

    edge_concurrency = _env_int("EDGE_VERIFY_CONCURRENCY", default_concurrency)
    edge_sync_concurrency = min(pool_capacity, max(1, edge_concurrency))

    return Settings(
        pdf_path=pdf_path or os.getenv("PDF_PATH", ""),
        out_dir=out_dir or _env_str("OUT_DIR", default_out_dir),
        nvidia_api_key=nvidia_api_key,
        nvidia_api_keys=nvidia_api_keys,
        ocr_space_api_key=_env_str("OCR_SPACE_API_KEY", ""),
        edge_verify=edge_verify,
        clause_repair=clause_repair,
        risk_analyzer=risk_analyzer,
        final_report=final_report,
        debug_traceflow=_env_str("DEBUG_TRACEFLOW", "false").lower() == "true",
        force_local_embeddings=_env_str("FORCE_LOCAL_EMBEDDINGS", "false").lower() == "true",
        risk_analyzer_concurrency=risk_concurrency,
        edge_verify_concurrency=edge_sync_concurrency,
        chat_models=_build_chat_models(),
        embedding_model=_env_str("EMBEDDING_MODEL", "nvidia/nv-embed-v1"),
        fallback_embedding_model=_env_str("FALLBACK_EMBEDDING_MODEL", "BAAI/bge-small-en-v1.5"),
        embedding_batch_size=max(1, _env_int("EMBEDDING_BATCH_SIZE", 64)),
        embedding_batch_max_chars=max(4_000, _env_int("EMBEDDING_BATCH_MAX_CHARS", 120_000)),
        app_data_dir=app_data_dir,
        host=_env_str("HOST", "127.0.0.1"),
        port=_env_int("PORT", 8000),
        max_upload_mb=max(1, _env_int("MAX_UPLOAD_MB", 25)),
        run_ttl_hours=max(1.0, _env_float("RUN_TTL_HOURS", 24.0)),
        cors_allow_origins=_env_csv(
            "CORS_ALLOW_ORIGINS",
            "http://localhost:5173,http://127.0.0.1:5173",
        ),
        ocr_min_text_chars=max(1, _env_int("OCR_MIN_TEXT_CHARS", 500)),
        ocr_enabled=_env_str("OCR_ENABLED", "true").lower() == "true",
        clause_repair_enabled=_env_str("CLAUSE_REPAIR_ENABLED", "true").lower() == "true",
        clause_repair_min_words=max(100, _env_int("CLAUSE_REPAIR_MIN_WORDS", 350)),
        clause_repair_timeout_sec=max(5, _env_int("CLAUSE_REPAIR_TIMEOUT_SEC", 25)),
        skip_retrieval_indexing=_env_str("SKIP_RETRIEVAL_INDEXING", "false").lower() == "true",
        llm_timeout_sec=max(10, _env_int("LLM_TIMEOUT_SEC", 30)),
        llm_max_in_flight_per_key=max(1, _env_int("LLM_MAX_IN_FLIGHT_PER_KEY", 1)),
        llm_max_retries=max(0, _env_int("LLM_MAX_RETRIES", 1)),
        llm_cooldown_sec=max(0.1, _env_float("LLM_COOLDOWN_SEC", 5.0)),
        final_report_race_keys=max(0, _env_int("FINAL_REPORT_RACE_KEYS", 0)),
        risk_group_max_chars=max(4000, _env_int("RISK_GROUP_MAX_CHARS", 18000)),
    )
