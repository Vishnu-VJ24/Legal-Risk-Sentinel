from __future__ import annotations

import logging
from typing import Any

from config import Settings
from models.pipeline_state import ExplainedClauseCandidate, PipelineState, ScoredClauseCandidate
from services.inference import HuggingFaceTextGenerator
from services.scorer import map_score_to_risk_level, map_severity_to_score

logger = logging.getLogger(__name__)


def _template_explanation(scored_clause: ScoredClauseCandidate) -> ExplainedClauseCandidate:
    score = map_severity_to_score(scored_clause.risk_severity)
    risk_level = map_score_to_risk_level(score)
    factors = ", ".join(scored_clause.risk_factors[:2]) if scored_clause.risk_factors else "risk allocation"
    return ExplainedClauseCandidate(
        clause_id=scored_clause.clause_id,
        explanation=(
            f"This {scored_clause.clause_category.lower()} clause is rated {risk_level} risk because it emphasizes "
            f"{factors}. {scored_clause.rationale}"
        ),
        renegotiation_suggestion=(
            "Narrow the obligation, add mutuality, and cap exposure to a commercially reasonable amount."
            if score >= 6.5
            else None
        ),
        similar_safe_clause=(
            "Each party's obligations should be limited to the specific risk addressed in this clause and capped where commercially reasonable."
            if score >= 8
            else None
        ),
    )


def _normalize_explainer_payload(payload: dict[str, Any], scored_clause: ScoredClauseCandidate) -> ExplainedClauseCandidate:
    explanation = str(payload.get("explanation", "")).strip()
    if not explanation:
        raise ValueError("Explainer response did not include explanation text.")

    suggestion = str(payload.get("renegotiation_suggestion", "")).strip() or None
    safe_clause = str(payload.get("similar_safe_clause", "")).strip() or None
    return ExplainedClauseCandidate(
        clause_id=scored_clause.clause_id,
        explanation=explanation,
        renegotiation_suggestion=suggestion,
        similar_safe_clause=safe_clause,
    )


async def explain_clauses(state: PipelineState, settings: Settings) -> PipelineState:
    generator = HuggingFaceTextGenerator(settings)
    explained: list[ExplainedClauseCandidate] = []

    if generator.available and settings.pipeline_mode != "mock":
        logger.info(
            "session=%s stage=explaining path=model model_id=%s clauses=%s",
            state.session_id,
            settings.hf_explainer_model_id,
            len(state.scored_clauses),
        )

    for clause in state.scored_clauses:
        score = map_severity_to_score(clause.risk_severity)
        if score < 6.5:
            explained.append(_template_explanation(clause))
            continue

        payload: dict[str, Any] | None = None
        if generator.available and settings.pipeline_mode != "mock":
            prompt = (
                "You explain legal contract clause risk. "
                "Return only JSON with keys: explanation, renegotiation_suggestion, similar_safe_clause.\n\n"
                f"Clause category: {clause.clause_category}\n"
                f"Clause text: {clause.clause_text}\n"
                f"Risk factors: {', '.join(clause.risk_factors) or 'none'}\n"
                f"Model rationale: {clause.rationale}\n"
            )
            try:
                payload = generator.generate_json(
                    model_id=settings.hf_explainer_model_id,
                    prompt=prompt,
                    max_new_tokens=600,
                    temperature=0.2,
                )
            except Exception as exc:  # pragma: no cover - depends on remote model
                state.add_diagnostic("explaining", f"Explainer model failed for {clause.clause_id}: {exc}", used_fallback=True)
                logger.warning(
                    "session=%s stage=explaining path=model_failed clause=%s error=%s",
                    state.session_id,
                    clause.clause_id,
                    exc,
                )

        if payload is None:
            explained.append(_template_explanation(clause))
            state.add_diagnostic("explaining", f"Used template explanation for {clause.clause_id}.", used_fallback=True)
            logger.info(
                "session=%s stage=explaining path=template clause=%s",
                state.session_id,
                clause.clause_id,
            )
            continue

        explained.append(_normalize_explainer_payload(payload, clause))

    state.explained_clauses = explained
    logger.info(
        "session=%s stage=explaining completed clauses=%s",
        state.session_id,
        len(state.explained_clauses),
    )
    return state
