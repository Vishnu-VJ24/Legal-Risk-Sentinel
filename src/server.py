"""
FastAPI backend server for the Contract Analysis pipeline.
Handles PDF uploads, runs the pipeline with progress tracking,
and serves the built frontend in production deployments.
"""
from __future__ import annotations

import shutil
import threading
import time
import uuid
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Optional

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import (
    FileResponse,
    JSONResponse,
    PlainTextResponse,
    Response,
    StreamingResponse,
)
from pydantic import BaseModel

from .artifacts import (
    ARTIFACTS,
    artifact_path,
    read_json,
    write_json_atomic,
)
from .chat_agent import stream_chat_impl
from .config import get_settings
from .pipeline import run_pipeline_with_progress

SERVER_SETTINGS = get_settings()
REPO_ROOT = Path(__file__).resolve().parent.parent
FRONTEND_DIST_DIR = REPO_ROOT / "frontend" / "dist"
APP_DATA_DIR = Path(SERVER_SETTINGS.app_data_dir)
UPLOAD_DIR = APP_DATA_DIR / "uploads"
RUNS_DIR = APP_DATA_DIR / "runs"
MAX_UPLOAD_BYTES = SERVER_SETTINGS.max_upload_mb * 1024 * 1024
MANIFEST_FILENAME = "job_status.json"


@dataclass
class JobStatus:
    run_id: str
    file_name: str
    stage: str = "UPLOADED"
    status: str = "running"
    error: Optional[str] = None
    out_dir: str = ""
    upload_path: str = ""
    created_at: float = 0.0
    updated_at: float = 0.0
    stage_detail: str = ""
    stage_progress: dict[str, Any] | None = None
    cancel_flag: bool = False

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "JobStatus":
        return cls(
            run_id=str(data.get("run_id", "")),
            file_name=str(data.get("file_name", "")),
            stage=str(data.get("stage", "UPLOADED")),
            status=str(data.get("status", "error")),
            error=data.get("error"),
            out_dir=str(data.get("out_dir", "")),
            upload_path=str(data.get("upload_path", "")),
            created_at=float(data.get("created_at", time.time())),
            updated_at=float(data.get("updated_at", time.time())),
            stage_detail=str(data.get("stage_detail", "")),
            stage_progress=data.get("stage_progress") if isinstance(data.get("stage_progress"), dict) else None,
            cancel_flag=bool(data.get("cancel_flag", False)),
        )


_jobs: dict[str, JobStatus] = {}
_jobs_lock = threading.Lock()
STAGE_ORDER = [
    "UPLOADED",
    "EXTRACTED",
    "SECTIONS_BUILT",
    "GRAPH_READY",
    "RISKS_ANALYZED",
    "REPORT_READY",
]


app = FastAPI(title="Legal AI Review", version="1.1.0")

if SERVER_SETTINGS.cors_allow_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(SERVER_SETTINGS.cors_allow_origins),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )


class ChatRequest(BaseModel):
    messages: list[dict]
    model_id: str | None = None


def _ensure_runtime_dirs() -> None:
    for path in (APP_DATA_DIR, UPLOAD_DIR, RUNS_DIR):
        path.mkdir(parents=True, exist_ok=True)


def _run_dir(run_id: str) -> Path:
    return RUNS_DIR / run_id


def _upload_path(run_id: str) -> Path:
    return UPLOAD_DIR / f"{run_id}.pdf"


def _manifest_path(run_id: str) -> Path:
    return _run_dir(run_id) / MANIFEST_FILENAME


def _save_job(job: JobStatus) -> None:
    run_dir = Path(job.out_dir) if job.out_dir else _run_dir(job.run_id)
    run_dir.mkdir(parents=True, exist_ok=True)
    job.out_dir = str(run_dir)
    if not job.upload_path:
        job.upload_path = str(_upload_path(job.run_id))
    write_json_atomic(_manifest_path(job.run_id), asdict(job))


def _remember_job(job: JobStatus) -> JobStatus:
    with _jobs_lock:
        _jobs[job.run_id] = job
    return job


