import json
import os
from typing import Any, Callable, Dict, List, Tuple

from .embeddings import get_embeddings
from .index_store import get_index_store


def _chunk_text(text: str, chunk_size: int = 1500) -> List[str]:
    """Helper to chunk long text (like report) roughly."""
    words = text.split()
    chunks = []
    current = []
    current_len = 0
    for w in words:
        current.append(w)
        current_len += len(w) + 1
        if current_len > chunk_size:
            chunks.append(" ".join(current))
            current = []
            current_len = 0
    if current:
        chunks.append(" ".join(current))
    return chunks

def index_sections(
    run_id: str,
    out_dir: str,
    sections: List[Any],
    api_key: str,
    progress_callback: Callable[[dict[str, Any]], None] | None = None,
):
    store = get_index_store(run_id, out_dir)
    docs = []
    texts = []
    
    for s in sections:
        # Assuming DataClass or dict
        s_dict = s if isinstance(s, dict) else s.__dict__
        sec_id = s_dict.get("id", str(s_dict.get("index", "")))
        text = s_dict.get("text", "")
        if not text.strip():
            continue
            
        doc = {
            "type": "section",
            "artifact_type": "contract_section",
            "run_id": run_id,
            "id": f"sec_{sec_id}",
            "section_id": sec_id,
            "section_title": s_dict.get("title", ""),
            "title": s_dict.get("title", ""),
            "display_title": f"Section {sec_id} — {s_dict.get('title', 'Text Segment')}",
            "content": text
        }
        docs.append(doc)
        texts.append(f"{doc['display_title']}\n{doc['content']}")
        
    if texts:
        if progress_callback:
            progress_callback(
                {
                    "stage_key": "section_indexing",
                    "label": "Indexing extracted sections",
                    "completed": 0,
                    "total": len(texts),
                    "unit": "sections",
                    "percent": 0,
                    "current_item_label": f"0 / {len(texts)} sections embedded",
                }
            )

        def _on_embedding_progress(completed: int, total: int, current_label: str) -> None:
            if progress_callback:
                progress_callback(
                    {
                        "stage_key": "section_indexing",
                        "label": "Indexing extracted sections",
                        "completed": completed,
                        "total": total,
                        "unit": "sections",
                        "percent": round((completed / total) * 100) if total else 100,
                        "current_item_label": current_label,
                    }
                )

        embeddings = get_embeddings(texts, api_key, input_type="passage", progress_callback=_on_embedding_progress)
        store.add_documents(docs, embeddings)


def index_risks(run_id: str, out_dir: str, risks: List[Dict[str, Any]], api_key: str):
    """Index individual risk flags from section-level risk analysis results."""
    store = get_index_store(run_id, out_dir)
    docs = []
    texts = []
    
    for section_risk in risks:
        sec_id = section_risk.get("section_id", "")
        sec_title = section_risk.get("title", "")
        overall_risk = section_risk.get("overall_section_risk", "")
        confidence = section_risk.get("confidence", 0)
        risk_flags = section_risk.get("risk_flags", [])
        
        # Index each individual risk flag
        for i, flag in enumerate(risk_flags):
            risk_type = flag.get("risk_type", "general")
            severity = flag.get("severity", "low").upper()
            rationale = flag.get("rationale", "")
            evidence = flag.get("evidence_quotes", [])
            
            content_parts = [rationale]
            if evidence:
                content_parts.append("Evidence: " + "; ".join(evidence))
            full_content = "\n".join(content_parts)
            
            doc = {
                "type": "risk",
                "artifact_type": "risk_finding",
                "run_id": run_id,
                "id": f"risk_{sec_id}_{risk_type.replace(' ', '_')}_{i}",
                "section_id": sec_id,
                "risk_type": risk_type,
                "severity": severity,
                "confidence": confidence,
                "display_title": f"Risk: Section {sec_id} — {risk_type.replace('_', ' ').title()} ({severity})",
                "content": full_content
            }
            docs.append(doc)
            texts.append(
                f"Section {sec_id}: {sec_title}\n"
                f"Risk Type: {risk_type} | Severity: {severity}\n"
                f"Rationale: {rationale}"
            )
        
        # Also index the section-level overall risk summary
        if overall_risk:
            doc = {
                "type": "risk",
                "artifact_type": "risk_summary",
                "run_id": run_id,
                "id": f"risk_summary_{sec_id}",
                "section_id": sec_id,
                "risk_type": "section_summary",
                "severity": "SUMMARY",
                "confidence": confidence,
                "display_title": f"Risk Summary: Section {sec_id} — {sec_title}",
                "content": overall_risk
            }
            docs.append(doc)
            texts.append(
                f"Section {sec_id}: {sec_title}\n"
                f"Overall Risk Assessment: {overall_risk}"
            )
        
    if texts:
        embeddings = get_embeddings(texts, api_key, input_type="passage")
        store.add_documents(docs, embeddings)


