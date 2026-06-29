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


def _round_to_target(values: list[float], target_sum: float, *, cap: float | None = None) -> list[float]:
    rounded = [round(min(cap, value) if cap is not None else value, 4) for value in values]
    remaining = round(target_sum - sum(rounded), 4)
    if abs(remaining) < 0.0001:
        return rounded

    if remaining > 0:
        for idx in range(len(rounded) - 1, -1, -1):
            capacity = remaining if cap is None else round(cap - rounded[idx], 4)
            if capacity <= 0:
                continue
            delta = min(capacity, remaining)
            rounded[idx] = round(rounded[idx] + delta, 4)
            remaining = round(remaining - delta, 4)
            if remaining <= 0:
                break
    else:
        remaining = abs(remaining)
        for idx in range(len(rounded) - 1, -1, -1):
            capacity = rounded[idx]
            if capacity <= 0:
                continue
            delta = min(capacity, remaining)
            rounded[idx] = round(rounded[idx] - delta, 4)
            remaining = round(remaining - delta, 4)
            if remaining <= 0:
                break
    return rounded


def _normalize_to_sum(values: list[float], target_sum: float, *, cap: float | None = None) -> list[float]:
    if not values:
        return []

    target = min(target_sum, cap * len(values)) if cap is not None else target_sum
    if target <= 0:
        return [0.0 for _ in values]

    total = sum(values)
    if total <= 0:
        values = [1.0 for _ in values]
        total = sum(values)

    if cap is None:
        scaled = [value / total * target for value in values]
        return _round_to_target(scaled, target)

    result = [0.0 for _ in values]
    active = set(range(len(values)))
    remaining = target
    weights = values[:]

    while active and remaining > 0:
        weight_total = sum(weights[idx] for idx in active)
        if weight_total <= 0:
            share = remaining / len(active)
            if share <= cap:
                for idx in active:
                    result[idx] = share
                remaining = 0
                break
            capped_now = set(active)
        else:
            allocations = {idx: remaining * weights[idx] / weight_total for idx in active}
            capped_now = {idx for idx, allocation in allocations.items() if allocation >= cap}
            if not capped_now:
                for idx, allocation in allocations.items():
                    result[idx] = allocation
                remaining = 0
                break

        for idx in capped_now:
            result[idx] = cap
            remaining -= cap
        active -= capped_now

    return _round_to_target(result, target, cap=cap)


def normalize_race_probabilities(rows: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
    out = [dict(row) for row in rows or []]
    for key, target_sum in [("win_probability", 100.0), ("podium_probability", 300.0), ("top10_probability", 1000.0)]:
        values = [max(0.0, safe_float(row.get(key)) or 0.0) for row in out]
        if sum(values) <= 0:
            values = [max(0.01, safe_float(row.get("score")) or 1.0) for row in out]
        cap = None if key == "win_probability" else 100.0
        normalized = _normalize_to_sum(values, target_sum, cap=cap)
        for row, value in zip(out, normalized):
            row[key] = value
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
    dnf_basis = {}
    for _ in range(max(1, runs)):
        sampled = []
        for row in rows:
            key = row.get("driver_id") or row.get("name")
            dnf_probability = safe_float(row.get("dnf_probability"))
            basis = "contract_dnf_probability"
            if dnf_probability is None:
                dnf_probability = safe_float(row.get("simulated_dnf_probability"))
                basis = "row_simulated_dnf_probability" if dnf_probability is not None else "fallback_default_unavailable_reliability"
            if dnf_probability is None:
                dnf_probability = 5.0
            dnf_basis[key] = basis
            dnf = rng.random() < dnf_probability / 100.0
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
            "dnf_probability_basis": dnf_basis.get(key, "fallback_default_unavailable_reliability"),
            "dnf_probability_fallback_used": dnf_basis.get(key) == "fallback_default_unavailable_reliability",
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
