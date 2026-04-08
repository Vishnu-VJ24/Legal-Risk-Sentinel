from __future__ import annotations

import logging
from statistics import fmean
from typing import Any

from config import Settings
from models.pipeline_state import ExtractedClauseCandidate, PipelineState, ScoredClauseCandidate
from models.schemas import RiskLevel
from services.cloudflare_inference import CloudflareLoraScorer

logger = logging.getLogger(__name__)


def map_severity_to_score(severity: int) -> float:
    severity = max(1, min(5, severity))
    return round(severity * 2.0, 1)


def map_score_to_risk_level(score: float) -> RiskLevel:
    if score >= 8:
        return "critical"
    if score >= 6.5:
        return "high"
    if score >= 4:
        return "medium"
    return "low"


def infer_risk_axes(text: str, category: str, severity: int) -> dict[str, int]:
    lowered = text.lower()
    axes = {"liability": 2, "indemnity": 2, "ip_rights": 2, "termination": 2}

    if category in {"Indemnification", "Limitation of Liability"} or "liability" in lowered:
        axes["liability"] = min(10, severity * 2)
    if category == "Indemnification" or "indemn" in lowered:
        axes["indemnity"] = min(10, severity * 2)
    if category == "IP Assignment" or "intellectual property" in lowered or "assign" in lowered:
        axes["ip_rights"] = min(10, severity * 2)
    if category == "Termination" or "terminate" in lowered:
        axes["termination"] = min(10, severity * 2)

    return axes


def build_overall_score(scored_clauses: list[ScoredClauseCandidate]) -> int:
    if not scored_clauses:
        return 0

    weighted_scores: list[float] = []
    for clause in scored_clauses:
        base_score = map_severity_to_score(clause.risk_severity)
        weight = 1.0
        if base_score >= 8:
            weight = 1.45
        elif base_score >= 6.5:
            weight = 1.2
        weighted_scores.extend([base_score] * int(weight * 10))

    normalized = fmean(weighted_scores) if weighted_scores else 0
    return max(0, min(100, round(normalized * 10)))


def _heuristic_score_clause(clause: ExtractedClauseCandidate) -> dict[str, Any]:
    lowered = clause.raw_text.lower()
    severity = 2
    risk_factors: list[str] = []

    severe_terms = {
        "unlimited": "unlimited liability",
        "consequential": "consequential damages",
        "punitive": "punitive damages",
        "indemnify": "unilateral indemnification",
        "exclusive": "one-sided exclusivity",
        "terminate": "termination leverage",
        "assign": "broad IP assignment",
        "audit": "burdensome audit rights",
        "competitor": "restrictive non-compete",
    }

    for keyword, label in severe_terms.items():
        if keyword in lowered:
            severity += 1
            risk_factors.append(label)

    if clause.predicted_category in {"Indemnification", "IP Assignment", "Limitation of Liability"}:
        severity += 1

    severity = max(1, min(5, severity))
    category = clause.predicted_category or "General Terms"
    rationale = (
        f"This {category.lower()} clause appears to shift risk through "
        f"{', '.join(risk_factors[:2]) if risk_factors else 'unbalanced obligations'}, "
        "so it merits closer legal review."
    )
    return {
        "clause_category": category,
        "risk_severity": severity,
        "is_unfair": severity >= 4,
        "risk_factors": risk_factors[:4] or ["allocation imbalance"],
        "rationale": rationale,
    }


def _normalize_score_payload(payload: dict[str, Any], clause: ExtractedClauseCandidate) -> ScoredClauseCandidate:
    category = str(payload.get("clause_category", clause.predicted_category)).strip() or clause.predicted_category
    try:
        severity = max(1, min(5, int(payload.get("risk_severity", 3))))
    except (TypeError, ValueError):
        severity = 3

    rationale = str(payload.get("rationale", "")).strip()
    if not rationale:
        raise ValueError("Scorer response did not include rationale.")

    raw_factors = payload.get("risk_factors", [])
    if isinstance(raw_factors, list):
        risk_factors = [str(item).strip() for item in raw_factors if str(item).strip()]
    else:
        risk_factors = []

    return ScoredClauseCandidate(
        clause_id=clause.clause_id,
        clause_text=clause.raw_text,
        clause_category=category,
        page_number=clause.page_number,
        bbox=clause.bbox or (70.0, 90.0, 500.0, 150.0),
        risk_severity=severity,
        is_unfair=bool(payload.get("is_unfair", severity >= 4)),
        risk_factors=risk_factors,
        rationale=rationale,
    )


async def score_clauses(state: PipelineState, settings: Settings) -> PipelineState:
    cloudflare_scorer = CloudflareLoraScorer(settings)
    scored: list[ScoredClauseCandidate] = []

    if cloudflare_scorer.available and settings.pipeline_mode != "mock":
        logger.info(
            "session=%s stage=scoring path=cloudflare_lora base_model=%s lora=%s clauses=%s",
            state.session_id,
            settings.cf_risk_base_model,
            settings.cf_risk_lora_name,
            len(state.extracted_clauses),
        )
    elif settings.pipeline_mode != "mock":
        logger.info(
            "session=%s stage=scoring path=heuristic_only reason=cloudflare_not_configured clauses=%s",
            state.session_id,
            len(state.extracted_clauses),
        )

    for clause in state.extracted_clauses:
        payload: dict[str, Any] | None = None
        if cloudflare_scorer.available and settings.pipeline_mode != "mock":
            prompt = (
                "You are a legal contract risk scoring model. "
                "Return only JSON with keys: clause_category, risk_severity, is_unfair, risk_factors, rationale. "
                "risk_severity must be an integer from 1 to 5.\n\n"
                f"Clause text:\n{clause.raw_text}"
            )
            try:
                payload = cloudflare_scorer.generate_json(
                    prompt=prompt,
                    max_tokens=220,
                    temperature=0.02,
                )
            except Exception as exc:  # pragma: no cover - depends on remote model
                state.add_diagnostic("scoring", f"Scorer model failed for {clause.clause_id}: {exc}", used_fallback=True)
                logger.warning(
                    "session=%s stage=scoring path=cloudflare_failed clause=%s base_model=%s lora=%s error=%s",
                    state.session_id,
                    clause.clause_id,
                    settings.cf_risk_base_model,
                    settings.cf_risk_lora_name,
                    exc,
                )

        if payload is None:
            payload = _heuristic_score_clause(clause)
            state.add_diagnostic("scoring", f"Used heuristic scoring for {clause.clause_id}.", used_fallback=True)
            logger.info(
                "session=%s stage=scoring path=heuristic clause=%s",
                state.session_id,
                clause.clause_id,
            )

        scored.append(_normalize_score_payload(payload, clause))

    if len(scored) != len(state.extracted_clauses):
        raise ValueError("Scoring did not return a result for every extracted clause.")

    state.scored_clauses = scored
    logger.info(
        "session=%s stage=scoring completed overall_score=%s clauses=%s",
        state.session_id,
        build_overall_score(state.scored_clauses),
        len(state.scored_clauses),
    )
    return state
