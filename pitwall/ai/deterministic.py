"""Deterministic, no-LLM explanations for existing prediction rows."""

from __future__ import annotations

from typing import Any

from pitwall.ai.schemas import DRIVER_AI_EXPLANATION_KEYS, as_list, clamp, humanize, pct, trust_label


def _position_range(row: dict[str, Any]) -> str:
    value = row.get("position_range")
    if isinstance(value, list) and len(value) >= 2:
        return f"P{value[0]}-P{value[1]}"
    low = row.get("best_case_finish") or row.get("finish_interval_low")
    high = row.get("worst_case_finish") or row.get("finish_interval_high")
    if low and high:
        return f"P{low}-P{high}"
    rank = row.get("rank") or row.get("predicted_finish")
    return f"P{rank}" if rank else "range unavailable"


def _stage_note(stage: str) -> str:
    stage = stage or "pre_weekend"
    if stage == "pre_weekend":
        return "This is a pre-weekend view, so practice, qualifying, grid, and race-result data are not used."
    if stage.startswith("post_fp"):
        return f"This is a {humanize(stage)} view; later sessions and race result data remain unavailable."
    if stage == "post_qualifying":
        return "This is a post-qualifying view; race execution, actual strategy, and incidents are still unknown."
    if stage == "post_race":
        return "This is a post-race audit generated after actual result data became available."
    if stage == "live":
        return "This is a live or timing-aware view and should be interpreted with feed freshness."
    return f"This prediction stage is {humanize(stage)}."


