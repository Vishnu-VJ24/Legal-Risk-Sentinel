import tempfile
import unittest

from src.server import JobStatus, _build_status_payload


class ServerStatusTests(unittest.TestCase):
    def test_completed_run_reports_missing_artifacts_without_reopening_job(self):
        with tempfile.TemporaryDirectory() as directory:
            job = JobStatus(
                run_id="completed-run",
                file_name="contract.pdf",
                stage="REPORT_READY",
                status="complete",
                out_dir=directory,
            )

            status = _build_status_payload(job)

            self.assertEqual(status["status"], "complete")
            self.assertFalse(status["report_ready"])
            self.assertEqual(len(status["artifact_warnings"]), 2)


if __name__ == "__main__":
    unittest.main()
