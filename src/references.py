from __future__ import annotations

import re
from typing import Any, Dict, List

# Tighter patterns:
# - Schedule must be followed by token like A / 1 / 1.2 / A-1 etc. (not "set")
RE_REF_SECTION = re.compile(r"\b(?:Section|Sec\.|§)\s*(\d{1,3}(?:\.\d{1,3}){0,4})(?:\([a-z]\))?\b", re.IGNORECASE)
RE_REF_ARTICLE = re.compile(r"\bArticle\s+([IVXLC]+|\d{1,3})\b", re.IGNORECASE)
# RE_REF_ARTICLE = re.compile(r"\bArticle\s+([IVXLC]+)\b", re.IGNORECASE)
RE_REF_EXHIBIT = re.compile(r"\bExhibit\s+([A-Z0-9]+(?:\.[A-Z0-9]+)*)\b", re.IGNORECASE)
RE_REF_SCHEDULE = re.compile(r"\bSchedule\s+([A-Z]|\d{1,3}(?:\.\d{1,3})*|[IVXLC]{1,6})\b")
RE_REF_SECTIONS_PLURAL = re.compile(
    r"\bSections?\s+(\d{1,3}(?:\.\d{1,3}){0,4})"
    r"(?:\s*(?:\([a-z]\))?)"
    r"(?:\s*(?:,|and|or|-|to)\s*(\d{1,3}(?:\.\d{1,3}){0,4})(?:\([a-z]\))?)*",
    re.IGNORECASE
)
# Strong cue + bare number (avoid matching "2007" etc.)
RE_REF_BARE_NUM_WITH_CUE = re.compile(
    r"\b(?:as defined in|defined in|pursuant to|subject to|except as provided in|in accordance with)\s+"
    r"(?:Section|Sec\.|§)?\s*(\d{1,3}(?:\.\d{1,3}){0,4})(?:\([a-z]\))?\b",
    re.IGNORECASE
)


def normalize_ref_target(kind: str, token: str) -> str:
    token = token.strip()
    if kind == "SECTION":
        return token
    if kind == "ARTICLE":
        return f"ARTICLE_{token.upper()}"
    if kind == "EXHIBIT":
        return f"EXHIBIT_{token.upper()}"
    if kind == "SCHEDULE":
        return f"SCHEDULE_{token.upper()}"
    return token


def extract_section_ids_from_list(s: str) -> list[str]:
    return re.findall(r"\d{1,3}(?:\.\d{1,3}){0,4}(?:\([a-z]\))?", s)


def extract_refs_from_section_text(text: str) -> List[Dict[str, Any]]:
    refs = []
    for m in RE_REF_SECTION.finditer(text):
        refs.append({
            "ref_type": "SECTION",
            "target_id": normalize_ref_target("SECTION", m.group(1)),
            "ref_text": m.group(0),
            "start": m.start(),
            "end": m.end()
        })
    for m in RE_REF_ARTICLE.finditer(text):
        refs.append({
            "ref_type": "ARTICLE",
            "target_id": normalize_ref_target("ARTICLE", m.group(1)),
            "ref_text": m.group(0),
            "start": m.start(),
            "end": m.end()
        })
    for m in RE_REF_EXHIBIT.finditer(text):
        refs.append({
            "ref_type": "EXHIBIT",
            "target_id": normalize_ref_target("EXHIBIT", m.group(1)),
            "ref_text": m.group(0),
            "start": m.start(),
            "end": m.end()
        })
    for m in RE_REF_SCHEDULE.finditer(text):
        refs.append({
            "ref_type": "SCHEDULE",
            "target_id": normalize_ref_target("SCHEDULE", m.group(1)),
            "ref_text": m.group(0),
            "start": m.start(),
            "end": m.end()
        })

    # New: plural list/range (captures first, and we parse rest)
    for m in RE_REF_SECTIONS_PLURAL.finditer(text):
        # This regex gives group(1) as first id; the rest are in the full match.
        full = m.group(0)
        start, end = m.start(), m.end()
        ids = re.findall(r"\d{1,3}(?:\.\d{1,3}){0,4}(?:\([a-z]\))?", full)
        for sid in ids:
            sid_norm = re.sub(r"\([a-z]\)$", "", sid)  # map 4.2(a) -> 4.2
            refs.append({"ref_type": "SECTION", "target_id": sid_norm, "ref_text": full, "start": start, "end": end})

    # New: cue-based bare references
    for m in RE_REF_BARE_NUM_WITH_CUE.finditer(text):
        sid = re.sub(r"\([a-z]\)$", "", m.group(1))
        refs.append({"ref_type": "SECTION", "target_id": sid, "ref_text": m.group(0), "start": m.start(), "end": m.end()})
    
    return refs


def resolve_target_fallback(target_id: str, node_index: dict[str, Any]) -> str | None:
    if target_id in node_index:
        return node_index[target_id].node_id
        
    # strip trailing letters like (a)
    stripped = re.sub(r"\([a-z]\)$", "", target_id)
    if stripped != target_id and stripped in node_index:
        return node_index[stripped].node_id
        
    # recursively chop dot separated parts
    parts = stripped.split('.')
    while len(parts) > 1:
        parts.pop()
        parent = ".".join(parts)
        if parent in node_index:
            return node_index[parent].node_id
            
    # if it's a bare number, check if the Article exists
    if len(parts) == 1 and parts[0].isdigit():
        article_id = f"ARTICLE_{parts[0]}"
        if article_id in node_index:
            return node_index[article_id].node_id
            
    return None


def build_reference_edges(sections: list[Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    node_index = {s.node_id: s for s in sections}
    for section in sections:
        canonical_id = getattr(section, "canonical_id", "")
        if canonical_id and canonical_id not in node_index:
            node_index[canonical_id] = section
    edges = []
    unresolved = []

    for s in sections:
        rs = extract_refs_from_section_text(s.text)
        for r in rs:
            if r["target_id"] in {s.node_id, getattr(s, "canonical_id", "")}:
                continue
            
            resolved_id = resolve_target_fallback(r["target_id"], node_index)
            if resolved_id:
                edges.append({
                    "from": s.node_id,
                    "to": resolved_id,
                    "ref_type": r["ref_type"],
                    "ref_text": r["ref_text"],
                    "ref_start": r["start"],
                    "ref_end": r["end"],
                    "resolved": True,
                })
            else:
                unresolved.append({
                    "from": s.node_id,
                    "target_id": r["target_id"],
                    "ref_type": r["ref_type"],
                    "ref_text": r["ref_text"],
                    "ref_start": r["start"],
                    "ref_end": r["end"],
                    "resolved": False,
                })

    return edges, unresolved
