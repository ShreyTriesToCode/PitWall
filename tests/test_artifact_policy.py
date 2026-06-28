import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


class ArtifactPolicyTests(unittest.TestCase):
    def run_staged_check(self, root):
        repo = Path(__file__).resolve().parents[1]
        script = repo / "scripts" / "check_artifact_sizes.py"
        return subprocess.run(
            [sys.executable, str(script), "--base-dir", str(root), "--staged", "--fail-cache-paths"],
            text=True,
            capture_output=True,
        )

    def test_staged_runtime_cache_path_fails_artifact_size_check(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            subprocess.run(["git", "init"], cwd=root, check=True, stdout=subprocess.DEVNULL)
            cache_file = root / "data_cache" / "full_races" / "2026-1.json.gz"
            cache_file.parent.mkdir(parents=True, exist_ok=True)
            cache_file.write_text("{}", encoding="utf-8")
            subprocess.run(["git", "add", str(cache_file.relative_to(root))], cwd=root, check=True)

            result = self.run_staged_check(root)

        self.assertNotEqual(result.returncode, 0)
        payload = json.loads(result.stdout)
        self.assertFalse(payload["ok"])
        self.assertEqual(payload["forbidden_staged_cache_paths"][0]["path"], "data_cache/full_races/2026-1.json.gz")

    def test_staged_fia_parsed_json_is_allowed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            subprocess.run(["git", "init"], cwd=root, check=True, stdout=subprocess.DEVNULL)
            parsed_file = root / "data_cache" / "fia-documents" / "2026" / "event" / "parsed" / "doc.json"
            parsed_file.parent.mkdir(parents=True, exist_ok=True)
            parsed_file.write_text("{}", encoding="utf-8")
            subprocess.run(["git", "add", str(parsed_file.relative_to(root))], cwd=root, check=True)

            result = self.run_staged_check(root)

        payload = json.loads(result.stdout)
        self.assertEqual(result.returncode, 0)
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["forbidden_staged_cache_paths"], [])

    def test_staged_fia_pdf_is_forbidden(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            subprocess.run(["git", "init"], cwd=root, check=True, stdout=subprocess.DEVNULL)
            pdf_file = root / "data_cache" / "fia-documents" / "2026" / "event" / "pdfs" / "doc.pdf"
            pdf_file.parent.mkdir(parents=True, exist_ok=True)
            pdf_file.write_bytes(b"%PDF-1.4\n")
            subprocess.run(["git", "add", str(pdf_file.relative_to(root))], cwd=root, check=True)

            result = self.run_staged_check(root)

        self.assertNotEqual(result.returncode, 0)
        payload = json.loads(result.stdout)
        self.assertFalse(payload["ok"])
        self.assertEqual(payload["forbidden_staged_cache_paths"][0]["path"], "data_cache/fia-documents/2026/event/pdfs/doc.pdf")


if __name__ == "__main__":
    unittest.main()
