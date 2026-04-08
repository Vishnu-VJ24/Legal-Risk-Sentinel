import unittest

from services.scorer import build_overall_score, map_score_to_risk_level, map_severity_to_score
from models.pipeline_state import ScoredClauseCandidate


class PipelineLogicTests(unittest.TestCase):
    def test_map_severity_to_score(self) -> None:
        self.assertEqual(map_severity_to_score(1), 2.0)
        self.assertEqual(map_severity_to_score(5), 10.0)

    def test_risk_level_buckets(self) -> None:
        self.assertEqual(map_score_to_risk_level(3.9), "low")
        self.assertEqual(map_score_to_risk_level(4.0), "medium")
        self.assertEqual(map_score_to_risk_level(6.5), "high")
        self.assertEqual(map_score_to_risk_level(8.0), "critical")

    def test_overall_score_weights_high_risk_clauses(self) -> None:
        clauses = [
            ScoredClauseCandidate(
                clause_id="clause_001",
                clause_text="Indemnify and hold harmless with unlimited liability.",
                clause_category="Indemnification",
                page_number=1,
                bbox=(70.0, 90.0, 500.0, 150.0),
                risk_severity=5,
                is_unfair=True,
                risk_factors=["unlimited liability"],
                rationale="Very high exposure.",
            ),
            ScoredClauseCandidate(
                clause_id="clause_002",
                clause_text="Reasonable confidentiality obligation.",
                clause_category="Confidentiality",
                page_number=1,
                bbox=(70.0, 180.0, 500.0, 240.0),
                risk_severity=2,
                is_unfair=False,
                risk_factors=["limited concern"],
                rationale="Low exposure.",
            ),
        ]
        overall = build_overall_score(clauses)
        self.assertGreaterEqual(overall, 60)
        self.assertLessEqual(overall, 100)


if __name__ == "__main__":
    unittest.main()
