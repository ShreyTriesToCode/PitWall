import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from scripts.validate_cache_manifest import portable_display_path, resolve_manifest_path


class CacheManifestValidatorTests(unittest.TestCase):
    def test_absolute_local_cache_path_resolves_inside_repo_checkout(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            cache_file = root / "data_cache" / "full_races" / "2026-6.json.gz"
            cache_file.parent.mkdir(parents=True, exist_ok=True)
            cache_file.write_text("{}", encoding="utf-8")

            local_mac_path = "/Users/shrey-mac/Downloads/Codes/PitWall-main 2/data_cache/full_races/2026-6.json.gz"

            self.assertEqual(resolve_manifest_path(local_mac_path, repo_root=root), cache_file)

    def test_relative_cache_path_resolves_from_repo_root(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.assertEqual(resolve_manifest_path("data_cache/cache_manifest.json", repo_root=root), root / "data_cache" / "cache_manifest.json")

    def test_allow_missing_reports_missing_references_as_warnings(self):
        with tempfile.TemporaryDirectory() as tmp:
            manifest = Path(tmp) / "cache_manifest.json"
            manifest.write_text(json.dumps({
                "schema_version": 1,
                "entries": {
                    "jolpica_full_race:2099:99": {
                        "source": "Jolpica",
                        "file_path": "/Users/shrey-mac/Downloads/Codes/PitWall-main 2/data_cache/full_races/2099-99.json.gz",
                        "latest_run_action": "reused",
                        "reason": "cache_valid",
                        "validation_status": "valid",
                    }
                },
            }), encoding="utf-8")

            strict = subprocess.run(
                [sys.executable, "scripts/validate_cache_manifest.py", "--path", str(manifest)],
                cwd=Path(__file__).resolve().parents[1],
                text=True,
                capture_output=True,
                check=False,
            )
            relaxed = subprocess.run(
                [sys.executable, "scripts/validate_cache_manifest.py", "--path", str(manifest), "--allow-missing"],
                cwd=Path(__file__).resolve().parents[1],
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(strict.returncode, 1)
            self.assertEqual(relaxed.returncode, 0)
            payload = json.loads(relaxed.stdout)
            self.assertEqual(payload["warning_count"], 1)
            self.assertEqual(payload["missing_references_sample"][0]["key"], "jolpica_full_race:2099:99")
            self.assertEqual(payload["missing_references_sample"][0]["file_path"], "data_cache/full_races/2099-99.json.gz")

    def test_warning_display_paths_do_not_expose_local_workspace_prefixes(self):
        self.assertEqual(
            portable_display_path("/Users/shrey-mac/Downloads/Codes/PitWall-main 2/data_cache/full_races/2026-6.json.gz"),
            "data_cache/full_races/2026-6.json.gz",
        )


if __name__ == "__main__":
    unittest.main()
