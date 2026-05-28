"""Model agreement and disagreement helpers for prediction rows."""

from __future__ import annotations

from typing import Any

from pitwall.models.simulation import clamp, safe_float


def _level(rank: float, predicted_finish: float, win_probability: float, top10_probability: float) -> tuple[str, list[str], float]:
    reasons: list[str] = []
    penalty = 0.0
    rank_gap = abs(rank - predicted_finish)

    if rank <= 3 and predicted_finish > 8:
        reasons.append("front_rank_conflicts_with_finish_model")
        penalty += 24
    if rank <= 3 and win_probability < 8:
        reasons.append("front_rank_low_win_probability")
        penalty += 12 if predicted_finish <= 8 else 18
    if rank <= 10 and top10_probability < 50:
        reasons.append("top10_rank_low_points_probability")
        penalty += 14
    if rank_gap >= 7:
        reasons.append("large_rank_finish_gap")
        penalty += 18
    elif rank_gap >= 4:
        reasons.append("moderate_rank_finish_gap")
        penalty += 9

    if penalty >= 24:
        return "high", reasons, penalty
    if penalty >= 10:
        return "medium", reasons, penalty
    return "low", reasons, penalty


def enrich_model_disagreement(row: dict[str, Any]) -> dict[str, Any]:
    """Attach disagreement fields and reduce confidence for contradictory signals."""

    out = dict(row)
    rank = safe_float(out.get("rank")) or 99.0
    predicted_finish = safe_float(out.get("predicted_finish_position") or out.get("predicted_finish") or out.get("likely_finish")) or rank
    win_probability = safe_float(out.get("win_probability")) or 0.0
    top10_probability = safe_float(out.get("top10_probability") or out.get("points_probability")) or 0.0
    existing_agreement = safe_float(out.get("model_agreement_score"))

    level, reasons, penalty = _level(rank, predicted_finish, win_probability, top10_probability)
    agreement = existing_agreement if existing_agreement is not None else max(0.0, 100.0 - penalty)
    if penalty:
        agreement = min(agreement, max(0.0, 100.0 - penalty))

    out["model_agreement_score"] = round(clamp(agreement, 0, 100, 55), 2)
    out["model_disagreement_level"] = level
    out["model_disagreement_reasons"] = reasons
    out["model_disagreement_penalty"] = round(penalty, 2)
    out["rank_finish_gap"] = round(abs(rank - predicted_finish), 2)
    if penalty:
        out["confidence"] = round(clamp((safe_float(out.get("confidence")) or 50.0) - penalty * 0.55, 0, 100, 40), 2)
        flags = list(out.get("disagreement_flags") or [])
        for reason in reasons:
            if reason not in flags:
                flags.append(reason)
        out["disagreement_flags"] = flags
    return out
