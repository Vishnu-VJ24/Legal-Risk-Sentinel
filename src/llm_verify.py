from __future__ import annotations

import hashlib
import json
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import TYPE_CHECKING, Any, Callable, Optional

from .llm_client import execute_with_fallback

if TYPE_CHECKING:
    from .sections import SectionNode


GENERIC_RELATION_LABELS = {
    "reference",
    "references",
    "related to",
    "generic",
    "override",
    "dependency",
    "carve out",
    "carve_out",
    "definition",
}
REFERENCE_IN_LABEL = re.compile(
    r"\b(section|article|exhibit|schedule)\s+([A-Z0-9_.()\-]+)",
    re.IGNORECASE,
)
EXPLICIT_REFERENCE_CUE = re.compile(
    r"\b(?:section|sec\.|article|exhibit|schedule)\b|§",
    re.IGNORECASE,
)


def candidate_edge_id(edge: dict[str, Any]) -> str:
    payload = "\0".join(
        str(edge.get(key, ""))
        for key in ("from", "to", "ref_start", "ref_end", "ref_text")
    )
    return f"edge_{hashlib.sha256(payload.encode('utf-8')).hexdigest()[:16]}"


def prepare_candidate_edges(edges: list[dict[str, Any]]) -> list[dict[str, Any]]:
    prepared: dict[str, dict[str, Any]] = {}
    for edge in edges:
        candidate = dict(edge)
        candidate["candidate_id"] = candidate_edge_id(candidate)
        prepared.setdefault(candidate["candidate_id"], candidate)
    return list(prepared.values())


def collapse_candidates_for_naming(
    candidates: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], dict[str, list[dict[str, Any]]]]:
    """Name one representative per visible relationship, not every citation.

    The original candidates remain the lossless graph source. A successful label
    is copied back to every citation for that source/target pair below.
    """
    grouped: dict[str, list[dict[str, Any]]] = {}
    for candidate in candidates:
        key = f"{candidate.get('from', '')}\0{candidate.get('to', '')}"
        grouped.setdefault(key, []).append(candidate)

    representatives: list[dict[str, Any]] = []
    for key, group in grouped.items():
        representative = dict(group[0])
        representative["candidate_id"] = (
            f"relationship_{hashlib.sha256(key.encode('utf-8')).hexdigest()[:16]}"
        )
        representative["citation_count"] = len(group)
        representatives.append(representative)
    return representatives, grouped


def expand_named_candidates(
    named_edges: list[dict[str, Any]],
    original_groups: dict[str, list[dict[str, Any]]],
) -> list[dict[str, Any]]:
    """Restore every deterministic citation after representative labeling."""
    expanded: list[dict[str, Any]] = []
    for named in named_edges:
        key = f"{named.get('from', '')}\0{named.get('to', '')}"
        originals = original_groups.get(key)
        if not originals:
            expanded.append(named)
            continue
        for original in originals:
            expanded.append(
                {
                    **original,
                    "relation_label": named.get("relation_label") or fallback_relation_label(str(original.get("ref_text", ""))),
                    "label_source": named.get("label_source", "fallback"),
                    "confidence": named.get("confidence", original.get("confidence", 1.0)),
                    "resolved": True,
                }
            )
    return expanded


def fallback_relation_label(evidence: str) -> str:
    text = (evidence or "").lower()
    if "notwithstanding" in text or "prevail" in text or "control" in text:
        return "overrides obligations in referenced clause"
    if "except" in text or "other than" in text:
        return "creates exception to referenced clause"
    if "defined in" in text:
        return "incorporates definition from referenced clause"
    if "subject to" in text:
        return "conditioned by referenced clause"
    if "pursuant to" in text or "in accordance with" in text:
        return "governed by referenced clause"
    return "expressly links to referenced clause"


