"""Offline dataset bootstrap planning helpers."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .f1db import F1DB_LATEST_VERIFIED_RELEASE


def dataset_bootstrap_plan(source: str, base_dir: str | Path = "data_cache/external", dry_run: bool = True) -> dict[str, Any]:
    source_key = source.strip().lower().replace("_", "-")
    base_dir = Path(base_dir)
    if source_key in {"f1db", "f1-db"}:
        artifact_dir = base_dir / "f1db" / F1DB_LATEST_VERIFIED_RELEASE
        sqlite_path = artifact_dir / "f1db.sqlite"
        return {
            "source": "f1db",
            "dry_run": dry_run,
            "will_download": not dry_run,
            "release": F1DB_LATEST_VERIFIED_RELEASE,
            "license": "CC-BY-4.0",
            "artifact_dir": str(artifact_dir),
            "env": {
                "F1DB_ENABLED": "true",
                "F1DB_SQLITE_PATH": str(sqlite_path),
                "F1DB_RELEASE_TAG": F1DB_LATEST_VERIFIED_RELEASE,
            },
            "steps": [
                "Download the selected F1DB SQLite release artifact from GitHub.",
                "Place or extract f1db.sqlite at F1DB_SQLITE_PATH.",
                "Run the PitWall source-health check to confirm table coverage.",
            ],
        }
    if source_key in {"relbench", "relbench-f1", "rel-f1"}:
        artifact_dir = base_dir / "relbench-f1"
        return {
            "source": "relbench",
            "dry_run": dry_run,
            "will_download": False,
            "license": "CC-BY-4.0",
            "artifact_dir": str(artifact_dir),
            "env": {
                "RELBENCH_F1_ENABLED": "true",
                "RELBENCH_F1_DOWNLOAD": "false",
            },
            "steps": [
                "Install the optional relbench package in the local Python environment.",
                "Run the RelBench status check with download disabled first.",
                "Set RELBENCH_F1_DOWNLOAD=true only for an explicit offline benchmark refresh.",
            ],
        }
    raise ValueError(f"Unsupported dataset source: {source}")
