"""Prediction contract enrichment helpers."""

from __future__ import annotations

from typing import Any

from pitwall.features.strategy import strategy_profile_for_row, text_level
from pitwall.models.simulation import clamp, confidence_label, safe_float


def weighted_average(items: list[tuple[Any, float]]) -> float | None:
    total = 0.0
    weight_sum = 0.0
    for value, weight in items:
        value = safe_float(value)
        if value is None:
            continue
        total += value * weight
        weight_sum += weight
    return total / weight_sum if weight_sum else None


def explanation_for_prediction_row(row: dict[str, Any], profile: dict[str, Any] | None = None, weather: dict[str, Any] | None = None) -> dict[str, Any]:
    components = row.get("component_scores") or {}
    strategy = row.get("expected_strategy") or strategy_profile_for_row(row, profile, weather)
    missing = (row.get("evidence_status") or {}).get("missing") or []
    pace_score = weighted_average([
        (components.get("race_pace"), 0.35),
        (components.get("timing_lap_pace"), 0.25),
        (components.get("ml_finish_position_score"), 0.20),
        (row.get("score"), 0.20),
    ])
    qualifying_score = components.get("qualifying") or components.get("timing_starting_grid")
    reliability = row.get("reliability") or components.get("reliability")
    rain = safe_float((weather or {}).get("rain_score")) or safe_float((weather or {}).get("rain_probability"))
    return {
        "pace": f"Pace signal {round(pace_score, 1) if pace_score is not None else 'pending'} from race-pace, timing, and finish-position components.",
        "strategy": strategy.get("basis") or "Strategy estimate uses pit-window, tyre-stress, and team-strategy components where available.",
        "tyres": f"Expected sequence: {', '.join(strategy.get('compound_sequence') or []) or 'not enough tyre data'}; tyre risk {profile.get('tyre_stress', 'unknown') if profile else 'unknown'}.",
        "weather": f"Rain impact score {round(rain, 1) if rain is not None else 'pending'}; weather confidence depends on source freshness.",
        "risk": f"Reliability/DNF risk is reflected by {round(reliability, 1) if reliability is not None else 'pending'} reliability and {row.get('dnf_probability', 'pending')}% DNF probability.",
        "qualifying": f"Qualifying/grid component {round(safe_float(qualifying_score), 1) if safe_float(qualifying_score) is not None else 'pending'} affects track-position confidence.",
        "key_reasons": row.get("reason_tags") or [],
        "missing_data": missing,
    }


def race_factors_from_context(profile: dict[str, Any] | None = None, weather: dict[str, Any] | None = None, source_health: dict[str, Any] | None = None) -> dict[str, Any]:
    profile = profile or {}
    weather = weather or {}
    safety_score = text_level(profile.get("safety_car"))
    rain_score = safe_float(weather.get("rain_score")) or safe_float(weather.get("rain_probability")) or text_level(weather.get("rain"))
    overtaking_score = text_level(profile.get("overtaking"))
    source_score = safe_float((source_health or {}).get("overall_score")) or 50
    return {
        "safety_car_probability": round(clamp(safety_score, 0, 100, 50), 2),
        "vsc_probability": round(clamp(safety_score * 0.72, 0, 100, 36), 2),
        "red_flag_probability": round(clamp(safety_score * 0.28 + max(0, rain_score - 50) * 0.20, 0, 100, 12), 2),
        "rain_impact": "high" if rain_score >= 60 else "medium" if rain_score >= 30 else "low",
        "track_overtaking_difficulty": profile.get("overtaking", "unknown"),
        "tyre_degradation_risk": profile.get("tyre_stress", "unknown"),
        "source_confidence": confidence_label(source_score),
    }
