"""Prediction trust scoring helpers."""

from __future__ import annotations

from typing import Any

from pitwall.models.simulation import clamp, confidence_label, safe_float


STAGE_CONFIDENCE = {
    "pre_weekend": 46,
    "post_fp1": 54,
    "post_fp2": 60,
    "post_fp3": 64,
    "post_sprint": 66,
    "post_qualifying": 72,
    "pre_race": 76,
    "live": 62,
    "live_adjusted": 62,
    "post_race": 90,
}


def _data_completeness(row: dict[str, Any]) -> tuple[float, list[str], list[str], float]:
    evidence = row.get("evidence_status") or {}
    available = list(evidence.get("available") or row.get("available_feature_groups") or [])
    missing = list(evidence.get("missing") or row.get("missing_feature_groups") or [])
    penalty_total = safe_float(evidence.get("penalty_total")) or safe_float(row.get("missing_data_penalty_total")) or 0.0
    total = max(1, len(available) + len(missing))
    coverage = len(available) / total * 100.0
    completeness = clamp(coverage - penalty_total * 0.65, 0, 100, 50)
    return completeness, available, missing, penalty_total


def trust_label(score: Any) -> str:
    value = safe_float(score)
    if value is None or value < 50:
        return "Low trust"
    if value < 75:
        return "Medium trust"
    return "High trust"


def enrich_prediction_trust(
    row: dict[str, Any],
    *,
    source_health: dict[str, Any] | None = None,
    stage: str | None = None,
    validation_strength: float | None = None,
) -> dict[str, Any]:
    """Attach per-driver trust fields based on agreement, sources, data, validation, and stage."""

    out = dict(row)
    source_health = source_health or {}
    completeness, available, missing, missing_penalty = _data_completeness(out)
    agreement = safe_float(out.get("model_agreement_score")) or 55.0
    source_score = safe_float(source_health.get("overall_score") or source_health.get("score") or out.get("source_confidence")) or 55.0
    validation = safe_float(validation_strength) or safe_float(out.get("validation_strength")) or safe_float(out.get("confidence")) or 55.0
    if validation <= 1:
        validation *= 100
    stage_score = STAGE_CONFIDENCE.get(str(stage or out.get("stage") or "pre_weekend"), 50)
    source_notes = out.get("source_notes") or {}
    source_warnings = list(source_notes.get("warnings") or out.get("source_warnings") or [])
    warning_penalty = min(18.0, len(source_warnings) * 2.5)
    disagreement_penalty = safe_float(out.get("model_disagreement_penalty")) or 0.0

    score = (
        agreement * 0.30
        + source_score * 0.25
        + completeness * 0.20
        + validation * 0.15
        + stage_score * 0.10
        - warning_penalty
        - disagreement_penalty * 0.35
    )
    score = round(clamp(score, 0, 100, 50), 2)
    out["prediction_trust_score"] = score
    out["prediction_trust_label"] = trust_label(score)
    out["trust_label"] = out["prediction_trust_label"]
    out["available_feature_groups"] = available
    out["missing_feature_groups"] = missing
    out["missing_data_penalty_total"] = round(missing_penalty, 2)
    out["source_warnings"] = source_warnings
    out["stale_source_warnings"] = [w for w in source_warnings if "stale" in str(w).lower()]
    out["stage_limitations"] = stage_limitations(stage or out.get("stage"), missing)
    out["trust_components"] = {
        "model_agreement": round(agreement, 2),
        "source_health": round(source_score, 2),
        "data_completeness": round(completeness, 2),
        "validation_strength": round(validation, 2),
        "stage_confidence": round(stage_score, 2),
        "warning_penalty": round(warning_penalty, 2),
        "disagreement_penalty": round(disagreement_penalty, 2),
    }
    out.setdefault("confidence_label", confidence_label(out.get("confidence")))
    return out


def stage_limitations(stage: str | None, missing: list[str]) -> list[str]:
    stage = str(stage or "pre_weekend")
    limitations = []
    if stage in {"pre_weekend", "pre_race"} and "qualifying" in missing:
        limitations.append("qualifying_missing_reduces_grid_confidence")
    if any(item in missing for item in ["practice_or_lap_pace", "practice_pace"]):
        limitations.append("practice_or_lap_pace_missing")
    if stage == "pre_weekend":
        limitations.append("pre_weekend_prediction_uses_no_future_session_data")
    if stage.startswith("post_fp"):
        limitations.append("later_sessions_and_race_result_are_stage_gated")
    if stage == "post_qualifying":
        limitations.append("race_result_and_actual_strategy_not_available")
    return limitations
