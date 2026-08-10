import unittest
from types import SimpleNamespace
from unittest.mock import patch

from src.report_generator import (
    build_clause_ledger,
    build_compatibility_report,
    build_ledger_fallback_markdown,
    build_report_payload,
    run_report_generator,
)


class ReportGeneratorTests(unittest.TestCase):
    def test_grouped_risk_is_attached_to_every_source_clause(self):
        sections = [
            SimpleNamespace(
                node_id="1(a)",
                canonical_id="1(a)",
                title="First",
                parent_id="1",
                page_start=1,
                page_end=1,
                sha256="a",
            ),
            SimpleNamespace(
                node_id="1(b)",
                canonical_id="1(b)",
                title="Second",
                parent_id="1",
                page_start=1,
                page_end=2,
                sha256="b",
            ),
        ]
        risk = {
            "section_id": "1",
            "source_clause_ids": ["1(a)", "1(b)"],
            "analysis_status": "SUCCESS",
            "risk_flags": [],
        }

        ledger = build_clause_ledger(sections, [risk])

        self.assertEqual(len(ledger), 2)
        self.assertTrue(all(item["risk_result"] is risk for item in ledger))

    def test_compatibility_json_is_deterministic(self):
        report = build_compatibility_report(
            [
                {
                    "section_id": "4.2",
                    "title": "Termination",
                    "risk_flags": [
                        {
                            "severity": "HIGH",
                            "rationale": "Termination is unilateral.",
                            "evidence_quotes": ["Either party may terminate."],
                        }
                    ],
                }
            ],
            "markdown",
        )

        self.assertEqual(report["overall_document_risk"], "high")
        self.assertEqual(report["recommended_review_order"], ["4.2"])
        self.assertEqual(report["top_risks"][0]["section_id"], "4.2")

    def test_ledger_fallback_is_renderable_markdown(self):
        markdown = build_ledger_fallback_markdown(
            [
                {
                    "section_id": "4.2",
                    "title": "Termination",
                    "risk_result": {
                        "section_id": "4.2",
                        "risk_flags": [
                            {
                                "risk_type": "termination",
                                "severity": "HIGH",
                                "rationale": "Termination is unilateral.",
                                "evidence_quotes": ["Either party may terminate."],
                            }
                        ],
                    },
                }
            ],
            "Model unavailable",
        )
        self.assertIn("# Contract Risk Report", markdown)
        self.assertIn("### HIGH: 4.2 - Termination", markdown)
        self.assertIn("> Either party may terminate.", markdown)

    def test_report_payload_is_compact_but_keeps_material_findings(self):
        payload = build_report_payload(
            [{
                "section_id": "4.2",
                "title": "Termination",
                "source_clause_ids": ["4.2(a)", "4.2(b)"],
                "overall_section_risk": "x" * 800,
                "risk_flags": [
                    {"severity": "LOW", "risk_type": "other", "rationale": "low"},
                    {"severity": "HIGH", "risk_type": "termination", "rationale": "high", "evidence_quotes": ["evidence"]},
                ],
            }]
        )
        self.assertEqual(payload[0]["source_clause_count"], 2)
        self.assertEqual(len(payload[0]["findings"]), 1)
        self.assertEqual(payload[0]["findings"][0]["severity"], "HIGH")
        self.assertLessEqual(len(payload[0]["overall_section_risk"]), 500)

    def test_no_successful_risks_returns_typed_fallback(self):
        section = SimpleNamespace(
            node_id="1",
            canonical_id="1",
            title="Scope",
            parent_id=None,
            page_start=1,
            page_end=1,
            sha256="hash",
        )

        result = run_report_generator([], SimpleNamespace(), sections=[section])

        self.assertEqual(result.report_json["generation_mode"], "ledger_fallback")
        self.assertEqual(result.generation_meta["mode"], "ledger_fallback")
        self.assertIn("# Contract Risk Report", result.markdown)

    @patch("src.llm_client.execute_with_fallback")
    def test_successful_synthesis_keeps_compatibility_json(self, execute):
        execute.return_value = ("# Executive Review\n\nGrounded report.", None)
        settings = SimpleNamespace(final_report=SimpleNamespace())
        risks = [
            {
                "section_id": "2",
                "title": "Payment",
                "source_clause_ids": ["2(a)"],
                "analysis_status": "SUCCESS",
                "risk_flags": [
                    {
                        "severity": "MEDIUM",
                        "rationale": "Payment timing is uncertain.",
                        "evidence_quotes": ["promptly after invoice"],
                    }
                ],
            }
        ]

        result = run_report_generator(risks, settings)

        self.assertEqual(result.report_json["generation_mode"], "markdown")
        self.assertEqual(result.report_json["overall_document_risk"], "medium")
        self.assertTrue(result.markdown.startswith("# Executive Review"))


if __name__ == "__main__":
    unittest.main()