def _load_job_from_disk(run_id: str) -> JobStatus | None:
    manifest_path = _manifest_path(run_id)
    if not manifest_path.exists():
        return None
    try:
        payload = read_json(manifest_path)
    except OSError:
        return None
    if not isinstance(payload, dict):
        return None

    job = JobStatus.from_dict(payload)
    if not job.out_dir:
        job.out_dir = str(_run_dir(run_id))
    if not job.upload_path:
        job.upload_path = str(_upload_path(run_id))
    return job


def _recover_job_if_needed(job: JobStatus) -> JobStatus:
    if job.status == "running":
        job.status = "error"
        job.error = "Server restarted while analysis was running."
        job.stage_detail = "Previous analysis was interrupted by an app restart."
        job.stage_progress = None
        job.cancel_flag = False
        job.updated_at = time.time()
        _save_job(job)
    return job


def _get_job(run_id: str) -> JobStatus | None:
    with _jobs_lock:
        existing = _jobs.get(run_id)
    if existing:
        return existing

    loaded = _load_job_from_disk(run_id)
    if not loaded:
        return None
    return _remember_job(_recover_job_if_needed(loaded))


def _safe_load_json(path: Path) -> Any | None:
    return read_json(path)


def _resolve_run_dir(run_id: str, job: JobStatus | None = None) -> Path:
    if job and job.out_dir:
        return Path(job.out_dir)
    return _run_dir(run_id)


def _artifact_path(run_id: str, filename: str) -> Path:
    return _resolve_run_dir(run_id, _get_job(run_id)) / filename


def _delete_run_artifacts(run_id: str) -> None:
    with _jobs_lock:
        _jobs.pop(run_id, None)

    run_dir = _run_dir(run_id)
    upload_path = _upload_path(run_id)
    if run_dir.exists():
        shutil.rmtree(run_dir, ignore_errors=True)
    if upload_path.exists():
        upload_path.unlink(missing_ok=True)


def _cleanup_stale_runs() -> None:
    _ensure_runtime_dirs()
    cutoff = time.time() - (SERVER_SETTINGS.run_ttl_hours * 3600)

    for run_dir in RUNS_DIR.iterdir():
        if not run_dir.is_dir():
            continue

        run_id = run_dir.name
        manifest = _safe_load_json(run_dir / MANIFEST_FILENAME)
        updated_at = run_dir.stat().st_mtime
        status = None

        if isinstance(manifest, dict):
            updated_at = float(manifest.get("updated_at", updated_at))
            status = manifest.get("status")

        if updated_at >= cutoff:
            continue
        if status == "running":
            continue

        _delete_run_artifacts(run_id)

    for upload_path in UPLOAD_DIR.glob("*.pdf"):
        if upload_path.stat().st_mtime >= cutoff:
            continue
        run_id = upload_path.stem
        if _run_dir(run_id).exists():
            continue
        upload_path.unlink(missing_ok=True)


def _restore_jobs_from_disk() -> None:
    _ensure_runtime_dirs()
    for manifest_path in RUNS_DIR.glob(f"*/{MANIFEST_FILENAME}"):
        try:
            payload = read_json(manifest_path)
        except OSError:
            continue
        if not isinstance(payload, dict):
            continue
        job = _recover_job_if_needed(JobStatus.from_dict(payload))
        if not job.run_id:
            continue
        if not job.out_dir:
            job.out_dir = str(manifest_path.parent)
        if not job.upload_path:
            job.upload_path = str(_upload_path(job.run_id))
        _remember_job(job)


