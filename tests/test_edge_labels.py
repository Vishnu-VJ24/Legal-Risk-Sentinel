import unittest
from types import SimpleNamespace

from src.aggregation import aggregate_edges_raw
from src.llm_verify import (
    build_edge_batches,
    collapse_candidates_for_naming,
    enforce_schema_and_ground,
    expand_named_candidates,
    normalize_relation_label,
    prepare_candidate_edges,
)


def section(node_id: str, text: str):
    return SimpleNamespace(node_id=node_id, title=node_id, text=text)


class EdgeLabelTests(unittest.TestCase):
    def setUp(self):
        self.source = section(
            "1",
            "Payment is subject to Section 2 before any amount becomes due.",
        )
        self.candidate = prepare_candidate_edges(
            [
                {
                    "from": "1",
                    "to": "2",
                    "ref_type": "SECTION",
                    "ref_text": "subject to Section 2",
                    "ref_start": 11,
                    "ref_end": 31,
                    "resolved": True,
                }
            ]
        )[0]

    def test_valid_free_form_label_covers_candidate_once(self):
        payload = {
            "results": [
                {
                    "from_node": "1",
                    "references": [
                        {
                            "candidate_id": self.candidate["candidate_id"],
                            "to_node": "2",
                            "relation_label": "payment conditioned on",
                            "evidence_quote": "subject to Section 2",
                            "confidence": 0.91,
                        }
                    ],
                }
            ]
        }

        edges, errors = enforce_schema_and_ground(
            payload,
            [self.source],
            {"1", "2"},
            [self.candidate],
        )

        self.assertEqual(errors, [])
        self.assertEqual(len(edges), 1)
        self.assertEqual(edges[0]["relation_label"], "payment conditioned on")
        self.assertEqual(edges[0]["label_source"], "llm")

    def test_missing_or_generic_label_preserves_candidate_with_fallback(self):
        payload = {
            "results": [
                {
                    "from_node": "1",
                    "references": [
                        {
                            "candidate_id": self.candidate["candidate_id"],
                            "to_node": "2",
                            "relation_label": "references",
                            "evidence_quote": "subject to Section 2",
                            "confidence": 1,
                        }
                    ],
                }
            ]
        }

        edges, errors = enforce_schema_and_ground(
            payload,
            [self.source],
            {"1", "2"},
            [self.candidate],
        )

        self.assertEqual(len(edges), 1)
        self.assertEqual(edges[0]["label_source"], "fallback")
        self.assertEqual(edges[0]["relation_label"], "conditioned by referenced clause")
        self.assertTrue(errors)

    def test_duplicate_candidate_response_is_not_duplicated(self):
        reference = {
            "candidate_id": self.candidate["candidate_id"],
            "to_node": "2",
            "relation_label": "payment conditioned on",
            "evidence_quote": "subject to Section 2",
            "confidence": 0.9,
        }
        payload = {
            "results": [
                {
                    "from_node": "1",
                    "references": [reference, dict(reference)],
                }
            ]
        }

        edges, errors = enforce_schema_and_ground(
            payload,
            [self.source],
            {"1", "2"},
            [self.candidate],
        )

        self.assertEqual(len(edges), 1)
        self.assertIn("duplicates candidate_id", errors[0])

    def test_discovered_edge_requires_explicit_grounded_reference(self):
        payload = {
            "results": [
                {
                    "from_node": "1",
                    "references": [
                        {
                            "candidate_id": None,
                            "to_node": "2",
                            "relation_label": "payment conditioned on",
                            "evidence_quote": "before any amount becomes due",
                            "confidence": 0.8,
                        }
                    ],
                }
            ]
        }

        edges, errors = enforce_schema_and_ground(
            payload,
            [self.source],
            {"1", "2"},
            [],
        )

        self.assertEqual(edges, [])
        self.assertIn("lacks an explicit reference phrase", errors[0])

    def test_unknown_identifier_in_label_is_rejected(self):
        label, error = normalize_relation_label(
            "conditioned by Section 999",
            {"1", "2"},
        )
        self.assertIsNone(label)
        self.assertIn("unknown identifier", error)

    def test_label_is_capped_at_word_boundary(self):
        label, error = normalize_relation_label(
            "payment obligation conditioned on delivery and acceptance of all required "
            "documents before the final settlement amount becomes due and payable",
            {"1", "2"},
        )
        self.assertIsNone(error)
        self.assertLessEqual(len(label), 80)
        self.assertFalse(label.endswith(" "))

    def test_aggregation_prefers_llm_and_retains_all_labels(self):
        edges = aggregate_edges_raw(
            [
                {
                    **self.candidate,
                    "relation_label": "conditioned by referenced clause",
                    "label_source": "fallback",
                    "confidence": 1,
                },
                {
                    **self.candidate,
                    "relation_label": "payment conditioned on",
                    "label_source": "llm",
                    "confidence": 0.8,
                },
            ]
        )

        self.assertEqual(len(edges), 1)
        self.assertEqual(edges[0]["relation_label"], "payment conditioned on")
        self.assertEqual(
            edges[0]["relation_labels"],
            ["payment conditioned on", "conditioned by referenced clause"],
        )
        self.assertNotIn("relations", edges[0])

    def test_large_source_is_split_by_candidate_limit(self):
        candidates = [
            {
                **self.candidate,
                "candidate_id": f"edge_{index}",
                "ref_start": index,
            }
            for index in range(17)
        ]

        batches = build_edge_batches(
            [self.source],
            candidates,
            [],
            source_batch_limit=4,
            candidate_batch_limit=8,
        )

        self.assertEqual([len(batch[1]) for batch in batches], [8, 8, 1])

    def test_relationship_naming_preserves_every_citation(self):
        originals = prepare_candidate_edges(
            [
                {**self.candidate, "ref_text": "subject to Section 2", "ref_start": 11},
                {**self.candidate, "ref_text": "under Section 2", "ref_start": 42},
            ]
        )
        representatives, groups = collapse_candidates_for_naming(originals)
        self.assertEqual(len(representatives), 1)
        named = [{**representatives[0], "relation_label": "payment conditioned on", "label_source": "llm"}]

        expanded = expand_named_candidates(named, groups)

        self.assertEqual(len(expanded), 2)
        self.assertTrue(all(edge["relation_label"] == "payment conditioned on" for edge in expanded))
        self.assertEqual({edge["candidate_id"] for edge in expanded}, {edge["candidate_id"] for edge in originals})


if __name__ == "__main__":
    unittest.main()
