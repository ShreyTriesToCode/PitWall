"""Deterministic post-race failure analysis from correction rows."""

from __future__ import annotations

from typing import Any

from pitwall.ai.schemas import as_list, humanize


def build_post_race_ai_review(corrections: list[dict[str, Any]] | dict[str, Any] | None) -> dict[str, Any]:
    rows = as_list(corrections.get("corrections") if isinstance(corrections, dict) else corrections)
    if not rows:
        return {
            "best_call": "No actual result audit is available yet.",
            "worst_miss": "No actual result audit is available yet.",
            "biggest_rank_errors": [],
            "likely_failure_causes": [],
            "source_gaps": [],
            "model_gaps": ["Actual race classification is required before a post-race miss analysis can be generated."],
            "feature_improvement_suggestions": [],
            "chaos_factors": [],
            "was_miss_predictable": "Not enough data in local PitWall sources.",
            "generated_by": "deterministic",
        }
    all_errors = []
    for correction in rows:
        for error in as_list(correction.get("errors")):
            if isinstance(error, dict):
                all_errors.append({**error, "race_id": correction.get("race_id"), "prediction_id": correction.get("prediction_id")})
    all_errors.sort(key=lambda row: abs(int(row.get("position_error") or 0)), reverse=True)
    biggest = all_errors[:5]
    best_call = "At least one audited race has actual result rows."
    if all_errors:
        low_error = sorted(all_errors, key=lambda row: abs(int(row.get("position_error") or 0)))[0]
        best_call = f"Best available audited call: {low_error.get('name')} was within {low_error.get('position_error')} positions."
    worst = "No major rank miss was detected."
    if biggest:
        miss = biggest[0]
        worst = f"Worst available miss: {miss.get('name')} predicted P{miss.get('predicted_position')} and finished P{miss.get('actual_position')}."
    causes = ["race execution", "strategy volatility", "incident timing"]
    suggestions = [
        "Review feature groups for drivers with the largest rank error.",
        "Separate car pace from strategy and incident outcomes when post-race data is available.",
    ]
    chaos = ["safety cars, red flags, reliability, weather, penalties, and traffic can create non-repeatable misses"]
    return {
        "best_call": best_call,
        "worst_miss": worst,
        "biggest_rank_errors": biggest,
        "likely_failure_causes": causes,
        "source_gaps": [],
        "model_gaps": [humanize(item) for item in causes],
        "feature_improvement_suggestions": suggestions,
        "chaos_factors": chaos,
        "was_miss_predictable": "Partly. Large errors should be treated as review prompts unless source data identifies a repeatable feature gap.",
        "generated_by": "deterministic",
    }
