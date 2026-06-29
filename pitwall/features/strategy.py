"""Strategy-context feature and annotation helpers."""

from __future__ import annotations

import os
import re
from statistics import median
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


def average(values: list[float | int | None]) -> float | None:
    clean = [float(value) for value in values if value is not None]
    return sum(clean) / len(clean) if clean else None


def compound_mapping_from_nomination(compounds: list[Any] | tuple[Any, ...] | set[Any], source: dict[str, Any] | None = None) -> dict[str, Any]:
    """Map FIA-nominated C-number compounds to event-relative Hard/Medium/Soft labels."""
    numbers: list[int] = []
    for compound in compounds or []:
        match = re.search(r"\bC([1-5])\b", str(compound).upper())
        if match:
            number = int(match.group(1))
            if number not in numbers:
                numbers.append(number)
    numbers = sorted(numbers)
    if len(numbers) != 3:
        return {
            "status": "unavailable",
            "reason": "expected_exactly_three_fia_slick_compounds",
            "nominated_compounds": [f"C{number}" for number in numbers],
            "source": source or {},
        }
    mapping = {
        "hard": f"C{numbers[0]}",
        "medium": f"C{numbers[1]}",
        "soft": f"C{numbers[2]}",
    }
    return {
        "status": "available",
        "nominated_compounds": [f"C{number}" for number in numbers],
        "mapping": mapping,
        "reverse_mapping": {compound: role for role, compound in mapping.items()},
        "rule": "lowest_C_number_is_hard_middle_is_medium_highest_is_soft_for_this_event",
        "source": source or {},
    }


def compound_role_for_value(compound: Any, compound_mapping: dict[str, Any] | None = None) -> str | None:
    value = str(compound or "").strip().lower()
    if not value:
        return None
    for role in ["soft", "medium", "hard", "intermediate", "wet"]:
        if role in value:
            return role
    match = re.search(r"\bC([1-5])\b", value.upper())
    if match and compound_mapping:
        reverse = compound_mapping.get("reverse_mapping") or {}
        return reverse.get(f"C{match.group(1)}")
    return None


def compound_identity_for_role(role: str, compound_mapping: dict[str, Any] | None = None) -> str | None:
    if not compound_mapping or compound_mapping.get("status") != "available":
        return None
    return (compound_mapping.get("mapping") or {}).get(str(role or "").lower())


def strategy_profile_for_row(row: dict[str, Any], profile: dict[str, Any] | None = None, weather: dict[str, Any] | None = None, compound_mapping: dict[str, Any] | None = None) -> dict[str, Any]:
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
        "compound_identities": [
            compound_identity_for_role(compound, compound_mapping)
            for compound in sequence
            if compound_identity_for_role(compound, compound_mapping)
        ],
        "confidence": confidence_label(row.get("confidence")),
        "basis": basis,
    }


def _record_data(record: dict[str, Any]) -> dict[str, Any]:
    data = record.get("data") if isinstance(record, dict) else {}
    if isinstance(data, dict) and isinstance(data.get("data"), dict):
        return data.get("data") or {}
    return data if isinstance(data, dict) else {}


