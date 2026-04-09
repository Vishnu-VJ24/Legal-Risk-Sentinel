from __future__ import annotations

from collections import Counter
from collections.abc import Mapping
import logging
from time import perf_counter
from typing import Any, Callable

from config import Settings, get_settings
from models.pipeline_state import PipelineState
from models.schemas import ClauseResult, ResultsResponse, RiskAxes, RiskDistribution
from services.explainer import explain_clauses
from services.extractor import chunk_document, extract_clauses
from services.mock_pipeline import build_mock_results
from services.parser import parse_document_content
from services.scorer import build_overall_score, infer_risk_axes, map_score_to_risk_level, map_severity_to_score, score_clauses

try:
    from langgraph.graph import END, StateGraph
except ImportError:  # pragma: no cover - installed in deployment
    END = "__end__"
    StateGraph = None  # type: ignore[assignment]

logger = logging.getLogger(__name__)


def _traceable(name: str) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    try:
        from langsmith import traceable

        return traceable(name=name)
    except ImportError:  # pragma: no cover - installed in deployment
        def decorator(fn: Callable[..., Any]) -> Callable[..., Any]:
            return fn

        return decorator


@_traceable("parse_document")
async def _parse_node(state: PipelineState, _: Settings, file_bytes: bytes) -> PipelineState:
    parsed = await parse_document_content(file_bytes, state.filename)
    state.document_name = str(parsed["document_name"])
    state.page_count = int(parsed["page_count"])
    state.pages = list(parsed["pages"])  # type: ignore[arg-type]
    state.full_text = str(parsed["full_text"])
    if not state.full_text.strip():
        raise ValueError("Document parser did not extract any text.")
    return state


@_traceable("chunk_document")
async def _chunk_node(state: PipelineState, _: Settings, __: bytes) -> PipelineState:
    return chunk_document(state)


@_traceable("extract_clauses")
async def _extract_node(state: PipelineState, settings: Settings, _: bytes) -> PipelineState:
    return await extract_clauses(state, settings)


@_traceable("score_clauses")
async def _score_node(state: PipelineState, settings: Settings, _: bytes) -> PipelineState:
    return await score_clauses(state, settings)


@_traceable("explain_clauses")
async def _explain_node(state: PipelineState, settings: Settings, _: bytes) -> PipelineState:
    return await explain_clauses(state, settings)


def _assemble_results(state: PipelineState) -> ResultsResponse:
    explained_by_id = {clause.clause_id: clause for clause in state.explained_clauses}
    extracted_by_id = {clause.clause_id: clause for clause in state.extracted_clauses}
    clauses: list[ClauseResult] = []

    for clause in state.scored_clauses:
        score = map_severity_to_score(clause.risk_severity)
        risk_level = map_score_to_risk_level(score)
        explanation = explained_by_id.get(clause.clause_id)
        axes = infer_risk_axes(clause.clause_text, clause.clause_category, clause.risk_severity)
        clauses.append(
            ClauseResult(
                id=clause.clause_id,
                type=clause.clause_category,
                text=clause.clause_text,
                page_number=clause.page_number,
                section_id=extracted_by_id.get(clause.clause_id).section_id if clause.clause_id in extracted_by_id else None,
                section_title=extracted_by_id.get(clause.clause_id).section_title if clause.clause_id in extracted_by_id else None,
                parent_section_id=extracted_by_id.get(clause.clause_id).parent_section_id if clause.clause_id in extracted_by_id else None,
                bbox=clause.bbox,
                risk_score=score,
                risk_axes=RiskAxes(**axes),
                risk_level=risk_level,
                explanation=(explanation.explanation if explanation else clause.rationale),
                renegotiation_suggestion=explanation.renegotiation_suggestion if explanation else None,
                similar_safe_clause=explanation.similar_safe_clause if explanation else None,
            )
        )

    distribution_counter = Counter(clause.risk_level for clause in clauses)
    distribution = RiskDistribution(
        critical=distribution_counter.get("critical", 0),
        high=distribution_counter.get("high", 0),
        medium=distribution_counter.get("medium", 0),
        low=distribution_counter.get("low", 0),
    )

    return ResultsResponse(
        session_id=state.session_id,
        document_name=state.document_name,
        total_clauses=len(clauses),
        overall_risk_score=build_overall_score(state.scored_clauses),
        processing_time_seconds=0.0,
        clauses=clauses,
        risk_distribution=distribution,
    )


