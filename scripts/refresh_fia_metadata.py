"""Refresh the existing FIA index without invoking prediction or PDF ingestion."""

from datetime import datetime, timezone
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import f1_briefing as research  # noqa: E402


def main():
    season = datetime.now(timezone.utc).year
    registry_file = ROOT / f"data_cache/source_registry/{season}.json"
    try:
        registry = json.loads(registry_file.read_text())
    except (OSError, ValueError):
        registry = research.load_or_build_source_registry(season)
    result = research.fetch_fia_season_index(season, registry=registry, refresh=True)
    # Provider errors/status are retained by the existing resolver and surfaced
    # in the published metadata archive. No synthetic document is generated.
    print(json.dumps({"status": result.get("status"), "source_authority": result.get("source_authority"),
                      "source_status": result.get("source_status"), "errors": result.get("errors", [])}))


if __name__ == "__main__":
    main()
