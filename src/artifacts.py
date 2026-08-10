from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class ArtifactNames:
    extraction: str = "extraction.json"
    normalized_text: str = "normalized_text.txt"
    sections: str = "sections.json"
    edges: str = "edges.json"
    partial_risks: str = "risk_analysis.partial.json"
    risks: str = "risk_analysis.json"
    risk_progress: str = "risk_progress.json"
    clause_ledger: str = "clause_ledger.json"
    report_generation: str = "report_generation.json"
    report_json: str = "final_report.json"
    report_markdown: str = "final_report.md"


ARTIFACTS = ArtifactNames()


def artifact_path(out_dir: str | Path, filename: str) -> Path:
    return Path(out_dir) / filename


def read_json(path: str | Path, default: Any = None) -> Any:
    try:
        source = Path(path)
        if source.exists():
            return json.loads(source.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, TypeError):
        pass
    return default


def write_json_atomic(path: str | Path, value: Any) -> None:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(destination.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, ensure_ascii=False), encoding="utf-8")
    temporary.replace(destination)


def write_text_atomic(path: str | Path, value: str) -> None:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(destination.suffix + ".tmp")
    temporary.write_text(value, encoding="utf-8")
    temporary.replace(destination)
