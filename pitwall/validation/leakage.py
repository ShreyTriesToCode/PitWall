"""Timestamp/stage leakage checks for feature sets."""

from __future__ import annotations

from typing import Iterable


STAGE_FORBIDDEN_PATTERNS = {
    "pre_weekend": ("fp1", "fp2", "fp3", "qualifying", "grid", "race_result", "finish_position", "pitstop", "stint", "fastest_lap"),
    "post_fp1": ("fp2", "fp3", "qualifying", "grid", "race_result", "finish_position", "pitstop", "stint", "fastest_lap"),
    "post_fp2": ("fp3", "qualifying", "grid", "race_result", "finish_position", "pitstop", "stint", "fastest_lap"),
    "post_fp3": ("qualifying_result", "race_result", "finish_position", "pitstop", "stint", "fastest_lap"),
    "post_qualifying": ("race_result", "finish_position", "pitstop", "stint", "fastest_lap"),
    "pre_race": ("race_result", "finish_position", "actual_pit", "actual_safety_car", "fastest_lap"),
}


def forbidden_feature_columns(stage: str, columns: Iterable[str]) -> list[str]:
    patterns = STAGE_FORBIDDEN_PATTERNS.get(str(stage or "").lower(), ())
    out = []
    for column in columns:
        clean = str(column).lower()
        if any(pattern in clean for pattern in patterns):
            out.append(str(column))
    return out


def assert_no_future_leakage(stage: str, columns: Iterable[str]) -> None:
    forbidden = forbidden_feature_columns(stage, columns)
    if forbidden:
        raise AssertionError(f"{stage} feature set contains future/leaky columns: {', '.join(forbidden[:20])}")
