from __future__ import annotations

import hashlib
import re
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Tuple

import fitz
import pdfplumber
import requests


def text_quality_score(s: str) -> Dict[str, float]:
    if not s:
        return {"printable_ratio": 0.0, "whitespace_ratio": 1.0, "avg_token_len": 0.0, "score": 0.0}
    printable = sum(ch.isprintable() for ch in s)
    whitespace = sum(ch.isspace() for ch in s)
    tokens = re.findall(r"\S+", s)
    avg_token_len = (sum(len(t) for t in tokens) / max(1, len(tokens))) if tokens else 0.0
    printable_ratio = printable / max(1, len(s))
    whitespace_ratio = whitespace / max(1, len(s))

    # Simple heuristic score (tweakable)
    score = 0.0
    score += 0.5 * printable_ratio
    score += 0.2 * (1.0 - min(whitespace_ratio, 0.9))  # too much whitespace is bad
    score += 0.3 * (1.0 if 2.0 <= avg_token_len <= 12.0 else 0.4)

    return {
        "printable_ratio": printable_ratio,
        "whitespace_ratio": whitespace_ratio,
        "avg_token_len": avg_token_len,
        "score": score
    }


def extract_with_pymupdf(pdf_path: str) -> List[Dict[str, Any]]:
    pages = []
    doc = fitz.open(pdf_path)
    for i in range(doc.page_count):
        page = doc.load_page(i)
        txt = page.get_text("text") or ""
        pages.append({"page_num": i+1, "text": txt, "char_count": len(txt)})
    doc.close()
    return pages

def extract_with_pdfplumber(pdf_path: str) -> List[Dict[str, Any]]:
    pages = []
    with pdfplumber.open(pdf_path) as pdf:
        for i, page in enumerate(pdf.pages):
            txt = page.extract_text() or ""
            pages.append({"page_num": i+1, "text": txt + "\n", "char_count": len(txt)})
    return pages


def build_full_text_and_offsets(pages: List[Dict[str, Any]]) -> Tuple[str, List[Dict[str, int]]]:
    """
    Concatenate page texts into full_text and compute page_offsets in full_text coordinates.
    """
    full_parts = []
    offsets = []
    cursor = 0
    for p in pages:
        t = p["text"] or ""
        full_parts.append(t)
        start = cursor
        cursor += len(t)
        end = cursor
        offsets.append({"page_num": p["page_num"], "start": start, "end": end})
    full_text = "".join(full_parts)
    return full_text, offsets


def _ocr_cache_path(pdf_path: str, cache_dir: str) -> Path:
    digest = hashlib.sha256(Path(pdf_path).read_bytes()).hexdigest()
    return Path(cache_dir) / f"{digest}.json"


def extract_with_ocr_space(pdf_path: str, api_key: str, cache_dir: str) -> tuple[List[Dict[str, Any]], bool]:
    """OCR full rendered pages individually and cache the combined page text."""
    cache_path = _ocr_cache_path(pdf_path, cache_dir)
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    if cache_path.exists():
        import json
        payload = json.loads(cache_path.read_text(encoding="utf-8"))
        return payload.get("pages", []), True

    with tempfile.TemporaryDirectory(prefix="legal-sentinel-ocr-") as tmp:
        prefix = str(Path(tmp) / "page")
        subprocess.run(
            ["pdftoppm", "-jpeg", "-r", "120", "-jpegopt", "quality=70", pdf_path, prefix],
            check=True,
            capture_output=True,
            text=True,
        )
        image_paths = sorted(Path(tmp).glob("page-*.jpg"))
        pages: List[Dict[str, Any]] = []
        for page_num, image_path in enumerate(image_paths, start=1):
            with image_path.open("rb") as handle:
                response = requests.post(
                    "https://api.ocr.space/parse/image",
                    files={"file": (image_path.name, handle, "image/jpeg")},
                    data={
                        "isOverlayRequired": False,
                        "apikey": api_key,
                        "language": "eng",
                        "OCREngine": 2,
                    },
                    timeout=120,
                )
            response.raise_for_status()
            payload = response.json()
            if payload.get("IsErroredOnProcessing"):
                raise RuntimeError(f"OCR.space failed on page {page_num}: {payload.get('ErrorMessage')}")
            parsed = payload.get("ParsedResults") or []
            text = "\n".join(item.get("ParsedText", "") for item in parsed).strip()
            pages.append({"page_num": page_num, "text": text + ("\n" if text else ""), "char_count": len(text)})

    import json
    cache_path.write_text(json.dumps({"pages": pages}, ensure_ascii=False), encoding="utf-8")
    return pages, False


def extract_pdf(
    pdf_path: str,
    *,
    ocr_space_api_key: str = "",
    ocr_cache_dir: str | None = None,
    ocr_min_text_chars: int = 500,
    ocr_enabled: bool = True,
) -> tuple[list[dict[str, Any]], str, list[dict[str, int]], dict[str, Any]]:
    pages_a = extract_with_pymupdf(pdf_path)
    full_a, offsets_a = build_full_text_and_offsets(pages_a)
    qa = text_quality_score(full_a)

    pages_b = extract_with_pdfplumber(pdf_path)
    full_b, offsets_b = build_full_text_and_offsets(pages_b)
    qb = text_quality_score(full_b)

    if qb["score"] > qa["score"] + 0.03:
        pages, full_text, page_offsets, extractor_used = pages_b, full_b, offsets_b, "pdfplumber"
    else:
        pages, full_text, page_offsets, extractor_used = pages_a, full_a, offsets_a, "pymupdf"

    ocr_used = False
    ocr_cache_hit = False
    ocr_error = ""
    if ocr_enabled and len(full_text.strip()) < ocr_min_text_chars and ocr_space_api_key:
        try:
            pages, ocr_cache_hit = extract_with_ocr_space(
                pdf_path,
                ocr_space_api_key,
                ocr_cache_dir or str(Path("/tmp") / "legal-sentinel-ocr-text"),
            )
            full_text, page_offsets = build_full_text_and_offsets(pages)
            extractor_used = "ocr_space"
            ocr_used = True
        except Exception as exc:
            ocr_error = str(exc)
            print(f"Warning: OCR fallback failed: {ocr_error}")

    meta = {
        "extractor_used": extractor_used,
        "quality_pymupdf": qa,
        "quality_pdfplumber": qb,
        "num_pages": len(pages),
        "ocr_used": ocr_used,
        "ocr_cache_hit": ocr_cache_hit,
        "ocr_error": ocr_error,
    }
    print("✅ Extraction complete")
    print("Extractor used:", extractor_used)
    print("Pages:", len(pages))
    print("Quality (pymupdf):", qa)
    print("Quality (pdfplumber):", qb)
    # print("\n--- Preview page 1 ---\n", (pages[0]["text"] or "")[:600])
    return pages, full_text, page_offsets, meta
