from functools import lru_cache
from os import getenv
from typing import Literal

from pydantic import BaseModel


PipelineMode = Literal["mock", "real", "hybrid"]


class Settings(BaseModel):
    pipeline_mode: PipelineMode = "hybrid"
    hf_token: str | None = None
    hf_extractor_model_id: str = "Qwen/Qwen2.5-3B-Instruct"
    hf_explainer_model_id: str = "Qwen/Qwen2.5-3B-Instruct"
    cf_account_id: str | None = None
    cf_api_token: str | None = None
    cf_risk_base_model: str = "@cf/mistral/mistral-7b-instruct-v0.2-lora"
    cf_risk_lora_name: str | None = None
    cf_scorer_concurrency: int = 3
    cf_scorer_timeout_seconds: int = 45
    max_remote_scored_clauses: int = 4
    langsmith_api_key: str | None = None
    langsmith_project: str = "lexai"
    langchain_tracing_v2: bool = False


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    tracing_enabled = getenv("LANGCHAIN_TRACING_V2", "false").lower() == "true"
    requested_mode = getenv("LEXAI_PIPELINE_MODE", "hybrid").lower()
    mode: PipelineMode = "hybrid"
    if requested_mode in {"mock", "real", "hybrid"}:
        mode = requested_mode  # type: ignore[assignment]

    return Settings(
        pipeline_mode=mode,
        hf_token=getenv("HF_TOKEN"),
        hf_extractor_model_id=getenv("HF_EXTRACTOR_MODEL_ID", "Qwen/Qwen2.5-3B-Instruct"),
        hf_explainer_model_id=getenv("HF_EXPLAINER_MODEL_ID", "Qwen/Qwen2.5-3B-Instruct"),
        cf_account_id=getenv("CF_ACCOUNT_ID"),
        cf_api_token=getenv("CF_API_TOKEN"),
        cf_risk_base_model=getenv("CF_RISK_BASE_MODEL", "@cf/mistral/mistral-7b-instruct-v0.2-lora"),
        cf_risk_lora_name=getenv("CF_RISK_LORA_NAME"),
        cf_scorer_concurrency=max(1, int(getenv("CF_SCORER_CONCURRENCY", "3"))),
        cf_scorer_timeout_seconds=max(10, int(getenv("CF_SCORER_TIMEOUT_SECONDS", "45"))),
        max_remote_scored_clauses=max(1, int(getenv("MAX_REMOTE_SCORED_CLAUSES", "4"))),
        langsmith_api_key=getenv("LANGSMITH_API_KEY"),
        langsmith_project=getenv("LANGSMITH_PROJECT", "lexai"),
        langchain_tracing_v2=tracing_enabled,
    )
