"""Optional local-only Ollama provider.

Disabled unless LOCAL_LLM_ENABLED=true. This module is safe to import on CI and
Vercel because it does not contact Ollama until called.
"""

from __future__ import annotations

import json
import os
import urllib.request
from typing import Any

from pitwall.ai.deterministic import build_driver_ai_explanation


class OllamaProvider:
    name = "ollama"

    def __init__(self, base_url: str | None = None, model: str | None = None, timeout: float = 3.0) -> None:
        self.base_url = (base_url or os.getenv("OLLAMA_BASE_URL") or "http://localhost:11434").rstrip("/")
        self.model = model or os.getenv("OLLAMA_MODEL", "")
        self.timeout = timeout

    def explain_driver(self, row: dict[str, Any], context: dict[str, Any] | None = None) -> dict[str, Any]:
        deterministic = build_driver_ai_explanation(row, context)
        if os.getenv("LOCAL_LLM_ENABLED", "false").lower() != "true" or not self.model:
            return deterministic
        prompt = (
            "Rewrite the following PitWall explanation concisely without adding facts, numbers, or claims. "
            "Do not alter rankings, probabilities, source state, race results, or timing state.\n"
            + json.dumps(deterministic, ensure_ascii=False)
        )
        try:
            body = json.dumps({"model": self.model, "prompt": prompt, "stream": False}).encode("utf-8")
            req = urllib.request.Request(f"{self.base_url}/api/generate", data=body, headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=self.timeout) as response:
                payload = json.loads(response.read().decode("utf-8"))
            rewritten = str(payload.get("response") or "").strip()
            if rewritten:
                deterministic["local_llm_note"] = rewritten[:800]
                deterministic["generated_by"] = "deterministic_with_local_ollama_summary"
        except Exception:
            deterministic["local_llm_note"] = "Local Ollama was unavailable; deterministic explanation used."
        return deterministic
