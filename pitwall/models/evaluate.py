"""Model evaluation helpers for PitWall training and notebooks."""

from __future__ import annotations

from math import sqrt
from typing import Any, Iterable

import numpy as np
import pandas as pd
from scipy.stats import spearmanr
from sklearn.metrics import brier_score_loss, mean_absolute_error, ndcg_score


def _average(values: Iterable[float]) -> float | None:
    clean = [float(value) for value in values if value is not None and np.isfinite(float(value))]
    return float(sum(clean) / len(clean)) if clean else None


def ranking_metrics(frame: pd.DataFrame, predicted_finish: Iterable[float], *, race_col: str = "race_id") -> dict[str, Any]:
    """Evaluate ranking quality race-by-race.

    The lower predicted finish position is considered better, matching the F1
    finish-position convention. Validation is grouped by race so a model cannot
    look good by merely separating points scorers across unrelated events.
    """

    if frame.empty:
        return {}
    predicted = list(predicted_finish)
    if len(predicted) != len(frame):
        raise ValueError("predicted_finish length must match evaluation frame")

    eval_df = frame[[race_col, "driver_id", "finish_position"]].copy()
    eval_df["predicted_finish_position"] = predicted
    buckets: dict[str, list[float]] = {
        "winner_hit_rate": [],
        "top3_recall": [],
        "top10_recall": [],
        "ndcg_at_3": [],
        "ndcg_at_10": [],
        "spearman": [],
    }

    for _, group in eval_df.groupby(race_col):
        if len(group) < 3:
            continue
        actual_order = group.sort_values("finish_position")
        predicted_order = group.sort_values("predicted_finish_position")
        buckets["winner_hit_rate"].append(float(str(actual_order.iloc[0]["driver_id"]) == str(predicted_order.iloc[0]["driver_id"])))

        for k, key in [(3, "top3_recall"), (10, "top10_recall")]:
            cutoff = min(k, len(group))
            actual = set(actual_order.head(cutoff)["driver_id"])
            predicted_set = set(predicted_order.head(cutoff)["driver_id"])
            buckets[key].append(len(actual & predicted_set) / max(1, len(actual)))

        try:
            relevance = (len(group) + 1 - group["finish_position"].astype(float)).to_numpy()[None, :]
            predicted_score = (len(group) + 1 - group["predicted_finish_position"].astype(float)).to_numpy()[None, :]
            buckets["ndcg_at_3"].append(float(ndcg_score(relevance, predicted_score, k=min(3, len(group)))))
            buckets["ndcg_at_10"].append(float(ndcg_score(relevance, predicted_score, k=min(10, len(group)))))
        except Exception:
            pass

        try:
            rho = spearmanr(group["finish_position"].astype(float), group["predicted_finish_position"].astype(float)).correlation
            if np.isfinite(rho):
                buckets["spearman"].append(float(rho))
        except Exception:
            pass

    return {key: round(value, 4) for key, vals in buckets.items() if (value := _average(vals)) is not None}


def regression_metrics(actual_finish: Iterable[float], predicted_finish: Iterable[float]) -> dict[str, float]:
    actual = np.asarray(list(actual_finish), dtype=float)
    predicted = np.asarray(list(predicted_finish), dtype=float)
    if len(actual) != len(predicted):
        raise ValueError("actual and predicted lengths must match")
    return {
        "finish_mae": float(mean_absolute_error(actual, predicted)),
        "finish_rmse": float(sqrt(np.mean((actual - predicted) ** 2))),
    }


def probability_metrics(targets: Iterable[int], probabilities: Iterable[float]) -> dict[str, float]:
    y = np.asarray(list(targets), dtype=int)
    probs = np.clip(np.asarray(list(probabilities), dtype=float), 0.0, 1.0)
    if len(y) != len(probs):
        raise ValueError("targets and probabilities lengths must match")
    if len(y) == 0:
        return {}
    return {"brier_score": float(brier_score_loss(y, probs))}


def evaluate_finish_predictions(frame: pd.DataFrame, predicted_finish: Iterable[float]) -> dict[str, Any]:
    predicted = list(predicted_finish)
    return {
        **regression_metrics(frame["finish_position"].astype(float), predicted),
        "ranking": ranking_metrics(frame, predicted),
        "rows": int(len(frame)),
        "races": int(frame["race_id"].nunique()) if "race_id" in frame else None,
    }


def compare_metric_tables(champion: dict[str, Any] | None, challenger: dict[str, Any] | None) -> dict[str, Any]:
    """Return a conservative champion/challenger comparison summary."""

    champion = champion or {}
    challenger = challenger or {}
    champion_mae = champion.get("finish_mae") or champion.get("finish_position", {}).get("mae")
    challenger_mae = challenger.get("finish_mae") or challenger.get("finish_position", {}).get("mae")
    winner = "insufficient_metrics"
    if champion_mae is not None and challenger_mae is not None:
        winner = "challenger" if float(challenger_mae) <= float(champion_mae) else "champion"
    return {
        "winner": winner,
        "champion_finish_mae": champion_mae,
        "challenger_finish_mae": challenger_mae,
        "ranking_metrics_required": True,
    }
