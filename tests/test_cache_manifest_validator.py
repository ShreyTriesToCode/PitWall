import tempfile
import unittest
from pathlib import Path

from scripts.validate_cache_manifest import resolve_manifest_path


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


if __name__ == "__main__":
    unittest.main()
