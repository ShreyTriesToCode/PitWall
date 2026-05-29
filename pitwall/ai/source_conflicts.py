"""Deterministic source conflict classification."""

from __future__ import annotations

from typing import Any

from pitwall.ai.schemas import as_dict, as_list, humanize


def detect_source_conflicts(payload: dict[str, Any] | None) -> list[dict[str, Any]]:
    payload = payload or {}
    latest = as_dict(payload.get("latest")) or payload
    source_health = as_dict(latest.get("source_health") or payload.get("source_health") or latest.get("source_status"))
    sources = as_list(source_health.get("sources"))
    conflicts: list[dict[str, Any]] = []

    for source in sources:
        if not isinstance(source, dict):
            continue
        name = str(source.get("source") or source.get("name") or "").strip()
        status = str(source.get("status") or "").lower()
        detail = str(source.get("detail") or source.get("fallback_reason") or "")
        if source.get("auth_restricted"):
            conflicts.append(_conflict("auth_restricted", ["live timing", "session enrichment"], [name], "Formula 1 timing/FastF1/Jolpica fallback", detail or f"{name} requires authentication.", "high", "Configure optional credentials or keep fallback mode."))
        if "stale" in status or "stale" in detail.lower():
            conflicts.append(_conflict("stale_cache", ["source freshness"], [name], "fresh official/current source when available", detail or f"{name} data is stale.", "medium", "Refresh cache or wait for next generated run."))
        if "missing" in status or "unavailable" in status or "failed" in status:
            conflicts.append(_conflict("source_unavailable", ["source availability"], [name], "available verified source", detail or f"{name} is unavailable.", "medium", "Use fallback data and lower trust."))

    warnings = as_list(latest.get("warnings")) + as_list(source_health.get("warnings"))
    for warning in warnings:
        text = str(warning)
        lower = text.lower()
        if "fia" in lower and ("403" in lower or "forbidden" in lower or "unavailable" in lower):
            conflicts.append(_conflict("fia_document_unavailable", ["FIA documents"], ["FIA documents"], "cached FIA text or public FIA metadata", text, "high", "Use cached official text if available; otherwise keep warning visible."))
        elif "weather" in lower and ("missing" in lower or "stale" in lower):
            conflicts.append(_conflict("weather_stale_or_missing", ["weather"], ["OpenF1", "Open-Meteo"], "latest available weather source", text, "medium", "Refresh weather or keep weather uncertainty penalty."))

    if latest.get("weather") in (None, {}, ""):
        conflicts.append(_conflict("weather_stale_or_missing", ["weather"], ["OpenF1", "Open-Meteo"], "Open-Meteo forecast or OpenF1 track weather", "No weather object is present in the latest contract.", "low", "Keep weather uncertainty visible."))
    if not sources:
        conflicts.append(_conflict("source_registry_missing", ["source registry"], ["local cache"], "generated source registry", "No individual source rows were found.", "medium", "Regenerate source health registry."))

    seen = set()
    unique = []
    for conflict in conflicts:
        key = (conflict["conflict_type"], tuple(conflict["sources"]), conflict["reason"])
        if key in seen:
            continue
        seen.add(key)
        unique.append(conflict)
    return unique[:25]


def _conflict(conflict_type: str, affected_fields: list[str], sources: list[str], preferred: str, reason: str, confidence: str, action: str) -> dict[str, Any]:
    return {
        "conflict_type": conflict_type,
        "affected_fields": [humanize(item) for item in affected_fields],
        "sources": [source for source in sources if source],
        "preferred_source": preferred,
        "reason": reason,
        "confidence": confidence,
        "action_needed": action,
    }
