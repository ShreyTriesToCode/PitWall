#!/usr/bin/env python
"""Generate a compact RUN_REPORT.md from committed PitWall artifacts."""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pitwall.validation.contracts import ContractValidationError, validate_contract_files  # noqa: E402


def read_json(path: Path, fallback):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return fallback


def main() -> int:
    contract = read_json(ROOT / "data_cache/frontend-contract.json", {})
    status = read_json(ROOT / "data_cache/model-status.json", {})
    latest = contract.get("latest") or {}
    try:
        validation = validate_contract_files(ROOT)
        validation_status = "passed"
    except ContractValidationError as error:
        validation = {"error": str(error)}
        validation_status = "failed"
    rows = latest.get("full_grid") or latest.get("all_predictions") or []
    disagreements = [row for row in rows if row.get("model_disagreement_level") in {"medium", "high"}]
    source_health = latest.get("source_health") or contract.get("source_health") or {}
    source_conflicts = latest.get("source_conflicts") or contract.get("source_conflicts") or []
    missing = sorted({item for row in rows for item in (row.get("missing_feature_groups") or [])})
    report = [
        "# PitWall Run Report",
        "",
        f"- Generated at: {datetime.now(timezone.utc).isoformat()}",
        f"- Model version: {latest.get('model_version') or status.get('model_version') or 'pending'}",
        f"- Target event/session: {latest.get('race_name') or contract.get('target_event') or 'pending'} / {latest.get('target_type') or 'race'}",
        f"- Top 10 availability: {len(latest.get('top10') or latest.get('top_10') or [])} rows",
        f"- Full grid availability: {len(rows)} rows",
        f"- Contract validation: {validation_status}",
        f"- Event trust: {latest.get('prediction_trust_score') or latest.get('event_trust_score') or 'pending'}",
        f"- Source health: {source_health.get('status') or 'pending'} / {source_health.get('overall_score') or source_health.get('score') or 'pending'}",
        f"- Source conflicts: {len(source_conflicts)}",
        f"- Major model disagreements: {len(disagreements)}",
        f"- Missing data groups: {', '.join(missing[:10]) if missing else 'none reported'}",
        "",
        "## Validation Details",
        "",
        "```json",
        json.dumps(validation, indent=2, ensure_ascii=False),
        "```",
        "",
        "## Next Recommended Improvements",
        "",
        "- Review high-disagreement driver rows before presenting confident narratives.",
        "- Keep deterministic AI text explanatory only; do not let it modify model outputs.",
        "- Refresh source registry and FIA cache when source conflicts rise.",
    ]
    (ROOT / "RUN_REPORT.md").write_text("\n".join(report) + "\n", encoding="utf-8")
    print(json.dumps({"ok": validation_status == "passed", "path": "RUN_REPORT.md", "validation": validation_status}, indent=2))
    return 0 if validation_status == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
