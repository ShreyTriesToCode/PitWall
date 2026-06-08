"""Validation gates for PitWall model training and prediction contracts."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable

import pandas as pd

from pitwall.validation.leakage import forbidden_feature_columns


TARGET_COLUMNS = {"finish_position", "is_win", "is_podium", "is_top10", "points"}
IDENTIFIER_COLUMNS = {"race_id", "season", "round", "driver_id", "driver_name", "constructor", "race_name", "circuit_id"}


def validate_training_frame(frame: pd.DataFrame, feature_columns: Iterable[str]) -> dict[str, Any]:
    errors: list[str] = []
    features = list(feature_columns)
    if frame.empty:
        errors.append("training frame is empty")
    for required in ["race_id", "season", "round", "driver_id", "finish_position"]:
        if required not in frame.columns:
            errors.append(f"missing required column: {required}")
    missing_features = [col for col in features if col not in frame.columns]
    if missing_features:
        errors.append(f"missing feature columns: {', '.join(missing_features[:20])}")
    leaky = sorted((TARGET_COLUMNS | IDENTIFIER_COLUMNS) & set(features))
    if leaky:
        errors.append(f"feature list includes target/identifier columns: {', '.join(leaky)}")
    if "race_id" in frame and frame["race_id"].nunique() < 4:
        errors.append("training frame has too few race groups for chronological validation")
    return {"ok": not errors, "errors": errors, "rows": int(len(frame)), "race_groups": int(frame["race_id"].nunique()) if "race_id" in frame else 0}


def validate_feature_stage(stage: str, columns: Iterable[str]) -> dict[str, Any]:
    forbidden = forbidden_feature_columns(stage, columns)
    return {"ok": not forbidden, "stage": stage, "forbidden_columns": forbidden}


def assert_chronological_split(train_df: pd.DataFrame, valid_df: pd.DataFrame) -> None:
    if train_df.empty or valid_df.empty:
        raise AssertionError("chronological split requires non-empty train and validation frames")
    if {"season", "round"} - set(train_df.columns) or {"season", "round"} - set(valid_df.columns):
        raise AssertionError("chronological split requires season and round columns")
    train_max = tuple(train_df[["season", "round"]].max().astype(int).tolist())
    valid_min = tuple(valid_df[["season", "round"]].min().astype(int).tolist())
    if train_max >= valid_min:
        raise AssertionError(f"validation starts before or at train end: train_max={train_max} valid_min={valid_min}")


def validate_artifact_paths(paths: Iterable[Path]) -> dict[str, Any]:
    rows = []
    for path in paths:
        rows.append({"path": str(path), "exists": path.exists(), "size": path.stat().st_size if path.exists() else 0})
    return {"ok": all(row["exists"] and row["size"] > 0 for row in rows), "artifacts": rows}


def promotion_gate(champion: dict[str, Any] | None, challenger: dict[str, Any] | None) -> dict[str, Any]:
    """Small, explicit promotion gate for notebooks and CI summaries."""

    challenger = challenger or {}
    ranking = challenger.get("ranking") or challenger.get("finish_position", {}).get("ranking") or {}
    checks = {
        "has_finish_mae": challenger.get("finish_mae") is not None or challenger.get("finish_position", {}).get("mae") is not None,
        "has_ranking_metrics": bool(ranking),
        "has_top10_recall": ranking.get("top10_recall") is not None,
    }
    return {
        "approved": all(checks.values()),
        "checks": checks,
        "champion_present": bool(champion),
        "notes": "Promotion still requires backend/frontend validation and artifact save/load checks.",
    }
