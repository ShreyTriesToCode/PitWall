"""Prediction-vs-actual comparison helpers.

These helpers only compare against actual classifications already present in
trusted project data. They never infer or fabricate race results.
"""

from __future__ import annotations

from math import log2, sqrt
from statistics import mean
from typing import Any, Iterable


MISSING_ACTUAL_STATUSES = {"pending", "unavailable", "incomplete", "source_stale", "source_failed", "not_yet_raced"}


def _driver_id(row: dict[str, Any]) -> str:
    return str(row.get("driver_id") or row.get("name") or "").strip().lower()


def _position(row: dict[str, Any], *keys: str) -> int | None:
    for key in keys:
        try:
            value = int(float(row.get(key)))
        except (TypeError, ValueError):
            continue
        if value > 0:
            return value
    return None


def _ranked(rows: Iterable[dict[str, Any]], *position_keys: str) -> list[dict[str, Any]]:
    cleaned = []
    for row in rows or []:
        if not isinstance(row, dict):
            continue
        pos = _position(row, *position_keys)
        if pos is None:
            continue
        cleaned.append({**row, "_position": pos, "_driver_id": _driver_id(row)})
    return sorted(cleaned, key=lambda item: item["_position"])


def _recall(predicted: list[dict[str, Any]], actual: list[dict[str, Any]], k: int) -> float | None:
    if not predicted or not actual:
        return None
    actual_ids = {row["_driver_id"] for row in actual[: min(k, len(actual))] if row.get("_driver_id")}
    predicted_ids = {row["_driver_id"] for row in predicted[: min(k, len(predicted))] if row.get("_driver_id")}
    return round(len(actual_ids & predicted_ids) / max(1, len(actual_ids)), 4)


def _spearman(errors: list[dict[str, Any]]) -> float | None:
    if len(errors) < 2:
        return None
    actual = [float(row["actual_position"]) for row in errors]
    predicted = [float(row["predicted_position"]) for row in errors]
    mean_actual = mean(actual)
    mean_predicted = mean(predicted)
    numerator = sum((a - mean_actual) * (p - mean_predicted) for a, p in zip(actual, predicted, strict=False))
    den_actual = sqrt(sum((a - mean_actual) ** 2 for a in actual))
    den_predicted = sqrt(sum((p - mean_predicted) ** 2 for p in predicted))
    if not den_actual or not den_predicted:
        return None
    return round(numerator / (den_actual * den_predicted), 4)


def _ndcg(errors: list[dict[str, Any]], k: int) -> float | None:
    if not errors:
        return None
    cutoff = min(k, len(errors))
    grid_size = max(row["actual_position"] for row in errors)
    by_predicted = sorted(errors, key=lambda row: row["predicted_position"])[:cutoff]
    by_actual = sorted(errors, key=lambda row: row["actual_position"])[:cutoff]

    def relevance(row: dict[str, Any]) -> float:
        return max(0.0, float(grid_size + 1 - row["actual_position"]))

    def dcg(rows: list[dict[str, Any]]) -> float:
        return sum((2**relevance(row) - 1) / log2(idx + 2) for idx, row in enumerate(rows))

    ideal = dcg(by_actual)
    if not ideal:
        return None
    return round(dcg(by_predicted) / ideal, 4)


