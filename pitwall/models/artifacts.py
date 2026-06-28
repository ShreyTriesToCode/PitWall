"""Artifact utilities for PitWall model bundles and metadata."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import joblib

from pitwall.io.atomic import atomic_write_json as shared_atomic_write_json


def atomic_write_json(path: Path, payload: dict[str, Any]) -> Path:
    return shared_atomic_write_json(path, payload, indent=2, ensure_ascii=True)


def save_model_bundle(bundle: dict[str, Any], path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    joblib.dump(bundle, tmp, compress=("xz", 3))
    loaded = joblib.load(tmp)
    if not isinstance(loaded, dict):
        tmp.unlink(missing_ok=True)
        raise ValueError("saved model bundle did not reload as a dictionary")
    tmp.replace(path)
    return path


def load_model_bundle(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    loaded = joblib.load(path)
    if not isinstance(loaded, dict):
        raise ValueError(f"{path} did not contain a PitWall model bundle")
    return loaded


def load_model_metadata(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    return data if isinstance(data, dict) else {}


def artifact_summary(bundle_path: Path, meta_path: Path) -> dict[str, Any]:
    meta = load_model_metadata(meta_path)
    return {
        "bundle_path": str(bundle_path),
        "bundle_exists": bundle_path.exists(),
        "bundle_size_mb": round(bundle_path.stat().st_size / (1024 * 1024), 3) if bundle_path.exists() else 0,
        "metadata_path": str(meta_path),
        "metadata_exists": meta_path.exists(),
        "trained_at": meta.get("trained_at"),
        "schema_version": meta.get("model_schema_version"),
        "feature_columns_hash": meta.get("feature_columns_hash"),
    }
