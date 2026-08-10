from __future__ import annotations

import json
import threading
from dataclasses import asdict
from pathlib import Path
from typing import Any, Callable, Optional

from .aggregation import aggregate_edges_raw
from .artifacts import ARTIFACTS, artifact_path, write_json_atomic, write_text_atomic
from .clause_repair import run_llm_clause_repair
from .config import get_settings
from .extraction import build_full_text_and_offsets, extract_pdf
from .llm_verify import run_llm_graph_verification
from .normalization import normalize_pages
from .references import build_reference_edges
from .report_generator import run_report_generator

# Added for Progressive RAG Indexing
from .retrieval import index_report, index_risks, index_sections
from .risk_analyzer import (
    build_risk_group_ownership,
    build_risk_groups,
    remap_edges_to_risk_groups,
    risk_group_cache_key,
    run_risk_analyzer,
)
from .sections import (
    extract_sections_from_text,
    fallback_chunks,
    map_sections_to_pages,
    recover_subclauses_deterministically,
)


def run_pipeline_with_progress(
    pdf_path: str,
    out_dir: str,
    progress_callback: Optional[Callable[[str, str, Optional[dict[str, Any]]], None]] = None,
    check_cancel: Optional[Callable[[], None]] = None,
):
    """
    Run the full contract analysis pipeline with stage-level progress reporting.
    
    Args:
        pdf_path: Path to the PDF file to analyze
        out_dir: Directory to save generated artifacts
        progress_callback: Function called after each stage completes: callback(stage_id, message)
    """
    def _report(stage: str, msg: str, progress: Optional[dict[str, Any]] = None):
        print(f"\n[{stage}] {msg}")
        if progress_callback:
            progress_callback(stage, msg, progress)

    _report("UPLOADED", "Starting analysis...")
    settings = get_settings(pdf_path=pdf_path, out_dir=out_dir)
    out_path = Path(settings.out_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    def _index_in_background(label: str, operation: Callable[[], None]) -> None:
        """Search enrichment must never delay the contract review pipeline."""
        def run() -> None:
            try:
                operation()
                print(f"[INDEX] {label} complete")
            except Exception as exc:
                print(f"[INDEX] {label} skipped: {exc}")
        threading.Thread(target=run, name=f"index-{label}", daemon=True).start()
    
    if check_cancel:
        check_cancel()
    
    # 1. Extraction
    _report("UPLOADED", "Extracting PDF content...")
    pages, _, _, meta = extract_pdf(
        settings.pdf_path,
        ocr_space_api_key=settings.ocr_space_api_key,
        ocr_cache_dir=str(Path(settings.app_data_dir) / "ocr_text"),
        ocr_min_text_chars=settings.ocr_min_text_chars,
        ocr_enabled=settings.ocr_enabled,
    )
    
    if check_cancel:
        check_cancel()
    
    # 2. Normalization
    norm_pages = normalize_pages(pages)
    norm_text, page_offsets = build_full_text_and_offsets(norm_pages)
    write_json_atomic(
        artifact_path(out_path, ARTIFACTS.extraction),
        {**meta, "text_chars": len(norm_text), "page_offsets": page_offsets},
    )
    write_text_atomic(
        artifact_path(out_path, ARTIFACTS.normalized_text), norm_text
    )
    _report("EXTRACTED", f"Text extracted — {len(pages)} pages, {len(norm_text)} characters")
    
    # 3. Section Extraction
    sections = extract_sections_from_text(norm_text)
    if not sections:
        print("⚠️ No headings detected. Falling back to lossless window chunking.")
        sections = fallback_chunks(norm_text)
    else:
        sections = recover_subclauses_deterministically(sections)
    sections = map_sections_to_pages(sections, page_offsets)
    
    if check_cancel:
        check_cancel()
    
    # Publish the deterministic map before optional LLM repair. The workspace is
    # useful immediately and a provider delay cannot hide the extracted contract.
    sections_out = [asdict(s) for s in sections]
    write_json_atomic(artifact_path(out_path, ARTIFACTS.sections), sections_out)
    _report("SECTIONS_BUILT", f"Identified {len(sections)} sections.")

    if settings.clause_repair_enabled:
        _report("SECTIONS_BUILT", "Refining ambiguous clauses without blocking the clause map.")
        sections, clause_repair_errors = run_llm_clause_repair(
            sections,
            settings,
            check_cancel=check_cancel,
        )
        if clause_repair_errors:
            print(f"Warning: clause repair preserved {len(clause_repair_errors)} unverified node(s).")
        sections = map_sections_to_pages(sections, page_offsets)
        sections_out = [asdict(s) for s in sections]
        write_json_atomic(artifact_path(out_path, ARTIFACTS.sections), sections_out)
    
    # Progressive Indexing: Sections
    run_id = out_path.name
    if not settings.skip_retrieval_indexing:
        _index_in_background("sections", lambda: index_sections(
            run_id, str(out_path), sections_out, settings.nvidia_api_key,
        ))

    
    # 4. Reference & Edge Extraction
    edge_candidates, unresolved = build_reference_edges(sections)
    def _on_graph_progress(progress: dict[str, Any]) -> None:
        _report("SECTIONS_BUILT", "Building clause graph from section references...", progress)

    contextual_edges, llm_errors = run_llm_graph_verification(
        sections,
        settings,
        candidate_edges=edge_candidates,
        unresolved_edges=unresolved,
        check_cancel=check_cancel,
        progress_callback=_on_graph_progress,
    )
    edges = aggregate_edges_raw(contextual_edges)
    
    if check_cancel:
        check_cancel()
    
    # Partial Dump: Edges
    write_json_atomic(artifact_path(out_path, ARTIFACTS.edges), edges)
    _report("GRAPH_READY", f"Mapped {len(edges)} clause dependencies.", None)
        
    # 5. Risk Analysis
    def _on_risk_progress(progress: dict[str, Any]) -> None:
        _report("GRAPH_READY", "Analyzing clause risks...", progress)

    analysis_sections = [section for section in sections if section.is_analysis_unit]
    risk_groups = build_risk_groups(analysis_sections, sections, max_chars=settings.risk_group_max_chars)
    risk_ownership = build_risk_group_ownership(risk_groups)
    risk_edges = remap_edges_to_risk_groups(edges, risk_ownership)
    partial_results: list[dict[str, Any]] = []
    partial_lock = threading.Lock()
    cache_dir = Path(settings.app_data_dir) / "risk_group_cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_paths = {
        group.node_id: cache_dir / (
            risk_group_cache_key(
                group,
                risk_edges,
                settings.risk_analyzer.provider,
                settings.risk_analyzer.model,
            )
            + ".json"
        )
        for group in risk_groups
    }
    cached_results, pending_groups = [], []
    for group in risk_groups:
        cache_path = cache_paths[group.node_id]
        try:
            cached = json.loads(cache_path.read_text(encoding="utf-8")) if cache_path.exists() else None
        except Exception:
            cached = None
        if isinstance(cached, dict) and cached.get("source_clause_ids") == group.source_clause_ids:
            cached_results.append(cached)
        else:
            pending_groups.append(group)

    def _on_risk_result(results: list[dict[str, Any]], completed: int, total: int) -> None:
        with partial_lock:
            partial_results.extend(results)
            for result in results:
                cache_path = cache_paths.get(result.get("section_id"))
                if cache_path:
                    write_json_atomic(cache_path, result)
            write_json_atomic(artifact_path(out_path, ARTIFACTS.partial_risks), partial_results)
            write_json_atomic(artifact_path(out_path, ARTIFACTS.risk_progress), {
                "completed": completed, "total": total, "revision": len(partial_results),
            })

    partial_results.extend(cached_results)
    risk_results, risk_errors = run_risk_analyzer(
        pending_groups,
        risk_edges,
        settings,
        check_cancel=check_cancel,
        progress_callback=_on_risk_progress,
        result_callback=_on_risk_result,
    )
    risk_results = cached_results + risk_results
    write_json_atomic(artifact_path(out_path, ARTIFACTS.risks), risk_results)
    _report("RISKS_ANALYZED", f"Risk scoring complete — {len(risk_results)} parent groups analyzed", None)
        
    # Progressive Indexing: Risks
    if not settings.skip_retrieval_indexing:
        _index_in_background("risks", lambda: index_risks(run_id, str(out_path), risk_results, settings.nvidia_api_key))

    if check_cancel:
        check_cancel()
        
    # 6. Final Report
    def _on_report_progress(kind: str, completed: int, total: int, label: str) -> None:
        _report("RISKS_ANALYZED", "Generating executive report...", {
            "stage_key": "report",
            "label": label,
            "completed": completed,
            "total": total,
            "unit": "section groups",
            "percent": round((completed / total) * 100) if total else 0,
            "current_item_label": label,
        })

    report = run_report_generator(
        risk_results,
        settings,
        sections=analysis_sections,
        progress_callback=_on_report_progress,
    )
    write_json_atomic(
        artifact_path(out_path, ARTIFACTS.clause_ledger), report.ledger
    )
    write_json_atomic(
        artifact_path(out_path, ARTIFACTS.report_generation),
        report.generation_meta,
    )
    write_json_atomic(
        artifact_path(out_path, ARTIFACTS.report_json), report.report_json
    )
    write_text_atomic(
        artifact_path(out_path, ARTIFACTS.report_markdown), report.markdown
    )
    _report("REPORT_READY", "Executive review generated.", None)
        
    # Progressive Indexing: Report
    if not settings.skip_retrieval_indexing:
        _index_in_background(
            "report",
            lambda: index_report(
                run_id, str(out_path), report.markdown, settings.nvidia_api_key
            ),
        )

        
    print(f"\n🎉 Pipeline complete! Results in {out_dir}")


def run_pipeline(pdf_path: str, out_dir: str):
    """Legacy entry point for CLI usage."""
    run_pipeline_with_progress(pdf_path, out_dir)


if __name__ == "__main__":
    import os
    project_root = Path(__file__).resolve().parent.parent
    pdf = os.getenv("PDF_PATH", str(project_root / "docs" / "CHIPMOSTECHNOLOGIESBERMUDALTD_04_18_2016-EX-4.72-Strategic Alliance Agreement.PDF"))
    out = os.getenv("OUT_DIR", str(project_root / "outputs" / "phase2_artifacts"))
    run_pipeline(pdf, out)
