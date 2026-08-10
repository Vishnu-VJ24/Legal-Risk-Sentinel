from __future__ import annotations

import re

HEADING_START = re.compile(r"^\s*(Article\b|ARTICLE\b|Section\b|SECTION\b|\d{1,3}(\.\d{1,3}){0,4}\b)", re.I)


def looks_like_heading(line: str) -> bool:
    return bool(HEADING_START.match((line or "").strip()))

def normalize_text(text: str) -> str:
    # normalize newlines
    t = text.replace("\r\n", "\n").replace("\r", "\n")

    lines = t.split("\n")
    new_lines = []
    i = 0
    while i < len(lines):
        line = lines[i].rstrip()
        if not line:
            new_lines.append("")
            i += 1
            continue

        # Conservative "soft wrap" fix:
        # If this line doesn't end in punctuation and next line starts lowercase, join with space.
        if i+1 < len(lines):
            next_line = lines[i+1].lstrip()
            if next_line and next_line[:1].islower():
                if not re.search(r"[.;:!?]\s*$", line):
                    line = line + " " + next_line
                    i += 2
                    new_lines.append(line)
                    continue

        new_lines.append(line)
        i += 1

    # collapse excessive whitespace inside lines but preserve blank lines
    cleaned = []
    for ln in new_lines:
        if ln.strip() == "":
            cleaned.append("")
        else:
            cleaned.append(re.sub(r"[ \t]+", " ", ln).strip())

    return "\n".join(cleaned)


def normalize_pages(pages: list[dict]) -> list[dict]:
    """Normalize each page independently so text offsets remain page-accurate."""
    normalized = []
    for page in pages:
        text = normalize_text(page.get("text", ""))
        if text and not text.endswith("\n"):
            text += "\n"
        normalized.append({**page, "text": text, "char_count": len(text)})
    return normalized
