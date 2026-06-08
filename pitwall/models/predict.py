"""Prediction helpers for model-backed PitWall outputs."""

from __future__ import annotations

from typing import Any


def generate_ml_predictions(drivers, race, current_round_data, bundle, *, stage: str = "pre_weekend"):
    import f1_briefing

    return f1_briefing.ml_predict_probabilities(drivers, race, current_round_data, bundle, stage=stage)


def top10_from_full_grid(full_grid: list[dict[str, Any]], *, limit: int = 10) -> list[dict[str, Any]]:
    return sorted(full_grid, key=lambda row: (row.get("rank") is None, row.get("rank", 999)))[:limit]


def validate_top10_subset(top10: list[dict[str, Any]], full_grid: list[dict[str, Any]]) -> bool:
    full_ids = {str(row.get("driver_id")) for row in full_grid}
    return all(str(row.get("driver_id")) in full_ids for row in top10)


def normalize_prediction_row(row: dict[str, Any], rank: int | None = None) -> dict[str, Any]:
    driver_id = str(row.get("driver_id") or row.get("name") or "").strip()
    normalized = {
        **row,
        "driver_id": driver_id,
        "name": row.get("name") or driver_id or "Unknown driver",
        "team": row.get("team") or "Unknown team",
        "rank": row.get("rank") if row.get("rank") is not None else rank,
        "predicted_position": row.get("predicted_position") or row.get("predicted_finish") or row.get("predicted_finish_position") or rank,
        "probability": row.get("probability") or row.get("top10_probability") or row.get("points_probability") or 0,
        "rank_score": row.get("rank_score") or row.get("score") or 0,
        "confidence": row.get("confidence") or row.get("prediction_confidence") or 0,
        "prediction_trust": row.get("prediction_trust") or row.get("prediction_trust_label") or "Trust pending",
        "explanation": row.get("explanation") or {},
        "source_notes": row.get("source_notes") or {},
        "expected_strategy": row.get("expected_strategy") or {},
        "points_probability": row.get("points_probability") or row.get("top10_probability") or 0,
        "fastest_lap_probability": row.get("fastest_lap_probability") or 0,
        "position_range": row.get("position_range") or [rank, rank],
    }
    return normalized
