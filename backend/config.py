from functools import lru_cache
from os import getenv
from typing import Literal

from pydantic import BaseModel


PipelineMode = Literal["mock", "real", "hybrid"]


class Settings(BaseModel):
    pipeline_mode: PipelineMode = "hybrid"
    hf_token: str | None = None
    hf_risk_model_id: str = "VJ24/llama-risk-tagger-merged"
    hf_extractor_model_id: str = "Qwen/Qwen2.5-3B-Instruct"
    hf_explainer_model_id: str = "Qwen/Qwen2.5-3B-Instruct"
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
        hf_risk_model_id=getenv("HF_RISK_MODEL_ID", "VJ24/llama-risk-tagger-merged"),
        hf_extractor_model_id=getenv("HF_EXTRACTOR_MODEL_ID", "Qwen/Qwen2.5-3B-Instruct"),
        hf_explainer_model_id=getenv("HF_EXPLAINER_MODEL_ID", "Qwen/Qwen2.5-3B-Instruct"),
        langsmith_api_key=getenv("LANGSMITH_API_KEY"),
        langsmith_project=getenv("LANGSMITH_PROJECT", "lexai"),
        langchain_tracing_v2=tracing_enabled,
    )
