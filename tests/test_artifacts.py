import tempfile
import unittest
from pathlib import Path

from src.artifacts import read_json, write_json_atomic, write_text_atomic


class ArtifactTests(unittest.TestCase):
    def test_atomic_writes_leave_no_temporary_files(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            json_path = root / "artifact.json"
            text_path = root / "artifact.md"

            write_json_atomic(json_path, {"ready": True})
            write_text_atomic(text_path, "# Ready")

            self.assertEqual(read_json(json_path), {"ready": True})
            self.assertEqual(text_path.read_text(encoding="utf-8"), "# Ready")
            self.assertFalse((root / "artifact.json.tmp").exists())
            self.assertFalse((root / "artifact.md.tmp").exists())

    def test_invalid_json_returns_default(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "invalid.json"
            path.write_text("{", encoding="utf-8")
            self.assertEqual(read_json(path, []), [])


if __name__ == "__main__":
    unittest.main()
