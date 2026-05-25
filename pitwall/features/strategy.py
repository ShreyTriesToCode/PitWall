"""Strategy-context feature and annotation helpers."""

from __future__ import annotations

import os
from typing import Any

from pitwall.models.simulation import confidence_label, safe_float, safe_int


def text_level(value: Any) -> float:
    if value is None:
        return 50.0
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).lower()
    if any(word in text for word in ["very high", "extreme"]):
        return 90.0
    if "high" in text:
        return 75.0
    if "medium" in text or "moderate" in text:
        return 55.0
    if "low" in text:
        return 30.0
    return 50.0


def strategy_profile_for_row(row: dict[str, Any], profile: dict[str, Any] | None = None, weather: dict[str, Any] | None = None) -> dict[str, Any]:
    profile = profile or {}
    weather = weather or {}
    tyre_score = text_level(profile.get("tyre_stress"))
    rain_score = safe_float(weather.get("rain_score")) or safe_float(weather.get("rain_probability")) or text_level(weather.get("rain"))
    overtaking_score = text_level(profile.get("overtaking"))

    if rain_score and rain_score >= 55:
        sequence = ["intermediate", "slick"]
        stops = 2 if tyre_score >= 65 else 1
        first_pit_lap = None
        basis = "Rain risk is high enough that crossover timing dominates the dry pit window."
    elif tyre_score >= 70:
        sequence = ["medium", "hard", "medium"]
        stops = 2
        first_pit_lap = 16
        basis = "High tyre-stress profile makes a two-stop strategy plausible."
    elif overtaking_score <= 38:
        sequence = ["medium", "hard"]
        stops = 1
        first_pit_lap = 24
        basis = "Low-overtaking profile increases track-position value."
    else:
        sequence = ["medium", "hard"]
        stops = 1
        first_pit_lap = 20
        basis = "Default dry strategy from historical pit-window and tyre-stress profile."

    return {
        "stops": stops,
        "first_pit_lap": first_pit_lap,
        "compound_sequence": sequence,
        "confidence": confidence_label(row.get("confidence")),
        "basis": basis,
    }


