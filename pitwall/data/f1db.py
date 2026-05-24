"""Optional F1DB adapter.

F1DB is useful for stable historical context, but PitWall should not download a
large release during every prediction run. This adapter therefore reads a local
SQLite artifact when configured and otherwise reports a clear pending/disabled
status.
"""

from __future__ import annotations

import csv
import os
import sqlite3
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable

from .schema_validation import first_present, numeric_or_none
from .source_registry import SourceMetadata, unavailable_source

F1DB_SOURCE_URL = "https://github.com/f1db/f1db"
F1DB_SCHEMA_URL = "https://raw.githubusercontent.com/f1db/f1db/main/f1db.schema.json"
F1DB_LATEST_VERIFIED_RELEASE = "v2026.4.2"
F1DB_LICENSE = "CC-BY-4.0"

F1DB_CATEGORIES = [
    "drivers",
    "constructors",
    "circuits",
    "seasons",
    "races",
    "practice_results",
    "qualifying_results",
    "sprint_results",
    "starting_grid",
    "race_results",
    "fastest_laps",
    "pit_stops",
    "standings",
    "tyre_manufacturers",
    "engine_manufacturers",
]


def env_flag(name: str, default: str = "false") -> bool:
    return str(os.getenv(name, default)).strip().lower() in {"1", "true", "yes", "on"}


def configured_sqlite_path() -> Path | None:
    raw = os.getenv("F1DB_SQLITE_PATH", "").strip()
    return Path(raw).expanduser() if raw else None


def configured_csv_dir() -> Path | None:
    raw = os.getenv("F1DB_CSV_DIR", "").strip()
    return Path(raw).expanduser() if raw else None


def f1db_metadata() -> dict[str, Any]:
    sqlite_path = configured_sqlite_path()
    csv_dir = configured_csv_dir()
    enabled = env_flag("F1DB_ENABLED")
    return {
        "source_name": "F1DB",
        "source_type": "historical_dataset",
        "enabled": enabled,
        "release": os.getenv("F1DB_RELEASE_TAG", F1DB_LATEST_VERIFIED_RELEASE),
        "latest_verified_release": F1DB_LATEST_VERIFIED_RELEASE,
        "license": F1DB_LICENSE,
        "source_url": F1DB_SOURCE_URL,
        "schema_url": F1DB_SCHEMA_URL,
        "sqlite_path": str(sqlite_path) if sqlite_path else "",
        "csv_dir": str(csv_dir) if csv_dir else "",
        "supported_categories": F1DB_CATEGORIES,
        "role": "optional historical feature enrichment and benchmark context",
    }


def _sqlite_tables(path: Path) -> set[str]:
    with sqlite3.connect(path) as conn:
        rows = conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'").fetchall()
    return {str(row[0]) for row in rows}


def _csv_tables(path: Path) -> set[str]:
    return {file.stem for file in path.glob("*.csv") if file.is_file()}


def f1db_status() -> dict[str, Any]:
    meta = f1db_metadata()
    enabled = bool(meta["enabled"])
    sqlite_path = configured_sqlite_path()
    csv_dir = configured_csv_dir()
    if sqlite_path and sqlite_path.exists():
        try:
            tables = sorted(_sqlite_tables(sqlite_path))
            return SourceMetadata(
                source_name="F1DB",
                source_type="historical_dataset",
                enabled=enabled,
                available=True,
                status="available",
                confidence=0.92,
                license=F1DB_LICENSE,
                version=meta["release"],
                source_url=F1DB_SOURCE_URL,
                schema_url=F1DB_SCHEMA_URL,
                artifact_path=str(sqlite_path),
                supported_categories=F1DB_CATEGORIES,
                notes={"format": "sqlite", "tables": tables[:80], "table_count": len(tables)},
            ).to_dict()
        except Exception as error:
            return unavailable_source(
                "F1DB",
                "historical_dataset",
                enabled=enabled,
                confidence=0.35,
                source_url=F1DB_SOURCE_URL,
                license_name=F1DB_LICENSE,
                version=meta["release"],
                warning=f"sqlite_status_error:{error}",
            ).to_dict()
    if csv_dir and csv_dir.exists():
        tables = sorted(_csv_tables(csv_dir))
        return SourceMetadata(
            source_name="F1DB",
            source_type="historical_dataset",
            enabled=enabled,
            available=bool(tables),
            status="available" if tables else "empty_csv_dir",
            confidence=0.86 if tables else 0.25,
            license=F1DB_LICENSE,
            version=meta["release"],
            source_url=F1DB_SOURCE_URL,
            schema_url=F1DB_SCHEMA_URL,
            artifact_path=str(csv_dir),
            supported_categories=F1DB_CATEGORIES,
            notes={"format": "csv", "tables": tables[:80], "table_count": len(tables)},
        ).to_dict()
    return unavailable_source(
        "F1DB",
        "historical_dataset",
        enabled=enabled,
        confidence=0.35,
        source_url=F1DB_SOURCE_URL,
        license_name=F1DB_LICENSE,
        version=meta["release"],
        warning="Set F1DB_SQLITE_PATH or F1DB_CSV_DIR to enable local F1DB enrichment.",
    ).to_dict()


