"""Prediction probability and Monte Carlo simulation helpers."""

from __future__ import annotations

import os
import random
from typing import Any


def safe_float(value: Any) -> float | None:
    try:
        if value is None or value == "":
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def safe_int(value: Any) -> int | None:
    try:
        if value is None or value == "":
            return None
        return int(float(value))
    except (TypeError, ValueError):
        return None


def clamp(value: Any, low: float = 0.0, high: float = 100.0, fallback: float | None = None) -> float:
    value = safe_float(value)
    if value is None:
        value = fallback if fallback is not None else low
    return max(low, min(high, value))


def confidence_label(value: Any) -> str:
    value = safe_float(value)
    if value is None:
        return "low"
    if value >= 72:
        return "high"
    if value >= 48:
        return "medium"
    return "low"


def probability_from_score(score: Any, low: float = 1.0, high: float = 18.0) -> float:
    score = clamp(score, 0, 100, 50)
    return round(low + (high - low) * (score / 100.0), 3)


def normalize_race_probabilities(rows: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
    out = [dict(row) for row in rows or []]
    for key, target_sum in [("win_probability", 100.0), ("podium_probability", 300.0), ("top10_probability", 1000.0)]:
        values = [max(0.0, safe_float(row.get(key)) or 0.0) for row in out]
        total = sum(values)
        if total <= 0:
            values = [max(0.01, safe_float(row.get("score")) or 1.0) for row in out]
            total = sum(values)
        for row, value in zip(out, values):
            row[key] = round(value / total * target_sum, 4) if total else 0.0
            if key != "win_probability":
                row[key] = round(min(100.0, row[key]), 4)
    return out


def simulate_race_outcomes(
    rows: list[dict[str, Any]] | None,
    runs: int | None = None,
    seed: int = 42,
    *,
    default_runs: int = 5000,
    github_actions_runs: int = 1000,
    enabled: bool = True,
) -> dict[str, Any]:
    rows = normalize_race_probabilities(rows)
    runs = safe_int(runs) or (github_actions_runs if os.getenv("GITHUB_ACTIONS") else default_runs)
    rng = random.Random(seed)
    tallies = {row.get("driver_id") or row.get("name"): [] for row in rows}
    dnf_counts = {key: 0 for key in tallies}
    for _ in range(max(1, runs)):
        sampled = []
        for row in rows:
            key = row.get("driver_id") or row.get("name")
            dnf = rng.random() < (safe_float(row.get("dnf_probability")) or safe_float(row.get("simulated_dnf_probability")) or 5) / 100.0
            if dnf:
                dnf_counts[key] += 1
            base_score = safe_float(row.get("score")) or (100 - (safe_float(row.get("rank")) or 10))
            noise = rng.gauss(0, 7 + (safe_float(row.get("uncertainty_score")) or 20) / 10)
            sampled.append((key, -999 if dnf else base_score + noise))
        sampled.sort(key=lambda item: item[1], reverse=True)
        for pos, (key, _) in enumerate(sampled, start=1):
            tallies[key].append(pos)
    drivers = []
    row_map = {row.get("driver_id") or row.get("name"): row for row in rows}
    for key, finishes in tallies.items():
        finishes = sorted(finishes)
        n = len(finishes)
        p10 = finishes[max(0, int(n * 0.10) - 1)]
        p90 = finishes[min(n - 1, int(n * 0.90))]
        row = row_map.get(key, {})
        drivers.append({
            "driver_id": key,
            "name": row.get("name"),
            "simulated_win_probability": round(sum(1 for x in finishes if x == 1) / n * 100, 3),
            "simulated_podium_probability": round(sum(1 for x in finishes if x <= 3) / n * 100, 3),
            "simulated_top5_probability": round(sum(1 for x in finishes if x <= 5) / n * 100, 3),
            "simulated_top10_probability": round(sum(1 for x in finishes if x <= 10) / n * 100, 3),
            "simulated_dnf_probability": round(dnf_counts[key] / n * 100, 3),
            "expected_finish": round(sum(finishes) / n, 2),
            "median_finish": finishes[n // 2],
            "p10_finish": p10,
            "p90_finish": p90,
            "upside_finish": p10,
            "downside_finish": p90,
            "confidence_interval_width": p90 - p10,
        })
    drivers.sort(key=lambda row: row["expected_finish"])
    return {
        "enabled": enabled,
        "runs": runs,
        "drivers": drivers,
        "most_volatile_drivers": sorted(drivers, key=lambda row: row["confidence_interval_width"], reverse=True)[:5],
        "safest_top10_drivers": sorted(drivers, key=lambda row: (-row["simulated_top10_probability"], row["confidence_interval_width"]))[:5],
        "dark_horse_candidates": [row for row in drivers if row["simulated_podium_probability"] >= 12 and row["expected_finish"] > 5][:5],
        "bust_risk_candidates": [row for row in drivers if row["simulated_dnf_probability"] >= 12 or row["confidence_interval_width"] >= 8][:5],
    }
