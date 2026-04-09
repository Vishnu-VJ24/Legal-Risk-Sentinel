from __future__ import annotations

import logging
import re
from collections import OrderedDict

from config import Settings
from models.pipeline_state import DocumentChunk, ExtractedClauseCandidate, PipelineState
from services.inference import HuggingFaceTextGenerator
from services.structure import build_section_tree, find_chunk_section

MIN_CLAUSE_LENGTH = 80

CATEGORY_KEYWORDS: "OrderedDict[str, tuple[str, ...]]" = OrderedDict(
    {
        "Indemnification": ("indemnify", "hold harmless", "defend"),
        "Limitation of Liability": ("liability", "consequential", "punitive damages"),
        "Termination": ("terminate", "termination", "for convenience"),
        "IP Assignment": ("intellectual property", "work made for hire", "assign", "ownership"),
        "Governing Law": ("governing law", "venue", "jurisdiction"),
        "Non-Compete": ("non-compete", "competitor", "similar services"),
        "Confidentiality": ("confidential", "non-disclosure", "trade secret"),
        "Payment Terms": ("invoice", "fees", "payment", "withhold"),
        "Data Security": ("security incident", "customer data", "safeguards"),
        "Audit Rights": ("audit", "books and records", "subcontractor controls"),
    }
)

logger = logging.getLogger(__name__)


def chunk_document(state: PipelineState, target_chunk_size: int = 900) -> PipelineState:
    chunks: list[DocumentChunk] = []
    for page in state.pages:
        paragraphs = [segment.strip() for segment in re.split(r"\n\s*\n", page.text) if segment.strip()]
        if not paragraphs:
            paragraphs = [page.text.strip()] if page.text.strip() else []
        current = ""
        chunk_index = 0
        for paragraph in paragraphs:
            next_value = f"{current}\n\n{paragraph}".strip() if current else paragraph
            if len(next_value) > target_chunk_size and current:
                chunk_index += 1
                chunks.append(
                    DocumentChunk(
                        chunk_id=f"chunk_{page.page_number:02d}_{chunk_index:02d}",
                        page_number=page.page_number,
                        text=current,
                    )
                )
                current = paragraph
            else:
                current = next_value
        if current:
            chunk_index += 1
            chunks.append(
                DocumentChunk(
                    chunk_id=f"chunk_{page.page_number:02d}_{chunk_index:02d}",
                    page_number=page.page_number,
                    text=current,
                )
            )
    state.chunks = chunks
    return state


def _predict_category(text: str) -> str:
    lowered = text.lower()
    for category, keywords in CATEGORY_KEYWORDS.items():
        if any(keyword in lowered for keyword in keywords):
            return category
    return "General Terms"


def _synthesize_bbox(index: int, page_number: int) -> tuple[float, float, float, float]:
    x1 = 68.0 + (index % 3) * 6
    y1 = 88.0 + ((index * 84) % 340)
    width = 430.0
    height = 52.0 + (page_number % 3) * 6
    return (x1, y1, x1 + width, y1 + height)


def _build_heuristic_candidates(chunks: list[DocumentChunk]) -> list[ExtractedClauseCandidate]:
    candidates: list[ExtractedClauseCandidate] = []
    seen_text: set[str] = set()

    for chunk in chunks:
        segments = [segment.strip() for segment in re.split(r"(?<=[.;])\s+(?=[A-Z])", chunk.text) if segment.strip()]
        segment_buffer = ""
        for segment in segments:
            candidate_text = f"{segment_buffer} {segment}".strip() if segment_buffer else segment
            if len(candidate_text) < MIN_CLAUSE_LENGTH:
                segment_buffer = candidate_text
                continue

            normalized = " ".join(candidate_text.split())
            if normalized in seen_text:
                segment_buffer = ""
                continue

            seen_text.add(normalized)
            clause_index = len(candidates) + 1
            candidates.append(
                ExtractedClauseCandidate(
                    clause_id=f"clause_{clause_index:03d}",
                    raw_text=normalized,
                    predicted_category=_predict_category(normalized),
                    page_number=chunk.page_number,
                    source_chunk_id=chunk.chunk_id,
                    bbox=_synthesize_bbox(clause_index, chunk.page_number),
                )
            )
            segment_buffer = ""

        if segment_buffer and len(segment_buffer) >= MIN_CLAUSE_LENGTH:
            normalized = " ".join(segment_buffer.split())
            if normalized not in seen_text:
                clause_index = len(candidates) + 1
                candidates.append(
                    ExtractedClauseCandidate(
                        clause_id=f"clause_{clause_index:03d}",
                        raw_text=normalized,
                        predicted_category=_predict_category(normalized),
                        page_number=chunk.page_number,
                        source_chunk_id=chunk.chunk_id,
                        bbox=_synthesize_bbox(clause_index, chunk.page_number),
                    )
                )

    return candidates[:12]