def normalize_relation_label(
    value: Any,
    known_ids: set[str],
) -> tuple[str | None, str | None]:
    if not isinstance(value, str) or not value.strip():
        return None, "Missing relation_label"
    if "\n" in value or "\r" in value:
        return None, "relation_label must be one line"

    label = " ".join(value.split()).strip(" .,:;")
    if len(label) > 80:
        label = label[:80].rsplit(" ", 1)[0].strip()
    normalized = label.lower().replace("_", " ").replace("-", " ")
    if normalized in GENERIC_RELATION_LABELS:
        return None, f"Generic or legacy relation_label: {label}"
    if len(re.findall(r"[A-Za-z]+", label)) < 2:
        return None, "relation_label must describe a contextual legal relationship"

    for kind, token in REFERENCE_IN_LABEL.findall(label):
        token = token.rstrip(".,;:").upper()
        possible_ids = {
            token,
            f"{kind.upper()}_{token}",
        }
        if not possible_ids.intersection({item.upper() for item in known_ids}):
            return None, f"relation_label contains unknown identifier: {kind} {token}"
    return label, None


def _ground_quote(source_text: str, quote: Any) -> tuple[str | None, int]:
    if not isinstance(quote, str) or not quote.strip():
        return None, -1
    grounded = quote.strip()
    start = source_text.find(grounded)
    if start >= 0:
        return grounded, start

    words = re.findall(r"\w+", grounded)
    if not words:
        return None, -1
    pattern = r"[\s\W]*".join(re.escape(word) for word in words)
    match = re.search(pattern, source_text, re.IGNORECASE)
    if not match:
        return None, -1
    return match.group(0), match.start()


def _fallback_edge(candidate: dict[str, Any]) -> dict[str, Any]:
    evidence = str(candidate.get("ref_text", "")).strip()
    return {
        **candidate,
        "relation_label": fallback_relation_label(evidence),
        "label_source": "fallback",
        "confidence": float(candidate.get("confidence", 1.0) or 1.0),
        "resolved": True,
    }


def make_llm_verify_prompt(
    batch_nodes: list[Any],
    known_ids: list[str],
    max_text_chars: int,
    candidate_edges: list[dict[str, Any]],
    unresolved_edges: list[dict[str, Any]],
) -> tuple[str, str]:
    candidates_by_source: dict[str, list[dict[str, Any]]] = {}
    for edge in candidate_edges:
        candidates_by_source.setdefault(str(edge["from"]), []).append(
            {
                "candidate_id": edge["candidate_id"],
                "to_node": edge["to"],
                "evidence_quote": edge.get("ref_text", ""),
            }
        )
    unresolved_by_source: dict[str, list[str]] = {}
    for edge in unresolved_edges:
        unresolved_by_source.setdefault(str(edge["from"]), []).append(
            str(edge.get("ref_text", ""))
        )

    payload_sections = []
    for node in batch_nodes:
        text = (node.text or "").strip()
        payload_sections.append(
            {
                "from_node": node.node_id,
                "title": node.title,
                "text": text[:max_text_chars]
                + ("..." if len(text) > max_text_chars else ""),
                "required_candidates": candidates_by_source.get(node.node_id, []),
                "unresolved_reference_hints": unresolved_by_source.get(node.node_id, []),
            }
        )

    system = (
        "You label explicit contract cross-references with concise descriptions of their "
        "legal effect. Return one JSON object and nothing else. Do not choose from a fixed "
        "taxonomy and never use generic labels such as 'references', 'related to', "
        "'dependency', or 'generic'. Preserve every required candidate exactly once. "
        "Only add a discovered reference when it is explicit in the supplied text. "
        "Evidence must be copied from the source clause and targets must come from "
        "KNOWN_SECTION_IDS."
    )
    user = json.dumps(
        {
            "known_section_ids": known_ids,
            "sections": payload_sections,
            "task": [
                "Return every required candidate exactly once using its candidate_id.",
                "Describe the legal effect in a short free-form relation_label.",
                "Resolve grounded unresolved hints when possible.",
                "Use candidate_id null only for an additional explicit reference.",
            ],
            "good_labels": [
                "payment conditioned on",
                "incorporates definition from",
                "exception to termination right",
                "notice obligation governed by",
            ],
            "schema": {
                "results": [
                    {
                        "from_node": "string",
                        "references": [
                            {
                                "candidate_id": "edge id or null",
                                "to_node": "known section id",
                                "relation_label": "concise contextual legal relationship",
                                "evidence_quote": "verbatim source text",
                                "confidence": 0.0,
                            }
                        ],
                    }
                ]
            },
        },
        ensure_ascii=False,
        indent=2,
    )
    return system, user


