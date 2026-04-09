from typing import Literal

from pydantic import BaseModel, Field


RiskLevel = Literal["low", "medium", "high", "critical"]
PipelineStage = Literal["parsing", "extracting", "scoring", "explaining", "done"]
PipelineStatus = Literal["processing", "complete", "error"]


class AnalyzeResponse(BaseModel):
    session_id: str
    status: PipelineStatus
    pipeline_stage: PipelineStage
    progress_pct: int = Field(ge=0, le=100)


class RiskAxes(BaseModel):
    liability: int
    indemnity: int
    ip_rights: int
    termination: int


class ClauseResult(BaseModel):
    id: str
    type: str
    text: str
    page_number: int
    section_id: str | None = None
    section_title: str | None = None
    parent_section_id: str | None = None
    bbox: tuple[float, float, float, float]
    risk_score: float
    risk_axes: RiskAxes
    risk_level: RiskLevel
    explanation: str
    renegotiation_suggestion: str | None = None
    similar_safe_clause: str | None = None


class RiskDistribution(BaseModel):
    critical: int
    high: int
    medium: int
    low: int


class ResultsResponse(BaseModel):
    session_id: str
    document_name: str
    total_clauses: int
    overall_risk_score: int
    processing_time_seconds: float
    clauses: list[ClauseResult]
    risk_distribution: RiskDistribution
