import asyncio
from time import perf_counter
from uuid import uuid4

from fastapi import APIRouter, File, HTTPException, UploadFile, status

from models.schemas import AnalyzeResponse, ResultsResponse
from services.mock_pipeline import build_mock_results
from services.parser import parse_document

router = APIRouter(tags=["analysis"])

ALLOWED_TYPES = {".pdf", ".docx", ".txt"}
MAX_FILE_SIZE = 10 * 1024 * 1024
SESSION_STORE: dict[str, ResultsResponse] = {}
IN_PROGRESS: set[str] = set()


async def _run_pipeline(session_id: str, filename: str, file_bytes: bytes) -> None:
    started = perf_counter()
    try:
        await asyncio.sleep(1)
        metadata = await parse_document(file_bytes, filename)
        await asyncio.sleep(2)
        await asyncio.sleep(2)
        await asyncio.sleep(3)
        results = build_mock_results(session_id, str(metadata["document_name"]), int(metadata["page_count"]))
        results.processing_time_seconds = round(perf_counter() - started, 1)
        SESSION_STORE[session_id] = results
    finally:
        IN_PROGRESS.discard(session_id)


@router.post("/analyze", response_model=AnalyzeResponse, status_code=status.HTTP_202_ACCEPTED)
async def analyze_document(file: UploadFile = File(...)) -> AnalyzeResponse:
    suffix = file.filename[file.filename.rfind(".") :].lower() if file.filename else ""
    if suffix not in ALLOWED_TYPES:
        raise HTTPException(status_code=400, detail="Unsupported file type. Please upload PDF, DOCX, or TXT.")

    file_bytes = await file.read()
    if len(file_bytes) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="File exceeds 10MB limit.")

    session_id = str(uuid4())
    IN_PROGRESS.add(session_id)
    asyncio.create_task(_run_pipeline(session_id, file.filename or "document", file_bytes))

    return AnalyzeResponse(
        session_id=session_id,
        status="processing",
        pipeline_stage="parsing",
        progress_pct=5,
    )


@router.get("/results/{session_id}", response_model=ResultsResponse)
async def get_results(session_id: str) -> ResultsResponse:
    if session_id in SESSION_STORE:
        return SESSION_STORE[session_id]
    if session_id in IN_PROGRESS:
        raise HTTPException(status_code=status.HTTP_202_ACCEPTED, detail="Analysis still processing.")
    raise HTTPException(status_code=404, detail="Session not found.")
