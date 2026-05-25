"""SQLite and optional hosted persistence helpers for PitWall."""

from __future__ import annotations

import json
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def init_pitwall_db(db_path: str | Path) -> None:
    db_path = Path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(db_path) as conn:
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS run_status (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT NOT NULL,
                status_type TEXT NOT NULL,
                payload_json TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS predictions (
                prediction_id TEXT PRIMARY KEY,
                created_at TEXT NOT NULL,
                race_id TEXT,
                target_type TEXT,
                payload_json TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS feature_snapshots (
                feature_id TEXT PRIMARY KEY,
                created_at TEXT NOT NULL,
                feature_version TEXT,
                payload_json TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS strategy_annotations (
                annotation_id TEXT PRIMARY KEY,
                created_at TEXT NOT NULL,
                race_id TEXT,
                driver_id TEXT,
                payload_json TEXT NOT NULL
            )
            """
        )
        conn.commit()


def sqlite_upsert_prediction(db_path: str | Path, entry: dict[str, Any], generated_at: str | None = None) -> None:
    init_pitwall_db(db_path)
    prediction_id = entry.get("prediction_id") or f"{entry.get('race_id')}-{entry.get('target_type')}-{entry.get('generated_iso')}"
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            """
            INSERT INTO predictions(prediction_id, created_at, race_id, target_type, payload_json)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(prediction_id) DO UPDATE SET
                created_at=excluded.created_at,
                race_id=excluded.race_id,
                target_type=excluded.target_type,
                payload_json=excluded.payload_json
            """,
            (
                prediction_id,
                entry.get("generated_iso") or generated_at or datetime.now(timezone.utc).isoformat(),
                entry.get("race_id"),
                entry.get("target_type"),
                json.dumps(entry, ensure_ascii=False, default=str),
            ),
        )
        conn.commit()


def sqlite_insert_run_status(db_path: str | Path, status_type: str, payload: dict[str, Any], created_at: str | None = None) -> None:
    init_pitwall_db(db_path)
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            "INSERT INTO run_status(created_at, status_type, payload_json) VALUES (?, ?, ?)",
            (created_at or datetime.now(timezone.utc).isoformat(), status_type, json.dumps(payload, ensure_ascii=False, default=str)),
        )
        conn.commit()


def supabase_sync_status(url: str | None = None, service_role_key: str | None = None) -> dict[str, Any]:
    url = (url if url is not None else os.getenv("SUPABASE_URL", "")).strip()
    service_role_key = (
        service_role_key
        if service_role_key is not None
        else os.getenv("SUPABASE_SERVICE_ROLE_KEY", os.getenv("SUPABASE_KEY", ""))
    ).strip()
    if not url or not service_role_key:
        return {"enabled": False, "status": "not_configured"}
    return {"enabled": True, "status": "configured_optional_manual_sync"}