def _coerce_pipeline_state(state: Any) -> PipelineState:
    if isinstance(state, PipelineState):
        return state
    if isinstance(state, Mapping):
        return PipelineState.model_validate(dict(state))
    raise TypeError(f"Unsupported pipeline state type: {type(state)!r}")


async def _run_pipeline_sequential(state: PipelineState, settings: Settings, file_bytes: bytes) -> PipelineState:
    for node in (_parse_node, _chunk_node, _extract_node, _score_node, _explain_node):
        state = await node(state, settings, file_bytes)
    return state


def _build_graph(
    settings: Settings, file_bytes: bytes
) -> Any | None:
    if StateGraph is None:
        return None

    async def parse_document_node(state: PipelineState) -> PipelineState:
        return await _parse_node(state, settings, file_bytes)

    async def chunk_document_node(state: PipelineState) -> PipelineState:
        return await _chunk_node(state, settings, file_bytes)

    async def extract_clauses_node(state: PipelineState) -> PipelineState:
        return await _extract_node(state, settings, file_bytes)

    async def score_clauses_node(state: PipelineState) -> PipelineState:
        return await _score_node(state, settings, file_bytes)

    async def explain_clauses_node(state: PipelineState) -> PipelineState:
        return await _explain_node(state, settings, file_bytes)

    graph = StateGraph(PipelineState)
    graph.add_node("parse_document", parse_document_node)
    graph.add_node("chunk_document", chunk_document_node)
    graph.add_node("extract_clauses", extract_clauses_node)
    graph.add_node("score_clauses", score_clauses_node)
    graph.add_node("explain_clauses", explain_clauses_node)
    graph.set_entry_point("parse_document")
    graph.add_edge("parse_document", "chunk_document")
    graph.add_edge("chunk_document", "extract_clauses")
    graph.add_edge("extract_clauses", "score_clauses")
    graph.add_edge("score_clauses", "explain_clauses")
    graph.add_edge("explain_clauses", END)
    return graph.compile()


async def run_analysis_pipeline(session_id: str, filename: str, file_bytes: bytes) -> ResultsResponse:
    settings = get_settings()
    started = perf_counter()
    logger.info(
        "session=%s pipeline_start mode=%s scorer_base_model=%s scorer_lora=%s extractor_model=%s explainer_model=%s",
        session_id,
        settings.pipeline_mode,
        settings.cf_risk_base_model,
        settings.cf_risk_lora_name,
        settings.hf_extractor_model_id,
        settings.hf_explainer_model_id,
    )

    if settings.pipeline_mode == "mock":
        parsed = await parse_document_content(file_bytes, filename)
        results = build_mock_results(session_id, str(parsed["document_name"]), int(parsed["page_count"]))
        results.processing_time_seconds = round(perf_counter() - started, 1)
        logger.info("session=%s pipeline_complete path=mock duration=%.2fs", session_id, results.processing_time_seconds)
        return results

    state = PipelineState(session_id=session_id, filename=filename)

    try:
        graph = _build_graph(settings, file_bytes)
        if graph is not None:
            state = _coerce_pipeline_state(await graph.ainvoke(state))
        else:
            state = _coerce_pipeline_state(await _run_pipeline_sequential(state, settings, file_bytes))
        results = _assemble_results(state)
        logger.info(
            "session=%s pipeline_complete path=dynamic duration=%.2fs clauses=%s overall_score=%s",
            session_id,
            round(perf_counter() - started, 1),
            len(results.clauses),
            results.overall_risk_score,
        )
    except Exception as exc:
        if settings.pipeline_mode == "real":
            logger.exception("session=%s pipeline_failed mode=real error=%s", session_id, exc)
            raise

        fallback_name = state.document_name or filename
        fallback_page_count = max(1, state.page_count)
        results = build_mock_results(session_id, fallback_name, fallback_page_count)
        results.document_name = fallback_name
        state.add_diagnostic("fallback_if_needed", f"Fell back to mock pipeline: {exc}", used_fallback=True)
        logger.warning(
            "session=%s pipeline_fallback path=mock error=%s",
            session_id,
            exc,
        )

    results.processing_time_seconds = round(perf_counter() - started, 1)
    return results