def build_edge_batches(
    source_sections: list[Any],
    candidate_edges: list[dict[str, Any]],
    unresolved_edges: list[dict[str, Any]],
    source_batch_limit: int,
    candidate_batch_limit: int,
) -> list[tuple[list[Any], list[dict[str, Any]], list[dict[str, Any]]]]:
    candidates_by_source: dict[str, list[dict[str, Any]]] = {}
    unresolved_by_source: dict[str, list[dict[str, Any]]] = {}
    for edge in candidate_edges:
        candidates_by_source.setdefault(str(edge.get("from", "")), []).append(edge)
    for edge in unresolved_edges:
        unresolved_by_source.setdefault(str(edge.get("from", "")), []).append(edge)

    units: list[tuple[Any, list[dict[str, Any]], list[dict[str, Any]]]] = []
    for section in source_sections:
        candidates = candidates_by_source.get(section.node_id, [])
        chunks = [
            candidates[index : index + candidate_batch_limit]
            for index in range(0, len(candidates), candidate_batch_limit)
        ] or [[]]
        for index, chunk in enumerate(chunks):
            units.append(
                (
                    section,
                    chunk,
                    unresolved_by_source.get(section.node_id, []) if index == 0 else [],
                )
            )

    batches: list[tuple[list[Any], list[dict[str, Any]], list[dict[str, Any]]]] = []
    batch_nodes: list[Any] = []
    batch_candidates: list[dict[str, Any]] = []
    batch_unresolved: list[dict[str, Any]] = []
    for section, candidates, unresolved in units:
        new_source = all(node.node_id != section.node_id for node in batch_nodes)
        exceeds_sources = new_source and len(batch_nodes) >= source_batch_limit
        exceeds_candidates = (
            bool(batch_candidates)
            and len(batch_candidates) + len(candidates) > candidate_batch_limit
        )
        if batch_nodes and (exceeds_sources or exceeds_candidates):
            batches.append((batch_nodes, batch_candidates, batch_unresolved))
            batch_nodes, batch_candidates, batch_unresolved = [], [], []
        if all(node.node_id != section.node_id for node in batch_nodes):
            batch_nodes.append(section)
        batch_candidates.extend(candidates)
        batch_unresolved.extend(unresolved)
    if batch_nodes:
        batches.append((batch_nodes, batch_candidates, batch_unresolved))
    return batches


