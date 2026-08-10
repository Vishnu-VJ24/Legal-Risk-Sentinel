from __future__ import annotations

from collections import defaultdict
from typing import Any

from .llm_verify import fallback_relation_label

LABEL_SOURCE_RANK = {"llm": 0, "fallback": 1, "legacy": 2}


def _label_detail(edge: dict[str, Any]) -> dict[str, Any]:
    label = str(
        edge.get("relation_label")
        or fallback_relation_label(str(edge.get("ref_text", "")))
    ).strip()
    source = str(
        edge.get("label_source")
        or ("legacy" if edge.get("relations") else "fallback")
    )
    try:
        confidence = float(edge.get("confidence", 0.0) or 0.0)
    except (TypeError, ValueError):
        confidence = 0.0
    return {
        "label": label[:80],
        "source": source,
        "confidence": max(0.0, min(1.0, confidence)),
    }


def aggregate_edges_raw(edges_raw: list[dict[str, Any]]) -> list[dict[str, Any]]:
    aggregated = defaultdict(
        lambda: {
            "from": None,
            "to": None,
            "label_details": {},
            "evidence_quotes": set(),
            "sources": set(),
            "max_confidence": 0.0,
        }
    )

    for edge in edges_raw:
        source_id = edge.get("from")
        target_id = edge.get("to")
        if not source_id or not target_id or source_id == target_id:
            continue

        record = aggregated[(source_id, target_id)]
        record["from"] = source_id
        record["to"] = target_id
        detail = _label_detail(edge)
        existing = record["label_details"].get(detail["label"])
        if not existing or (
            LABEL_SOURCE_RANK.get(detail["source"], 3),
            -detail["confidence"],
        ) < (
            LABEL_SOURCE_RANK.get(existing["source"], 3),
            -existing["confidence"],
        ):
            record["label_details"][detail["label"]] = detail

        evidence = str(edge.get("ref_text", "")).strip()
        if evidence:
            record["evidence_quotes"].add(evidence)
        record["sources"].add(str(edge.get("ref_type") or "UNKNOWN"))
        record["max_confidence"] = max(
            record["max_confidence"],
            detail["confidence"],
        )

    output = []
    for record in aggregated.values():
        details = sorted(
            record["label_details"].values(),
            key=lambda item: (
                LABEL_SOURCE_RANK.get(item["source"], 3),
                -item["confidence"],
                item["label"],
            ),
        )
        primary = details[0]
        output.append(
            {
                "from": record["from"],
                "to": record["to"],
                "relation_label": primary["label"],
                "relation_labels": [detail["label"] for detail in details],
                "relation_label_details": details,
                "label_source": primary["source"],
                "evidence_quotes": sorted(record["evidence_quotes"]),
                "sources": sorted(record["sources"]),
                "max_confidence": record["max_confidence"],
                "evidence_quotes_n": len(record["evidence_quotes"]),
            }
        )
    return output
