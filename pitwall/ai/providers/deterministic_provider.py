"""Default free provider backed by deterministic templates."""

from __future__ import annotations

from typing import Any

from pitwall.ai.deterministic import build_driver_ai_explanation


class DeterministicProvider:
    name = "deterministic"

    def explain_driver(self, row: dict[str, Any], context: dict[str, Any] | None = None) -> dict[str, Any]:
        return build_driver_ai_explanation(row, context)
