"""Shared metadata helpers for optional PitWall data sources."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(frozen=True)
class SourceMetadata:
    source_name: str
    source_type: str
    enabled: bool
    available: bool
    status: str
    confidence: float
    license: str | None = None
    version: str | None = None
    source_url: str | None = None
    schema_url: str | None = None
    artifact_path: str | None = None
    checked_at: str = field(default_factory=utc_now_iso)
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    supported_categories: list[str] = field(default_factory=list)
    notes: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def unavailable_source(
    name: str,
    source_type: str,
    *,
    enabled: bool,
    confidence: float,
    source_url: str | None = None,
    license_name: str | None = None,
    version: str | None = None,
    warning: str | None = None,
) -> SourceMetadata:
    warnings = [warning] if warning else []
    return SourceMetadata(
        source_name=name,
        source_type=source_type,
        enabled=enabled,
        available=False,
        status="pending" if enabled else "disabled",
        confidence=confidence,
        license=license_name,
        version=version,
        source_url=source_url,
        warnings=warnings,
    )
