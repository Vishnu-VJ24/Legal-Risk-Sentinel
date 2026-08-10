import unittest
from types import SimpleNamespace
from unittest.mock import patch

from src.clause_repair import _validated_segments, run_llm_clause_repair
from src.references import build_reference_edges
from src.sections import SectionNode


def node(text: str) -> SectionNode:
    return SectionNode("1", "Services", 1, "1. Services", 0, len(text), text, canonical_id="1")


class ClauseRepairTests(unittest.TestCase):
    def test_requires_contiguous_grounded_coverage(self):
        source = node("1. Services\n(a) First duty.\n(b) Second duty.")
        payload = {"segments": [
            {"start_quote": "1. Services", "end_quote": "First duty.", "heading": "1"},
            {"start_quote": "(b) Second", "end_quote": "Second duty.", "heading": "1(b)"},
        ]}
        self.assertIsNotNone(_validated_segments(source, payload))

    def test_rejects_ungrounded_or_gapped_segments(self):
        source = node("1. Services\n(a) First duty.\n(b) Second duty.")
        payload = {"segments": [
            {"start_quote": "1. Services", "end_quote": "Services", "heading": "1"},
            {"start_quote": "(b) Second", "end_quote": "Second duty.", "heading": "1(b)"},
        ]}
        self.assertIsNone(_validated_segments(source, payload))

    def test_references_resolve_against_canonical_id(self):
        source = node("1. Services subject to Section 2.1.")
        target = SectionNode("2.1__2", "Term", 2, "2.1 Term", 40, 50, "2.1 Term", canonical_id="2.1")
        edges, unresolved = build_reference_edges([source, target])
        self.assertEqual(unresolved, [])
        self.assertEqual(edges[0]["to"], "2.1__2")

    @patch("src.clause_repair.execute_with_fallback")
    def test_repair_is_single_attempt_and_uses_its_own_timeout(self, execute):
        source = node("1. Services\n" + "word " * 400)
        source.word_count = 401
        settings = SimpleNamespace(
            clause_repair_min_words=350,
            clause_repair_timeout_sec=25,
            clause_repair=SimpleNamespace(),
        )
        execute.side_effect = TimeoutError("timed out")

        repaired, errors = run_llm_clause_repair([source], settings)

        self.assertEqual(repaired, [source])
        self.assertEqual(len(errors), 1)
        self.assertEqual(execute.call_args.kwargs["timeout_sec"], 25)
        self.assertEqual(execute.call_args.kwargs["max_retries"], 0)


if __name__ == "__main__":
    unittest.main()