def enforce_schema_and_ground(
    llm_json: dict[str, Any],
    batch_nodes: list["SectionNode"],
    known_ids_set: set[str],
    candidate_edges: list[dict[str, Any]] | None = None,
) -> tuple[list[dict[str, Any]], list[str]]:
    errors: list[str] = []
    valid_edges: list[dict[str, Any]] = []
    candidates = candidate_edges or []
    candidates_by_id = {edge["candidate_id"]: edge for edge in candidates}
    accepted_candidates: set[str] = set()
    batch_texts = {node.node_id: node.text for node in batch_nodes}

    results = llm_json.get("results") if isinstance(llm_json, dict) else None
    if not isinstance(results, list):
        return [_fallback_edge(edge) for edge in candidates], [
            "Missing top-level results list"
        ]

    for result_index, item in enumerate(results):
        if not isinstance(item, dict):
            errors.append(f"results[{result_index}] is not an object")
            continue
        from_node = item.get("from_node")
        references = item.get("references", [])
        if from_node not in batch_texts:
            errors.append(f"results[{result_index}].from_node not in batch: {from_node}")
            continue
        if not isinstance(references, list):
            errors.append(f"results[{result_index}].references must be a list")
            continue

        for reference_index, reference in enumerate(references):
            path = f"results[{result_index}].references[{reference_index}]"
            if not isinstance(reference, dict):
                errors.append(f"{path} is not an object")
                continue

            candidate_id = reference.get("candidate_id")
            candidate = candidates_by_id.get(candidate_id) if candidate_id else None
            if candidate_id and not candidate:
                errors.append(f"{path} has unknown candidate_id: {candidate_id}")
                continue
            if candidate_id in accepted_candidates:
                errors.append(f"{path} duplicates candidate_id: {candidate_id}")
                continue

            to_node = reference.get("to_node")
            if not isinstance(to_node, str) or to_node not in known_ids_set:
                errors.append(f"{path} has unknown to_node: {to_node}")
                continue
            if to_node == from_node:
                errors.append(f"{path} is a self-reference")
                continue
            if candidate and (
                candidate.get("from") != from_node or candidate.get("to") != to_node
            ):
                errors.append(f"{path} changes deterministic candidate endpoints")
                continue

            quote, start = _ground_quote(
                batch_texts[from_node],
                reference.get("evidence_quote"),
            )
            if quote is None:
                errors.append(f"{path} has ungrounded evidence_quote")
                continue
            label, label_error = normalize_relation_label(
                reference.get("relation_label"),
                known_ids_set,
            )
            if label_error:
                errors.append(f"{path}: {label_error}")
                continue

            try:
                confidence = float(reference.get("confidence", 0.0))
            except (TypeError, ValueError):
                confidence = 0.0
            confidence = max(0.0, min(1.0, confidence))

            if candidate:
                accepted_candidates.add(candidate_id)
                valid_edges.append(
                    {
                        **candidate,
                        "relation_label": label,
                        "label_source": "llm",
                        "confidence": confidence,
                        "resolved": True,
                    }
                )
            else:
                if not EXPLICIT_REFERENCE_CUE.search(quote):
                    errors.append(
                        f"{path} discovered edge lacks an explicit reference phrase"
                    )
                    continue
                valid_edges.append(
                    {
                        "from": from_node,
                        "to": to_node,
                        "candidate_id": None,
                        "ref_type": "LLM_DISCOVERED",
                        "relation_label": label,
                        "label_source": "llm",
                        "ref_text": quote,
                        "ref_start": start,
                        "ref_end": start + len(quote),
                        "resolved": True,
                        "confidence": confidence,
                    }
                )

    for candidate in candidates:
        if candidate["candidate_id"] not in accepted_candidates:
            valid_edges.append(_fallback_edge(candidate))
    return valid_edges, errors


