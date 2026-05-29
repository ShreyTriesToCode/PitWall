"""Provider protocol for optional local-only AI helpers."""

from __future__ import annotations

from typing import Any, Protocol


class AIProvider(Protocol):
    name: str

    def explain_driver(self, row: dict[str, Any], context: dict[str, Any] | None = None) -> dict[str, Any]:
        """Return explanation text for an existing prediction row."""
