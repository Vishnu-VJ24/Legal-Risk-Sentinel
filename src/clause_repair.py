from __future__ import annotations

import json
import re
from typing import Any, Callable

from .io_utils import sha256_text
from .llm_client import execute_with_fallback
from .sections import SectionNode


def suspicious_clause_nodes(nodes: list[SectionNode], min_words: int) -> list[SectionNode]:
    """Keep LLM repair tightly scoped to unusually large atomic units."""
    return [
        node for node in nodes
        if node.is_analysis_unit and node.node_type == "section" and node.word_count >= min_words
    ]


def _prompt(node: SectionNode) -> tuple[str, str]:
    system = (
        "You split contract text into explicit clauses. Return JSON only. Do not paraphrase, "
        "invent headings, or omit text. A split is valid only when the supplied text contains "
        "an explicit clause heading or paragraph label."
    )
    user = json.dumps({
        "task": "Return one segment when no reliable split exists. Otherwise return contiguous segments that cover the entire source text.",
        "source_node_id": node.node_id,
        "source_text": node.text,
        "schema": {
            "segments": [{
                "heading": "verbatim heading or empty string",
                "start_quote": "verbatim opening text of this segment",
                "end_quote": "verbatim closing text of this segment"
            }]
        },
        "rules": [
            "The first start_quote must begin at the first non-whitespace character.",
            "Each next start_quote must occur after the preceding end_quote.",
            "The final end_quote must end at the last non-whitespace character.",
            "Do not create a segment for a cross-reference such as 'Section 2.1, or'."
        ],
    }, ensure_ascii=False)
    return system, user


def _validated_segments(node: SectionNode, payload: dict[str, Any]) -> list[tuple[int, int, str]] | None:
    segments = payload.get("segments") if isinstance(payload, dict) else None
    if not isinstance(segments, list) or len(segments) < 2:
        return None
    text = node.text
    cursor, output = 0, []
    for item in segments:
        if not isinstance(item, dict):
            return None
        start_quote = str(item.get("start_quote", "")).strip()
        end_quote = str(item.get("end_quote", "")).strip()
        if not start_quote or not end_quote:
            return None
        start = text.find(start_quote, cursor)
        if start < 0:
            return None
        end_start = text.find(end_quote, start)
        if end_start < 0:
            return None
        end = end_start + len(end_quote)
        output.append((start, end, str(item.get("heading", "")).strip()))
        cursor = end
    first, last = output[0], output[-1]
    if text[:first[0]].strip() or text[last[1]:].strip():
        return None
    if any(text[output[i][1]:output[i + 1][0]].strip() for i in range(len(output) - 1)):
        return None
    return output


def _node_from_segment(parent: SectionNode, index: int, start: int, end: int, heading: str) -> SectionNode:
    text = parent.text[start:end].strip("\n")
    identifier = re.match(r"(?:SECTION\s+)?(\d{1,3}(?:\.\d{1,3}){0,4}(?:\([a-z]\))?)\b", heading, re.I)
    canonical = identifier.group(1) if identifier else f"{parent.canonical_id or parent.node_id}__part_{index}"
    return SectionNode(
        node_id=canonical,
        canonical_id=canonical,
        title=heading or f"{parent.title} (part {index})",
        level=canonical.count(".") + 1 if re.match(r"\d", canonical) else parent.level + 1,
        raw_heading=heading,
        start_char=parent.start_char + start,
        end_char=parent.start_char + end,
        text=text,
        page_start=parent.page_start,
        page_end=parent.page_end,
        char_len=len(text),
        word_count=len(re.findall(r"\S+", text)),
        sha256=sha256_text(text),
        parent_id=parent.node_id,
        node_type="repaired_clause",
    )


def run_llm_clause_repair(
    nodes: list[SectionNode],
    settings: Any,
    check_cancel: Callable[[], None] | None = None,
) -> tuple[list[SectionNode], list[str]]:
    """Replace only fully grounded, contiguous oversized nodes; otherwise preserve input."""
    errors: list[str] = []
    output: list[SectionNode] = []
    for node in nodes:
        if check_cancel:
            check_cancel()
        if node not in suspicious_clause_nodes([node], settings.clause_repair_min_words):
            output.append(node)
            continue
        system, user = _prompt(node)
        try:
            _, parsed = execute_with_fallback(
                stage_name="clause_repair",
                trace_id=node.node_id,
                stage_config=settings.clause_repair,
                settings=settings,
                messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
                temperature=0.0,
                max_tokens=2500,
                response_format={"type": "json_object"},
                validator_fn=lambda value: None if isinstance(value, dict) and isinstance(value.get("segments"), list) else (_ for _ in ()).throw(ValueError("Missing segments")),
                timeout_sec=settings.clause_repair_timeout_sec,
                max_retries=0,
            )
            segments = _validated_segments(node, parsed or {})
            if not segments:
                output.append(node)
                continue
            node.is_analysis_unit = False
            output.append(node)
            output.extend(_node_from_segment(node, i + 1, start, end, heading) for i, (start, end, heading) in enumerate(segments))
        except Exception as exc:
            errors.append(f"{node.node_id}: {exc}")
            output.append(node)
    counts: dict[str, int] = {}
    for node in output:
        canonical = node.canonical_id or node.node_id
        counts[canonical] = counts.get(canonical, 0) + 1
        if counts[canonical] > 1:
            node.duplicate_of = canonical
            node.node_id = f"{canonical}__{counts[canonical]}"
    return output, errors