def index_report(run_id: str, out_dir: str, report_md: str, api_key: str):
    store = get_index_store(run_id, out_dir)
    docs = []
    texts = []
    
    chunks = _chunk_text(report_md, 2000)
    for i, chunk in enumerate(chunks):
        doc = {
            "type": "report",
            "artifact_type": "executive_report",
            "run_id": run_id,
            "id": f"report_chunk_{i}",
            "report_segment_name": f"Segment {i}",
            "display_title": f"Report: Executive Summary (Part {i+1})",
            "content": chunk
        }
        docs.append(doc)
        texts.append(f"Executive Report Segment:\n{chunk}")
        
    if texts:
        embeddings = get_embeddings(texts, api_key, input_type="passage")
        store.add_documents(docs, embeddings)

def is_contract_query(query: str) -> bool:
    """
    Very simple heuristic: if it looks like general chitchat or pure standard QA unrelated to facts,
    we might skip RAG. However, default policy is conservative -> USE RAG.
    We'll only return False for very obvious non-contract things, or just always return True to be safe.
    Let's just use a list of common greeting/chitchat words.
    """
    q = query.lower().strip()
    if q in ["hi", "hello", "hey", "how are you", "who are you", "what can you do"]:
        return False
    # Defensiveness: prefer RAG
    return True

