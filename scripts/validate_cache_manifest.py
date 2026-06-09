"""Validate PitWall cache manifest structure."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PORTABLE_PATH_ROOTS = {
    "briefings",
    "data_cache",
    "model_artifacts",
    "models",
    "notebooks",
}


def resolve_manifest_path(raw_path: str, *, repo_root: Path = ROOT) -> Path:
    """Resolve checked-in manifest paths across local and CI workspaces."""
    path = Path(raw_path)
    if not raw_path:
        return path
    if not path.is_absolute():
        return repo_root / path
    parts = path.parts
    for marker in PORTABLE_PATH_ROOTS:
        if marker in parts:
            marker_index = parts.index(marker)
            candidate = repo_root.joinpath(*parts[marker_index:])
            if candidate.exists():
                return candidate
    if path.exists():
        return path
    return path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--path", default="data_cache/cache_manifest.json")
    parser.add_argument("--allow-missing", action="store_true")
    args = parser.parse_args()
    path = Path(args.path)
    if not path.exists():
        if args.allow_missing:
            print(json.dumps({"ok": True, "missing": True, "path": str(path)}))
            return 0
        print(json.dumps({"ok": False, "error": f"{path} is missing"}))
        return 1
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or not isinstance(data.get("entries"), dict):
        print(json.dumps({"ok": False, "error": "manifest must contain an entries object"}))
        return 1
    bad = []
    remapped_paths = 0
    for key, entry in data["entries"].items():
        if not isinstance(entry, dict):
            bad.append(f"{key}: entry is not an object")
            continue
        for required in ["source", "file_path", "latest_run_action", "reason", "validation_status"]:
            if required not in entry:
                bad.append(f"{key}: missing {required}")
        raw_file_path = str(entry.get("file_path", ""))
        file_path = Path(raw_file_path)
        resolved_path = resolve_manifest_path(raw_file_path)
        if file_path.is_absolute() and file_path != resolved_path and resolved_path.exists():
            remapped_paths += 1
        if entry.get("latest_run_action") in {"reused", "refreshed", "fallback_reused"} and not resolved_path.exists():
            bad.append(f"{key}: referenced file is missing: {raw_file_path} (resolved: {resolved_path})")
    if bad:
        print(json.dumps({"ok": False, "errors": bad}, indent=2))
        return 1
    print(json.dumps({"ok": True, "entry_count": len(data["entries"]), "remapped_paths": remapped_paths}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