def _build_status_payload(job: JobStatus) -> dict[str, Any]:
    stage_idx = STAGE_ORDER.index(job.stage) if job.stage in STAGE_ORDER else 0
    stage_total = len(STAGE_ORDER)
    stage_number = stage_idx + 1

    out_dir = Path(job.out_dir)
    sections_path = artifact_path(out_dir, ARTIFACTS.sections)
    edges_path = artifact_path(out_dir, ARTIFACTS.edges)
    partial_risks_path = artifact_path(out_dir, ARTIFACTS.partial_risks)
    final_risks_path = artifact_path(out_dir, ARTIFACTS.risks)
    report_json_path = artifact_path(out_dir, ARTIFACTS.report_json)
    report_markdown_path = artifact_path(out_dir, ARTIFACTS.report_markdown)
    sections = _safe_load_json(sections_path)
    edges = _safe_load_json(edges_path)
    risks = _safe_load_json(final_risks_path)
    report = _safe_load_json(report_json_path)
    risk_progress = _safe_load_json(
        artifact_path(out_dir, ARTIFACTS.risk_progress)
    )

    total_sections = len(sections) if isinstance(sections, list) else None
    total_edges = len(edges) if isinstance(edges, list) else None

    flagged_sections = None
    top_risk_preview = None
    if isinstance(risks, list):
        flagged_items = [item for item in risks if isinstance(item, dict) and item.get("risk_flags")]
        flagged_sections = len(flagged_items)

    if isinstance(report, dict):
        overall_risk = report.get("overall_risk_score") or report.get("overall_document_risk")
        raw_top_risks = report.get("top_risks")
        if isinstance(raw_top_risks, list):
            preview = []
            for item in raw_top_risks[:3]:
                if not isinstance(item, dict):
                    continue
                preview.append(
                    {
                        "section_id": item.get("section_id"),
                        "title": item.get("title"),
                        "severity": item.get("severity"),
                        "summary": item.get("summary"),
                    }
                )
            top_risk_preview = preview or None
    else:
        overall_risk = None

    if top_risk_preview is None and isinstance(risks, list):
        preview = []
        for item in risks:
            if not isinstance(item, dict):
                continue
            flags = item.get("risk_flags")
            if not isinstance(flags, list) or not flags:
                continue
            first_flag = flags[0] if isinstance(flags[0], dict) else {}
            preview.append(
                {
                    "section_id": item.get("section_id"),
                    "title": item.get("title"),
                    "severity": first_flag.get("severity"),
                    "summary": first_flag.get("rationale"),
                }
            )
            if len(preview) == 3:
                break
        top_risk_preview = preview or None

    artifact_warnings: list[str] = []
    if job.status == "complete":
        if not report_markdown_path.exists():
            artifact_warnings.append(
                "Analysis completed, but the executive Markdown report is unavailable."
            )
        if not report_json_path.exists() or not isinstance(report, dict):
            artifact_warnings.append(
                "Analysis completed, but report summary metadata is unavailable."
            )

    return {
        "run_id": job.run_id,
        "file_name": job.file_name,
        "stage": job.stage,
        "status": job.status,
        "error": job.error,
        "stage_detail": job.stage_detail,
        "stage_index": stage_number,
        "stage_total": stage_total,
        "progress_percent": round((stage_number / stage_total) * 100),
        "stage_progress": job.stage_progress,
        "total_sections": total_sections,
        "total_edges": total_edges,
        "flagged_sections": flagged_sections,
        "overall_risk": overall_risk,
        "top_risk_preview": top_risk_preview,
        "sections_ready": sections_path.exists(),
        "edges_ready": edges_path.exists(),
        "risks_ready": partial_risks_path.exists() or final_risks_path.exists(),
        "report_ready": report_markdown_path.exists(),
        "artifact_warnings": artifact_warnings,
        "edges_revision": int(edges_path.stat().st_mtime_ns) if edges_path.exists() else 0,
        "risk_revision": int(risk_progress.get("revision", 0)) if isinstance(risk_progress, dict) else (len(risks) if isinstance(risks, list) else 0),
        "risk_groups_completed": int(risk_progress.get("completed", 0)) if isinstance(risk_progress, dict) else (len(risks) if isinstance(risks, list) else 0),
        "risk_groups_total": int(risk_progress.get("total", 0)) if isinstance(risk_progress, dict) else (len(risks) if isinstance(risks, list) else 0),
    }


