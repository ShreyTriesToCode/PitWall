import json
import tempfile
import unittest
from pathlib import Path

from pitwall.io.atomic import atomic_write_json, atomic_write_text


class AtomicIoTests(unittest.TestCase):
    def test_atomic_write_json_writes_valid_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "payload.json"
            atomic_write_json(path, {"ok": True, "items": [1, 2]})
            self.assertEqual(json.loads(path.read_text(encoding="utf-8")), {"ok": True, "items": [1, 2]})

    def test_atomic_write_json_creates_missing_parent_directories(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "missing" / "parents" / "payload.json"
            atomic_write_json(path, {"created": True})
            self.assertTrue(path.exists())
            self.assertEqual(json.loads(path.read_text(encoding="utf-8"))["created"], True)

    def test_atomic_write_text_replaces_existing_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "payload.txt"
            atomic_write_text(path, "old")
            atomic_write_text(path, "new")
            self.assertEqual(path.read_text(encoding="utf-8"), "new")

    def test_atomic_write_json_does_not_leave_temp_files_on_success(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = root / "payload.json"
            atomic_write_json(path, {"ok": True})
            leftovers = [item for item in root.iterdir() if item.name.startswith("payload.json.tmp-")]
            self.assertEqual(leftovers, [])


if __name__ == "__main__":
    unittest.main()
