"""Deterministic race and change summaries for frontend contracts."""

from __future__ import annotations

from typing import Any

from pitwall.ai.schemas import as_dict, as_list, clamp, humanize, trust_label


def _top_rows(contract_or_latest: dict[str, Any]) -> list[dict[str, Any]]:
    latest = as_dict(contract_or_latest.get("latest")) or contract_or_latest
    return [row for row in as_list(latest.get("full_grid") or latest.get("all_predictions") or latest.get("top10")) if isinstance(row, dict)]


def build_race_intelligence_summary(latest: dict[str, Any] | None) -> dict[str, Any]:
    latest = latest or {}
    rows = _top_rows(latest)
    top = rows[0] if rows else {}
    race_name = latest.get("race_name") or latest.get("event_title") or latest.get("target_event") or "current target"
    stage = latest.get("prediction_stage") or latest.get("stage") or "pending"
    trust_score = clamp(latest.get("prediction_trust_score") or latest.get("event_trust_score"), 0, 100, 0)
    high_disagreements = [row for row in rows if row.get("model_disagreement_level") == "high"]
    missing_groups = sorted({humanize(item) for row in rows for item in as_list(row.get("missing_feature_groups"))})
    warnings = as_list(latest.get("warnings"))
    source_health = as_dict(latest.get("source_health") or latest.get("source_status"))
    source_warnings = as_list(source_health.get("warnings")) + warnings
    top_text = f"{top.get('name')} leads the PitWall ranking" if top.get("name") else "No top prediction row is available"
    headline = f"{race_name}: {top_text} with {trust_label(trust_score)} trust."
    race_week_summary = (
        f"PitWall generated a {humanize(stage)} prediction using committed structured race, model, and source-health data. "
        f"Event trust is {trust_score:.1f}/100. Numeric rankings and probabilities come from the model contract, not this summary."
    )
    uncertainties = []
    if high_disagreements:
        uncertainties.append(f"{len(high_disagreements)} driver rows have high model disagreement.")
    if missing_groups:
        uncertainties.append(f"Missing feature groups include {', '.join(missing_groups[:6])}.")
    if source_warnings:
        uncertainties.append("Some source warnings are present; check the source-health panel.")
    if not uncertainties:
        uncertainties.append("No major deterministic uncertainty flag was reported.")
    disagreement_summary = (
        f"{len(high_disagreements)} high-disagreement rows; inspect badges before treating rank order as strong."
        if high_disagreements
        else "Ranking and probability signals are broadly aligned for the available rows."
    )
    return {
        "headline": headline,
        "race_week_summary": race_week_summary,
        "key_uncertainties": uncertainties[:8],
        "source_warnings": [humanize(item) for item in source_warnings[:8]],
        "model_disagreement_summary": disagreement_summary,
        "recommended_user_takeaway": "Use the Top 10 and Full Grid as calibrated, uncertainty-aware projections rather than certain outcomes.",
        "confidence_limitations": [
            "Crashes, safety cars, red flags, mechanical issues, late penalties, and weather shifts can change actual results.",
            "Deterministic AI text summarizes existing fields only and never changes predictions.",
        ],
        "generated_by": "deterministic",
    }


def build_changed_since_last_run(previous_contract: dict[str, Any] | None, next_contract: dict[str, Any] | None) -> dict[str, Any]:
    previous_latest = as_dict(as_dict(previous_contract).get("latest"))
    next_latest = as_dict(as_dict(next_contract).get("latest"))
    if not previous_latest or not next_latest:
        return {
            "available": False,
            "rank_changes": [],
            "confidence_changes": [],
            "trust_changes": [],
            "probability_changes": [],
            "source_changes": [],
            "weather_changes": [],
            "session_ingestion_changes": [],
            "model_version_changes": [],
            "summary": "No previous valid contract available.",
        }
    prev_rows = {row.get("driver_id"): row for row in _top_rows(previous_latest)}
    next_rows = {row.get("driver_id"): row for row in _top_rows(next_latest)}
    rank_changes = []
    confidence_changes = []
    trust_changes = []
    probability_changes = []
    for driver_id, row in next_rows.items():
        prev = prev_rows.get(driver_id)
        if not prev:
            continue
        rank_delta = (float(prev.get("rank") or 0) - float(row.get("rank") or 0))
        if rank_delta:
            rank_changes.append({"driver_id": driver_id, "name": row.get("name"), "rank_delta": round(rank_delta, 2), "new_rank": row.get("rank")})
        confidence_delta = float(row.get("confidence") or 0) - float(prev.get("confidence") or 0)
        if abs(confidence_delta) >= 2:
            confidence_changes.append({"driver_id": driver_id, "name": row.get("name"), "confidence_delta": round(confidence_delta, 2)})
        trust_delta = float(row.get("prediction_trust_score") or 0) - float(prev.get("prediction_trust_score") or 0)
        if abs(trust_delta) >= 2:
            trust_changes.append({"driver_id": driver_id, "name": row.get("name"), "trust_delta": round(trust_delta, 2)})
        win_delta = float(row.get("win_probability") or 0) - float(prev.get("win_probability") or 0)
        if abs(win_delta) >= 1:
            probability_changes.append({"driver_id": driver_id, "name": row.get("name"), "win_probability_delta": round(win_delta, 2)})
    source_changes = []
    if as_dict(previous_latest.get("source_health")).get("status") != as_dict(next_latest.get("source_health")).get("status"):
        source_changes.append({"field": "source_health.status", "previous": as_dict(previous_latest.get("source_health")).get("status"), "current": as_dict(next_latest.get("source_health")).get("status")})
    weather_changes = []
    if previous_latest.get("weather") != next_latest.get("weather"):
        weather_changes.append({"field": "weather", "previous": previous_latest.get("weather"), "current": next_latest.get("weather")})
    session_changes = []
    for field in ["last_ingested_session", "next_session_to_ingest", "session_data_delay_status"]:
        if previous_latest.get(field) != next_latest.get(field):
            session_changes.append({"field": field, "previous": previous_latest.get(field), "current": next_latest.get(field)})
    model_changes = []
    if previous_latest.get("model_version") != next_latest.get("model_version"):
        model_changes.append({"previous": previous_latest.get("model_version"), "current": next_latest.get("model_version")})
    summary = (
        f"{len(rank_changes)} rank changes, {len(probability_changes)} probability changes, "
        f"{len(trust_changes)} trust changes, {len(source_changes)} source changes."
    )
    return {
        "available": True,
        "rank_changes": sorted(rank_changes, key=lambda row: abs(row["rank_delta"]), reverse=True)[:10],
        "confidence_changes": sorted(confidence_changes, key=lambda row: abs(row["confidence_delta"]), reverse=True)[:10],
        "trust_changes": sorted(trust_changes, key=lambda row: abs(row["trust_delta"]), reverse=True)[:10],
        "probability_changes": sorted(probability_changes, key=lambda row: abs(row["win_probability_delta"]), reverse=True)[:10],
        "source_changes": source_changes,
        "weather_changes": weather_changes,
        "session_ingestion_changes": session_changes,
        "model_version_changes": model_changes,
        "summary": summary,
    }
