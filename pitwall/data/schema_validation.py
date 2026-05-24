"""Small schema guards for optional source adapters."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable, Mapping


@dataclass(frozen=True)
class SchemaCheck:
    source: str
    ok: bool
    missing: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def require_keys(row: Mapping[str, Any] | None, required: Iterable[str], source: str) -> SchemaCheck:
    """Validate that a row-like object contains the required keys.

    The adapters use this as a guard before exposing derived features. It is
    deliberately permissive about additional columns because F1 datasets evolve
    over time.
    """

    if not isinstance(row, Mapping):
        return SchemaCheck(source=source, ok=False, missing=list(required), warnings=["row_not_mapping"])
    missing = [key for key in required if key not in row or row.get(key) in (None, "")]
    return SchemaCheck(source=source, ok=not missing, missing=missing)


def numeric_or_none(value: Any) -> float | None:
    try:
        if value in (None, ""):
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def first_present(row: Mapping[str, Any], *names: str) -> Any:
    for name in names:
        if name in row and row.get(name) not in (None, ""):
            return row.get(name)
    return None