def _pit_stop_rows(data: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for race in data.get("pitstops", []) or []:
        rows.extend(race.get("PitStops", []) if isinstance(race, dict) else [])
    rows.extend(data.get("pit_stops", []) or [])
    return [row for row in rows if isinstance(row, dict)]


def _race_control_rows(data: dict[str, Any]) -> list[dict[str, Any]]:
    rows = data.get("race_control") or data.get("raceControl") or data.get("race_control_messages") or []
    return [row for row in rows if isinstance(row, dict)]


def _race_lap_count(data: dict[str, Any]) -> int | None:
    for race in data.get("results", []) or []:
        for row in race.get("Results", []) if isinstance(race, dict) else []:
            laps = safe_int(row.get("laps"))
            if laps:
                return laps
    max_lap = None
    for race in data.get("laps", []) or []:
        for lap in race.get("Laps", []) if isinstance(race, dict) else []:
            lap_no = safe_int(lap.get("number") or lap.get("lap"))
            if lap_no:
                max_lap = max(lap_no, max_lap or lap_no)
    return max_lap


def _derive_lap_degradation(records: list[dict[str, Any]]) -> dict[str, Any]:
    slopes: list[float] = []
    for record in records:
        data = _record_data(record)
        by_driver: dict[str, list[tuple[int, float]]] = {}
        for race in data.get("laps", []) or []:
            for lap in race.get("Laps", []) if isinstance(race, dict) else []:
                lap_no = safe_int(lap.get("number") or lap.get("lap"))
                if lap_no is None or lap_no <= 1:
                    continue
                for timing in lap.get("Timings", []) if isinstance(lap, dict) else []:
                    driver_id = timing.get("driverId") or timing.get("driver_id")
                    seconds = _lap_time_to_seconds(timing.get("time"))
                    if driver_id and seconds and 45 <= seconds <= 180:
                        by_driver.setdefault(str(driver_id), []).append((lap_no, seconds))
        for laps in by_driver.values():
            laps = sorted(laps)
            if len(laps) < 8:
                continue
            cut = max(3, len(laps) // 4)
            early = average([seconds for _, seconds in laps[:cut]])
            late = average([seconds for _, seconds in laps[-cut:]])
            lap_span = max(1, laps[-cut][0] - laps[cut - 1][0])
            if early is not None and late is not None:
                slope = (late - early) / lap_span
                if -0.5 <= slope <= 0.8:
                    slopes.append(slope)
    if not slopes:
        return {
            "status": "unavailable",
            "basis": "No usable cached lap-time stints were available for a data-derived degradation slope.",
            "samples": 0,
        }
    return {
        "status": "lap_timing_derived",
        "average_seconds_per_lap": round(average(slopes) or 0, 4),
        "samples": len(slopes),
        "basis": "Derived from cached historical lap-time drift. Compound-specific FastF1 labels were not available for every sample, so this is a relative degradation estimate.",
    }


def _lap_time_to_seconds(value: Any) -> float | None:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        if ":" in text:
            minutes, seconds = text.split(":", 1)
            return int(minutes) * 60 + float(seconds)
        return float(text)
    except (TypeError, ValueError):
        return None


def _strategy_sequence_for_conditions(stops: int, profile: dict[str, Any], weather: dict[str, Any]) -> list[str]:
    rain_score = safe_float(weather.get("rain_score")) or safe_float(weather.get("rain_probability")) or text_level(weather.get("rain"))
    tyre_score = text_level(profile.get("tyre_stress"))
    if rain_score and rain_score >= 55:
        return ["intermediate", "slick"] if stops <= 1 else ["intermediate", "slick", "medium"][: stops + 1]
    if stops >= 3:
        return ["medium", "hard", "medium", "soft"]
    if stops == 2:
        return ["medium", "hard", "medium"] if tyre_score >= 65 else ["soft", "hard", "medium"]
    return ["medium", "hard"]


def _allocate_stints(total_laps: int, stops: int, first_pit_lap: int | None) -> list[tuple[int, int]]:
    total_laps = max(1, int(total_laps or 60))
    stints = stops + 1
    if stops <= 0:
        return [(1, total_laps)]
    first = max(5, min(first_pit_lap or round(total_laps / stints), total_laps - stops))
    cut_points = [first]
    remaining = max(1, total_laps - first)
    for stop_idx in range(1, stops):
        cut_points.append(first + round(remaining * stop_idx / stops))
    starts = [1] + [point + 1 for point in cut_points]
    ends = cut_points + [total_laps]
    return [(max(1, start), max(start, end)) for start, end in zip(starts, ends)]


def simulate_multi_stint_strategy(
    profile: dict[str, Any] | None = None,
    weather: dict[str, Any] | None = None,
    top10: list[dict[str, Any]] | None = None,
    compound_mapping: dict[str, Any] | None = None,
    historical_records: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    profile = profile or {}
    weather = weather or {}
    records = [record for record in (historical_records or []) if isinstance(_record_data(record), dict)]
    pit_laps: list[int] = []
    pit_durations: list[float] = []
    stop_counts: list[int] = []
    lap_counts: list[int] = []
    for record in records:
        data = _record_data(record)
        lap_count = _race_lap_count(data)
        if lap_count:
            lap_counts.append(lap_count)
        by_driver: dict[str, int] = {}
        for row in _pit_stop_rows(data):
            lap = safe_int(row.get("lap") or row.get("lap_number"))
            duration = safe_float(row.get("duration") or row.get("pit_duration"))
            driver_id = str(row.get("driverId") or row.get("driver_id") or "")
            if lap and lap > 0:
                pit_laps.append(lap)
            if duration and 1.0 <= duration <= 80.0:
                pit_durations.append(duration)
            if driver_id:
                by_driver[driver_id] = by_driver.get(driver_id, 0) + 1
        stop_counts.extend(count for count in by_driver.values() if count > 0)
    heuristic = strategy_profile_for_row({}, profile, weather, compound_mapping)
    data_enough = len(pit_laps) >= 6 or len(stop_counts) >= 6
    stops = round(median(stop_counts)) if stop_counts else safe_int(heuristic.get("stops")) or 1
    stops = max(1, min(3, stops))
    first_pit_lap = round(median(pit_laps)) if pit_laps else safe_int(heuristic.get("first_pit_lap"))
    total_laps = round(median(lap_counts)) if lap_counts else safe_int(profile.get("race_laps")) or 60
    sequence = _strategy_sequence_for_conditions(stops, profile, weather)[: stops + 1]
    if len({compound for compound in sequence if compound in {"soft", "medium", "hard"}}) < 2 and all(compound in {"soft", "medium", "hard"} for compound in sequence):
        sequence[-1] = "hard" if sequence[0] != "hard" else "medium"
    windows = _allocate_stints(total_laps, stops, first_pit_lap)
    stints = []
    for idx, (compound, (lap_start, lap_end)) in enumerate(zip(sequence, windows), start=1):
        identity = compound_identity_for_role(compound, compound_mapping)
        stint = {
            "stint": idx,
            "compound": compound,
            "laps": max(1, lap_end - lap_start + 1),
            "lap_start": lap_start,
            "lap_end": lap_end,
        }
        if identity:
            stint["compound_identity"] = identity
        stints.append(stint)
    degradation = _derive_lap_degradation(records)
    basis = (
        f"Derived from {len(records)} cached same-circuit race(s), {len(pit_laps)} pit-lap samples, and {len(stop_counts)} driver stop-count samples."
        if data_enough
        else "Limited cached same-circuit strategy data; using transparent heuristic fallback from track tyre stress, overtaking, and weather profile."
    )
    return {
        "status": "data_derived" if data_enough else "heuristic_fallback",
        "stops": stops,
        "sequence": stints,
        "first_pit_lap": first_pit_lap,
        "total_laps": total_laps,
        "mandatory_compound_rule": "applied_to_dry_race_candidates",
        "confidence": "medium" if data_enough and len(records) >= 2 else "low",
        "basis": basis,
        "data_points": {
            "historical_races": len(records),
            "pit_lap_samples": len(pit_laps),
            "stop_count_samples": len(stop_counts),
            "pit_duration_samples": len(pit_durations),
        },
        "pit_loss_basis": {
            "status": "stationary_pit_duration" if pit_durations else "unavailable",
            "average_seconds": round(average(pit_durations) or 0, 3) if pit_durations else None,
            "note": "Cached data exposes stationary pit duration; full in-lap/out-lap pit-lane loss was not available for every historical race.",
        },
        "degradation_model": degradation,
        "compound_mapping": compound_mapping if compound_mapping and compound_mapping.get("status") == "available" else None,
    }


def safety_car_window_from_history(
    historical_records: list[dict[str, Any]] | None = None,
    *,
    bucket_size: int = 5,
    min_races: int = 3,
) -> dict[str, Any]:
    records = [record for record in (historical_records or []) if isinstance(_record_data(record), dict)]
    race_count = len(records)
    if race_count < min_races:
        return {
            "status": "thin_data",
            "supporting_races": race_count,
            "bucket_size_laps": bucket_size,
            "windows": [],
            "warning": f"Need at least {min_races} cached same-circuit races before showing a robust safety-car window.",
        }
    buckets: dict[tuple[int, int], int] = {}
    for record in records:
        data = _record_data(record)
        seen: set[tuple[int, int]] = set()
        for event in _race_control_rows(data):
            message = str(event.get("message") or event.get("category") or event.get("flag") or "").lower()
            if not any(token in message for token in ["safety car", "virtual safety", "vsc", "red flag"]):
                continue
            lap = safe_int(event.get("lap") or event.get("lap_number"))
            if not lap or lap <= 0:
                continue
            start = ((lap - 1) // bucket_size) * bucket_size + 1
            seen.add((start, start + bucket_size - 1))
        for bucket in seen:
            buckets[bucket] = buckets.get(bucket, 0) + 1
    windows = [
        {
            "lap_start": start,
            "lap_end": end,
            "share": round(count / race_count, 3),
            "events": count,
            "supporting_races": race_count,
        }
        for (start, end), count in sorted(buckets.items(), key=lambda item: (-item[1], item[0][0]))
    ][:5]
    return {
        "status": "available" if windows else "no_events_observed",
        "supporting_races": race_count,
        "bucket_size_laps": bucket_size,
        "windows": windows,
        "basis": f"Aggregated race-control safety car/VSC/red-flag events across {race_count} cached same-circuit races.",
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