def build_driver_ai_explanation(row: dict[str, Any], context: dict[str, Any] | None = None) -> dict[str, str]:
    """Create concise explanation text using only existing row/context fields."""

    context = context or {}
    name = row.get("name") or row.get("driver_id") or "This driver"
    team = row.get("team") or "unknown team"
    rank = row.get("rank") or row.get("predicted_finish") or "?"
    predicted_finish = row.get("predicted_finish_position") or row.get("predicted_finish") or row.get("likely_finish") or rank
    confidence = pct(row.get("confidence"))
    trust_score = clamp(row.get("prediction_trust_score"), 0, 100, 0)
    trust = str(row.get("prediction_trust_label") or trust_label(trust_score)).lower().replace(" trust", "")
    missing = [humanize(item) for item in as_list(row.get("missing_feature_groups"))]
    available = [humanize(item) for item in as_list(row.get("available_feature_groups"))]
    disagreement = str(row.get("model_disagreement_level") or "low").lower()
    disagreement_reasons = [humanize(item) for item in as_list(row.get("model_disagreement_reasons"))]
    warnings = [humanize(item) for item in as_list(row.get("source_warnings"))]
    stage = row.get("stage") or context.get("stage") or context.get("prediction_stage") or "pre_weekend"
    scenario = context.get("race_factors") or row.get("race_factors") or {}
    strategy = row.get("expected_strategy") or {}
    top_reason = as_list(row.get("reason_tags"))[:2]
    weak_reason = as_list(row.get("weakness_tags"))[:2]
    dnf = row.get("dnf_probability")
    range_label = _position_range(row)

    simple = (
        f"{name} is ranked P{rank} for {team} with {confidence} confidence and {trust} trust. "
        f"The model's likely finish is P{predicted_finish}, with an expected range of {range_label}."
    )
    if disagreement != "low":
        simple += f" Disagreement is {disagreement}, so treat the rank cautiously."
    if missing:
        simple += f" Missing signals: {', '.join(missing[:3])}."

    expert_bits = []
    if top_reason:
        expert_bits.append(f"positive signals: {', '.join(map(humanize, top_reason))}")
    if weak_reason:
        expert_bits.append(f"negative signals: {', '.join(map(humanize, weak_reason))}")
    if available:
        expert_bits.append(f"{len(available)} feature groups available")
    if missing:
        expert_bits.append(f"{len(missing)} feature groups missing")
    expert = f"{name}: " + ("; ".join(expert_bits) if expert_bits else "not enough structured evidence for a detailed explanation.")

    if missing:
        missing_note = f"Not enough data for {', '.join(missing[:5])}; confidence and trust are penalized."
    else:
        missing_note = "No major missing feature groups were reported for this row."

    if disagreement_reasons:
        agreement_note = f"Model disagreement is {disagreement}: {', '.join(disagreement_reasons[:4])}."
    else:
        agreement_note = "Ranking, predicted finish, and probabilities are broadly aligned."

    if warnings:
        source_note = f"Source warnings affect this view: {', '.join(warnings[:4])}."
    else:
        source_note = "No row-level source warnings were reported."

    pit = strategy.get("first_pit_lap")
    stops = strategy.get("stops")
    strategy_text = "Expected strategy is unavailable."
    if stops is not None or pit is not None:
        strategy_text = f"Expected strategy: {stops if stops is not None else 'unknown'} stops"
        if pit is not None:
            strategy_text += f", first pit around lap {pit}"
        compounds = strategy.get("compound_sequence") or []
        if compounds:
            strategy_text += f", compounds {' > '.join(map(str, compounds[:4]))}"
        strategy_text += "."

    safety = scenario.get("safety_car_probability")
    rain = scenario.get("rain_impact")
    scenario_note = _stage_note(str(stage))
    if safety is not None:
        scenario_note += f" Safety-car probability is {pct(safety)}."
    if rain:
        scenario_note += f" Rain impact: {humanize(rain)}."

    risk_parts = []
    if dnf is not None:
        risk_parts.append(f"DNF risk {pct(dnf)}")
    if disagreement != "low":
        risk_parts.append(f"{disagreement} model disagreement")
    if missing:
        risk_parts.append(f"{len(missing)} missing feature groups")
    risk_summary = ", ".join(risk_parts) if risk_parts else "No major structured risk flag was reported."

    upside = f"Upside case: {name} reaches the front of the projected range ({range_label}) if available strengths translate cleanly."
    if top_reason:
        upside += f" Main support: {', '.join(map(humanize, top_reason))}."
    downside = f"Downside case: {name} falls toward the back of the range if missing data or risk flags dominate."
    if weak_reason:
        downside += f" Main concerns: {', '.join(map(humanize, weak_reason))}."

    return {
        "simple_explanation": simple,
        "expert_explanation": expert,
        "risk_summary": risk_summary,
        "upside_case": upside,
        "downside_case": downside,
        "missing_data_note": missing_note,
        "model_agreement_note": agreement_note,
        "source_health_note": source_note,
        "scenario_note": scenario_note,
        "generated_by": "deterministic",
        "strategy_note": strategy_text,
    }


def enrich_driver_ai_explanation(row: dict[str, Any], context: dict[str, Any] | None = None) -> dict[str, Any]:
    out = dict(row)
    explanation = build_driver_ai_explanation(out, context)
    existing = out.get("ai_explanation") if isinstance(out.get("ai_explanation"), dict) else {}
    out["ai_explanation"] = {**{key: "" for key in DRIVER_AI_EXPLANATION_KEYS}, **existing, **explanation}
    out.setdefault("simple_explanation", out["ai_explanation"]["simple_explanation"])
    out.setdefault("expert_explanation", out["ai_explanation"]["expert_explanation"])
    out.setdefault("trust_explanation", _trust_explanation(out))
    return out


def _trust_explanation(row: dict[str, Any]) -> str:
    trust_score = clamp(row.get("prediction_trust_score"), 0, 100, 0)
    label = str(row.get("prediction_trust_label") or trust_label(trust_score)).lower().replace(" trust", "")
    pieces = row.get("trust_components") or {}
    if not pieces:
        return f"Trust is {label} because detailed trust components are not available."
    return (
        f"Trust is {label} at {trust_score:.1f}/100, combining model agreement "
        f"{pct(pieces.get('model_agreement'))}, source health {pct(pieces.get('source_health'))}, "
        f"data completeness {pct(pieces.get('data_completeness'))}, validation strength "
        f"{pct(pieces.get('validation_strength'))}, and stage confidence {pct(pieces.get('stage_confidence'))}."
    )
