from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List, Optional, Tuple

from .io_utils import sha256_text


@dataclass
class SectionNode:
    node_id: str
    title: str
    level: int
    raw_heading: str
    start_char: int
    end_char: int
    text: str
    page_start: int = -1
    page_end: int = -1
    char_len: int = 0
    word_count: int = 0
    sha256: str = ""
    parent_id: Optional[str] = None
    canonical_id: str = ""
    node_type: str = "section"
    is_analysis_unit: bool = True
    duplicate_of: Optional[str] = None


RE_NUM_HEADING2 = re.compile(
    r"^\s*(\d{1,3}(?:\.\d{1,3}){0,4})(?![,:;])\s*(?:[.)]|[-–:])?\s+(.+?)\s*$"
)
RE_ARTICLE2 = re.compile(r"^\s*ARTICLE\s+((?:[IVXLC]+)|(?:\d{1,3}))\.?\s*[-–:]*\s*(.*)\s*$", re.I)
RE_SECTION2 = re.compile(r"^\s*SECTION\s+(\d{1,3}(?:\.\d{1,3}){0,4})(?![,:;])\.?\s*[-–:]?\s*(.*)\s*$", re.I)
RE_EXH2 = re.compile(r"^\s*EXHIBIT\s+([A-Z0-9]+(?:\.[A-Z0-9]+)*)\s*[-–:]*\s*(.*)\s*$", re.I)
RE_SCH2 = re.compile(r"^\s*SCHEDULE\s+([A-Z0-9]+(?:\.[A-Z0-9]+)*)\s*[-–:]*\s*(.*)\s*$", re.I)
RE_PARA = re.compile(r"^\s*\(([a-z]|[ivxlcdm]+)\)\s+(.+?)\s*$", re.I)


def is_likely_heading(num_id: str, title: str) -> bool:
    title = title.strip()
    if not title or len(title) > 220:
        return False
    if "." in num_id:
        return bool(re.search(r"[A-Za-z]", title))
    words = re.findall(r"[A-Za-z]+", title)
    if not words or len(words) > 30:
        return False
    return title.endswith(":") or len(title) <= 80 or sum(w[0].isupper() for w in words) / len(words) >= 0.2


def is_likely_explicit_section_heading(num_id: str, title: str) -> bool:
    if not title.strip():
        return True
    return is_likely_heading(num_id, title) and bool(re.match(r"[A-Z]", title.strip()))


def canon_id_from_heading(line: str) -> Tuple[Optional[str], Optional[str], int, str]:
    line = line.strip()
    if not line:
        return None, None, -1, ""
    for pattern, prefix, level in ((RE_EXH2, "EXHIBIT_", 0), (RE_SCH2, "SCHEDULE_", 0), (RE_ARTICLE2, "ARTICLE_", 0)):
        match = pattern.match(line)
        if match:
            token, tail = match.group(1).upper(), (match.group(2) or "").strip()
            canonical = f"{prefix}{token}"
            return canonical, tail or canonical.replace("_", " "), level, line
    match = RE_SECTION2.match(line)
    if match:
        sid, tail = match.group(1), (match.group(2) or "").strip()
        if is_likely_explicit_section_heading(sid, tail):
            return sid, tail or f"SECTION {sid}", sid.count(".") + 1, line
    match = RE_NUM_HEADING2.match(line)
    if match:
        sid, title = match.group(1), match.group(2).strip()
        if is_likely_heading(sid, title):
            return sid, title, sid.count(".") + 1, line
    return None, None, -1, ""


def _make_node(**kwargs) -> SectionNode:
    node = SectionNode(**kwargs)
    node.char_len = len(node.text)
    node.word_count = len(re.findall(r"\S+", node.text))
    node.sha256 = sha256_text(node.text)
    return node


def _unique_id(canonical_id: str, counts: dict[str, int]) -> tuple[str, Optional[str]]:
    counts[canonical_id] = counts.get(canonical_id, 0) + 1
    occurrence = counts[canonical_id]
    return (canonical_id if occurrence == 1 else f"{canonical_id}__{occurrence}", canonical_id if occurrence > 1 else None)


def _node_type(canonical_id: str) -> str:
    if canonical_id.startswith("ARTICLE_"):
        return "article"
    if canonical_id.startswith("EXHIBIT_"):
        return "exhibit"
    if canonical_id.startswith("SCHEDULE_"):
        return "schedule"
    return "section"


