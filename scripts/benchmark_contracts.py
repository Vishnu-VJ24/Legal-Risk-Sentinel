"""Reproducible contract extraction benchmark and reviewed-gold evaluator."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def _load_json(path: Path, fallback: Any) -> Any:
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else fallback


def _coverage(sections: list[dict[str, Any]], source_text: str) -> tuple[int, int, float]:
    intervals = sorted(
        (int(item["start_char"]), int(item["end_char"]))
        for item in sections if item.get("is_analysis_unit", True)
    )
    covered, end = set(), 0
    for start, finish in intervals:
        start, finish = max(start, end), max(start, finish)
        covered.update(range(start, finish))
        end = max(end, finish)
    non_whitespace = {index for index, char in enumerate(source_text) if not char.isspace()}
    covered_non_whitespace = len(covered & non_whitespace)
    return covered_non_whitespace, len(non_whitespace) - covered_non_whitespace, (covered_non_whitespace / len(non_whitespace) if non_whitespace else 1.0)


def evaluate_run(run_dir: Path, gold: dict[str, Any]) -> dict[str, Any]:
    sections = _load_json(run_dir / "sections.json", [])
    edges = _load_json(run_dir / "edges.json", [])
    extraction = _load_json(run_dir / "extraction.json", {})
    expected = gold.get("clauses", [])
    expected_ids = {item["canonical_id"] for item in expected}
    actual = [item for item in sections if item.get("is_analysis_unit", True)]
    actual_ids = {item.get("canonical_id") or item["node_id"].split("__", 1)[0] for item in actual}
    correct = expected_ids & actual_ids
    precision = len(correct) / len(actual_ids) if actual_ids else 0.0
    recall = len(correct) / len(expected_ids) if expected_ids else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    source_text = (run_dir / "normalized_text.txt").read_text(encoding="utf-8") if (run_dir / "normalized_text.txt").exists() else ""
    text_chars = len(source_text) or int(extraction.get("text_chars", 0))
    covered, unassigned, coverage = _coverage(actual, source_text)
    expected_refs = {(item["from"], item["to"]) for item in gold.get("references", [])}
    actual_refs = {(item.get("from"), item.get("to")) for item in edges}
    ref_correct = expected_refs & actual_refs
    return {
        "pdf": gold.get("pdf", run_dir.name), "expected_clauses": len(expected_ids),
        "extracted_clauses": len(actual_ids), "correctly_extracted": len(correct),
        "missed_clauses": sorted(expected_ids - actual_ids), "false_positive_clauses": sorted(actual_ids - expected_ids),
        "precision": round(precision, 4), "recall": round(recall, 4), "f1": round(f1, 4),
        "content_chars": text_chars, "covered_non_whitespace_chars": covered, "unassigned_non_whitespace_chars": unassigned, "content_coverage": round(coverage, 4),
        "edges": len(edges), "reference_precision": round(len(ref_correct) / len(actual_refs), 4) if actual_refs else 0.0,
        "reference_recall": round(len(ref_correct) / len(expected_refs), 4) if expected_refs else 0.0,
        "extractor": extraction.get("extractor_used"), "ocr_used": extraction.get("ocr_used", False),
        "ocr_cache_hit": extraction.get("ocr_cache_hit", False),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--runs", type=Path, required=True, help="Directory containing one artifact directory per PDF")
    parser.add_argument("--gold", type=Path, default=Path("benchmarks/gold"))
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    reports = []
    for gold_path in sorted(args.gold.glob("*.json")):
        gold = _load_json(gold_path, {})
        run_dir = args.runs / gold.get("run_dir", gold_path.stem)
        reports.append(evaluate_run(run_dir, gold))
    aggregate = {
        "pdfs": len(reports),
        "expected_clauses": sum(item["expected_clauses"] for item in reports),
        "extracted_clauses": sum(item["extracted_clauses"] for item in reports),
        "correctly_extracted": sum(item["correctly_extracted"] for item in reports),
        "content_coverage": round(sum(item["content_coverage"] for item in reports) / len(reports), 4) if reports else 0.0,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps({"runs": reports, "aggregate": aggregate}, indent=2), encoding="utf-8")
    print(json.dumps({"aggregate": aggregate, "output": str(args.output)}, indent=2))


if __name__ == "__main__":
    main()