def detect_strategy_context_annotations(strategy_context: dict[str, Any] | None = None, weather_context: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    if os.getenv("STRATEGY_CONTEXT_ENABLED", "true").lower() == "false":
        return []
    strategy_context = strategy_context or {}
    weather_context = weather_context or {}
    annotations: list[dict[str, Any]] = []

    starting_compound = str(strategy_context.get("starting_compound") or strategy_context.get("compound") or "").lower()
    first_pit_lap = safe_int(strategy_context.get("first_pit_lap") or strategy_context.get("first_stop_lap"))
    rainfall_actual = safe_float(weather_context.get("rainfall_actual") or weather_context.get("rainfall") or 0) or 0
    rain_probability = safe_float(weather_context.get("rain_probability") or weather_context.get("forecast_rain_probability") or 0) or 0
    track_status_events = [str(item).lower() for item in weather_context.get("track_status_events") or strategy_context.get("track_status_events") or []]
    pit_context = str(strategy_context.get("pit_context") or "").lower()
    post_switch_delta = safe_float(strategy_context.get("post_switch_pace_delta"))
    degradation_slope = safe_float(strategy_context.get("degradation_slope"))
    double_stack_loss = safe_float(strategy_context.get("double_stack_loss"))
    traffic_loss = safe_float(strategy_context.get("traffic_loss"))

    wet_start = any(token in starting_compound for token in ["inter", "wet"])
    if wet_start and rainfall_actual <= 0.01:
        annotations.append({
            "label": "wrong_starting_tyre_for_actual_weather",
            "message": "Started on a wet-weather tyre but actual early-session rain evidence was dry or negligible.",
            "confidence": "medium" if rain_probability >= 0.35 else "high",
            "source": "tyre/weather strategy annotation",
        })
    if first_pit_lap is not None and first_pit_lap <= 6:
        annotations.append({
            "label": "early_tyre_correction",
            "message": f"First stop on lap {first_pit_lap} suggests an early tyre or setup correction rather than pure car pace.",
            "confidence": "high",
            "source": "pit-stop timing",
        })
    if post_switch_delta is not None and post_switch_delta < -0.15:
        annotations.append({
            "label": "competitive_after_compound_switch",
            "message": "Pace improved after the tyre change, so final result should not be treated as only weak baseline pace.",
            "confidence": "medium",
            "source": "post-switch pace delta",
        })
    if "safety" in pit_context or any("safety" in item for item in track_status_events):
        annotations.append({
            "label": "safety_car_aided_stop",
            "message": "Pit timing overlapped with safety-car context, which can distort normal strategy evaluation.",
            "confidence": "medium",
            "source": "race-control context",
        })
    if "vsc" in pit_context or any("vsc" in item or "virtual safety" in item for item in track_status_events):
        annotations.append({
            "label": "vsc_aided_stop",
            "message": "Pit timing overlapped with VSC context, reducing pit-loss comparability.",
            "confidence": "medium",
            "source": "race-control context",
        })
    if "red" in pit_context or any("red flag" in item for item in track_status_events):
        annotations.append({
            "label": "red_flag_free_tyre_change",
            "message": "Red-flag context may have allowed tyre reset outside normal green-flag strategy.",
            "confidence": "medium",
            "source": "race-control context",
        })
    if double_stack_loss is not None and double_stack_loss >= 1.5:
        annotations.append({
            "label": "double_stack_time_loss",
            "message": "Detected double-stack time loss that should be separated from driver/car pace.",
            "confidence": "medium",
            "source": "pit-stop timing",
        })
    if traffic_loss is not None and traffic_loss >= 1.0:
        annotations.append({
            "label": "traffic_after_pit_loss",
            "message": "Post-stop traffic loss should be separated from clean-air car pace.",
            "confidence": "medium",
            "source": "pit-window traffic context",
        })
    if degradation_slope is not None and degradation_slope >= 0.16:
        annotations.append({
            "label": "degradation_cliff",
            "message": "Stint degradation slope points to tyre drop-off as a race-outcome driver.",
            "confidence": "medium",
            "source": "stint pace trend",
        })

    return annotations


def _driver_matches(row: dict[str, Any], driver_id: str) -> bool:
    return str(row.get("driver_id") or row.get("driverId") or row.get("driver") or "").lower() == str(driver_id).lower()


def build_strategy_context_for_driver(
    driver_id: str,
    *,
    pitstops: list[dict[str, Any]] | None = None,
    stints: list[dict[str, Any]] | None = None,
    race_control: list[dict[str, Any]] | None = None,
    weather: dict[str, Any] | None = None,
    lap_metrics: dict[str, Any] | None = None,
) -> dict[str, Any]:
    pitstops = [row for row in (pitstops or []) if _driver_matches(row, driver_id)]
    stints = [row for row in (stints or []) if _driver_matches(row, driver_id)]
    race_control = race_control or []
    weather = weather or {}
    lap_metrics = lap_metrics or {}
    first_stop = min(pitstops, key=lambda row: safe_int(row.get("lap") or row.get("lap_number")) or 9999) if pitstops else {}
    first_pit_lap = safe_int(first_stop.get("lap") or first_stop.get("lap_number"))
    starting_stint = min(stints, key=lambda row: safe_int(row.get("stint_number") or row.get("stint")) or 99) if stints else {}
    starting_compound = starting_stint.get("compound") or starting_stint.get("tyre_compound") or first_stop.get("starting_compound")
    events_near_stop = []
    for event in race_control:
        event_lap = safe_int(event.get("lap_number") or event.get("lap"))
        message = str(event.get("message") or event.get("category") or event.get("flag") or "")
        if first_pit_lap is None or event_lap is None or abs(event_lap - first_pit_lap) <= 2:
            events_near_stop.append(message)
    context = {
        "driver_id": driver_id,
        "first_pit_lap": first_pit_lap,
        "starting_compound": starting_compound,
        "pit_stop_count": len(pitstops),
        "pit_context": " ".join(events_near_stop),
        "track_status_events": events_near_stop,
        "post_switch_pace_delta": lap_metrics.get("post_switch_pace_delta"),
        "degradation_slope": lap_metrics.get("degradation_slope"),
        "double_stack_loss": lap_metrics.get("double_stack_loss"),
        "traffic_loss": lap_metrics.get("traffic_loss"),
    }
    context["annotations"] = detect_strategy_context_annotations(context, weather)
    return context