def _serve_json_artifact(run_id: str, filename: str) -> JSONResponse:
    job = _get_job(run_id)
    path = _artifact_path(run_id, filename)
    if job is None and not path.exists():
        raise HTTPException(status_code=404, detail="Run not found.")
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"{filename} not ready yet.")
    data = read_json(path)
    if data is None:
        raise HTTPException(status_code=500, detail=f"{filename} is not valid JSON.")
    return JSONResponse(content=data, headers={"Cache-Control": "no-store"})


def _serve_frontend(path: str = "") -> Response:
    index_path = FRONTEND_DIST_DIR / "index.html"
    if not index_path.exists():
        return PlainTextResponse(
            "Frontend build not found. Run `npm run build` inside /frontend before starting the production server.",
            status_code=503,
        )

    if path:
        candidate = (FRONTEND_DIST_DIR / path).resolve()
        if candidate.is_relative_to(FRONTEND_DIST_DIR.resolve()) and candidate.is_file():
            return FileResponse(candidate)

    return FileResponse(index_path)


def _run_pipeline_thread(run_id: str, pdf_path: str, out_dir: str) -> None:
    job = _jobs[run_id]

    def on_progress(stage: str, detail: str = "", progress: dict[str, Any] | None = None) -> None:
        job.stage = stage
        job.stage_detail = detail
        job.stage_progress = progress
        job.updated_at = time.time()
        _save_job(job)

    def check_cancel() -> None:
        if job.cancel_flag:
            raise Exception("Pipeline cancelled by user.")

    try:
        run_pipeline_with_progress(
            pdf_path=pdf_path,
            out_dir=out_dir,
            progress_callback=on_progress,
            check_cancel=check_cancel,
        )
        job.status = "complete"
        job.stage = "REPORT_READY"
        job.stage_detail = "Analysis complete."
        job.stage_progress = None
        job.updated_at = time.time()
        _save_job(job)
    except Exception as exc:
        job.status = "error"
        job.error = str(exc)
        job.stage_detail = f"Pipeline failed: {exc}"
        job.stage_progress = None
        job.updated_at = time.time()
        _save_job(job)
        print(f"Pipeline error for run {run_id}: {exc}")


@app.on_event("startup")
async def startup_event() -> None:
    _ensure_runtime_dirs()
    _cleanup_stale_runs()
    _restore_jobs_from_disk()


@app.get("/healthz")
async def healthz() -> dict[str, Any]:
    _ensure_runtime_dirs()
    return {
        "status": "ok",
        "frontend_built": FRONTEND_DIST_DIR.joinpath("index.html").exists(),
        "app_data_dir": str(APP_DATA_DIR),
        "active_jobs": sum(1 for job in _jobs.values() if job.status == "running"),
    }


@app.post("/api/upload")
async def upload_pdf(file: UploadFile = File(...)) -> dict[str, str]:
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are accepted.")

    _cleanup_stale_runs()

    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Uploaded PDF is empty.")
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"Uploaded file exceeds the {SERVER_SETTINGS.max_upload_mb} MB limit.",
        )

    run_id = uuid.uuid4().hex[:12]
    now = time.time()
    upload_path = _upload_path(run_id)
    run_out_dir = _run_dir(run_id)

    _ensure_runtime_dirs()
    run_out_dir.mkdir(parents=True, exist_ok=True)
    upload_path.write_bytes(content)

    job = JobStatus(
        run_id=run_id,
        file_name=file.filename,
        stage="UPLOADED",
        status="running",
        out_dir=str(run_out_dir),
        upload_path=str(upload_path),
        created_at=now,
        updated_at=now,
        stage_detail="PDF received, starting pipeline...",
    )
    _remember_job(job)
    _save_job(job)

    thread = threading.Thread(
        target=_run_pipeline_thread,
        args=(run_id, str(upload_path), str(run_out_dir)),
        daemon=True,
    )
    thread.start()

    return {"run_id": run_id, "file_name": file.filename, "status": "running"}


