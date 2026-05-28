#!/usr/bin/env python
"""Report oversized generated artifacts before committing."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


DEFAULT_PATHS = [
    "data_cache/frontend-contract.json",
    "data_cache/model-status.json",
    "data_cache/latest-model-debug.json",
    "briefings/index.json",
    "models/saved_models",
    "fastf1_cache",
    "data_cache/full_races",
]


def iter_files(path: Path):
    if path.is_file():
        yield path
    elif path.is_dir():
        yield from (item for item in path.rglob("*") if item.is_file())


def main() -> int:
    parser = argparse.ArgumentParser(description="Check PitWall generated artifact sizes.")
    parser.add_argument("--base-dir", default=".")
    parser.add_argument("--warn-mb", type=float, default=25.0)
    parser.add_argument("--fail-mb", type=float, default=95.0)
    args = parser.parse_args()
    base = Path(args.base_dir)
    rows = []
    failed = []
    for relative in DEFAULT_PATHS:
        path = base / relative
        for file in iter_files(path):
            size_mb = file.stat().st_size / 1024 / 1024
            if size_mb >= args.warn_mb:
                row = {"path": str(file.relative_to(base)), "size_mb": round(size_mb, 3)}
                rows.append(row)
                if size_mb >= args.fail_mb:
                    failed.append(row)
    print(json.dumps({"ok": not failed, "warn_mb": args.warn_mb, "fail_mb": args.fail_mb, "large_artifacts": rows}, indent=2))
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
