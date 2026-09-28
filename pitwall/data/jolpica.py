"""Validated, bounded Jolpica access. No stale response is silently reused."""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import logging
from pathlib import Path
import re

import requests

from pitwall.io.atomic import atomic_write_json

BASE = "https://api.jolpi.ca/ergast/f1"
LOG = logging.getLogger(__name__)


class DataUnavailable(ValueError):
    """Missing, incomplete, inconsistent, or failed provider response."""


def instant(value: str) -> datetime:
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            raise ValueError("timezone absent")
        return dt.astimezone(timezone.utc)
    except (TypeError, AttributeError, ValueError) as exc:
        raise DataUnavailable("Invalid timezone-aware timestamp") from exc


def digest(value) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def integer(value, minimum=1) -> int:
    if isinstance(value, bool) or not re.fullmatch(r"\d+", str(value)) or int(value) < minimum:
        raise DataUnavailable("Invalid integer in provider response")
    return int(value)


def race_identity(raw: dict) -> tuple[int, int]:
    return integer(raw.get("season"), 1950), integer(raw.get("round"))


def race_event(raw: dict) -> dict:
    season, round_no = race_identity(raw)
    if not raw.get("raceName") or not raw.get("Circuit", {}).get("circuitId"):
        raise DataUnavailable("Race name or circuit identifier missing")
    start = instant(f"{raw.get('date')}T{raw.get('time')}").isoformat() if raw.get("time") else None
    # Missing start times remain unknown; midnight is not an event start time.
    sessions = []
    for key, label in [("FirstPractice", "Practice 1"), ("SecondPractice", "Practice 2"),
                       ("ThirdPractice", "Practice 3"), ("SprintQualifying", "Sprint qualifying"),
                       ("SprintShootout", "Sprint qualifying"), ("Sprint", "Sprint"), ("Qualifying", "Qualifying")]:
        session = raw.get(key)
        if session:
            stamp = instant(f"{session.get('date')}T{session.get('time')}").isoformat() if session.get("time") else None
            sessions.append({"name": label, "start_at": stamp, "date": session.get("date")})
    sessions.append({"name": "Race", "start_at": start, "date": raw.get("date")})
    return {"id": f"{season}:{round_no}:race", "season": season, "round": round_no,
            "name": raw["raceName"], "circuit": raw["Circuit"]["circuitName"],
            "location": raw["Circuit"].get("Location", {}).get("locality"),
            "date": raw.get("date"), "start_at": start, "sessions": sessions,
            "source_url": f"{BASE}/{season}/{round_no}/races/"}


def races(payload: dict, season: int | None = None) -> list[dict]:
    try:
        values = payload["MRData"]["RaceTable"]["Races"]
        if not isinstance(values, list):
            raise DataUnavailable("RaceTable.Races must be an array")
        ids = [race_identity(r) for r in values]
        if len(ids) != len(set(ids)) or (season and any(y != season for y, _ in ids)):
            raise DataUnavailable("Duplicate races or incorrect season")
        return values
    except (KeyError, TypeError) as exc:
        raise DataUnavailable("Jolpica response schema changed") from exc


def classification(raw: dict, field: str) -> list[dict]:
    values = raw.get(field)
    if not isinstance(values, list) or len(values) < 2:
        raise DataUnavailable(f"{field} is missing or incomplete")
    rows = []
    for item in values:
        try:
            driver = item["Driver"]
            position = integer(item["position"])
            rows.append({"driver_id": driver["driverId"], "name": f"{driver['givenName']} {driver['familyName']}",
                         "team": item["Constructor"]["name"], "position": position,
                         "status": item.get("status"), "points": item.get("points"),
                         "q1": item.get("Q1"), "q2": item.get("Q2"), "q3": item.get("Q3")})
        except (KeyError, TypeError) as exc:
            raise DataUnavailable(f"Invalid {field} row") from exc
    ids = [row["driver_id"] for row in rows]
    positions = [row["position"] for row in rows]
    if len(set(ids)) != len(ids) or sorted(positions) != list(range(1, len(rows) + 1)):
        raise DataUnavailable(f"Duplicate drivers or incomplete positions in {field}")
    return sorted(rows, key=lambda row: row["position"])


def validate_envelope(data):
    meta = data["MRData"]
    if integer(meta["total"], 0) > integer(meta["limit"], 1) or integer(meta["offset"], 0) != 0:
        raise DataUnavailable("Incomplete provider pagination")


class Jolpica:
    def __init__(self, cache_dir: Path):
        self.cache_dir = cache_dir
        self.sources: list[dict] = []

    def fetch(self, endpoint: str, *, ttl: int = 300) -> dict:
        if not re.fullmatch(r"[\w/.-]+", endpoint) or ".." in endpoint:
            raise ValueError("Invalid provider endpoint")
        url = f"{BASE}/{endpoint.strip('/')}/?limit=100"
        cache = self.cache_dir / f"{digest(url)}.json"
        now = datetime.now(timezone.utc)
        try:
            saved = json.loads(cache.read_text())
            age = (now - instant(saved["retrieved_at"])).total_seconds()
            if 0 <= age < ttl and saved["url"] == url:
                validate_envelope(saved["data"])
                self.sources.append({"url": url, "retrieved_at": saved["retrieved_at"], "status": "CACHED", "sha256": digest(saved["data"])})
                return saved["data"]
        except FileNotFoundError:
            pass
        except (OSError, ValueError, KeyError, TypeError) as exc:
            LOG.warning("Ignoring invalid provider cache %s (%s)", cache.name, type(exc).__name__)
        try:
            response = requests.get(url, timeout=(5, 20), headers={"User-Agent": "PitWall/3 (F1 analytics)"})
            response.raise_for_status()
            if len(response.content) > 5_000_000:
                raise DataUnavailable("Provider response exceeds size limit")
            data = response.json()
            # Single-race/calendar endpoints fit within 100. Never accept a truncated page.
            validate_envelope(data)
            stamp = datetime.now(timezone.utc).isoformat()
            atomic_write_json(cache, {"url": url, "retrieved_at": stamp, "data": data})
            self.sources.append({"url": url, "retrieved_at": stamp, "status": "AVAILABLE", "sha256": digest(data)})
            return data
        except (requests.RequestException, ValueError, KeyError, TypeError) as exc:
            LOG.warning("Jolpica request failed: %s (%s)", url, type(exc).__name__)
            self.sources.append({"url": url, "retrieved_at": None, "status": "UNAVAILABLE"})
            raise DataUnavailable("Jolpica data is unavailable or invalid") from exc


def select_event(events: list[dict], completed: set[str], now: datetime) -> dict:
    now = instant(now.isoformat())
    if any(e.get("start_at") is None and e.get("date", "") >= now.date().isoformat() for e in events):
        return {"state": "UNAVAILABLE", "event": None, "reason": "Calendar contains a future race with an unknown start time."}
    ordered = sorted((e for e in events if e.get("start_at")), key=lambda e: instant(e["start_at"]))
    for event in ordered:
        start = instant(event["start_at"])
        if event["id"] in completed:
            continue
        if start > now:
            return {"state": "UPCOMING", "event": event, "reason": None}
        # Schedule alone is insufficient to assert LIVE. Cancellation, postponement
        # and delayed results require a separate verified session feed.
        if (now - start).total_seconds() < 8 * 3600:
            return {"state": "UPDATING", "event": event, "reason": "Scheduled start has passed; check timing for verified session activity."}
    return {"state": "UNAVAILABLE", "event": None, "reason": "No upcoming race with a confirmed start time is available."}
