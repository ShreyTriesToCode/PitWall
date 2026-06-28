#!/usr/bin/env python
"""Report oversized generated artifacts before committing."""

from __future__ import annotations

import argparse
import json
import subprocess
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
FORBIDDEN_CACHE_PREFIXES = [
    "fastf1_cache/",
    "data_cache/full_races/",
    "models/saved_models/",
]
FIA_DOCUMENT_CACHE_PREFIX = "data_cache/fia-documents/"


def is_forbidden_cache_path(relative: str) -> bool:
    if any(relative.startswith(prefix) for prefix in FORBIDDEN_CACHE_PREFIXES):
        return True
    if not relative.startswith(FIA_DOCUMENT_CACHE_PREFIX):
        return False
    lower = relative.lower()
    return "/pdfs/" in lower or lower.endswith(".pdf") or ".pdf." in lower


def iter_files(path: Path):
    if path.is_file():
        yield path
    elif path.is_dir():
        yield from (item for item in path.rglob("*") if item.is_file())


def staged_files(base: Path) -> list[Path]:
    try:
        result = subprocess.run(
            ["git", "diff", "--cached", "--name-only"],
            cwd=base,
            check=True,
            text=True,
            capture_output=True,
        )
    except Exception:
        return []
    return [base / line.strip() for line in result.stdout.splitlines() if line.strip()]


def main() -> int:
    parser = argparse.ArgumentParser(description="Check PitWall generated artifact sizes.")
    parser.add_argument("--base-dir", default=".")
    parser.add_argument("--warn-mb", type=float, default=25.0)
    parser.add_argument("--fail-mb", type=float, default=95.0)
    parser.add_argument("--staged", action="store_true", help="Check currently staged files instead of default artifact paths.")
    parser.add_argument("--fail-cache-paths", action="store_true", help="Fail if staged files include reproducible runtime cache directories.")
    parser.add_argument("--max-large-json-count", type=int, default=4, help="Fail when more than this many JSON artifacts exceed warn threshold.")
    args = parser.parse_args()
    base = Path(args.base_dir)
    base = base.resolve()
    rows = []
    failed = []
    forbidden = []
    files = staged_files(base) if args.staged else [file for relative in DEFAULT_PATHS for file in iter_files(base / relative)]
    for file in files:
        if not file.exists() or not file.is_file():
            continue
        relative = str(file.relative_to(base)).replace("\\", "/")
        if args.fail_cache_paths and is_forbidden_cache_path(relative):
            forbidden.append({"path": relative, "reason": "runtime_cache_not_for_git"})
        size_mb = file.stat().st_size / 1024 / 1024
        if size_mb >= args.warn_mb:
            row = {"path": relative, "size_mb": round(size_mb, 3)}
            rows.append(row)
            if size_mb >= args.fail_mb:
                failed.append(row)
    large_json = [row for row in rows if row["path"].endswith(".json")]
    if len(large_json) > args.max_large_json_count:
        failed.append({"path": "multiple-large-json-artifacts", "size_mb": None, "count": len(large_json)})
    failed.extend(forbidden)
    print(json.dumps({
        "ok": not failed,
        "warn_mb": args.warn_mb,
        "fail_mb": args.fail_mb,
        "large_artifacts": rows,
        "forbidden_staged_cache_paths": forbidden,
        "failed": failed,
    }, indent=2))
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
