import unittest

from src.scaling import compute_report_params


class ScalingTests(unittest.TestCase):
    def test_executive_report_budget_is_bounded(self):
        self.assertEqual(compute_report_params(14)["max_tokens"], 4096)
        self.assertEqual(compute_report_params(500)["max_tokens"], 4096)
        self.assertEqual(compute_report_params(1)["max_tokens"], 3072)


if __name__ == "__main__":
    unittest.main()