def retrieve_context(run_id: str, out_dir: str, query: str, api_key: str) -> Tuple[str, List[Dict[str, Any]]]:
    """
    Retrieve top-k items and perform artifact-aware augmentation.
    """
    import re
    store = get_index_store(run_id, out_dir)

    # --- Pre-retrieval: Query Expansion for section references ---
    # Detects patterns like "section 2.2", "clause 2.2", "§ 2.2", "2.2", "ARTICLE_3", "EXHIBIT_4.72"
    sections_path = os.path.join(out_dir, "sections.json")
    sections_map = {}
    if os.path.exists(sections_path):
        try:
            with open(sections_path, "r", encoding="utf-8") as f:
                sec_list = json.load(f)
                for s in sec_list:
                    sections_map[str(s.get("id"))] = f"{s.get('title', '')}\n{s.get('text', '')}"
        except Exception:
            pass

    expanded_query = query
    # Match patterns like "section 2.2", "clause 3.1", "§2.2", or bare IDs like "2.2", "ARTICLE_3"
    sec_ref_patterns = re.findall(
        r'(?:section|clause|§)\s*([A-Za-z0-9_.]+)',
        query, re.IGNORECASE
    )
    # Also try to match bare numeric IDs like "2.2" if the query is short
    if not sec_ref_patterns:
        bare_ids = re.findall(r'\b(\d+\.\d+)\b', query)
        sec_ref_patterns.extend(bare_ids)
        # Match ARTICLE_X or EXHIBIT_X patterns
        special_ids = re.findall(r'\b(ARTICLE_\d+|EXHIBIT_[\d.]+)\b', query, re.IGNORECASE)
        sec_ref_patterns.extend([s.upper() for s in special_ids])

    for ref_id in sec_ref_patterns:
        if ref_id in sections_map:
            sec_text = sections_map[ref_id]
            # Append section context to the query for better embedding match
            expansion = f"\n[Section {ref_id}: {sec_text[:500]}]"
            expanded_query += expansion
            print(f"  ↳ Query expanded with Section {ref_id} context ({len(expansion)} chars)")

    # --- Direct section injection: bypass embedding for explicitly referenced sections ---
    directly_injected_ids = set()
    injected_context_parts = []
    injected_metadata = []
    
    # Load risk analysis data for direct injection
    risk_analysis_path = os.path.join(out_dir, "risk_analysis.json")
    risk_analysis_map = {}
    if os.path.exists(risk_analysis_path):
        try:
            with open(risk_analysis_path, "r", encoding="utf-8") as f:
                risk_data = json.load(f)
                for r in risk_data:
                    risk_analysis_map[str(r.get("section_id", ""))] = r
        except Exception:
            pass

    for ref_id in sec_ref_patterns:
        if ref_id in sections_map:
            directly_injected_ids.add(ref_id)
            sec_content = sections_map[ref_id]
            parts = sec_content.split('\n', 1)
            sec_title = parts[0].strip() if parts else ref_id
            sec_text = parts[1].strip() if len(parts) > 1 else ""
            
            # Inject section text
            injected_context_parts.append(
                f"--- Section {ref_id} (Directly Referenced) ---\n"
                f"Title: {sec_title}\n"
                f"Text: {sec_text}"
            )
            injected_metadata.append({
                "id": f"sec_{ref_id}",
                "type": "section",
                "title": f"Section {ref_id} — {sec_title}",
                "section_id": ref_id,
                "score": 1.0  # Direct match = perfect relevance
            })
            
            # Also inject risk analysis for this section if available
            if ref_id in risk_analysis_map:
                risk_info = risk_analysis_map[ref_id]
                risk_flags = risk_info.get("risk_flags", [])
                overall_risk = risk_info.get("overall_section_risk", "")
                
                if risk_flags or overall_risk:
                    risk_text = f"--- Risk Analysis for Section {ref_id} ---\n"
                    if overall_risk:
                        risk_text += f"Overall Assessment: {overall_risk}\n"
                    for flag in risk_flags:
                        risk_text += (
                            f"\nRisk Type: {flag.get('risk_type', 'N/A')} | "
                            f"Severity: {flag.get('severity', 'N/A')}\n"
                            f"Rationale: {flag.get('rationale', '')}\n"
                        )
                        evidence = flag.get("evidence_quotes", [])
                        if evidence:
                            risk_text += "Evidence: " + "; ".join(f'"{e}"' for e in evidence) + "\n"
                    
                    injected_context_parts.append(risk_text)
                    injected_metadata.append({
                        "id": f"risk_summary_{ref_id}",
                        "type": "risk",
                        "title": f"Risk Analysis: Section {ref_id} — {sec_title}",
                        "section_id": ref_id,
                        "score": 0.95
                    })
            
            print(f"  ↳ Directly injected Section {ref_id} + risk data into context")

    # 1. Embed query (the expanded version) for additional retrieval
    q_emb = get_embeddings([expanded_query], api_key, input_type="query")[0]

    # Check if query is summary oriented
    q_lower = query.lower()
    is_summary = any(w in q_lower for w in ["summary", "summarize", "main", "overall", "report", "executive"])

    # 2. Retrieve top_k
    top_k = 10 if is_summary else 8
    raw_results = store.search(q_emb, top_k=top_k)
    
    # We will also load edges if applicable to augment sections
    edges_path = os.path.join(out_dir, "edges.json")
    edges_data = {}
    if os.path.exists(edges_path):
        try:
            with open(edges_path, "r", encoding="utf-8") as f:
                edges_list = json.load(f)
                for e in edges_list:
                    src = str(e.get("source"))
                    tgt = str(e.get("target"))
                    if src not in edges_data:
                        edges_data[src] = []
                    edges_data[src].append(tgt)
        except Exception:
            pass
            
    # sections_map already loaded above for query expansion

    context_parts = list(injected_context_parts)  # Start with directly injected content
    used_metadata = list(injected_metadata)
    
    if not raw_results and not injected_context_parts:
        return "", []
    
    # Sort results to group by type for neatness
    if raw_results:
        raw_results.sort(key=lambda x: x[0]["type"])
    
    for doc, score in raw_results:
        dtype = doc["type"]
        sec_id = doc.get("section_id", "")
        
        # Skip items that were already directly injected
        if sec_id in directly_injected_ids and dtype in ("section", "risk"):
            continue
        
        title = ""
        if dtype == "report":
            title = f"Report — {doc.get('id', 'Executive Summary').replace('_', ' ').title()}"
        elif dtype == "risk":
            title = f"Risk {sec_id} — {doc.get('risk_type', 'Flagged Item')}"
        elif dtype == "section":
            base_title = "Clause"
            if str(sec_id) in sections_map:
                parts = sections_map[str(sec_id)].split('\n')
                if parts and parts[0].strip():
                    base_title = parts[0].strip()
            title = f"Clause {sec_id} — {base_title}"
            
        used_metadata.append({
            "id": doc.get("id"),
            "type": dtype,
            "title": doc.get("display_title") or title,
            "section_id": sec_id,
            "score": score
        })
        
        if dtype == "report":
            context_parts.append(f"--- Executive Report Excerpt ---\n{doc['content']}")
            
        elif dtype == "risk":
            sec_id = doc.get("section_id", "")
            part = f"--- Risk Node ---\nRisk Type: {doc.get('risk_type')}\nSeverity: {doc.get('severity')}\nRationale: {doc.get('content')}"
            if str(sec_id) in sections_map:
                # Surface section metadata as well as the risk record
                part += f"\nAssociated Clause Text (Section {sec_id}):\n{sections_map[str(sec_id)]}"
            context_parts.append(part)
            
        elif dtype == "section":
            sec_id = doc.get("section_id", "")
            part = f"--- Section {sec_id} ---\nTitle: {doc.get('title')}\nText: {doc['content']}"
            
            # Augment with linked graph neighbors if available
            rel_ids = edges_data.get(str(sec_id), [])
            if rel_ids:
                part += f"\nGraph Context -> Sub-sections referenced: {', '.join(rel_ids)}"
                # optionally pull a snippet of a child
                for child_id in rel_ids[:1]:
                    if str(child_id) in sections_map:
                        snippet = sections_map[str(child_id)][:150].replace("\n", " ") + "..."
                        part += f"\n[Child {child_id} text]: {snippet}"
                        
            context_parts.append(part)

    final_context = "\n\n".join(context_parts)
    return final_context, used_metadata