def extract_sections_from_text(text: str) -> List[SectionNode]:
    """Build lossless, ordered analysis units from explicit line headings.

    Every source interval is represented exactly once: preamble text is retained as a
    node, and each heading owns the text up to the next heading.
    """
    lines = text.split("\n")
    line_spans, cursor = [], 0
    for line in lines:
        line_spans.append((cursor, line))
        cursor += len(line) + 1

    headings = []
    for idx, (start, line) in enumerate(line_spans):
        canonical_id, title, level, raw = canon_id_from_heading(line)
        if canonical_id:
            headings.append({"idx": idx, "start": start, "canonical_id": canonical_id, "title": title, "level": level, "raw": raw})
    if not headings:
        return []

    nodes: List[SectionNode] = []
    if headings[0]["start"] > 0 and text[:headings[0]["start"]].strip():
        nodes.append(_make_node(node_id="PREAMBLE_001", canonical_id="PREAMBLE_001", title="Preamble", level=0,
                                raw_heading="", start_char=0, end_char=headings[0]["start"], text=text[:headings[0]["start"]].strip("\n"), node_type="preamble"))

    counts: dict[str, int] = {}
    stack: list[tuple[int, str]] = []
    for index, heading in enumerate(headings):
        start = heading["start"]
        end = headings[index + 1]["start"] if index + 1 < len(headings) else len(text)
        canonical_id = heading["canonical_id"]
        node_id, duplicate_of = _unique_id(canonical_id, counts)
        while stack and stack[-1][0] >= heading["level"]:
            stack.pop()
        parent_id = stack[-1][1] if stack else None
        node = _make_node(node_id=node_id, canonical_id=canonical_id, title=heading["title"], level=heading["level"],
                          raw_heading=heading["raw"], start_char=start, end_char=end, text=text[start:end].strip("\n"),
                          parent_id=parent_id, node_type=_node_type(canonical_id), duplicate_of=duplicate_of)
        nodes.append(node)
        stack.append((heading["level"], node_id))
    return nodes


def fallback_chunks(text: str, chunk_chars: int = 9000, overlap: int = 0) -> List[SectionNode]:
    """Lossless fallback chunks. Overlap is intentionally disabled for coverage metrics."""
    nodes, start, counter = [], 0, 1
    while start < len(text):
        end = min(len(text), start + chunk_chars)
        nodes.append(_make_node(node_id=f"CHUNK_{counter:03d}", canonical_id=f"CHUNK_{counter:03d}", title=f"Chunk {counter}",
                                level=99, raw_heading="", start_char=start, end_char=end, text=text[start:end].strip("\n"), node_type="chunk"))
        start, counter = end, counter + 1
    return nodes


def _split_paragraph_children(node: SectionNode) -> list[SectionNode]:
    """Split a node only when line-start paragraph labels form a real sequence."""
    offsets, cursor = [], 0
    for line in node.text.split("\n"):
        match = RE_PARA.match(line)
        if match:
            offsets.append((cursor, match.group(1), match.group(2)))
        cursor += len(line) + 1
    if len(offsets) < 2:
        return [node]
    children: list[SectionNode] = []
    if node.text[:offsets[0][0]].strip():
        intro_text = node.text[:offsets[0][0]].strip("\n")
        children.append(_make_node(node_id=f"{node.node_id}__intro", canonical_id=f"{node.canonical_id or node.node_id}__intro",
                                   title=f"{node.title} (intro)", level=node.level + 1, raw_heading=node.raw_heading,
                                   start_char=node.start_char, end_char=node.start_char + offsets[0][0], text=intro_text,
                                   parent_id=node.node_id, node_type="subclause_intro"))
    for index, (relative_start, token, title) in enumerate(offsets):
        relative_end = offsets[index + 1][0] if index + 1 < len(offsets) else len(node.text)
        canonical = f"{node.canonical_id or node.node_id}({token.lower()})"
        children.append(_make_node(node_id=canonical, canonical_id=canonical, title=title[:100], level=node.level + 1,
                                   raw_heading=node.text[relative_start:relative_start + len(node.text[relative_start:].split("\n", 1)[0])],
                                   start_char=node.start_char + relative_start, end_char=node.start_char + relative_end,
                                   text=node.text[relative_start:relative_end].strip("\n"), parent_id=node.node_id, node_type="subclause"))
    return children


def recover_subclauses_deterministically(nodes: list[SectionNode]) -> list[SectionNode]:
    """Recover paragraph subclauses without discarding the parent text interval."""
    repaired: list[SectionNode] = []
    for node in nodes:
        children = _split_paragraph_children(node)
        if len(children) == 1:
            repaired.append(node)
            continue
        node.is_analysis_unit = False
        repaired.append(node)
        repaired.extend(children)
    return repaired


def map_char_to_page(char_idx: int, page_offsets: list[dict[str, int]]) -> int:
    for offset in page_offsets:
        if offset["start"] <= char_idx < offset["end"]:
            return offset["page_num"]
    return page_offsets[-1]["page_num"] if page_offsets else -1


def map_sections_to_pages(sections: list[SectionNode], page_offsets: list[dict[str, int]]) -> list[SectionNode]:
    for section in sections:
        section.page_start = map_char_to_page(section.start_char, page_offsets)
        section.page_end = map_char_to_page(max(section.start_char, section.end_char - 1), page_offsets)
    return sections