def _normalize_candidate_payload(
    payload: dict[str, object], chunk: DocumentChunk, index: int
) -> ExtractedClauseCandidate | None:
    text = str(payload.get("text", "")).strip()
    if len(text) < MIN_CLAUSE_LENGTH:
        return None

    category = str(payload.get("clause_category", "")).strip() or _predict_category(text)
    page_value = payload.get("page_number", chunk.page_number)
    try:
        page_number = max(1, int(page_value))
    except (TypeError, ValueError):
        page_number = chunk.page_number

    return ExtractedClauseCandidate(
        clause_id=f"clause_{index:03d}",
        raw_text=" ".join(text.split()),
        predicted_category=category,
        page_number=page_number,
        source_chunk_id=chunk.chunk_id,
        bbox=_synthesize_bbox(index, page_number),
    )


async def extract_clauses(state: PipelineState, settings: Settings) -> PipelineState:
    generator = HuggingFaceTextGenerator(settings)
    candidates: list[ExtractedClauseCandidate] = []
    sections = build_section_tree(state.pages)
    section_lookup = {section.node_id: section for section in sections}

    if generator.available and settings.pipeline_mode != "mock":
        logger.info(
            "session=%s stage=extracting path=model model_id=%s chunks=%s",
            state.session_id,
            settings.hf_extractor_model_id,
            len(state.chunks),
        )
        for chunk in state.chunks:
            prompt = (
                "You extract legal clause candidates from contract text. "
                "Return only JSON with this shape: "
                '{"clauses":[{"text":"...","clause_category":"...","page_number":1}]}. '
                "Only include material clauses, not boilerplate section titles.\n\n"
                f"Contract chunk (page {chunk.page_number}):\n{chunk.text}"
            )
            try:
                payload = generator.generate_json(
                    model_id=settings.hf_extractor_model_id,
                    prompt=prompt,
                    max_new_tokens=700,
                )
                raw_clauses = payload.get("clauses", [])
                if isinstance(raw_clauses, list):
                    for raw_clause in raw_clauses:
                        if not isinstance(raw_clause, dict):
                            continue
                        candidate = _normalize_candidate_payload(raw_clause, chunk, len(candidates) + 1)
                        if candidate:
                            section = find_chunk_section(chunk, sections)
                            if section:
                                candidate.section_id = section.node_id
                                candidate.section_title = section.title
                                candidate.parent_section_id = section.parent_id
                            candidates.append(candidate)
            except Exception as exc:  # pragma: no cover - depends on remote model
                state.add_diagnostic("extracting", f"Extractor model failed for {chunk.chunk_id}: {exc}", used_fallback=True)
                logger.warning(
                    "session=%s stage=extracting path=model_failed chunk=%s error=%s",
                    state.session_id,
                    chunk.chunk_id,
                    exc,
                )

    if len(candidates) < 4:
        heuristic_candidates = _build_heuristic_candidates(state.chunks)
        if heuristic_candidates:
            candidates = heuristic_candidates
            state.add_diagnostic("extracting", "Used heuristic clause extraction fallback.", used_fallback=True)
            logger.info(
                "session=%s stage=extracting path=heuristic clauses=%s",
                state.session_id,
                len(candidates),
            )

    if len(candidates) < 2:
        raise ValueError("Extractor did not produce enough plausible clauses.")

    deduped: list[ExtractedClauseCandidate] = []
    seen_normalized: set[str] = set()
    for candidate in candidates:
        normalized = candidate.raw_text.lower()
        if normalized in seen_normalized:
            continue
        seen_normalized.add(normalized)
        if not candidate.section_id:
            source_chunk = next((chunk for chunk in state.chunks if chunk.chunk_id == candidate.source_chunk_id), None)
            if source_chunk:
                section = find_chunk_section(source_chunk, sections)
                if section:
                    candidate.section_id = section.node_id
                    candidate.section_title = section.title
                    candidate.parent_section_id = section.parent_id
        if candidate.section_id and candidate.section_id in section_lookup and not candidate.section_title:
            candidate.section_title = section_lookup[candidate.section_id].title
        deduped.append(candidate)

    state.extracted_clauses = deduped[:12]
    logger.info(
        "session=%s stage=extracting completed clauses=%s",
        state.session_id,
        len(state.extracted_clauses),
    )
    return state
