from io import BytesIO
from pathlib import Path

import fitz
from docx import Document

from models.pipeline_state import ParsedPage


async def parse_document(file_bytes: bytes, filename: str) -> dict[str, int | str]:
    parsed = await parse_document_content(file_bytes, filename)
    return {"document_name": parsed["document_name"], "page_count": parsed["page_count"]}


async def parse_document_content(file_bytes: bytes, filename: str) -> dict[str, int | str | list[ParsedPage]]:
    suffix = Path(filename).suffix.lower()
    document_name = Path(filename).name

    if suffix == ".pdf":
        with fitz.open(stream=file_bytes, filetype="pdf") as pdf_document:
            page_count = pdf_document.page_count
            pages = [
                ParsedPage(page_number=index + 1, text=pdf_document.load_page(index).get_text("text").strip())
                for index in range(page_count)
            ]
    elif suffix == ".docx":
        document = Document(BytesIO(file_bytes))
        sections = len(document.sections) or 1
        page_count = max(sections, 1)
        paragraphs = [paragraph.text.strip() for paragraph in document.paragraphs if paragraph.text.strip()]
        if not paragraphs:
            paragraphs = ["Untitled DOCX document."]
        paragraphs_per_page = max(1, len(paragraphs) // page_count)
        pages = []
        for page_index in range(page_count):
            start = page_index * paragraphs_per_page
            end = None if page_index == page_count - 1 else (page_index + 1) * paragraphs_per_page
            page_text = "\n".join(paragraphs[start:end]).strip()
            pages.append(ParsedPage(page_number=page_index + 1, text=page_text or ""))
    elif suffix == ".txt":
        decoded = file_bytes.decode("utf-8", errors="ignore")
        lines = decoded.splitlines()
        line_count = len(lines)
        page_count = max(1, min(6, (line_count // 45) + 1))
        lines_per_page = max(1, len(lines) // page_count)
        pages = []
        for page_index in range(page_count):
            start = page_index * lines_per_page
            end = None if page_index == page_count - 1 else (page_index + 1) * lines_per_page
            page_text = "\n".join(lines[start:end]).strip()
            pages.append(ParsedPage(page_number=page_index + 1, text=page_text or ""))
    else:
        raise ValueError("Unsupported document type")

    full_text = "\n\n".join(page.text for page in pages if page.text).strip()
    return {
        "document_name": document_name,
        "page_count": page_count,
        "pages": pages,
        "full_text": full_text,
    }
