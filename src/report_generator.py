from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Callable

SEVERITY_ORDER = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}


@dataclass(frozen=True)
class ReportResult:
    report_json: dict[str, Any]
    markdown: str
    ledger: list[dict[str, Any]]
    generation_meta: dict[str, Any]
    warning: str | None = None


def build_clause_ledger(sections: list[Any], risks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    risk_by_clause: dict[str, dict[str, Any]] = {}
    for risk in risks:
        clause_ids = risk.get("source_clause_ids") or [risk.get("section_id")]
        for clause_id in clause_ids:
            if clause_id:
                risk_by_clause[str(clause_id)] = risk

    ledger = []
    for index, section in enumerate(sections, start=1):
        section_id = str(section.node_id)
        risk = risk_by_clause.get(section_id, {})
        ledger.append(
            {
                "ledger_id": f"clause_{index:04d}",
                "section_id": section_id,
                "canonical_id": getattr(section, "canonical_id", section_id),
                "title": section.title,
                "parent_id": getattr(section, "parent_id", None),
                "page_start": getattr(section, "page_start", -1),
                "page_end": getattr(section, "page_end", -1),
                "source_sha256": getattr(section, "sha256", ""),
                "analysis_status": risk.get("analysis_status", "NOT_ANALYZED"),
                "risk_result": risk,
            }
        )
    return ledger


def build_compatibility_report(risks: list[dict[str, Any]], generation_mode: str) -> dict[str, Any]:
    top_risks: list[dict[str, Any]] = []
    summaries: list[dict[str, Any]] = []

    for risk in risks:
        flags = [flag for flag in risk.get("risk_flags", []) if isinstance(flag, dict)]
        if not flags:
            continue
        ranked = sorted(
            flags,
            key=lambda flag: SEVERITY_ORDER.get(str(flag.get("severity", "LOW")).upper(), 3),
        )
        highest = str(ranked[0].get("severity", "LOW")).lower()
        section_id = str(risk.get("section_id", ""))
        title = str(risk.get("title", "") or section_id)
        summaries.append(
            {
                "section_id": section_id,
                "title": title,
                "summary": ranked[0].get("rationale", "Review the grounded findings."),
                "risk_count": len(ranked),
                "highest_severity": highest,
            }
        )
        for flag in ranked:
            top_risks.append(
                {
                    "section_id": section_id,
                    "title": title,
                    "severity": str(flag.get("severity", "LOW")).lower(),
                    "summary": flag.get("rationale", "Review this clause."),
                    "evidence_quotes": list(flag.get("evidence_quotes", [])),
                }
            )

    top_risks.sort(
        key=lambda item: SEVERITY_ORDER.get(str(item["severity"]).upper(), 3)
    )
    summaries.sort(
        key=lambda item: (
            SEVERITY_ORDER.get(str(item["highest_severity"]).upper(), 3),
            item["section_id"],
        )
    )
    overall_risk = top_risks[0]["severity"] if top_risks else "low"
    document_summary = (
        f"The analysis identified {len(top_risks)} grounded risk finding"
        f"{'' if len(top_risks) == 1 else 's'} across {len(summaries)} section group"
        f"{'' if len(summaries) == 1 else 's'}."
        if top_risks
        else "No material risks were identified in the available validated analyses."
    )
    return {
        "document_summary": document_summary,
        "overall_document_risk": overall_risk,
        "overall_risk_score": overall_risk,
        "top_risks": top_risks[:10],
        "all_section_summaries": summaries,
        "recommended_review_order": [item["section_id"] for item in summaries],
        "generation_mode": generation_mode,
    }


def build_ledger_fallback_markdown(
    ledger: list[dict[str, Any]], reason: str
) -> str:
    lines = [
        "# Contract Risk Report",
        "",
        "## Executive Review",
        "",
        "This report was assembled from validated clause findings because narrative synthesis was unavailable.",
        "",
    ]
    findings: list[tuple[str, dict[str, Any], dict[str, Any]]] = []
    seen: set[tuple[str, str, str]] = set()
    for item in ledger:
        for flag in item.get("risk_result", {}).get("risk_flags", []):
            key = (
                str(item["risk_result"].get("section_id", item["section_id"])),
                str(flag.get("risk_type", "")),
                str(flag.get("rationale", "")),
            )
            if key in seen:
                continue
            seen.add(key)
            findings.append((str(flag.get("severity", "LOW")).upper(), item, flag))

    findings.sort(key=lambda finding: SEVERITY_ORDER.get(finding[0], 3))
    if not findings:
        lines.extend(
            ["No material risks were identified in the available clause analyses.", ""]
        )
    else:
        lines.extend(["## Findings", ""])
        for severity, item, flag in findings[:10]:
            lines.extend(
                [
                    f"### {severity}: {item['section_id']} - {item['title']}",
                    "",
                    str(flag.get("rationale", "Review this clause.")),
                    "",
                ]
            )
            for quote in flag.get("evidence_quotes", [])[:2]:
                lines.extend([f"> {quote}", ""])
    lines.extend(["## Generation Note", "", reason])
    return "\n".join(lines)


def _compact_text(value: Any, limit: int) -> str:
    text = " ".join(str(value or "").split())
    return text if len(text) <= limit else f"{text[:limit - 3].rstrip()}..."


def build_report_payload(risks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Provide the executive writer the material facts, not the full audit ledger."""
    payload: list[dict[str, Any]] = []
    for risk in risks:
        flags = [flag for flag in risk.get("risk_flags", []) if isinstance(flag, dict)]
        ranked = sorted(
            flags,
            key=lambda flag: SEVERITY_ORDER.get(str(flag.get("severity", "LOW")).upper(), 3),
        )
        material = [
            flag for flag in ranked
            if str(flag.get("severity", "LOW")).upper() in {"CRITICAL", "HIGH"}
        ]
        # Keep one lower-severity example so the document-level assessment is not
        # distorted into a high-risk-only summary.
        if not material and ranked:
            material = ranked[:1]
        payload.append(
            {
                "section_id": str(risk.get("section_id", "")),
                "title": _compact_text(risk.get("title", ""), 140),
                "overall_section_risk": _compact_text(risk.get("overall_section_risk", ""), 500),
                "source_clause_count": len(risk.get("source_clause_ids") or []),
                "findings": [
                    {
                        "risk_type": _compact_text(flag.get("risk_type", "other"), 80),
                        "severity": str(flag.get("severity", "LOW")).upper(),
                        "rationale": _compact_text(flag.get("rationale", ""), 500),
                        "evidence_quotes": [
                            _compact_text(quote, 600)
                            for quote in (flag.get("evidence_quotes") or [])[:2]
                        ],
                        "affected_clause_ids": list(flag.get("affected_clause_ids") or [])[:12],
                    }
                    for flag in material
                ],
            }
        )
    return payload


def _report_prompt(risks: list[dict[str, Any]]) -> tuple[str, str]:
    system = (
        "You are a Chief Legal Officer. Write a concise, grounded executive contract "
        "review in Markdown. Use headings, bullets, and Markdown tables when useful. "
        "Do not return JSON or code fences. Only make claims supported by the supplied "
        "grouped findings and verbatim evidence."
    )
    user = (
        "Create the executive review now. Include an overall assessment, the most "
        "material findings, quoted evidence where it matters, and a recommended review "
        "order. Do not omit a supplied high or critical finding.\n\n"
        "COMPACT GROUPED RISK RESULTS:\n"
        + json.dumps(build_report_payload(risks), ensure_ascii=False)
    )
    return system, user


def run_report_generator(
    structured_risks: list[dict[str, Any]],
    settings: Any,
    sections: list[Any] | None = None,
    progress_callback: Callable[[str, int, int, str], None] | None = None,
) -> ReportResult:
    from .llm_client import execute_with_fallback
    from .scaling import compute_report_params, log_scaling_decision

    usable_risks = [
        risk
        for risk in structured_risks
        if risk.get("analysis_status") == "SUCCESS"
        or risk.get("analysis_status") == "PARTIAL_VALIDATION_ERRORS"
    ]
    ledger = build_clause_ledger(sections or [], structured_risks)

    if not usable_risks:
        warning = "No successful LLM risk analyses were available."
        report_json = build_compatibility_report(
            structured_risks, "ledger_fallback"
        )
        return ReportResult(
            report_json=report_json,
            markdown=build_ledger_fallback_markdown(ledger, warning),
            ledger=ledger,
            generation_meta={
                "mode": "ledger_fallback",
                "reason": warning,
                "ledger_clause_count": len(ledger),
            },
            warning=warning,
        )

    risky_count = sum(bool(risk.get("risk_flags")) for risk in usable_risks)
    scale_params = compute_report_params(risky_count)
    log_scaling_decision("final_report", risky_count, scale_params)
    system, user = _report_prompt(usable_risks)
    prompt_bytes = len(user.encode("utf-8"))

    try:
        if progress_callback:
            progress_callback("report", 0, 1, "Generating executive Markdown review")
        markdown, _ = execute_with_fallback(
            "final_report",
            "macro_report",
            settings.final_report,
            settings,
            [{"role": "system", "content": system}, {"role": "user", "content": user}],
            max_tokens=scale_params["max_tokens"],
            race_nvidia_keys=True,
        )
        if not markdown.strip():
            raise ValueError("Model returned an empty Markdown report")
        if progress_callback:
            progress_callback("report", 1, 1, "Executive Markdown review complete")
        return ReportResult(
            report_json=build_compatibility_report(usable_risks, "markdown"),
            markdown=markdown.strip(),
            ledger=ledger,
            generation_meta={
                "mode": "markdown",
                "ledger_clause_count": len(ledger),
                "risk_group_count": len(usable_risks),
                "prompt_bytes": prompt_bytes,
            },
        )
    except Exception as exc:
        warning = f"Narrative synthesis was unavailable: {exc}"
        return ReportResult(
            report_json=build_compatibility_report(
                usable_risks, "ledger_fallback"
            ),
            markdown=build_ledger_fallback_markdown(ledger, warning),
            ledger=ledger,
            generation_meta={
                "mode": "ledger_fallback",
                "reason": warning,
                "ledger_clause_count": len(ledger),
            },
            warning=warning,
        )
