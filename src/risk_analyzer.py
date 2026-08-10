from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any, Callable, Optional

RISK_PROMPT_VERSION = "group-risk-v2"


@dataclass(frozen=True)
class RiskGroup:
    node_id: str
    title: str
    text: str
    source_clause_ids: list[str]
    start_char: int


def build_risk_groups(
    atomic_sections: list[Any],
    all_sections: list[Any],
    max_chars: int = 18000,
) -> list[RiskGroup]:
    """Analyze nearest-parent clause groups while retaining every atomic clause ID."""
    by_id = {section.node_id: section for section in all_sections}
    grouped: dict[str, list[Any]] = {}
    for section in atomic_sections:
        group_id = section.parent_id if section.parent_id in by_id else section.node_id
        grouped.setdefault(group_id, []).append(section)

    groups: list[RiskGroup] = []
    for parent_id, members in grouped.items():
        parent = by_id.get(parent_id)
        members.sort(key=lambda section: section.start_char)
        chunk, chunk_chars, chunk_index = [], 0, 1
        for member in members:
            rendered = f"[CLAUSE {member.node_id}]\n{member.text.strip()}\n"
            if chunk and chunk_chars + len(rendered) > max_chars:
                groups.append(_make_risk_group(parent_id, parent, chunk, chunk_index))
                chunk, chunk_chars, chunk_index = [], 0, chunk_index + 1
            chunk.append(member)
            chunk_chars += len(rendered)
        if chunk:
            groups.append(_make_risk_group(parent_id, parent, chunk, chunk_index))
    return groups


def _make_risk_group(
    parent_id: str,
    parent: Any,
    members: list[Any],
    chunk_index: int,
) -> RiskGroup:
    group_id = parent_id if chunk_index == 1 else f"{parent_id}__group_{chunk_index}"
    title = getattr(parent, "title", None) or members[0].title
    return RiskGroup(
        node_id=group_id,
        title=title,
        text="\n".join(f"[CLAUSE {member.node_id}]\n{member.text.strip()}" for member in members),
        source_clause_ids=[member.node_id for member in members],
        start_char=members[0].start_char,
    )


def build_risk_group_ownership(groups: list[RiskGroup]) -> dict[str, str]:
    ownership: dict[str, str] = {}
    for group in groups:
        ownership[group.node_id] = group.node_id
        for clause_id in group.source_clause_ids:
            ownership[clause_id] = group.node_id
    return ownership


def remap_edges_to_risk_groups(
    edges: list[dict[str, Any]],
    ownership: dict[str, str],
) -> list[dict[str, Any]]:
    grouped_edges: dict[tuple[str, str], dict[str, Any]] = {}
    valid_groups = set(ownership.values())
    for edge in edges:
        source = ownership.get(str(edge.get("from")), str(edge.get("from", "")))
        target = ownership.get(str(edge.get("to")), str(edge.get("to", "")))
        if (
            source == target
            or source not in valid_groups
            or target not in valid_groups
        ):
            continue
        key = (source, target)
        record = grouped_edges.setdefault(
            key,
            {
                "from": source,
                "to": target,
                "relation_labels": set(),
                "evidence_quotes": set(),
                "max_confidence": 0.0,
            },
        )
        labels = edge.get("relation_labels") or [edge.get("relation_label")]
        record["relation_labels"].update(label for label in labels if label)
        record["evidence_quotes"].update(edge.get("evidence_quotes", []))
        record["max_confidence"] = max(
            record["max_confidence"], float(edge.get("max_confidence", 0.0) or 0.0)
        )

    return [
        {
            "from": source,
            "to": target,
            "relation_labels": sorted(record["relation_labels"]),
            "relation_label": "; ".join(sorted(record["relation_labels"])),
            "evidence_quotes": sorted(record["evidence_quotes"]),
            "max_confidence": record["max_confidence"],
        }
        for (source, target), record in grouped_edges.items()
    ]


