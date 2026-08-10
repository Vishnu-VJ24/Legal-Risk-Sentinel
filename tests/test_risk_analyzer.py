import unittest
from types import SimpleNamespace

from src.risk_analyzer import (
    build_risk_group_ownership,
    build_risk_groups,
    dedupe_risk_results,
    remap_edges_to_risk_groups,
    risk_group_cache_key,
)


class RiskAnalyzerDedupeTests(unittest.TestCase):
    def test_parent_groups_preserve_every_atomic_clause(self):
        parent = SimpleNamespace(node_id="1.1", title="Definitions")
        first = SimpleNamespace(node_id="1.1(a)", parent_id="1.1", title="A", text="Alpha clause", start_char=0)
        second = SimpleNamespace(node_id="1.1(b)", parent_id="1.1", title="B", text="Beta clause", start_char=20)
        standalone = SimpleNamespace(node_id="2.1", parent_id=None, title="Term", text="Term clause", start_char=40)
        groups = build_risk_groups([first, second, standalone], [parent, first, second, standalone], max_chars=1000)
        self.assertEqual([group.node_id for group in groups], ["1.1", "2.1"])
        self.assertEqual([clause for group in groups for clause in group.source_clause_ids], ["1.1(a)", "1.1(b)", "2.1"])

    def test_edges_are_remapped_to_group_owners(self):
        parent = SimpleNamespace(node_id="1", title="One")
        other_parent = SimpleNamespace(node_id="2", title="Two")
        first = SimpleNamespace(node_id="1(a)", parent_id="1", title="A", text="Alpha", start_char=0)
        second = SimpleNamespace(node_id="2(a)", parent_id="2", title="B", text="Beta", start_char=20)
        groups = build_risk_groups(
            [first, second],
            [parent, other_parent, first, second],
        )
        ownership = build_risk_group_ownership(groups)
        edges = remap_edges_to_risk_groups(
            [
                {
                    "from": "1(a)",
                    "to": "2(a)",
                    "relation_label": "payment conditioned on",
                    "relation_labels": ["payment conditioned on"],
                    "evidence_quotes": ["subject to Section 2(a)"],
                }
            ],
            ownership,
        )

        self.assertEqual([(edge["from"], edge["to"]) for edge in edges], [("1", "2")])
        self.assertEqual(edges[0]["relation_label"], "payment conditioned on")
        self.assertEqual(edges[0]["relation_labels"], ["payment conditioned on"])

    def test_cache_key_changes_with_relationship_context(self):
        clause = SimpleNamespace(node_id="1(a)", parent_id=None, title="A", text="Alpha", start_char=0)
        group = build_risk_groups([clause], [clause])[0]
        first = risk_group_cache_key(group, [], "nvidia", "model")
        second = risk_group_cache_key(
            group,
            [
                {
                    "from": "1(a)",
                    "to": "2",
                    "relation_label": "expressly links to referenced clause",
                }
            ],
            "nvidia",
            "model",
        )
        self.assertNotEqual(first, second)

    def test_collapses_duplicate_section_results(self):
        results = [
            {
                "section_id": "2.1",
                "title": "Term",
                "analysis_status": "SUCCESS",
                "risk_flags": [
                    {
                        "risk_type": "termination",
                        "severity": "medium",
                        "rationale": "Short cure period.",
                        "evidence_quotes": ["ten days"],
                    }
                ],
            },
            {
                "section_id": "2.1",
                "title": "Term",
                "analysis_status": "SUCCESS",
                "risk_flags": [
                    {
                        "risk_type": "termination",
                        "severity": "medium",
                        "rationale": "Short cure period.",
                        "evidence_quotes": ["ten days"],
                    }
                ],
            },
        ]

        deduped = dedupe_risk_results(results)

        self.assertEqual(len(deduped), 1)
        self.assertEqual(deduped[0]["section_id"], "2.1")
        self.assertEqual(len(deduped[0]["risk_flags"]), 1)

    def test_preserves_distinct_flags_for_duplicate_section(self):
        results = [
            {
                "section_id": "2.1",
                "title": "Term",
                "analysis_status": "SUCCESS",
                "risk_flags": [
                    {
                        "risk_type": "termination",
                        "severity": "medium",
                        "rationale": "Short cure period.",
                        "evidence_quotes": ["ten days"],
                    }
                ],
            },
            {
                "section_id": "2.1",
                "title": "Term",
                "analysis_status": "SUCCESS",
                "risk_flags": [
                    {
                        "risk_type": "termination",
                        "severity": "high",
                        "rationale": "Immediate termination for incurable breach.",
                        "evidence_quotes": ["immediately terminate"],
                    }
                ],
            },
        ]

        deduped = dedupe_risk_results(results)

        self.assertEqual(len(deduped), 1)
        self.assertEqual(len(deduped[0]["risk_flags"]), 2)

    def test_prefers_first_successful_result(self):
        results = [
            {
                "section_id": "2.1",
                "title": "Term",
                "analysis_status": "FAILED_ANALYSIS",
                "analysis_error": "omitted",
                "risk_flags": [],
            },
            {
                "section_id": "2.1",
                "title": "Term",
                "analysis_status": "SUCCESS",
                "analysis_error": "",
                "risk_flags": [
                    {
                        "risk_type": "termination",
                        "severity": "medium",
                        "rationale": "Short cure period.",
                        "evidence_quotes": ["ten days"],
                    }
                ],
            },
        ]

        deduped = dedupe_risk_results(results)

        self.assertEqual(len(deduped), 1)
        self.assertEqual(deduped[0]["analysis_status"], "SUCCESS")
        self.assertEqual(len(deduped[0]["risk_flags"]), 1)


if __name__ == "__main__":
    unittest.main()