@app.get("/api/status/{run_id}")
async def get_status(run_id: str) -> JSONResponse:
    job = _get_job(run_id)
    if not job:
        raise HTTPException(status_code=404, detail="Run not found.")
    return JSONResponse(content=_build_status_payload(job), headers={"Cache-Control": "no-store"})


@app.post("/api/cancel/{run_id}")
async def cancel_run(run_id: str) -> dict[str, str]:
    job = _get_job(run_id)
    if not job:
        raise HTTPException(status_code=404, detail="Run not found.")
    if job.status == "complete":
        return {"status": "already_complete"}

    job.cancel_flag = True
    job.status = "error"
    job.error = "Pipeline cancelled by user."
    job.stage_detail = "Process stopped."
    job.stage_progress = None
    job.updated_at = time.time()
    _save_job(job)
    return {"status": "cancelled"}


@app.get("/api/results/{run_id}/sections")
async def get_sections(run_id: str) -> JSONResponse:
    return _serve_json_artifact(run_id, ARTIFACTS.sections)


@app.get("/api/results/{run_id}/edges")
async def get_edges(run_id: str) -> JSONResponse:
    return _serve_json_artifact(run_id, ARTIFACTS.edges)


@app.get("/api/results/{run_id}/risks")
async def get_risks(run_id: str) -> JSONResponse:
    final_path = _artifact_path(run_id, ARTIFACTS.risks)
    if not final_path.exists():
        return _serve_json_artifact(run_id, ARTIFACTS.partial_risks)
    return _serve_json_artifact(run_id, ARTIFACTS.risks)


@app.get("/api/results/{run_id}/report-json")
async def get_report_json(run_id: str) -> JSONResponse:
    return _serve_json_artifact(run_id, ARTIFACTS.report_json)


@app.get("/api/results/{run_id}/report-md")
async def get_report_md(run_id: str) -> PlainTextResponse:
    path = _artifact_path(run_id, ARTIFACTS.report_markdown)
    if not path.exists():
        raise HTTPException(status_code=404, detail="Report not ready yet.")
    return PlainTextResponse(
        path.read_text(encoding="utf-8"),
        headers={"Cache-Control": "no-store"},
    )


@app.get("/api/chat/models")
async def get_chat_models() -> dict[str, Any]:
    settings = get_settings()
    return {
        "models": [
            {
                "id": model.id,
                "model": model.model,
                "attribute": model.attribute,
                "display_name": model.display_name,
                "assistant_name": model.assistant_name,
                "max_tokens": model.max_tokens,
            }
            for model in settings.chat_models
        ],
        "default_model_id": settings.chat_models[0].id if settings.chat_models else None,
    }


@app.post("/api/chat/{run_id}/stream")
async def chat_stream(run_id: str, req: ChatRequest) -> StreamingResponse:
    out_dir = _resolve_run_dir(run_id, _get_job(run_id))
    if not out_dir.exists():
        raise HTTPException(status_code=404, detail="Run not found on disk.")

    settings = get_settings()
    selected_model = settings.chat_models[0] if settings.chat_models else None
    if req.model_id:
        selected_model = next((item for item in settings.chat_models if item.id == req.model_id), selected_model)
    if selected_model is None:
        raise HTTPException(status_code=500, detail="No chat models are configured.")

    return StreamingResponse(
        stream_chat_impl(
            run_id=run_id,
            out_dir=str(out_dir),
            messages=req.messages,
            api_key=settings.nvidia_api_key,
            model=selected_model.model,
            model_attribute=selected_model.attribute,
            max_tokens=selected_model.max_tokens,
        ),
        media_type="text/event-stream",
    )


@app.get("/", include_in_schema=False)
async def serve_root() -> Response:
    return _serve_frontend()


@app.get("/{full_path:path}", include_in_schema=False)
async def serve_frontend_routes(full_path: str) -> Response:
    if full_path.startswith("api/"):
        raise HTTPException(status_code=404, detail="Not found")
    return _serve_frontend(full_path)
