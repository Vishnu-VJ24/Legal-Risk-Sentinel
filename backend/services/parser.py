from io import BytesIO
from pathlib import Path

import fitz
from docx import Document


async def parse_document(file_bytes: bytes, filename: str) -> dict[str, int | str]:
    suffix = Path(filename).suffix.lower()
    document_name = Path(filename).name

    if suffix == ".pdf":
        with fitz.open(stream=file_bytes, filetype="pdf") as pdf_document:
            page_count = pdf_document.page_count
    elif suffix == ".docx":
        document = Document(BytesIO(file_bytes))
        sections = len(document.sections) or 1
        page_count = max(sections, 1)
    elif suffix == ".txt":
        line_count = len(file_bytes.decode("utf-8", errors="ignore").splitlines())
        page_count = max(1, min(6, (line_count // 45) + 1))
    else:
        raise ValueError("Unsupported document type")

    return {"document_name": document_name, "page_count": page_count}
