"""Validate PitWall cache manifest structure."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


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
    for key, entry in data["entries"].items():
        if not isinstance(entry, dict):
            bad.append(f"{key}: entry is not an object")
            continue
        for required in ["source", "file_path", "latest_run_action", "reason", "validation_status"]:
            if required not in entry:
                bad.append(f"{key}: missing {required}")
        file_path = Path(entry.get("file_path", ""))
        if entry.get("latest_run_action") in {"reused", "refreshed", "fallback_reused"} and not file_path.exists():
            bad.append(f"{key}: referenced file is missing: {file_path}")
    if bad:
        print(json.dumps({"ok": False, "errors": bad}, indent=2))
        return 1
    print(json.dumps({"ok": True, "entry_count": len(data["entries"])}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