def run_llm_graph_verification(
    sections: list[Any],
    settings: Any,
    candidate_edges: list[dict[str, Any]] | None = None,
    unresolved_edges: list[dict[str, Any]] | None = None,
    check_cancel: Optional[Callable[[], None]] = None,
    progress_callback: Optional[Callable[[dict[str, Any]], None]] = None,
) -> tuple[list[dict[str, Any]], list[str]]:
    from .scaling import compute_edge_verify_params, log_scaling_decision

    prepared_candidates = prepare_candidate_edges(candidate_edges or [])
    naming_candidates, candidate_groups = collapse_candidates_for_naming(prepared_candidates)
    unresolved = unresolved_edges or []
    node_index = {section.node_id: section for section in sections}
    known_ids = list(node_index)[: settings.max_ids_in_prompt]
    for edge in prepared_candidates:
        target = str(edge.get("to", ""))
        if target in node_index and target not in known_ids:
            known_ids.append(target)
    known_ids_set = set(node_index)

    source_ids = {
        str(edge.get("from", ""))
        for edge in [*naming_candidates, *unresolved]
        if edge.get("from")
    }
    source_sections = [
        section for section in sections if section.node_id in source_ids
    ]
    scale_params = compute_edge_verify_params(len(source_sections))
    batch_size = scale_params["batch_size"]
    edge_max_tokens = scale_params["max_tokens"]
    edge_max_text_chars = scale_params["max_text_chars"]
    candidate_batch_limit = max(8, batch_size * 4)
    log_scaling_decision("edge_verify", len(source_sections), scale_params)
    batches = build_edge_batches(
        source_sections,
        naming_candidates,
        unresolved,
        source_batch_limit=batch_size,
        candidate_batch_limit=candidate_batch_limit,
    )
    total_batches = len(batches)
    print(
        f"Candidate edges: {len(prepared_candidates)} | "
        f"Relationships to name: {len(naming_candidates)} | "
        f"Source sections: {len(source_sections)} | "
        f"Expected API calls: {total_batches}"
    )

    if progress_callback:
        progress_callback(
            {
                "stage_key": "graph_creation",
                "label": "Naming clause relationships",
                "completed": 0,
                "total": total_batches,
                "unit": "batches",
                "percent": 0,
                "current_item_label": f"0 / {total_batches} batches complete",
            }
        )

    def process_batch(
        batch_index: int,
        batch: tuple[list[Any], list[dict[str, Any]], list[dict[str, Any]]],
    ) -> tuple[list[dict[str, Any]], list[str]]:
        batch_nodes, batch_candidates, batch_unresolved = batch
        if check_cancel:
            check_cancel()
        system, user = make_llm_verify_prompt(
            batch_nodes,
            known_ids,
            edge_max_text_chars,
            batch_candidates,
            batch_unresolved,
        )
        print(
            f"\n➡️ Edge naming batch {batch_index}/{total_batches} | "
            f"candidates: {len(batch_candidates)}"
        )
        try:
            _, parsed = execute_with_fallback(
                stage_name="edge_verify",
                trace_id=f"batch_{batch_index}",
                stage_config=settings.edge_verify,
                settings=settings,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                temperature=settings.temperature,
                max_tokens=edge_max_tokens,
                response_format=(
                    {"type": "json_object"}
                    if settings.edge_verify.use_response_format
                    else None
                ),
                validator_fn=lambda value: (
                    None
                    if isinstance(value, dict)
                    and isinstance(value.get("results"), list)
                    else (_ for _ in ()).throw(
                        ValueError("Missing top-level results list")
                    )
                ),
            )
            return enforce_schema_and_ground(
                parsed or {},
                batch_nodes,
                known_ids_set,
                batch_candidates,
            )
        except Exception as exc:
            return [
                _fallback_edge(edge) for edge in batch_candidates
            ], [f"Batch {batch_index}: {exc}"]

    all_edges: list[dict[str, Any]] = []
    all_errors: list[str] = []
    completed_batches = 0
    max_workers = getattr(settings, "edge_verify_concurrency", 3)
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(process_batch, index, batch): index
            for index, batch in enumerate(batches, start=1)
        }
        for future in as_completed(futures):
            edges, errors = future.result()
            all_edges.extend(edges)
            all_errors.extend(errors)
            completed_batches += 1
            if progress_callback:
                progress_callback(
                    {
                        "stage_key": "graph_creation",
                        "label": "Naming clause relationships",
                        "completed": completed_batches,
                        "total": total_batches,
                        "unit": "batches",
                        "percent": round(
                            (completed_batches / total_batches) * 100
                        )
                        if total_batches
                        else 100,
                        "current_item_label": (
                            f"Batch {completed_batches} of {total_batches}"
                        ),
                        "validated_edges_so_far": len(all_edges),
                    }
                )

    expanded_edges = expand_named_candidates(all_edges, candidate_groups)
    deduplicated: dict[tuple[str, ...], dict[str, Any]] = {}
    for edge in expanded_edges:
        key = (
            str(edge.get("candidate_id") or ""),
            str(edge.get("from", "")),
            str(edge.get("to", "")),
            str(edge.get("ref_text", "")),
        )
        existing = deduplicated.get(key)
        if not existing or (
            existing.get("label_source") != "llm"
            and edge.get("label_source") == "llm"
        ) or float(edge.get("confidence", 0.0) or 0.0) > float(
            existing.get("confidence", 0.0) or 0.0
        ):
            deduplicated[key] = edge

    print("\n====================")
    print("✅ Contextual edge naming complete")
    print("Candidate edges retained:", len(prepared_candidates))
    print("Output edges:", len(deduplicated))
    print("Validation warnings:", len(all_errors))
    return list(deduplicated.values()), all_errors
