from pydantic import BaseModel, Field


class ParsedPage(BaseModel):
    page_number: int
    text: str


class DocumentChunk(BaseModel):
    chunk_id: str
    page_number: int
    text: str


class ExtractedClauseCandidate(BaseModel):
    clause_id: str
    raw_text: str
    predicted_category: str
    page_number: int
    source_chunk_id: str | None = None
    section_id: str | None = None
    section_title: str | None = None
    parent_section_id: str | None = None
    bbox: tuple[float, float, float, float] | None = None


class ScoredClauseCandidate(BaseModel):
    clause_id: str
    clause_text: str
    clause_category: str
    page_number: int
    bbox: tuple[float, float, float, float]
    risk_severity: int = Field(ge=1, le=5)
    is_unfair: bool
    risk_factors: list[str] = Field(default_factory=list)
    rationale: str


class ExplainedClauseCandidate(BaseModel):
    clause_id: str
    explanation: str
    renegotiation_suggestion: str | None = None
    similar_safe_clause: str | None = None


class PipelineDiagnostics(BaseModel):
    stage: str
    message: str
    used_fallback: bool = False


class PipelineState(BaseModel):
    session_id: str
    filename: str
    document_name: str = ""
    page_count: int = 0
    full_text: str = ""
    pages: list[ParsedPage] = Field(default_factory=list)
    chunks: list[DocumentChunk] = Field(default_factory=list)
    extracted_clauses: list[ExtractedClauseCandidate] = Field(default_factory=list)
    scored_clauses: list[ScoredClauseCandidate] = Field(default_factory=list)
    explained_clauses: list[ExplainedClauseCandidate] = Field(default_factory=list)
    diagnostics: list[PipelineDiagnostics] = Field(default_factory=list)

    def add_diagnostic(self, stage: str, message: str, used_fallback: bool = False) -> None:
        self.diagnostics.append(
            PipelineDiagnostics(stage=stage, message=message, used_fallback=used_fallback)
        )
