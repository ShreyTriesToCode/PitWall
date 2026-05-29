"""Small schema helpers for deterministic PitWall intelligence payloads."""

from __future__ import annotations

from typing import Any


DRIVER_AI_EXPLANATION_KEYS = [
    "simple_explanation",
    "expert_explanation",
    "risk_summary",
    "upside_case",
    "downside_case",
    "missing_data_note",
    "model_agreement_note",
    "source_health_note",
    "scenario_note",
]


def as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def safe_float(value: Any, default: float | None = None) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return default
    return number


def clamp(value: Any, low: float = 0.0, high: float = 100.0, default: float = 0.0) -> float:
    number = safe_float(value, default)
    if number is None:
        number = default
    return max(low, min(high, number))


def pct(value: Any, fallback: str = "not enough data") -> str:
    number = safe_float(value)
    if number is None:
        return fallback
    return f"{number:.1f}%"


def trust_label(score: Any) -> str:
    number = clamp(score, 0, 100, 0)
    if number >= 75:
        return "high"
    if number >= 50:
        return "medium"
    return "low"


def humanize(value: Any) -> str:
    text = str(value or "").replace("_", " ").replace("-", " ").strip()
    return text or "not enough data"
