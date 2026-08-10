from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any


def sha256_text(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8", errors="ignore")).hexdigest()


def extract_all_json_candidates(text: str) -> list[tuple[dict, str]]:
    """
    Finds all structured dictionaries in a text block, prioritizing markdown fences
    and trailing iteratively matched JSON blocks for reasoning models.
    Returns [(parsed_dict, status_string), ...] in order of discovery.
    """
    text = text.strip()
    if not text:
        return []

    candidates = []

    # 0. Strip <think> reasoning blocks FIRST so all strategies work on clean text.
    #    Handles both closed <think>...</think> and unclosed trailing <think>...
    cleaned = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()
    # Handle unclosed <think> tag (model cut off mid-reasoning)
    cleaned = re.sub(r"<think>.*$", "", cleaned, flags=re.DOTALL).strip()

    # 1. Naked JSON (entire cleaned text is valid JSON)
    try:
        parsed = json.loads(cleaned)
        if isinstance(parsed, dict):
            candidates.append((parsed, "valid_json"))
    except Exception:
        pass

    # 2. Markdown fences
    matches = list(re.finditer(r"```(?:json)?\s*(\[.*?\]|\{.*?\})\s*```", cleaned, re.DOTALL))
    for m in matches:
        try:
            parsed = json.loads(m.group(1))
            if isinstance(parsed, dict) and parsed not in [c[0] for c in candidates]:
                candidates.append((parsed, "json_extracted_from_fences"))
        except Exception:
            pass

    # 3. Brace matching — find the outermost valid JSON object
    start_idx = cleaned.find("{")
    while start_idx != -1:
        # For each opening brace, try from the farthest closing brace inward
        end_idx = cleaned.rfind("}")
        while end_idx > start_idx:
            try:
                candidate_str = cleaned[start_idx:end_idx+1]
                parsed = json.loads(candidate_str)
                if isinstance(parsed, dict) and parsed not in [c[0] for c in candidates]:
                    candidates.append((parsed, "json_extracted_from_reasoning"))
                break  # Found the outermost valid match for this start
            except Exception:
                end_idx = cleaned.rfind("}", 0, end_idx)
        start_idx = cleaned.find("{", start_idx + 1)

    return candidates


def save_json(data: Any, path: str | Path) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)