from __future__ import annotations

import re
from dataclasses import dataclass

from models.pipeline_state import DocumentChunk, ParsedPage


SECTION_HEADING_PATTERN = re.compile(
    r"^(ARTICLE\s+\d+|SECTION\s+\d+(?:\.\d+)*|\d+(?:\.\d+)+)\b[:.\-\s]*(.*)$",
    re.IGNORECASE | re.MULTILINE,
)


@dataclass
class SectionNode:
    node_id: str
    title: str
    level: int
    page_start: int
    page_end: int
    text: str
    parent_id: str | None = None


def build_section_tree(pages: list[ParsedPage]) -> list[SectionNode]:
    if not pages:
        return []

    sections: list[SectionNode] = []
    seen_ids: dict[str, int] = {}

    for page in pages:
        matches = list(SECTION_HEADING_PATTERN.finditer(page.text))
        if not matches:
            continue

        for index, match in enumerate(matches):
            start = match.start()
            end = matches[index + 1].start() if index + 1 < len(matches) else len(page.text)
            raw_id = match.group(1).strip().upper().replace(" ", "_")
            title_suffix = (match.group(2) or "").strip()
            body = page.text[start:end].strip()
            if len(body) < 40:
                continue

            occurrence = seen_ids.get(raw_id, 0) + 1
            seen_ids[raw_id] = occurrence
            node_id = raw_id if occurrence == 1 else f"{raw_id}__{occurrence}"

            if raw_id.startswith("ARTICLE") or raw_id.startswith("SECTION"):
                level = 1
            else:
                level = raw_id.count(".") + 1

            title_line = body.splitlines()[0].strip()
            title = title_suffix or title_line[:120]

            sections.append(
                SectionNode(
                    node_id=node_id,
                    title=title,
                    level=level,
                    page_start=page.page_number,
                    page_end=page.page_number,
                    text=body,
                )
            )

    stack: list[SectionNode] = []
    for section in sections:
        while stack and stack[-1].level >= section.level:
            stack.pop()
        if stack:
            section.parent_id = stack[-1].node_id
        stack.append(section)

    return sections


def find_chunk_section(chunk: DocumentChunk, sections: list[SectionNode]) -> SectionNode | None:
    for section in sections:
        if section.page_start <= chunk.page_number <= section.page_end and chunk.text[:80].strip() in section.text:
            return section
    for section in sections:
        if section.page_start == chunk.page_number:
            return section
    return None