def default_actual_result_comparison(
    *,
    status: str = "pending",
    race: dict[str, Any] | None = None,
    warnings: list[str] | None = None,
    source_health: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    safe_status = status if status in MISSING_ACTUAL_STATUSES or status == "available" else "unavailable"
    return {
        "status": safe_status,
        "race": race or {},
        "predicted_winner": {},
        "actual_winner": {},
        "winner_hit": False,
        "predicted_podium": [],
        "actual_podium": [],
        "podium_recall": None,
        "predicted_top10": [],
        "actual_top10": [],
        "top10_recall": None,
        "driver_position_errors": [],
        "race_by_race": [],
        "metrics": {},
        "source_health": source_health or [],
        "warnings": warnings or [],
    }


def compare_predictions_to_actuals(
    predictions: Iterable[dict[str, Any]] | None,
    actual_result: dict[str, Any] | None,
    *,
    race: dict[str, Any] | None = None,
    source_health: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    predicted = _ranked(predictions or [], "predicted_position", "predicted_finish_position", "likely_finish", "rank")
    actual_rows = _ranked((actual_result or {}).get("classification") or [], "position", "positionOrder", "rank")
    if not predicted:
        return default_actual_result_comparison(
            status="unavailable",
            race=race,
            source_health=source_health,
            warnings=["Prediction rows are unavailable for actual-result comparison."],
        )
    if not actual_rows:
        return default_actual_result_comparison(
            status="pending",
            race=race,
            source_health=source_health,
            warnings=["Trusted actual race classification is not available yet."],
        )

    actual_by_id = {row["_driver_id"]: row for row in actual_rows if row.get("_driver_id")}
    errors = []
    for row in predicted:
        actual = actual_by_id.get(row.get("_driver_id"))
        if not actual:
            continue
        predicted_position = row["_position"]
        actual_position = actual["_position"]
        errors.append({
            "driver_id": row.get("driver_id") or actual.get("driver_id"),
            "name": row.get("name") or actual.get("name"),
            "team": row.get("team") or actual.get("team"),
            "predicted_position": predicted_position,
            "actual_position": actual_position,
            "position_error": abs(predicted_position - actual_position),
        })

    if not errors:
        return default_actual_result_comparison(
            status="incomplete",
            race=race,
            source_health=source_health,
            warnings=["Actual results exist but no predicted drivers could be matched by driver_id."],
        )

    predicted_winner = predicted[0] if predicted else {}
    actual_winner = actual_rows[0] if actual_rows else {}
    winner_hit = bool(predicted_winner.get("_driver_id") and predicted_winner.get("_driver_id") == actual_winner.get("_driver_id"))
    mae = round(mean(row["position_error"] for row in errors), 4)
    rmse = round(sqrt(mean(row["position_error"] ** 2 for row in errors)), 4)
    exact_position_accuracy = round(sum(1 for row in errors if row["position_error"] == 0) / len(errors), 4)
    comparison = {
        "status": "available",
        "race": race or {},
        "predicted_winner": {k: v for k, v in predicted_winner.items() if not k.startswith("_")},
        "actual_winner": {k: v for k, v in actual_winner.items() if not k.startswith("_")},
        "winner_hit": winner_hit,
        "predicted_podium": [{k: v for k, v in row.items() if not k.startswith("_")} for row in predicted[:3]],
        "actual_podium": [{k: v for k, v in row.items() if not k.startswith("_")} for row in actual_rows[:3]],
        "podium_recall": _recall(predicted, actual_rows, 3),
        "predicted_top10": [{k: v for k, v in row.items() if not k.startswith("_")} for row in predicted[:10]],
        "actual_top10": [{k: v for k, v in row.items() if not k.startswith("_")} for row in actual_rows[:10]],
        "top10_recall": _recall(predicted, actual_rows, 10),
        "driver_position_errors": sorted(errors, key=lambda row: row["position_error"], reverse=True),
        "race_by_race": [{
            "race": race or {},
            "winner_hit": winner_hit,
            "podium_recall": _recall(predicted, actual_rows, 3),
            "top10_recall": _recall(predicted, actual_rows, 10),
            "position_mae": mae,
        }],
        "metrics": {
            "winner_hit": winner_hit,
            "podium_recall": _recall(predicted, actual_rows, 3),
            "top10_recall": _recall(predicted, actual_rows, 10),
            "exact_position_accuracy": exact_position_accuracy,
            "mae": mae,
            "rmse": rmse,
            "spearman_rank_correlation": _spearman(errors),
            "ndcg_at_3": _ndcg(errors, 3),
            "ndcg_at_10": _ndcg(errors, 10),
        },
        "source_health": source_health or [],
        "warnings": [],
    }
    return comparison