def _query_sqlite(path: Path, sql: str, params: Iterable[Any] = ()) -> list[dict[str, Any]]:
    with sqlite3.connect(path) as conn:
        conn.row_factory = sqlite3.Row
        return [dict(row) for row in conn.execute(sql, tuple(params)).fetchall()]


def read_circuits(limit: int | None = None) -> list[dict[str, Any]]:
    """Read normalized F1DB circuit rows from configured SQLite or CSV data."""

    sqlite_path = configured_sqlite_path()
    csv_dir = configured_csv_dir()
    rows: list[dict[str, Any]] = []
    if sqlite_path and sqlite_path.exists() and "circuits" in _sqlite_tables(sqlite_path):
        sql = "SELECT * FROM circuits"
        if limit:
            sql += " LIMIT ?"
            rows = _query_sqlite(sqlite_path, sql, (int(limit),))
        else:
            rows = _query_sqlite(sqlite_path, sql)
    elif csv_dir and (csv_dir / "circuits.csv").exists():
        with (csv_dir / "circuits.csv").open(newline="", encoding="utf-8") as handle:
            reader = csv.DictReader(handle)
            for row in reader:
                rows.append(dict(row))
                if limit and len(rows) >= limit:
                    break
    return [normalize_circuit_row(row) for row in rows if row]


def normalize_circuit_row(row: dict[str, Any]) -> dict[str, Any]:
    """Normalize common F1DB circuit columns across release formats."""

    return {
        "circuit_id": first_present(row, "id", "circuitId", "circuit_id"),
        "circuit_ref": first_present(row, "ref", "circuitRef", "circuit_ref", "identifier"),
        "name": first_present(row, "name", "fullName", "full_name"),
        "country": first_present(row, "country", "countryName", "country_name"),
        "locality": first_present(row, "locality", "placeName", "place_name"),
        "latitude": numeric_or_none(first_present(row, "latitude", "lat")),
        "longitude": numeric_or_none(first_present(row, "longitude", "lng", "lon")),
        "source": "F1DB",
        "source_confidence": 0.92,
    }


def pit_stop_team_summary(limit: int | None = None) -> list[dict[str, Any]]:
    """Return coarse pit-stop aggregates when a recognizable F1DB table exists."""

    sqlite_path = configured_sqlite_path()
    if not sqlite_path or not sqlite_path.exists():
        return []
    tables = _sqlite_tables(sqlite_path)
    table_name = next((name for name in ("pit_stops", "pitStops", "pitstops") if name in tables), None)
    if not table_name:
        return []
    rows = _query_sqlite(sqlite_path, f"SELECT * FROM {table_name}")
    by_constructor: dict[str, list[float]] = defaultdict(list)
    for row in rows:
        constructor = first_present(row, "constructorId", "constructor_id", "team", "constructor")
        duration = numeric_or_none(first_present(row, "duration", "milliseconds", "time"))
        if constructor and duration is not None:
            by_constructor[str(constructor)].append(duration)
    summary = []
    for constructor, values in by_constructor.items():
        if not values:
            continue
        mean = sum(values) / len(values)
        variance = sum((value - mean) ** 2 for value in values) / len(values)
        summary.append({
            "constructor": constructor,
            "pit_stop_count": len(values),
            "avg_duration": round(mean, 4),
            "std_duration": round(variance ** 0.5, 4),
            "source": "F1DB",
        })
    summary.sort(key=lambda row: row["pit_stop_count"], reverse=True)
    return summary[:limit] if limit else summary