def risk_group_cache_key(
    group: RiskGroup,
    edges: list[dict[str, Any]],
    provider: str,
    model: str,
) -> str:
    related_edges = sorted(
        (
            edge
            for edge in edges
            if edge.get("from") == group.node_id or edge.get("to") == group.node_id
        ),
        key=lambda edge: (
            str(edge.get("from", "")),
            str(edge.get("to", "")),
            str(edge.get("relation_label", "")),
        ),
    )
    payload = {
        "prompt_version": RISK_PROMPT_VERSION,
        "provider": provider,
        "model": model,
        "group_id": group.node_id,
        "source_clause_ids": group.source_clause_ids,
        "text": group.text,
        "related_edges": related_edges,
    }
    serialized = json.dumps(payload, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def make_risk_prompt(batch: list[dict[str, Any]]) -> tuple[str, str]:
    def clip(s: str, limit: int = 4000) -> str:
        s = (s or "").strip()
        return s[:limit] + ("..." if len(s) > limit else "")

    system = (
        "You are an expert contract risk analyzer.\n"
        "\n"
        f"Your task is to analyze a batch of {len(batch)} primary contract sections along with their linked graph context, "
        "then produce a grounded structured risk assessment for EACH section.\n"
        "\n"
        "You MUST return exactly ONE valid JSON object and NOTHING else.\n"
        "Do NOT include markdown fences, commentary, preambles, explanations outside JSON, or reasoning text.\n"
        "\n"
        "GROUNDING RULES:\n"
        "- Use ONLY the text provided in the primary section and linked sections.\n"
        "- Do NOT invent facts, obligations, carveouts, exceptions, or risks.\n"
        "- `evidence_quotes` MUST be verbatim substrings copied exactly from the provided text.\n"
        "- If a risk depends on linked context, reflect that in `related_sections`.\n"
        "- If the linked context weakens or narrows an apparent risk, account for that conservatively.\n"
        "\n"
        "RISK TYPE RULES:\n"
        "Allowed values for `risk_type` are exactly:\n"
        "liability, indemnity, termination, payment, exclusivity, confidentiality, ip, compliance, operational, ambiguity, other\n"
        "\n"
        "SEVERITY RULES:\n"
        "Allowed values for `severity` are exactly:\n"
        "low, medium, high, critical\n"
        "\n"
        "SEVERITY GUIDANCE:\n"
        "- critical: severe and immediate legal/commercial exposure, extreme imbalance, or major unbounded downside clearly supported by text\n"
        "- high: materially adverse term or significant exposure with strong textual support\n"
        "- medium: meaningful but not extreme concern, ambiguity, imbalance, or operational/legal burden\n"
        "- low: minor concern, drafting weakness, or limited risk with narrow scope\n"
        "\n"
        "NO-RISK RULE:\n"
        "- If no meaningful risk is present, return `risk_flags: []`.\n"
        "- In that case, `overall_section_risk` should still be a short conservative summary, such as "
        "'No material risk identified in this section based on the provided text.'\n"
        "\n"
        "RATIONALE RULES:\n"
        "- `rationale` must explain why the clause is risky in plain, precise legal/business language.\n"
        "- Do not repeat the quote as the rationale.\n"
        "- Keep rationales concise but specific.\n"
        "\n"
        "CONFIDENCE RULES:\n"
        "- `confidence` must be a number between 0 and 1.\n"
        "- Use higher confidence only when the textual support is explicit and strong.\n"
        "- Use lower confidence when the issue depends on interpretation, ambiguity, or incomplete linked context.\n"
    )

    user_parts = [
        f"Analyze the following {len(batch)} primary sections and their linked graph context.\n"
    ]

    for item in batch:
        primary_node = item.get("primary", {})
        related_nodes = item.get("related", [])
        edges_used = item.get("edges_used", [])

        primary_text = clip(primary_node.get("text", ""), 4500)
        primary_title = (primary_node.get("title", "") or "").strip()
        section_id = item["section_id"]
        source_clause_ids = item.get("source_clause_ids", [section_id])

        related_ctx = []
        for r in related_nodes:
            rid = r.get("node_id", "")
            rtitle = r.get("title", "")
            rtext = clip(r.get("text", ""), 1800)
            related_ctx.append(
                f"--- LINKED SECTION ---\n"
                f"ID: {rid}\n"
                f"Title: {rtitle}\n"
                f"Text:\n{rtext}"
            )
        related_ctx_str = "\n\n".join(related_ctx) if related_ctx else "None"
        edges_str = json.dumps(edges_used, indent=2, ensure_ascii=False) if edges_used else "[]"

        user_parts.append(f"==================== SECTION {section_id} ====================")
        user_parts.append(f"PRIMARY SECTION GROUP\nID: {section_id}\nTitle: {primary_title}\nSOURCE CLAUSE IDS: {json.dumps(source_clause_ids)}\nText:\n{primary_text}\n")
        user_parts.append(f"LINKED CONTEXT\n{related_ctx_str}\n")
        user_parts.append(f"GRAPH EDGES USED TO BUILD THIS CONTEXT\n{edges_str}\n")

    user_parts.append(
        "INSTRUCTIONS:\n"
        "1. Identify only meaningful risks for each primary section.\n"
        "2. Use linked context only to interpret or clarify the primary section.\n"
        "3. If a risk depends on another section, include that section ID in `related_sections`.\n"
        "4. Each risk flag MUST include `affected_clause_ids`, using one or more IDs from the SOURCE CLAUSE IDS for that group.\n"
        "5. Return exactly ONE JSON object containing a `results` array with exactly one entry per section group provided.\n"
        "\n"
        "OUTPUT JSON SCHEMA (must match exactly):\n"
        "{\n"
        '  "results": [\n'
        "    {\n"
        '      "section_id": "string",\n'
        '      "title": "string",\n'
        '      "risk_flags": [\n'
        "        {\n"
        '          "risk_type": "liability|indemnity|termination|payment|exclusivity|confidentiality|ip|compliance|operational|ambiguity|other",\n'
        '          "severity": "low|medium|high|critical",\n'
        '          "rationale": "string",\n'
        '          "evidence_quotes": ["string"],\n'
        '          "related_sections": ["string"],\n'
        '          "affected_clause_ids": ["string"]\n'
        "        }\n"
        "      ],\n"
        '      "overall_section_risk": "string",\n'
        '      "confidence": 0.0\n'
        "    }\n"
        "  ]\n"
        "}\n"
        "\n"
        "FIELD REQUIREMENTS:\n"
        "- `results` array MUST contain exactly one entry for each provided section group.\n"
        "- `section_id` and `title` must exactly match the ones provided above.\n"
        "- `evidence_quotes` must contain only exact copied substrings from the provided text.\n"
        "- Do not output null values.\n"
    )

    user = "\n".join(user_parts)
    return system, user


def validate_risk_flags(parsed: dict[str, Any], section_id: str, source_clause_ids: list[str] | None = None) -> tuple[dict[str, Any], list[str]]:
    errors = []
    
    if not isinstance(parsed, dict):
        return {"section_id": section_id, "risk_flags": []}, ["Not a dictionary"]
        
    if "risk_flags" not in parsed:
        parsed["risk_flags"] = []
    if not isinstance(parsed["risk_flags"], list):
        errors.append("'risk_flags' is not a list")
        parsed["risk_flags"] = []
        
    valid_flags = []
    allowed_types = {"liability", "indemnity", "termination", "payment", "exclusivity", 
                     "confidentiality", "ip", "compliance", "operational", "ambiguity", "other"}
    allowed_severity = {"low", "medium", "high", "critical"}
    
    for i, flag in enumerate(parsed["risk_flags"]):
        if not isinstance(flag, dict):
            errors.append(f"risk_flags[{i}] is not an object")
            continue
            
        rtype = (flag.get("risk_type") or "").lower().strip()
        rsev = (flag.get("severity") or "").lower().strip()
        
        if rtype not in allowed_types:
            flag["risk_type"] = "other"  # Graceful degrade
        if rsev not in allowed_severity:
            flag["severity"] = "low"     # Graceful degrade
            
        if not isinstance(flag.get("evidence_quotes"), list):
            flag["evidence_quotes"] = []
        if not isinstance(flag.get("related_sections"), list):
            flag["related_sections"] = []
        allowed_clause_ids = set(source_clause_ids or [section_id])
        affected = flag.get("affected_clause_ids")
        if not isinstance(affected, list) or not affected:
            flag["affected_clause_ids"] = list(source_clause_ids or [section_id])
        elif not set(str(item) for item in affected).issubset(allowed_clause_ids):
            errors.append(f"risk_flags[{i}] references an unknown affected clause")
            flag["affected_clause_ids"] = [item for item in affected if str(item) in allowed_clause_ids]
            
        valid_flags.append(flag)
        
    parsed["risk_flags"] = valid_flags
    parsed["section_id"] = section_id # Ensure integrity
    
    return parsed, errors


def _normalized_risk_text(value: Any) -> str:
    return " ".join(str(value or "").lower().split())


def _risk_flag_key(flag: dict[str, Any]) -> tuple[str, str, str, tuple[str, ...]]:
    evidence = flag.get("evidence_quotes", [])
    if not isinstance(evidence, list):
        evidence = []

    return (
        _normalized_risk_text(flag.get("risk_type")),
        _normalized_risk_text(flag.get("severity")),
        _normalized_risk_text(flag.get("rationale")),
        tuple(sorted(_normalized_risk_text(item) for item in evidence)),
    )


def dedupe_risk_flags(flags: list[Any]) -> list[dict[str, Any]]:
    seen = set()
    unique = []

    for flag in flags:
        if not isinstance(flag, dict):
            continue
        key = _risk_flag_key(flag)
        if key in seen:
            continue
        seen.add(key)
        unique.append(flag)

    return unique


def dedupe_risk_results(results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_section: dict[str, dict[str, Any]] = {}
    order: list[str] = []
    skipped = []

    for result in results:
        if not isinstance(result, dict):
            continue

        section_id = str(result.get("section_id", ""))
        if not section_id:
            continue

        result["risk_flags"] = dedupe_risk_flags(result.get("risk_flags", []))

        if section_id not in by_section:
            by_section[section_id] = result
            order.append(section_id)
            continue

        skipped.append(section_id)
        existing = by_section[section_id]
        existing_success = existing.get("analysis_status") == "SUCCESS"
        result_success = result.get("analysis_status") == "SUCCESS"

        if result_success and not existing_success:
            by_section[section_id] = result
            existing = result

        merged_flags = dedupe_risk_flags(
            list(existing.get("risk_flags", [])) + list(result.get("risk_flags", []))
        )
        existing["risk_flags"] = merged_flags

    if skipped:
        skipped_ids = ", ".join(sorted(set(skipped)))
        print(f"⚠️ Collapsed duplicate risk result section_id(s): {skipped_ids}")

    return [by_section[section_id] for section_id in order]


def run_risk_analyzer(
    sections: list[Any],
    edges: list[dict[str, Any]],
    settings: Any,
    check_cancel: Optional[Callable[[], None]] = None,
    progress_callback: Optional[Callable[[dict[str, Any]], None]] = None,
    result_callback: Optional[Callable[[list[dict[str, Any]], int, int], None]] = None,
) -> tuple[list[dict[str, Any]], list[str]]:
    
    import re
    from concurrent.futures import ThreadPoolExecutor, as_completed

    from .graph_ops import build_adjacency, get_context_pack
    from .llm_client import execute_with_fallback
    from .scaling import compute_risk_analyzer_params, log_scaling_decision

    node_index = {s.node_id: s for s in sections}
    adj, rev_adj = build_adjacency(edges)
    edge_lookup = {
        (str(edge.get("from")), str(edge.get("to"))): edge for edge in edges
    }

    all_errors = []
    
    # Dynamic scaling based on number of sections
    scale_params = compute_risk_analyzer_params(len(sections))
    risk_max_tokens = scale_params["max_tokens"]
    batch_size = scale_params.get("batch_size", 3)
    log_scaling_decision("risk_analyzer", len(sections), scale_params)
    
    print("\n====================")
    print(f"🕵️‍♂️ Starting Risk Analyzer stage for {len(sections)} sections (Batched)...")
    print(f"⚡ Concurrency limit: {settings.risk_analyzer_concurrency} | Batch size: {batch_size}")
    
    # 1) Context cache to avoid redundant graph traversals
    context_cache = {}
    
    # 2) Helper to rigorously validate schema before accepting
    def _validate_risk(parsed):
        if not isinstance(parsed, dict):
            raise ValueError("Root must be a JSON object")
        if "results" not in parsed:
            raise ValueError("Missing 'results' array")
        if not isinstance(parsed["results"], list):
            raise ValueError("'results' must be an array")
        for item in parsed["results"]:
            if "risk_flags" not in item:
                raise ValueError("Item missing 'risk_flags' array")

    def analyze_batch(batch_idx, batch_sections):
        valid_items = []
        results_map = {}

        for sec in batch_sections:
            text = sec.text or ""
            # Lexical pruning check
            if len(text.strip()) < 50 or not re.search(r'[a-zA-Z]{5,}', text):
                results_map[sec.node_id] = {
                    "section_id": sec.node_id,
                    "title": sec.title,
                    "risk_flags": [],
                    "overall_section_risk": "",
                    "confidence": 1.0,
                    "analysis_status": "SKIPPED_LEXICAL",
                    "analysis_error": ""
                }
                continue

            if sec.node_id not in context_cache:
                context_cache[sec.node_id] = get_context_pack(sec.node_id, node_index, adj, rev_adj, max_hops=1, max_nodes=3)
            
            cpack = context_cache[sec.node_id]
            cpack["edges_used"] = [
                edge_lookup.get(
                    (str(edge.get("from")), str(edge.get("to"))),
                    edge,
                )
                for edge in cpack.get("edges_used", [])
            ]
            cpack["section_id"] = sec.node_id
            cpack["source_clause_ids"] = list(getattr(sec, "source_clause_ids", [sec.node_id]))
            valid_items.append(cpack)
            
            # Pre-fill a failure to be overwritten if LLM succeeds
            results_map[sec.node_id] = {
                "section_id": sec.node_id,
                "title": sec.title,
                "risk_flags": [],
                "overall_section_risk": "",
                "confidence": 0.0,
                "analysis_status": "FAILED_ANALYSIS",
                "analysis_error": "LLM omitted this section from outputs.",
                "source_clause_ids": list(getattr(sec, "source_clause_ids", [sec.node_id])),
            }

        # If all sections in this batch were skipped due to lexical pruning
        if not valid_items:
            return list(results_map.values())
            
        system, user = make_risk_prompt(valid_items)
        trace_id = f"batch_{batch_idx}_{valid_items[0]['section_id']}"
        
        if check_cancel:
            check_cancel()
        
        try:
            raw, parsed = execute_with_fallback(
                stage_name="risk_analyzer",
                trace_id=trace_id,
                stage_config=settings.risk_analyzer,
                settings=settings,
                messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
                temperature=settings.temperature,
                max_tokens=risk_max_tokens,
                response_format={"type": "json_object"} if settings.risk_analyzer.use_response_format else None,
                validator_fn=_validate_risk
            )
            
            for item in parsed.get("results", []):
                sid = str(item.get("section_id", ""))
                if sid in results_map:
                    source_clause_ids = list(getattr(next(sec for sec in batch_sections if sec.node_id == sid), "source_clause_ids", [sid]))
                    validated_item, errs = validate_risk_flags(item, sid, source_clause_ids)
                    validated_item["source_clause_ids"] = source_clause_ids
                    if errs:
                        validated_item["analysis_status"] = "PARTIAL_VALIDATION_ERRORS"
                        validated_item["analysis_error"] = "; ".join(errs)
                    else:
                        validated_item["analysis_status"] = "SUCCESS"
                        validated_item["analysis_error"] = ""
                    results_map[sid] = validated_item
                        
        except Exception as e:
            for sid in results_map:
                if results_map[sid]["analysis_status"] == "FAILED_ANALYSIS":
                    results_map[sid]["analysis_error"] = str(e)

        return list(results_map.values())

    # 3) Group sections into chunks of batch_size
    batches = [sections[i:i + batch_size] for i in range(0, len(sections), batch_size)]
    total_sections = len(sections)
    completed_sections = 0
    if progress_callback:
        progress_callback(
            {
                "stage_key": "risk_analysis",
                "label": "Analyzing sections",
                "completed": 0,
                "total": total_sections,
                "unit": "sections",
                "percent": 0,
                "current_item_label": f"0 / {total_sections} sections analyzed",
            }
        )
    
    futures = {}
    with ThreadPoolExecutor(max_workers=settings.risk_analyzer_concurrency) as executor:
        for i, b in enumerate(batches):
            fut = executor.submit(analyze_batch, i, b)
            futures[fut] = b
            
        # We need to maintain original global order based on node_id index
        id_to_result = {}
        
        for fut in as_completed(futures):
            orig_batch = futures[fut]
            try:
                res_list = fut.result()
                for r in res_list:
                    id_to_result[r["section_id"]] = r
                    
                    status = r["analysis_status"]
                    node_id = r["section_id"]
                    if status == "SUCCESS":
                        print(f"✅ {node_id}: Found {len(r['risk_flags'])} risks")
                    elif status == "SKIPPED_LEXICAL":
                        print(f"⏭️ {node_id}: Skipped (lexical pruning)")
                    else:
                        print(f"❌ {node_id}: {status} -> {r['analysis_error']}")
                        all_errors.append(f"Node {node_id}: {r['analysis_error']}")
                completed_sections += len(orig_batch)
                if result_callback:
                    result_callback(res_list, completed_sections, total_sections)
                if progress_callback:
                    last_label = res_list[-1]["section_id"] if res_list else orig_batch[-1].node_id
                    progress_callback(
                        {
                            "stage_key": "risk_analysis",
                            "label": "Analyzing sections",
                            "completed": min(completed_sections, total_sections),
                            "total": total_sections,
                            "unit": "sections",
                            "percent": round((min(completed_sections, total_sections) / total_sections) * 100) if total_sections else 100,
                            "current_item_label": f"Processed through {last_label}",
                        }
                    )
                        
            except Exception as e:
                for sec in orig_batch:
                    id_to_result[sec.node_id] = {
                        "section_id": sec.node_id,
                        "title": sec.title,
                        "risk_flags": [],
                        "overall_section_risk": "",
                        "confidence": 0.0,
                        "analysis_status": "CRITICAL_THREAD_FAIL",
                        "analysis_error": str(e)
                    }
                    print(f"❌ {sec.node_id}: Critical thread failure -> {str(e)}")
                    all_errors.append(f"Node {sec.node_id} Thread Fail: {str(e)}")
                completed_sections += len(orig_batch)
                if progress_callback:
                    progress_callback(
                        {
                            "stage_key": "risk_analysis",
                            "label": "Analyzing sections",
                            "completed": min(completed_sections, total_sections),
                            "total": total_sections,
                            "unit": "sections",
                            "percent": round((min(completed_sections, total_sections) / total_sections) * 100) if total_sections else 100,
                            "current_item_label": f"Processed {min(completed_sections, total_sections)} / {total_sections} sections",
                        }
                    )

    # Restitch into original order
    sorted_results = []
    for sec in sections:
        if sec.node_id in id_to_result:
            sorted_results.append(id_to_result[sec.node_id])

    # Remove skipped nodes from final artifact
    valid_results = [
        r for r in dedupe_risk_results(sorted_results)
        if r["analysis_status"] != "SKIPPED_LEXICAL"
    ]

    print(f"✅ Risk Analyzer complete. Processed {len(sections)} sections, extracted {len(valid_results)} usable results.")
    return valid_results, all_errors
