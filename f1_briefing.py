import os
import re
import json
import time
import gzip
import io
import zlib
import base64
import smtplib
import argparse
import subprocess
from pathlib import Path
from datetime import datetime, timedelta, timezone
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

import joblib
import numpy as np
import pandas as pd
import requests
from icalendar import Calendar
from dateutil import tz
from sklearn.ensemble import ExtraTreesClassifier, ExtraTreesRegressor, RandomForestClassifier, RandomForestRegressor, HistGradientBoostingClassifier, HistGradientBoostingRegressor
from sklearn.metrics import roc_auc_score, brier_score_loss, mean_absolute_error
from sklearn.neural_network import MLPRegressor
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

try:
    import fastf1
except Exception:
    fastf1 = None


F1_ICS_URL = os.getenv("F1_ICS_URL", "").strip()

EMAIL_ENABLED = os.getenv("EMAIL_ENABLED", "true").lower() == "true"
EMAIL_ADDRESS = os.getenv("EMAIL_ADDRESS")
EMAIL_APP_PASSWORD = os.getenv("EMAIL_APP_PASSWORD")
EMAIL_TO = os.getenv("EMAIL_TO")

GITHUB_REPOSITORY = os.getenv("GITHUB_REPOSITORY")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")

USER_TIMEZONE_NAME = os.getenv("USER_TIMEZONE", "Asia/Kolkata")
USER_TIMEZONE = tz.gettz(USER_TIMEZONE_NAME) or timezone.utc
LOOKAHEAD_DAYS = int(os.getenv("LOOKAHEAD_DAYS", "90"))
FINAL_RESULTS_DELAY_HOURS = int(os.getenv("FINAL_RESULTS_DELAY_HOURS", "8"))
NOTIFICATION_WINDOW_HOURS = int(os.getenv("NOTIFICATION_WINDOW_HOURS", "8"))
FORCE_NOTIFY = os.getenv("FORCE_NOTIFY", "false").lower() == "true"
OUTPUT_MODE = os.getenv("OUTPUT_MODE", "auto").lower().strip()
GITHUB_EVENT_NAME = os.getenv("GITHUB_EVENT_NAME", "").lower().strip()

ML_START_YEAR = int(os.getenv("ML_START_YEAR", "2018"))
USE_FULL_HISTORICAL_DATA = os.getenv("USE_FULL_HISTORICAL_DATA", "true").lower() == "true"
FULL_DATA_BACKFILL_LIMIT = int(os.getenv("FULL_DATA_BACKFILL_LIMIT", "10"))
JOLPICA_REQUEST_SLEEP = float(os.getenv("JOLPICA_REQUEST_SLEEP", "1.2"))

BASE_DIR = Path(__file__).resolve().parent
BRIEFINGS_DIR = BASE_DIR / "briefings"
DATA_CACHE_DIR = BASE_DIR / "data_cache"
HTTP_CACHE_DIR = Path(os.getenv("HTTP_CACHE_DIR", DATA_CACHE_DIR / "http"))
FULL_RACE_CACHE_DIR = Path(os.getenv("FULL_RACE_CACHE_DIR", DATA_CACHE_DIR / "full_races"))
FASTF1_CACHE_DIR = Path(os.getenv("FASTF1_CACHE_DIR", BASE_DIR / "fastf1_cache"))
MODEL_DIR = Path(os.getenv("MODEL_DIR", BASE_DIR / "models" / "saved_models"))

MODEL_BUNDLE_PATH = MODEL_DIR / "f1_hybrid_full_data_bundle.pkl"
MODEL_META_PATH = MODEL_DIR / "f1_hybrid_full_data_meta.json"
MODEL_STATUS_PATH = BASE_DIR / "MODEL_STATUS.md"
MODEL_SCHEMA_VERSION = "2026.05-high-accuracy-v4"

JOLPICA_BASE = "https://api.jolpi.ca/ergast/f1"
F1_LIVE_TIMING_STATIC_BASE = os.getenv("F1_LIVE_TIMING_STATIC_BASE", "https://livetiming.formula1.com/static").rstrip("/")
OPENF1_BASE = os.getenv("OPENF1_BASE", "https://api.openf1.org/v1").rstrip("/")
OPENF1_ENABLED = os.getenv("OPENF1_ENABLED", "true").lower() == "true"
OPENF1_REQUEST_SLEEP = float(os.getenv("OPENF1_REQUEST_SLEEP", "0.45"))
UPGRADES_ENABLED = os.getenv("UPGRADES_ENABLED", "true").lower() == "true"
F1_REGULATIONS_ENABLED = os.getenv("F1_REGULATIONS_ENABLED", "true").lower() == "true"
OFFICIAL_CALENDAR_ENABLED = os.getenv("OFFICIAL_CALENDAR_ENABLED", "true").lower() == "true"
FIA_TECH_UPDATE_BASE = os.getenv("FIA_TECH_UPDATE_BASE", "https://www.fia.com/news").rstrip("/")
OFFICIAL_F1_CALENDAR_URL = os.getenv("OFFICIAL_F1_CALENDAR_URL", "https://www.formula1.com/en/racing/{year}")
UPGRADE_NEWS_URLS = [u.strip() for u in os.getenv("UPGRADE_NEWS_URLS", "").split(",") if u.strip()]
JOLPICA_HEADERS = {
    "User-Agent": "f1-race-intel/3.0 cache-first full-data model",
    "Accept": "application/json",
}

FASTF1_SESSION_ORDER = ["R", "Q", "SQ", "S", "FP3", "FP2", "FP1"]

PREDICTION_LABELS = {
    "ml_win_probability": "ML win probability",
    "ml_podium_probability": "ML podium probability",
    "ml_top10_probability": "ML top 10 probability",
    "ml_finish_position_score": "ML finish-position model",
    "ml_lap_time_forecast_score": "neural lap-time forecast",
    "transparent_racecraft_score": "transparent racecraft score",
    "driver_form": "driver form",
    "driver_skill": "driver skill profile",
    "car_performance": "car performance",
    "constructor_form": "constructor form",
    "recent_result": "recent race result",
    "qualifying": "qualifying and grid position",
    "circuit_history": "same-circuit history",
    "race_pace": "historical lap pace",
    "pit_execution": "pit-stop execution",
    "team_strategy": "team strategy gain",
    "reliability": "reliability",
    "team_track_fit": "team-track fit",
    "weather_adaptation": "weather adaptation",
    "track_trait_fit": "track trait fit",
    "sprint_performance": "sprint performance",
    "current_season_car_performance": "current-season car performance",
    "current_season_recent_form": "current-season recent constructor form",
    "upgrade_package_impact": "official upgrade package impact",
    "regulation_fit": "regulation-era fit",
    "calendar_confidence": "official calendar confidence",
    "timing_session_result": "official timing session result",
    "timing_starting_grid": "official timing starting grid",
    "timing_lap_pace": "official timing lap pace",
    "timing_sector_performance": "official sector performance",
    "timing_pit_execution": "official timing pit execution",
    "timing_stint_strength": "official tyre stint strength",
    "timing_telemetry_speed": "official telemetry speed",
    "timing_position_gain": "official timing position gain",
    "timing_car_performance": "official timing car performance",
    "fastf1_race_pace": "FastF1 clean-lap pace",
    "fastf1_consistency": "FastF1 consistency",
    "fastf1_tyre_stint": "FastF1 tyre/stint evidence",
}


class BackfillBudget:
    def __init__(self, limit):
        self.limit = int(limit)
        self.used = 0
        self.fetched = []

    def can_fetch(self):
        return self.used < self.limit

    def mark(self, key):
        self.used += 1
        self.fetched.append(key)


BACKFILL_BUDGET = BackfillBudget(FULL_DATA_BACKFILL_LIMIT)
_RESULT_READINESS_CACHE = None


def ensure_dirs():
    for path in [BRIEFINGS_DIR, DATA_CACHE_DIR, HTTP_CACHE_DIR, FULL_RACE_CACHE_DIR, FASTF1_CACHE_DIR, MODEL_DIR]:
        path.mkdir(parents=True, exist_ok=True)


def now_local():
    return datetime.now(USER_TIMEZONE)


def safe_float(value):
    try:
        if value is None or value == "":
            return None
        if isinstance(value, str) and value.strip().lower() in {"nan", "none"}:
            return None
        number = float(value)
        return number if np.isfinite(number) else None
    except (TypeError, ValueError):
        return None


def safe_int(value):
    try:
        if value is None or value == "":
            return None
        return int(float(value))
    except (TypeError, ValueError):
        return None


def average(values):
    clean = [safe_float(v) for v in values]
    clean = [v for v in clean if v is not None]
    return sum(clean) / len(clean) if clean else None


def safe_std(values):
    clean = [safe_float(v) for v in values]
    clean = [v for v in clean if v is not None]
    return float(np.std(clean)) if len(clean) > 1 else None


def regulation_era_factor(season):
    season = safe_int(season) or now_local().year
    if season <= 2013:
        return 0.1
    if season <= 2021:
        return 1.0
    if season <= 2025:
        return 0.5
    return 0.8


def weighted_average(items):
    total = 0.0
    weight_sum = 0.0
    for value, weight in items:
        value = safe_float(value)
        if value is None:
            continue
        total += value * weight
        weight_sum += weight
    return total / weight_sum if weight_sum else None


def normalize_scores(raw, reverse=False):
    if not raw:
        return {}
    values = [safe_float(v) for v in raw.values()]
    values = [v for v in values if v is not None]
    if not values:
        return {}
    low = min(values)
    high = max(values)
    out = {}
    for key, value in raw.items():
        value = safe_float(value)
        if value is None:
            continue
        if high == low:
            out[key] = 75.0
        elif reverse:
            out[key] = max(0.0, min(100.0, (high - value) / (high - low) * 100.0))
        else:
            out[key] = max(0.0, min(100.0, (value - low) / (high - low) * 100.0))
    return out


def normalize_name(name):
    text = str(name or "").replace("_", " ").strip()
    return " ".join(part.capitalize() if part.isupper() else part for part in text.split())


def make_slug(text):
    text = str(text or "").lower()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    return text.strip("-")[:100] or "f1"


def score_position(position, field_size=22):
    position = safe_int(position)
    if position is None or position <= 0:
        return None
    return max(0.0, 100.0 * (field_size - position) / max(1, field_size - 1))


def parse_lap_time_to_seconds(value):
    if value is None:
        return None
    text = str(value).strip()
    try:
        parts = text.split(":")
        if len(parts) == 1:
            return float(parts[0])
        if len(parts) == 2:
            return int(parts[0]) * 60 + float(parts[1])
        if len(parts) == 3:
            return int(parts[0]) * 3600 + int(parts[1]) * 60 + float(parts[2])
    except (TypeError, ValueError):
        return None
    return None


def require_env_vars():
    missing = []
    if not F1_ICS_URL:
        missing.append("F1_ICS_URL")
    if EMAIL_ENABLED:
        for key, value in {
            "EMAIL_ADDRESS": EMAIL_ADDRESS,
            "EMAIL_APP_PASSWORD": EMAIL_APP_PASSWORD,
            "EMAIL_TO": EMAIL_TO,
        }.items():
            if not value:
                missing.append(key)
    if missing:
        raise RuntimeError("Missing required environment variables: " + ", ".join(missing))


def safe_step(name, fn, *args, **kwargs):
    try:
        return fn(*args, **kwargs)
    except Exception as error:
        print(f"{name} failed, continuing: {error}")
        return None


def cache_key_for_url(url, params=None):
    return make_slug(url + "?" + json.dumps(params or {}, sort_keys=True))


def polite_sleep():
    if JOLPICA_REQUEST_SLEEP > 0:
        time.sleep(JOLPICA_REQUEST_SLEEP)


def safe_get(url, params=None, timeout=30, headers=None, optional_404=False, use_cache=True):
    ensure_dirs()
    cache_path = HTTP_CACHE_DIR / f"{cache_key_for_url(url, params)}.json"

    if use_cache and cache_path.exists():
        try:
            age = time.time() - cache_path.stat().st_mtime
            if age < 12 * 3600:
                fake = requests.Response()
                fake.status_code = 200
                fake._content = cache_path.read_bytes()
                return fake
        except Exception:
            pass

    for attempt in range(4):
        try:
            response = requests.get(url, params=params or {}, headers=headers or {}, timeout=timeout)

            if response.status_code == 404 and optional_404:
                print(f"Optional endpoint not available: {url}")
                return None

            if response.status_code == 429:
                wait = 5 + attempt * 5
                print(f"Rate limited. Waiting {wait}s before retry.")
                time.sleep(wait)
                continue

            response.raise_for_status()

            if use_cache and "json" in response.headers.get("content-type", "").lower():
                cache_path.write_bytes(response.content)

            return response
        except Exception as error:
            print(f"GET failed: {url} params={params} attempt={attempt + 1}/4 error={error}")
            if attempt < 3:
                time.sleep(2 + attempt * 2)

    if use_cache and cache_path.exists():
        try:
            print(f"Using stale HTTP cache after network failure: {url}")
            fake = requests.Response()
            fake.status_code = 200
            fake._content = cache_path.read_bytes()
            return fake
        except Exception:
            pass

    return None


def jolpica_get(endpoint, params=None, optional_404=False, use_cache=True):
    if not endpoint.startswith("/"):
        endpoint = "/" + endpoint
    if not endpoint.endswith(".json"):
        endpoint += ".json"

    polite_sleep()
    response = safe_get(JOLPICA_BASE + endpoint, params=params, headers=JOLPICA_HEADERS, optional_404=optional_404, use_cache=use_cache)
    if not response:
        return {}
    try:
        data = response.json()
    except json.JSONDecodeError:
        print(f"Jolpica returned non-JSON for {endpoint}")
        return {}
    print(f"Jolpica OK: {endpoint}")
    return data


def mrdata_list(data, table_name, list_name):
    try:
        return data.get("MRData", {}).get(table_name, {}).get(list_name, [])
    except AttributeError:
        return []


def mrdata_standing_list(data):
    try:
        lists = data.get("MRData", {}).get("StandingsTable", {}).get("StandingsLists", [])
        return lists[0] if lists else {}
    except Exception:
        return {}


def fetch_schedule(year):
    return mrdata_list(jolpica_get(f"/{year}"), "RaceTable", "Races")


def parse_race_datetime(race):
    date = race.get("date")
    time_value = race.get("time") or "00:00:00Z"
    if not date:
        return None
    try:
        return datetime.fromisoformat(f"{date}T{time_value}".replace("Z", "+00:00")).astimezone(USER_TIMEZONE)
    except ValueError:
        return None


def final_results_cutoff(race):
    race_dt = parse_race_datetime(race)
    if race_dt is None:
        return None
    return race_dt + timedelta(hours=FINAL_RESULTS_DELAY_HOURS)


def is_race_past_calendar_cutoff(race):
    cutoff = final_results_cutoff(race)
    return bool(cutoff and now_local() >= cutoff)


def is_race_future_or_not_final_yet(race):
    return not is_race_past_calendar_cutoff(race)


def race_has_results(data):
    try:
        races = data.get("results", [])
        return bool(races and races[0].get("Results"))
    except AttributeError:
        return False


def cache_status_for_race(race, data):
    if race_has_results(data):
        return "final_results_available"
    if race is not None and is_race_past_calendar_cutoff(race):
        return "past_calendar_no_results_yet"
    return "future_or_partial"


def should_use_cached_round(cached, race=None, require_final_if_past=False):
    if not cached:
        return False

    data = cached.get("data", {})
    status = cached.get("status")

    if race is None:
        return True

    if require_final_if_past and is_race_past_calendar_cutoff(race):
        # Old caches may not have a status field. For past races, trust only caches with race results.
        return race_has_results(data)

    if status == "future_or_partial" and is_race_past_calendar_cutoff(race):
        # A race cached before it happened must be refreshed after the GP.
        return False

    return True


def full_race_cache_path(season, round_no):
    return FULL_RACE_CACHE_DIR / f"{season}-{round_no}.json.gz"


def read_full_race_cache(season, round_no):
    path = full_race_cache_path(season, round_no)
    if not path.exists():
        return None
    try:
        with gzip.open(path, "rt", encoding="utf-8") as f:
            return json.load(f)
    except Exception as error:
        print(f"Could not read full race cache {path}: {error}")
        return None


def write_full_race_cache(season, round_no, payload):
    path = full_race_cache_path(season, round_no)
    path.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(path, "wt", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False)
    return path


def fetch_round_data_direct(season, round_no, use_cache=True):
    return {
        "results": mrdata_list(jolpica_get(f"/{season}/{round_no}/results", use_cache=use_cache), "RaceTable", "Races"),
        "qualifying": mrdata_list(jolpica_get(f"/{season}/{round_no}/qualifying", optional_404=True, use_cache=use_cache), "RaceTable", "Races"),
        "pitstops": mrdata_list(jolpica_get(f"/{season}/{round_no}/pitstops", optional_404=True, use_cache=use_cache), "RaceTable", "Races"),
        "laps": mrdata_list(jolpica_get(f"/{season}/{round_no}/laps", optional_404=True, use_cache=use_cache), "RaceTable", "Races"),
        "sprint": mrdata_list(jolpica_get(f"/{season}/{round_no}/sprint", optional_404=True, use_cache=use_cache), "RaceTable", "Races"),
        "sprint_qualifying": mrdata_list(
            jolpica_get(f"/{season}/{round_no}/sprint/qualifying", optional_404=True, use_cache=use_cache),
            "RaceTable",
            "Races",
        ),
    }


def fetch_round_data_cached(season, round_no, allow_backfill=True, force_fetch=False, race=None, training_mode=False):
    """
    Cache-first full race loader.

    Rules:
    1. Historical ML training uses only races whose scheduled GP time plus FINAL_RESULTS_DELAY_HOURS has passed.
    2. A race is used for ML training only when race results exist.
    3. Future GPs may still be fetched for prediction/session context when force_fetch=True, but they are not used as final training rows.
    4. If a race was cached before it had results, it is refreshed after the GP cutoff.
    """
    cached = read_full_race_cache(season, round_no)

    if cached and not force_fetch and should_use_cached_round(cached, race=race, require_final_if_past=training_mode):
        data = cached.get("data", {})
        if training_mode and not race_has_results(data):
            return {}
        return data

    key = f"{season}-{round_no}"

    if race is not None and training_mode and is_race_future_or_not_final_yet(race):
        print(f"Skipping future/not-final GP for training cache: {key}")
        return {}

    if allow_backfill and not force_fetch and not BACKFILL_BUDGET.can_fetch():
        print(f"Full-data backfill limit reached. Skipping uncached historical race {key}.")
        return {}

    print(f"Fetching full round data for {key}")
    bypass_http_cache = bool(training_mode and race is not None and is_race_past_calendar_cutoff(race))
    data = fetch_round_data_direct(season, round_no, use_cache=not bypass_http_cache)
    status = cache_status_for_race(race, data) if race is not None else ("final_results_available" if race_has_results(data) else "unknown")

    # Avoid storing empty future training files as if they were complete history.
    if training_mode and status == "future_or_partial":
        print(f"Not caching future/partial training race: {key}")
        return {}

    payload = {
        "season": season,
        "round": str(round_no),
        "fetched_at": now_local().isoformat(),
        "status": status,
        "final_results_delay_hours": FINAL_RESULTS_DELAY_HOURS,
        "data": data,
    }
    write_full_race_cache(season, round_no, payload)

    if allow_backfill and not force_fetch:
        BACKFILL_BUDGET.mark(key)

    if training_mode and not race_has_results(data):
        return {}

    return data


def fetch_driver_standings(season):
    data = jolpica_get(f"/{season}/driverStandings")
    standing = mrdata_standing_list(data)
    return standing.get("DriverStandings", []) if standing else []


def fetch_constructor_standings(season):
    data = jolpica_get(f"/{season}/constructorStandings")
    standing = mrdata_standing_list(data)
    return standing.get("ConstructorStandings", []) if standing else []


def fetch_last_results(season):
    races = mrdata_list(jolpica_get(f"/{season}/last/results"), "RaceTable", "Races")
    return races[0].get("Results", []) if races else []


def fetch_ics_calendar():
    url = F1_ICS_URL.strip().strip('"').strip("'")
    if url.startswith("webcal://"):
        url = "https://" + url.replace("webcal://", "", 1)
    if not url.startswith(("http://", "https://")):
        raise RuntimeError("F1_ICS_URL must be a normal HTTP URL.")
    response = requests.get(url, timeout=30)
    response.raise_for_status()
    return Calendar.from_ical(response.content)


def normalize_datetime(value):
    if isinstance(value, datetime):
        dt = value
    else:
        dt = datetime.combine(value, datetime.min.time())
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(USER_TIMEZONE)


def find_next_calendar_event(calendar):
    events = get_f1_calendar_events(calendar)
    return events[0] if events else None


def get_f1_calendar_events(calendar):
    now = now_local()
    max_date = now + timedelta(days=LOOKAHEAD_DAYS)
    events = []

    for component in calendar.walk():
        if component.name != "VEVENT":
            continue

        title = str(component.get("summary", ""))
        location = str(component.get("location", ""))
        description = str(component.get("description", ""))
        start_raw = component.get("dtstart")
        end_raw = component.get("dtend")

        if not start_raw:
            continue

        start = normalize_datetime(start_raw.dt)
        end = normalize_datetime(end_raw.dt) if end_raw else None
        text_value = f"{title} {location} {description}".lower()

        if any(k in text_value for k in ["formula 1", "f1", "grand prix", "gp", "sprint", "race", "qualifying", "practice"]):
            if now <= start <= max_date:
                event = {
                    "title": title,
                    "location": location,
                    "description": description,
                    "start": start,
                    "end": end,
                }
                event["target_type"] = classify_output_target_event(event)
                events.append(event)

    events.sort(key=lambda item: item["start"])
    return events


def classify_output_target_event(event):
    """
    Output target classifier.

    Practice, Qualifying, Sprint Qualifying, Sprint Shootout, and Sprint Qualification
    are input signals only. They are never direct output targets.

    Only two target types are allowed in public output:
    - sprint race
    - final race
    """
    title = str(event.get("title", "")).lower()
    description = str(event.get("description", "")).lower()
    text_value = f"{title} {description}"

    input_only_markers = [
        "practice", "fp1", "fp2", "fp3",
        "qualifying", "qualification", "sprint qualifying",
        "sprint qualification", "sprint shootout", "shootout",
        "sq"
    ]

    if any(k in text_value for k in input_only_markers):
        return "input_only"

    # Sprint race, not sprint qualifying/qualification.
    if "sprint" in text_value:
        return "sprint"

    # Final race. A plain Grand Prix calendar event usually means Race.
    if "race" in text_value or "grand prix" in text_value or " gp" in text_value:
        return "race"

    return "input_only"


def is_output_target_event(event):
    return classify_output_target_event(event) in {"sprint", "race"}


def selected_output_mode():
    """
    workflow_dispatch/manual run: weekend output by default.
    schedule/automatic run: today-only output by default.
    Local runs default to weekend unless OUTPUT_MODE is explicitly set.
    """
    if OUTPUT_MODE in {"weekend", "today", "next"}:
        return OUTPUT_MODE

    if GITHUB_EVENT_NAME == "schedule":
        return "today"

    if GITHUB_EVENT_NAME == "workflow_dispatch":
        return "weekend"

    return "weekend"


def event_weekend_window(anchor_event):
    start = anchor_event["start"]
    # Covers Thu-Mon around normal and sprint weekends, while avoiding pulling the next GP.
    return start - timedelta(days=4), start + timedelta(days=2)


def events_match_same_race(a, b):
    """
    Uses Jolpica matching to group Sprint and Race from the same GP.
    Falls back to title token overlap if one match fails.
    """
    try:
        race_a = find_best_race(a)
        race_b = find_best_race(b)
        if race_a and race_b:
            return str(race_a.get("season")) == str(race_b.get("season")) and str(race_a.get("round")) == str(race_b.get("round"))
    except Exception:
        pass

    tokens_a = set(tokenize(a.get("title", "")))
    tokens_b = set(tokenize(b.get("title", "")))
    return len(tokens_a & tokens_b) >= 1


def select_output_events(calendar):
    """
    Returns Sprint/Race output targets only.

    Manual/weekend mode:
      Return Sprint and Race for the next race weekend in one briefing.
      If there is no Sprint event, return Race only.

    Scheduled/today mode:
      Return only today's Sprint or Race event(s).
      Practice and Qualifying are ignored as output targets.

    Next mode:
      Return the next single Sprint/Race target.
    """
    mode = selected_output_mode()
    events = get_f1_calendar_events(calendar)
    targets = [event for event in events if is_output_target_event(event)]
    now = now_local()

    if not targets:
        return mode, []

    if mode == "today":
        today_targets = [
            event for event in targets
            if event["start"].astimezone(USER_TIMEZONE).date() == now.date()
        ]
        today_targets.sort(key=lambda item: (0 if item["target_type"] == "sprint" else 1, item["start"]))
        return mode, today_targets

    if mode == "next":
        return mode, [targets[0]]

    # Weekend mode.
    next_race = next((event for event in targets if event["target_type"] == "race"), None)
    anchor_event = next_race or targets[0]
    start_window, end_window = event_weekend_window(anchor_event)

    weekend_targets = [
        event for event in targets
        if start_window <= event["start"] <= end_window and events_match_same_race(event, anchor_event)
    ]

    # Always order Sprint before Race in the combined weekend output.
    weekend_targets.sort(key=lambda item: (0 if item["target_type"] == "sprint" else 1, item["start"]))

    # Keep at most one sprint and one race target.
    deduped = []
    seen_types = set()
    for event in weekend_targets:
        target_type = event["target_type"]
        if target_type not in seen_types:
            deduped.append(event)
            seen_types.add(target_type)

    return mode, deduped


def make_report_event(events, mode):
    if not events:
        return None

    first = events[0]
    race = find_best_race(first)
    race_name = race.get("raceName") if race else first.get("title", "F1")

    if mode == "weekend" and len(events) > 1:
        title = f"F1 Weekend Briefing: {race_name} Sprint + Race"
    elif mode == "weekend":
        title = f"F1 Weekend Briefing: {race_name}"
    else:
        title = f"F1 Briefing: {first.get('title')}"

    return {
        "title": title,
        "location": first.get("location", ""),
        "description": " | ".join(event.get("title", "") for event in events),
        "start": min(event["start"] for event in events),
        "end": max((event.get("end") or event["start"]) for event in events),
        "target_type": "weekend" if len(events) > 1 else first.get("target_type"),
    }


def tokenize(text):
    stop = {"formula", "one", "f1", "grand", "prix", "race", "practice", "qualifying", "sprint", "session", "round", "the", "and", "for", "gp"}
    words = re.findall(r"[a-z0-9]+", str(text).lower())
    return [w for w in words if len(w) >= 4 and w not in stop]


def race_text(race):
    circuit = race.get("Circuit", {})
    location = circuit.get("Location", {})
    return " ".join([
        str(race.get("raceName", "")),
        str(circuit.get("circuitName", "")),
        str(circuit.get("circuitId", "")),
        str(location.get("locality", "")),
        str(location.get("country", "")),
    ]).lower()


def find_best_race(event):
    event_year = event["start"].year
    tokens = tokenize(f"{event['title']} {event['location']} {event['description']}")
    best = None
    best_score = -999
    for year in [event_year, event_year - 1]:
        for race in fetch_schedule(year):
            text = race_text(race)
            score = sum(6 for token in tokens if token in text)
            race_dt = parse_race_datetime(race)
            if race_dt:
                delta = abs((race_dt.date() - event["start"].date()).days)
                if year == event_year:
                    score += 8
                if delta <= 1:
                    score += 24
                elif delta <= 7:
                    score += 8
                else:
                    score -= min(delta, 30)
            if score > best_score:
                best = race
                best_score = score
    return best if best_score >= 5 else None


def driver_name(driver):
    return normalize_name(f"{driver.get('givenName', '')} {driver.get('familyName', '')}")


def standings_to_drivers(driver_standings):
    drivers = []
    for row in driver_standings:
        driver = row.get("Driver", {})
        constructors = row.get("Constructors", [])
        team = constructors[0].get("name") if constructors else "Unknown Team"
        drivers.append({
            "driver_id": driver.get("driverId"),
            "name": driver_name(driver),
            "team": team,
            "number": str(driver.get("permanentNumber") or "").strip(),
            "code": str(driver.get("code") or "").strip(),
            "points": safe_float(row.get("points")) or 0.0,
            "position": safe_int(row.get("position")),
            "wins": safe_int(row.get("wins")) or 0,
            "image": None,
            "team_colour": None,
        })
    return drivers


def result_rows_from_race_data(season, round_no, race, data):
    rows = []
    result_races = data.get("results", [])
    if not result_races:
        return rows

    q_positions = {}
    q_races = data.get("qualifying", [])
    if q_races:
        for q in q_races[0].get("QualifyingResults", []):
            driver_id = q.get("Driver", {}).get("driverId")
            q_positions[driver_id] = safe_int(q.get("position"))

    sprint_positions = {}
    sprint_races = data.get("sprint", [])
    if sprint_races:
        for s in sprint_races[0].get("SprintResults", []) or sprint_races[0].get("Results", []):
            driver_id = s.get("Driver", {}).get("driverId")
            sprint_positions[driver_id] = safe_int(s.get("positionOrder") or s.get("position"))

    lap_metrics = driver_lap_metrics_from_data(data)
    pit_metrics = pit_metrics_from_data(data)

    race_id = f"{season}-{round_no}"
    circuit = race.get("Circuit", {})
    circuit_id = circuit.get("circuitId")
    race_dt = parse_race_datetime(race)

    for result in result_races[0].get("Results", []):
        driver = result.get("Driver", {})
        constructor = result.get("Constructor", {})
        driver_id = driver.get("driverId")
        team = constructor.get("name")
        pos = safe_int(result.get("positionOrder") or result.get("position"))
        grid = safe_int(result.get("grid"))
        status = str(result.get("status", ""))

        if not driver_id or not team or not pos:
            continue

        dm = lap_metrics.get(driver_id, {})
        pm = pit_metrics.get(driver_id, {})
        fastest_lap_seconds = parse_lap_time_to_seconds(((result.get("FastestLap") or {}).get("Time") or {}).get("time"))

        rows.append({
            "race_id": race_id,
            "season": season,
            "round": safe_int(round_no),
            "date": race_dt.isoformat() if race_dt else None,
            "race_name": race.get("raceName"),
            "circuit_id": circuit_id,
            "circuit_name": circuit.get("circuitName"),
            "driver_id": driver_id,
            "driver_name": driver_name(driver),
            "constructor": team,
            "grid": grid if grid and grid > 0 else q_positions.get(driver_id),
            "qualifying": q_positions.get(driver_id),
            "sprint_position": sprint_positions.get(driver_id),
            "finish_position": pos,
            "points": safe_float(result.get("points")) or 0.0,
            "status": status,
            "is_finished": 1 if ("Finished" in status or "+" in status) else 0,
            "is_win": 1 if pos == 1 else 0,
            "is_podium": 1 if pos <= 3 else 0,
            "is_top10": 1 if pos <= 10 else 0,
            "best_clean_lap": dm.get("best_lap") or fastest_lap_seconds,
            "avg_best_35pct_lap": dm.get("avg_best_35pct") or fastest_lap_seconds,
            "lap_consistency": dm.get("consistency"),
            "valid_laps": dm.get("valid_laps", 0),
            "pit_stop_count": pm.get("pit_stop_count", 0),
            "avg_pit_duration": pm.get("avg_pit_duration"),
            "min_pit_duration": pm.get("min_pit_duration"),
        })
    return rows


def driver_lap_metrics_from_data(data):
    raw = {}
    for race in data.get("laps", []) or []:
        for lap in race.get("Laps", []):
            for timing in lap.get("Timings", []):
                driver_id = timing.get("driverId")
                sec = parse_lap_time_to_seconds(timing.get("time"))
                if not driver_id or sec is None:
                    continue
                if 45 <= sec <= 180:
                    raw.setdefault(driver_id, []).append(sec)

    out = {}
    for driver_id, times in raw.items():
        if len(times) < 3:
            continue
        fastest = min(times)
        filtered = [x for x in times if x <= fastest + 7.0]
        filtered = sorted(filtered)
        if len(filtered) < 3:
            continue
        n = max(3, int(len(filtered) * 0.35))
        sample = filtered[:n]
        out[driver_id] = {
            "best_lap": fastest,
            "avg_best_35pct": average(sample),
            "consistency": float(np.std(sample)) if len(sample) > 1 else None,
            "valid_laps": len(filtered),
        }
    return out


def pit_metrics_from_data(data):
    raw = {}
    for race in data.get("pitstops", []) or []:
        for stop in race.get("PitStops", []):
            driver_id = stop.get("driverId")
            duration = safe_float(stop.get("duration"))
            if not driver_id or duration is None:
                continue
            if 1.5 <= duration <= 65:
                raw.setdefault(driver_id, []).append(duration)

    out = {}
    for driver_id, durations in raw.items():
        out[driver_id] = {
            "pit_stop_count": len(durations),
            "avg_pit_duration": average(durations),
            "min_pit_duration": min(durations) if durations else None,
        }
    return out


def track_traits_from_race_data(data):
    rows = []
    result_races = data.get("results", [])
    if result_races:
        for row in result_races[0].get("Results", []):
            grid = safe_int(row.get("grid"))
            finish = safe_int(row.get("positionOrder") or row.get("position"))
            status = str(row.get("status", "")).lower()
            rows.append({"grid": grid, "finish": finish, "status": status})

    overtake_moves = []
    dnf = 0
    finished = 0
    for row in rows:
        if row["grid"] and row["grid"] > 0 and row["finish"]:
            overtake_moves.append(abs(row["grid"] - row["finish"]))
        if "finished" in row["status"] or "+" in row["status"]:
            finished += 1
        else:
            dnf += 1

    pits = pit_metrics_from_data(data)
    pit_counts = [item.get("pit_stop_count", 0) for item in pits.values()]
    laps = driver_lap_metrics_from_data(data)
    consistency = [item.get("consistency") for item in laps.values() if item.get("consistency") is not None]

    return {
        "avg_grid_finish_movement": average(overtake_moves),
        "dnf_rate": dnf / max(1, dnf + finished),
        "avg_pit_stops": average(pit_counts),
        "avg_lap_consistency": average(consistency),
        "drivers_with_lap_data": len(laps),
        "drivers_with_pit_data": len(pits),
    }


def collect_race_rows(start_year, end_year):
    rows = []
    races_used = 0
    races_skipped_uncached = 0

    for year in range(start_year, end_year + 1):
        print(f"Collecting full historical rows for {year}")
        schedule = fetch_schedule(year)

        for race in schedule:
            round_no = race.get("round")
            if not round_no:
                continue

            data = fetch_round_data_cached(
                year,
                round_no,
                allow_backfill=True,
                force_fetch=False,
                race=race,
                training_mode=True,
            )

            if not data or not race_has_results(data):
                races_skipped_uncached += 1
                continue

            race_rows = result_rows_from_race_data(year, round_no, race, data)
            rows.extend(race_rows)
            races_used += 1

    df = pd.DataFrame(rows)
    if not df.empty:
        df = df.sort_values(["season", "round", "finish_position"]).reset_index(drop=True)

    print(f"Historical full-data races used: {races_used}; skipped/uncached this run: {races_skipped_uncached}; new backfilled: {BACKFILL_BUDGET.used}")
    return df


def create_ml_features(df):
    if df.empty:
        return df, []

    df = df.copy()
    df = df.sort_values(["season", "round"]).reset_index(drop=True)
    numeric_cols = [
        "grid", "qualifying", "sprint_position", "finish_position", "points",
        "best_clean_lap", "avg_best_35pct_lap", "lap_consistency",
        "valid_laps", "pit_stop_count", "avg_pit_duration", "min_pit_duration"
    ]
    for col in numeric_cols:
        df[col] = pd.to_numeric(df.get(col), errors="coerce")

    df["grid"] = df["grid"].fillna(20)
    df["qualifying"] = df["qualifying"].fillna(df["grid"])
    df["sprint_position"] = df["sprint_position"].fillna(20)
    df["points"] = df["points"].fillna(0)
    df["pit_stop_count"] = df["pit_stop_count"].fillna(0)
    df["valid_laps"] = df["valid_laps"].fillna(0)

    feature_rows = []
    grouped_driver = {k: g.sort_values(["season", "round"]) for k, g in df.groupby("driver_id")}
    grouped_team = {k: g.sort_values(["season", "round"]) for k, g in df.groupby("constructor")}
    grouped_circuit_driver = {k: g.sort_values(["season", "round"]) for k, g in df.groupby(["circuit_id", "driver_id"])}
    grouped_circuit_team = {k: g.sort_values(["season", "round"]) for k, g in df.groupby(["circuit_id", "constructor"])}
    grouped_circuit = {k: g.sort_values(["season", "round"]) for k, g in df.groupby("circuit_id")}

    for _, race in df.iterrows():
        season = race["season"]
        round_no = race["round"]

        def before(frame):
            if frame is None or len(frame) == 0:
                return pd.DataFrame()
            return frame[(frame["season"] < season) | ((frame["season"] == season) & (frame["round"] < round_no))]

        d_hist = before(grouped_driver.get(race["driver_id"]))
        t_hist = before(grouped_team.get(race["constructor"]))
        cd_hist = before(grouped_circuit_driver.get((race["circuit_id"], race["driver_id"])))
        ct_hist = before(grouped_circuit_team.get((race["circuit_id"], race["constructor"])))
        c_hist = before(grouped_circuit.get(race["circuit_id"]))
        field_hist = before(df)

        if len(d_hist) < 3 or len(t_hist) < 3:
            continue

        recent3 = d_hist.tail(3)
        recent5 = d_hist.tail(5)
        team_recent10 = t_hist.tail(10)
        field_recent = field_hist.tail(200)

        def mean_or(frame, col, fallback):
            if len(frame) and col in frame:
                val = frame[col].mean()
                if pd.notna(val):
                    return float(val)
            return fallback

        circuit_movement = mean_or(c_hist, "grid", 10) - mean_or(c_hist, "finish_position", 10)
        circuit_abs_movement = average([
            abs((safe_float(row.get("grid")) or 10) - (safe_float(row.get("finish_position")) or 10))
            for _, row in c_hist.iterrows()
        ]) if len(c_hist) else 3
        track_position_sensitivity = 100.0 / max(1.0, 1.0 + abs(circuit_abs_movement or 3))
        driver_recent_grid_gain = mean_or(recent5, "grid", 12) - mean_or(recent5, "finish_position", 12)
        team_recent_grid_gain = mean_or(team_recent10, "grid", 12) - mean_or(team_recent10, "finish_position", 12)
        driver_finish_consistency = safe_std(recent5["finish_position"]) if len(recent5) else None
        team_finish_consistency = safe_std(team_recent10["finish_position"]) if len(team_recent10) else None
        driver_recent_pace = mean_or(recent5, "avg_best_35pct_lap", 100)
        team_recent_pace = mean_or(team_recent10, "avg_best_35pct_lap", 100)
        field_recent_pace = mean_or(field_recent, "avg_best_35pct_lap", team_recent_pace)
        driver_recent_pit = mean_or(recent5, "avg_pit_duration", 3.5)
        team_recent_pit = mean_or(team_recent10, "avg_pit_duration", 3.5)
        field_recent_pit = mean_or(field_recent, "avg_pit_duration", team_recent_pit)
        driver_min_pit = mean_or(recent5, "min_pit_duration", driver_recent_pit)
        team_min_pit = mean_or(team_recent10, "min_pit_duration", team_recent_pit)
        target_lap_pace = safe_float(race.get("avg_best_35pct_lap")) or safe_float(race.get("best_clean_lap"))

        features = {
            "race_id": race["race_id"],
            "season": season,
            "round": round_no,
            "race_name": race["race_name"],
            "circuit_id": race["circuit_id"],
            "driver_id": race["driver_id"],
            "driver_name": race["driver_name"],
            "constructor": race["constructor"],
            "finish_position": race["finish_position"],
            "is_win": race["is_win"],
            "is_podium": race["is_podium"],
            "is_top10": race["is_top10"],
            "target_lap_pace": target_lap_pace,

            "grid_position": race["grid"],
            "qualifying_position": race["qualifying"],
            "sprint_position": race["sprint_position"],

            "driver_avg_finish": d_hist["finish_position"].mean(),
            "driver_median_finish": d_hist["finish_position"].median(),
            "driver_avg_points": d_hist["points"].mean(),
            "driver_win_rate": d_hist["is_win"].mean(),
            "driver_podium_rate": d_hist["is_podium"].mean(),
            "driver_top10_rate": d_hist["is_top10"].mean(),
            "driver_finish_rate": d_hist["is_finished"].mean(),
            "driver_recent3_finish": recent3["finish_position"].mean(),
            "driver_recent5_points": recent5["points"].mean(),
            "driver_recent5_podium_rate": recent5["is_podium"].mean(),
            "driver_recent_grid_gain": driver_recent_grid_gain,
            "driver_finish_consistency": driver_finish_consistency or 4,
            "driver_finish_momentum": mean_or(d_hist, "finish_position", 12) - mean_or(recent3, "finish_position", 12),
            "driver_points_momentum": mean_or(recent5, "points", 0) - mean_or(d_hist, "points", 0),
            "driver_qualifying_strength_recent": mean_or(recent5, "qualifying", 12),
            "driver_qualifying_delta": mean_or(d_hist.tail(8), "qualifying", 12) - mean_or(d_hist.tail(8), "finish_position", 12),

            "team_avg_finish": t_hist["finish_position"].mean(),
            "team_avg_points": t_hist["points"].mean(),
            "team_win_rate": t_hist["is_win"].mean(),
            "team_podium_rate": t_hist["is_podium"].mean(),
            "team_top10_rate": t_hist["is_top10"].mean(),
            "team_finish_rate": t_hist["is_finished"].mean(),
            "team_recent_points": team_recent10["points"].mean(),
            "team_recent_grid_gain": team_recent_grid_gain,
            "team_finish_consistency": team_finish_consistency or 4,
            "team_finish_momentum": mean_or(t_hist, "finish_position", 12) - mean_or(team_recent10, "finish_position", 12),
            "team_points_momentum": mean_or(team_recent10, "points", 0) - mean_or(t_hist, "points", 0),
            "team_qualifying_strength_recent": mean_or(team_recent10, "qualifying", 12),
            "team_reliability_recent": mean_or(team_recent10, "is_finished", 0.85),

            "driver_circuit_avg_finish": mean_or(cd_hist, "finish_position", d_hist["finish_position"].mean()),
            "driver_circuit_podium_rate": mean_or(cd_hist, "is_podium", d_hist["is_podium"].mean()),
            "driver_circuit_grid_gain": mean_or(cd_hist, "grid", 12) - mean_or(cd_hist, "finish_position", 12),
            "team_circuit_avg_finish": mean_or(ct_hist, "finish_position", t_hist["finish_position"].mean()),
            "team_circuit_podium_rate": mean_or(ct_hist, "is_podium", t_hist["is_podium"].mean()),
            "team_circuit_grid_gain": mean_or(ct_hist, "grid", 12) - mean_or(ct_hist, "finish_position", 12),

            "career_starts": len(d_hist),
            "team_starts": len(t_hist),
            "circuit_experience": len(cd_hist),
            "driver_experience_log": float(np.log1p(len(d_hist))),
            "team_experience_log": float(np.log1p(len(t_hist))),

            "driver_lap_pace": driver_recent_pace,
            "driver_lap_consistency": mean_or(recent5, "lap_consistency", 3),
            "driver_valid_laps": mean_or(recent5, "valid_laps", 0),
            "driver_pace_momentum": mean_or(d_hist, "avg_best_35pct_lap", driver_recent_pace) - driver_recent_pace,
            "driver_pace_vs_team_recent": driver_recent_pace - team_recent_pace,
            "driver_pit_duration": driver_recent_pit,
            "driver_min_pit_duration": driver_min_pit,
            "driver_pit_vs_team_recent": driver_recent_pit - team_recent_pit,
            "driver_pit_stop_count": mean_or(recent5, "pit_stop_count", 1),
            "team_lap_pace": team_recent_pace,
            "team_lap_consistency": mean_or(team_recent10, "lap_consistency", 3),
            "team_pace_momentum": mean_or(t_hist, "avg_best_35pct_lap", team_recent_pace) - team_recent_pace,
            "team_pace_vs_field_recent": team_recent_pace - field_recent_pace,
            "team_pit_duration": team_recent_pit,
            "team_min_pit_duration": team_min_pit,
            "team_pit_vs_field_recent": team_recent_pit - field_recent_pit,
            "team_pit_stop_count": mean_or(team_recent10, "pit_stop_count", 1),
            "track_avg_pit_stops": mean_or(c_hist, "pit_stop_count", 1),
            "track_avg_lap_consistency": mean_or(c_hist, "lap_consistency", 3),
            "track_lap_pace_baseline": mean_or(c_hist, "avg_best_35pct_lap", field_recent_pace),
            "track_pit_duration_baseline": mean_or(c_hist, "avg_pit_duration", field_recent_pit),
            "track_dnf_rate": 1 - mean_or(c_hist, "is_finished", 0.85),
            "track_overtake_proxy": circuit_movement,
            "track_abs_overtake_proxy": circuit_abs_movement or 3,
            "track_position_sensitivity": track_position_sensitivity,
            "regulation_era_factor": regulation_era_factor(season),
            "season_progress": (safe_float(round_no) or 1) / 24.0,
        }
        feature_rows.append(features)

    feature_df = pd.DataFrame(feature_rows)

    feature_columns = [
        "grid_position", "qualifying_position", "sprint_position",
        "driver_avg_finish", "driver_median_finish", "driver_avg_points",
        "driver_win_rate", "driver_podium_rate", "driver_top10_rate", "driver_finish_rate",
        "driver_recent3_finish", "driver_recent5_points", "driver_recent5_podium_rate",
        "driver_recent_grid_gain", "driver_finish_consistency", "driver_finish_momentum",
        "driver_points_momentum", "driver_qualifying_strength_recent", "driver_qualifying_delta",
        "team_avg_finish", "team_avg_points", "team_win_rate", "team_podium_rate",
        "team_top10_rate", "team_finish_rate", "team_recent_points",
        "team_recent_grid_gain", "team_finish_consistency", "team_finish_momentum",
        "team_points_momentum", "team_qualifying_strength_recent", "team_reliability_recent",
        "driver_circuit_avg_finish", "driver_circuit_podium_rate", "driver_circuit_grid_gain",
        "team_circuit_avg_finish", "team_circuit_podium_rate", "team_circuit_grid_gain",
        "career_starts", "team_starts", "circuit_experience", "driver_experience_log", "team_experience_log",
        "driver_lap_pace", "driver_lap_consistency", "driver_valid_laps", "driver_pace_momentum",
        "driver_pace_vs_team_recent", "driver_pit_duration", "driver_min_pit_duration",
        "driver_pit_vs_team_recent", "driver_pit_stop_count",
        "team_lap_pace", "team_lap_consistency", "team_pace_momentum", "team_pace_vs_field_recent",
        "team_pit_duration", "team_min_pit_duration", "team_pit_vs_field_recent", "team_pit_stop_count",
        "track_avg_pit_stops", "track_avg_lap_consistency", "track_lap_pace_baseline", "track_pit_duration_baseline",
        "track_dnf_rate", "track_overtake_proxy", "track_abs_overtake_proxy",
        "track_position_sensitivity", "regulation_era_factor", "season_progress",
    ]

    return feature_df, feature_columns


def latest_completed_race_id(current_year=None):
    year = current_year or now_local().year
    completed = []
    for race in fetch_schedule(year):
        race_dt = parse_race_datetime(race)
        if race_dt and now_local() >= race_dt + timedelta(hours=FINAL_RESULTS_DELAY_HOURS):
            data = fetch_round_data_cached(
                year,
                race.get("round"),
                allow_backfill=False,
                race=race,
                training_mode=True,
            )
            if race_has_results(data):
                completed.append((race_dt, f"{year}-{race.get('round')}"))
    if not completed and year > 1950:
        return latest_completed_race_id(year - 1)
    completed.sort(key=lambda x: x[0])
    return completed[-1][1] if completed else None


def race_status_summary(race, race_dt=None):
    race_dt = race_dt or parse_race_datetime(race)
    cutoff = final_results_cutoff(race)
    return {
        "race_id": f"{race.get('season')}-{race.get('round')}",
        "season": safe_int(race.get("season")),
        "round": safe_int(race.get("round")),
        "race_name": race.get("raceName"),
        "circuit": ((race.get("Circuit") or {}).get("circuitName")),
        "scheduled_at": race_dt.isoformat() if race_dt else None,
        "final_results_cutoff": cutoff.isoformat() if cutoff else None,
    }


def latest_result_readiness(refresh=False):
    global _RESULT_READINESS_CACHE
    if _RESULT_READINESS_CACHE is not None and not refresh:
        return _RESULT_READINESS_CACHE

    year = now_local().year
    now = now_local()
    completed = []
    waiting_delay = []
    waiting_api = []
    next_race = None

    for race in fetch_schedule(year):
        race_dt = parse_race_datetime(race)
        if not race_dt:
            continue

        summary = race_status_summary(race, race_dt)
        if race_dt > now:
            if next_race is None or race_dt < parse_race_datetime(next_race):
                next_race = race
            continue

        cutoff = final_results_cutoff(race)
        if cutoff and now < cutoff:
            summary["status"] = "waiting_final_results_delay"
            waiting_delay.append((race_dt, summary))
            continue

        data = fetch_round_data_cached(
            year,
            race.get("round"),
            allow_backfill=False,
            race=race,
            training_mode=True,
        )
        if race_has_results(data):
            summary["status"] = "api_results_available"
            completed.append((race_dt, summary))
        else:
            summary["status"] = "past_cutoff_waiting_for_api_results"
            waiting_api.append((race_dt, summary))

    completed.sort(key=lambda item: item[0])
    waiting_delay.sort(key=lambda item: item[0])
    waiting_api.sort(key=lambda item: item[0])

    previous_latest = None
    if not completed and year > 1950:
        previous_latest = latest_completed_race_id(year - 1)

    latest_completed = completed[-1][1] if completed else None
    result = {
        "checked_at": now.isoformat(),
        "current_year": year,
        "final_results_delay_hours": FINAL_RESULTS_DELAY_HOURS,
        "latest_completed_race_id": latest_completed.get("race_id") if latest_completed else previous_latest,
        "latest_completed_race": latest_completed,
        "waiting_for_delay": waiting_delay[-1][1] if waiting_delay else None,
        "waiting_for_api_results": waiting_api[-1][1] if waiting_api else None,
        "next_race": race_status_summary(next_race) if next_race else None,
    }
    if result["waiting_for_api_results"]:
        result["status"] = "past_gp_waiting_for_api_results"
    elif result["waiting_for_delay"]:
        result["status"] = "recent_gp_waiting_final_results_delay"
    elif result["latest_completed_race_id"]:
        result["status"] = "latest_results_available"
    else:
        result["status"] = "no_completed_results_found"

    _RESULT_READINESS_CACHE = result
    return result


def read_model_meta():
    if not MODEL_META_PATH.exists():
        return {}
    try:
        return json.loads(MODEL_META_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}


def model_retrain_status(force=False):
    meta = read_model_meta()
    readiness = latest_result_readiness()
    reasons = []

    if force:
        reasons.append("manual_force_retrain_requested")
    if not MODEL_BUNDLE_PATH.exists():
        reasons.append("missing_model_bundle")
    if not MODEL_META_PATH.exists() or not meta:
        reasons.append("missing_or_unreadable_model_meta")
    if meta and meta.get("model_schema_version") != MODEL_SCHEMA_VERSION:
        reasons.append("model_schema_changed")

    latest_id = readiness.get("latest_completed_race_id")
    meta_latest = meta.get("latest_completed_race_id")
    if latest_id and meta_latest and latest_id != meta_latest:
        reasons.append("new_completed_race_results_available")
    elif latest_id and not meta_latest:
        reasons.append("model_missing_latest_completed_race_marker")

    if not reasons and readiness.get("status") in {"recent_gp_waiting_final_results_delay", "past_gp_waiting_for_api_results"}:
        action = "wait_for_final_results"
    elif reasons:
        action = "retrain_now"
    else:
        action = "model_current"

    return {
        "action": action,
        "should_retrain": bool(reasons),
        "reasons": reasons,
        "model_latest_completed_race_id": meta_latest,
        "api_latest_completed_race_id": latest_id,
        "readiness": readiness,
        "meta": meta,
    }


def should_retrain(force=False):
    return model_retrain_status(force).get("should_retrain", True)


def ranking_validation_metrics(valid_df, predicted_finish):
    if valid_df.empty or len(predicted_finish) != len(valid_df):
        return {}

    eval_df = valid_df[["race_id", "driver_id", "finish_position"]].copy()
    eval_df["predicted_finish_position"] = predicted_finish
    metrics = {
        "winner_hit": [],
        "top3_recall": [],
        "top5_recall": [],
        "top10_recall": [],
        "exact_position_accuracy": [],
        "mean_position_error": [],
    }

    for _, group in eval_df.groupby("race_id"):
        if len(group) < 10:
            continue
        actual_order = group.sort_values("finish_position")
        predicted_order = group.sort_values("predicted_finish_position")

        actual_winner = str(actual_order.iloc[0]["driver_id"])
        predicted_winner = str(predicted_order.iloc[0]["driver_id"])
        metrics["winner_hit"].append(1.0 if actual_winner == predicted_winner else 0.0)

        for k, key in [(3, "top3_recall"), (5, "top5_recall"), (10, "top10_recall")]:
            actual = set(actual_order.head(k)["driver_id"])
            predicted = set(predicted_order.head(k)["driver_id"])
            metrics[key].append(len(actual & predicted) / max(1, len(actual)))

        merged = actual_order[["driver_id", "finish_position"]].merge(
            predicted_order[["driver_id", "predicted_finish_position"]],
            on="driver_id",
            how="inner",
        )
        if not merged.empty:
            rounded = merged["predicted_finish_position"].round().clip(1, 24)
            metrics["exact_position_accuracy"].append(float((rounded == merged["finish_position"]).mean()))
            metrics["mean_position_error"].append(float((rounded - merged["finish_position"]).abs().mean()))

    return {
        key: round(average(values), 4)
        for key, values in metrics.items()
        if values
    }


def train_ml_model(force=False):
    retrain_decision = model_retrain_status(force)
    if not retrain_decision.get("should_retrain"):
        print("ML model is current. Checking saved bundle.")
        existing_bundle = load_ml_bundle()
        if existing_bundle:
            existing_bundle["training_action"] = "loaded_current_model"
            existing_bundle["training_decision"] = retrain_decision
            print("Saved ML bundle loaded successfully. Skipping retrain.")
            return existing_bundle
        print("Saved ML bundle could not be loaded. Retraining with current dependency versions.")
        retrain_decision["reasons"] = retrain_decision.get("reasons", []) + ["saved_bundle_load_failed"]
        retrain_decision["should_retrain"] = True
        retrain_decision["action"] = "retrain_now"

    print("Training full-data ML model from cached/backfilled historical data.")
    print("Retrain reasons: " + ", ".join(retrain_decision.get("reasons") or ["routine_retrain"]))
    current_year = now_local().year
    raw_df = collect_race_rows(ML_START_YEAR, current_year)

    raw_path = DATA_CACHE_DIR / "ml_full_race_results_raw.csv"
    feature_path = DATA_CACHE_DIR / "ml_full_race_features.csv"
    raw_df.to_csv(raw_path, index=False)

    feature_df, feature_columns = create_ml_features(raw_df)
    feature_df.to_csv(feature_path, index=False)

    if len(feature_df) < 80:
        print(f"Not enough full-data feature rows yet: {len(feature_df)}. More backfill runs needed.")
        return load_ml_bundle()

    seasons = sorted(feature_df["season"].dropna().unique())
    validation_year = seasons[-1]
    train_df = feature_df[feature_df["season"] < validation_year].copy()
    valid_df = feature_df[feature_df["season"] == validation_year].copy()

    if len(train_df) < 60 or len(valid_df) < 20:
        train_df = feature_df.sample(frac=0.8, random_state=42)
        valid_df = feature_df.drop(train_df.index)

    X_train = train_df[feature_columns].replace([np.inf, -np.inf], np.nan).fillna(0)
    X_valid = valid_df[feature_columns].replace([np.inf, -np.inf], np.nan).fillna(0)

    targets = {"win": "is_win", "podium": "is_podium", "top10": "is_top10"}
    models = {}
    metrics = {}
    validation_probabilities = {}

    for name, target_col in targets.items():
        y_train = train_df[target_col].astype(int)
        y_valid = valid_df[target_col].astype(int)

        rf = RandomForestClassifier(
            n_estimators=280,
            max_depth=11,
            min_samples_leaf=3,
            random_state=42,
            n_jobs=-1,
            class_weight="balanced_subsample",
        )
        et = ExtraTreesClassifier(
            n_estimators=260,
            max_depth=13,
            min_samples_leaf=2,
            random_state=84,
            n_jobs=-1,
            class_weight="balanced",
        )
        hgb = HistGradientBoostingClassifier(
            max_iter=180,
            learning_rate=0.055,
            max_leaf_nodes=31,
            l2_regularization=0.03,
            random_state=42,
        )

        rf.fit(X_train, y_train)
        et.fit(X_train, y_train)
        hgb.fit(X_train, y_train)

        rf_prob = rf.predict_proba(X_valid)[:, 1]
        et_prob = et.predict_proba(X_valid)[:, 1]
        hgb_prob = hgb.predict_proba(X_valid)[:, 1]
        prob = 0.44 * rf_prob + 0.34 * hgb_prob + 0.22 * et_prob

        try:
            auc = roc_auc_score(y_valid, prob)
        except Exception:
            auc = None
        try:
            brier = brier_score_loss(y_valid, prob)
        except Exception:
            brier = None

        models[name] = {"rf": rf, "hgb": hgb, "et": et}
        metrics[name] = {"auc": auc, "brier": brier, "validation_rows": len(valid_df)}
        validation_probabilities[name] = prob

    y_train_finish = train_df["finish_position"].astype(float)
    y_valid_finish = valid_df["finish_position"].astype(float)
    rf_finish = RandomForestRegressor(
        n_estimators=340,
        max_depth=12,
        min_samples_leaf=2,
        random_state=42,
        n_jobs=-1,
    )
    et_finish = ExtraTreesRegressor(
        n_estimators=320,
        max_depth=14,
        min_samples_leaf=2,
        random_state=84,
        n_jobs=-1,
    )
    hgb_finish = HistGradientBoostingRegressor(
        max_iter=230,
        learning_rate=0.045,
        max_leaf_nodes=31,
        l2_regularization=0.04,
        random_state=42,
    )
    rf_finish.fit(X_train, y_train_finish)
    et_finish.fit(X_train, y_train_finish)
    hgb_finish.fit(X_train, y_train_finish)
    finish_pred = 0.40 * rf_finish.predict(X_valid) + 0.40 * hgb_finish.predict(X_valid) + 0.20 * et_finish.predict(X_valid)
    finish_pred = np.clip(finish_pred, 1, 24)

    try:
        mae = mean_absolute_error(y_valid_finish, finish_pred)
    except Exception:
        mae = None
    try:
        rmse = float(np.sqrt(np.mean((np.array(y_valid_finish) - finish_pred) ** 2)))
    except Exception:
        rmse = None

    metrics["finish_position"] = {
        "mae": mae,
        "rmse": rmse,
        "validation_rows": len(valid_df),
        "ranking": ranking_validation_metrics(valid_df, finish_pred),
    }
    if "win" in validation_probabilities:
        win_prob_finish_proxy = 1 + (1 - validation_probabilities["win"]) * 19
        metrics["win_probability_ranking"] = ranking_validation_metrics(valid_df, win_prob_finish_proxy)

    lap_pace_model = None
    lap_train_df = train_df[pd.to_numeric(train_df.get("target_lap_pace"), errors="coerce").notna()].copy()
    lap_valid_df = valid_df[pd.to_numeric(valid_df.get("target_lap_pace"), errors="coerce").notna()].copy()
    if len(lap_train_df) >= 80 and len(lap_valid_df) >= 20:
        X_lap_train = lap_train_df[feature_columns].replace([np.inf, -np.inf], np.nan).fillna(0)
        X_lap_valid = lap_valid_df[feature_columns].replace([np.inf, -np.inf], np.nan).fillna(0)
        y_lap_train = pd.to_numeric(lap_train_df["target_lap_pace"], errors="coerce").astype(float)
        y_lap_valid = pd.to_numeric(lap_valid_df["target_lap_pace"], errors="coerce").astype(float)
        lap_pace_model = make_pipeline(
            StandardScaler(),
            MLPRegressor(
                hidden_layer_sizes=(96, 48, 24),
                activation="relu",
                solver="adam",
                alpha=0.004,
                learning_rate_init=0.001,
                max_iter=650,
                early_stopping=True,
                validation_fraction=0.18,
                n_iter_no_change=20,
                random_state=42,
            ),
        )
        lap_pace_model.fit(X_lap_train, y_lap_train)
        lap_pred = np.clip(lap_pace_model.predict(X_lap_valid), 45, 180)
        metrics["neural_lap_time_forecast"] = {
            "mae_seconds": float(mean_absolute_error(y_lap_valid, lap_pred)),
            "rmse_seconds": float(np.sqrt(np.mean((np.array(y_lap_valid) - lap_pred) ** 2))),
            "validation_rows": len(lap_valid_df),
        }
    else:
        metrics["neural_lap_time_forecast"] = {
            "status": "insufficient_lap_time_rows",
            "train_rows": len(lap_train_df),
            "validation_rows": len(lap_valid_df),
        }

    latest_id = latest_completed_race_id()
    bundle = {
        "models": models,
        "finish_model": {"rf": rf_finish, "hgb": hgb_finish, "et": et_finish},
        "lap_pace_model": lap_pace_model,
        "feature_columns": feature_columns,
        "trained_at": now_local().isoformat(),
        "ml_start_year": ML_START_YEAR,
        "latest_completed_race_id": latest_id,
        "metrics": metrics,
        "model_schema_version": MODEL_SCHEMA_VERSION,
        "training_action": "retrained_model",
        "training_decision": retrain_decision,
    }

    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    joblib.dump(bundle, MODEL_BUNDLE_PATH, compress=("xz", 3))

    meta = {
        "trained_at": bundle["trained_at"],
        "model_schema_version": MODEL_SCHEMA_VERSION,
        "ml_start_year": ML_START_YEAR,
        "rows_raw": len(raw_df),
        "rows_features": len(feature_df),
        "latest_completed_race_id": latest_id,
        "metrics": metrics,
        "feature_columns": feature_columns,
        "backfill_used_this_run": BACKFILL_BUDGET.used,
        "backfilled_races_this_run": BACKFILL_BUDGET.fetched,
        "training_action": "retrained_model",
        "training_reasons": retrain_decision.get("reasons", []),
        "result_readiness": retrain_decision.get("readiness", {}),
    }
    MODEL_META_PATH.write_text(json.dumps(meta, indent=2), encoding="utf-8")

    print(f"ML model saved: {MODEL_BUNDLE_PATH}")
    return bundle


def load_ml_bundle():
    if not MODEL_BUNDLE_PATH.exists():
        return None
    try:
        return joblib.load(MODEL_BUNDLE_PATH)
    except Exception as error:
        print(f"Could not load ML bundle: {error}")
        return None


def historical_feature_context(start_year, target_season):
    df = collect_race_rows(start_year, target_season)
    if df.empty:
        return df
    return df.sort_values(["season", "round"]).reset_index(drop=True)


def build_prediction_feature_rows(drivers, race, current_round_data, historical_df, feature_columns):
    season = safe_int(race.get("season")) or now_local().year
    round_no = safe_int(race.get("round")) or 0
    circuit_id = race.get("Circuit", {}).get("circuitId")

    q_positions = {}
    if current_round_data.get("qualifying"):
        for q in current_round_data["qualifying"][0].get("QualifyingResults", []):
            q_positions[q.get("Driver", {}).get("driverId")] = safe_int(q.get("position"))

    sprint_positions = {}
    if current_round_data.get("sprint"):
        for s in current_round_data["sprint"][0].get("SprintResults", []) or current_round_data["sprint"][0].get("Results", []):
            sprint_positions[s.get("Driver", {}).get("driverId")] = safe_int(s.get("positionOrder") or s.get("position"))

    current_laps = driver_lap_metrics_from_data(current_round_data)
    current_pits = pit_metrics_from_data(current_round_data)

    rows = []
    for driver in drivers:
        driver_id = driver["driver_id"]
        team = driver["team"]
        hist = historical_df[(historical_df["season"] < season) | ((historical_df["season"] == season) & (historical_df["round"] < round_no))].copy() if not historical_df.empty else pd.DataFrame()

        d_hist = hist[hist["driver_id"] == driver_id] if not hist.empty else pd.DataFrame()
        t_hist = hist[hist["constructor"] == team] if not hist.empty else pd.DataFrame()
        cd_hist = hist[(hist["circuit_id"] == circuit_id) & (hist["driver_id"] == driver_id)] if not hist.empty else pd.DataFrame()
        ct_hist = hist[(hist["circuit_id"] == circuit_id) & (hist["constructor"] == team)] if not hist.empty else pd.DataFrame()
        c_hist = hist[hist["circuit_id"] == circuit_id] if not hist.empty else pd.DataFrame()

        def mean_or(frame, col, fallback):
            if len(frame) and col in frame:
                val = pd.to_numeric(frame[col], errors="coerce").mean()
                if pd.notna(val):
                    return float(val)
            return fallback

        recent5 = d_hist.tail(5)
        team_recent10 = t_hist.tail(10)
        field_recent = hist.tail(200) if not hist.empty else pd.DataFrame()
        circuit_abs_movement = average([
            abs((safe_float(row.get("grid")) or 10) - (safe_float(row.get("finish_position")) or 10))
            for _, row in c_hist.iterrows()
        ]) if len(c_hist) else 3
        track_position_sensitivity = 100.0 / max(1.0, 1.0 + abs(circuit_abs_movement or 3))
        driver_recent_grid_gain = mean_or(recent5, "grid", 12) - mean_or(recent5, "finish_position", 12)
        team_recent_grid_gain = mean_or(team_recent10, "grid", 12) - mean_or(team_recent10, "finish_position", 12)
        driver_finish_consistency = safe_std(pd.to_numeric(recent5["finish_position"], errors="coerce")) if len(recent5) else None
        team_finish_consistency = safe_std(pd.to_numeric(team_recent10["finish_position"], errors="coerce")) if len(team_recent10) else None
        driver_recent_pace = mean_or(recent5, "avg_best_35pct_lap", 100)
        team_recent_pace = mean_or(team_recent10, "avg_best_35pct_lap", 100)
        field_recent_pace = mean_or(field_recent, "avg_best_35pct_lap", team_recent_pace)
        driver_recent_pit = mean_or(recent5, "avg_pit_duration", 3.5)
        team_recent_pit = mean_or(team_recent10, "avg_pit_duration", 3.5)
        field_recent_pit = mean_or(field_recent, "avg_pit_duration", team_recent_pit)
        driver_min_pit = mean_or(recent5, "min_pit_duration", driver_recent_pit)
        team_min_pit = mean_or(team_recent10, "min_pit_duration", team_recent_pit)

        standing_proxy = min(20, max(1, safe_int(driver.get("position")) or 12))
        lap_now = current_laps.get(driver_id, {})
        pit_now = current_pits.get(driver_id, {})
        current_lap_pace = lap_now.get("avg_best_35pct") or driver_recent_pace
        current_lap_consistency = lap_now.get("consistency") or mean_or(recent5, "lap_consistency", 3)
        current_pit_duration = pit_now.get("avg_pit_duration") or driver_recent_pit

        row = {
            "driver_id": driver_id,
            "driver_name": driver["name"],
            "constructor": team,
            "grid_position": q_positions.get(driver_id) or standing_proxy,
            "qualifying_position": q_positions.get(driver_id) or standing_proxy,
            "sprint_position": sprint_positions.get(driver_id) or 20,

            "driver_avg_finish": mean_or(d_hist, "finish_position", 12),
            "driver_median_finish": float(pd.to_numeric(d_hist["finish_position"], errors="coerce").median()) if len(d_hist) else 12,
            "driver_avg_points": mean_or(d_hist, "points", 0),
            "driver_win_rate": mean_or(d_hist, "is_win", 0),
            "driver_podium_rate": mean_or(d_hist, "is_podium", 0),
            "driver_top10_rate": mean_or(d_hist, "is_top10", 0),
            "driver_finish_rate": mean_or(d_hist, "is_finished", 0.85),
            "driver_recent3_finish": mean_or(d_hist.tail(3), "finish_position", mean_or(d_hist, "finish_position", 12)),
            "driver_recent5_points": mean_or(d_hist.tail(5), "points", mean_or(d_hist, "points", 0)),
            "driver_recent5_podium_rate": mean_or(d_hist.tail(5), "is_podium", mean_or(d_hist, "is_podium", 0)),
            "driver_recent_grid_gain": driver_recent_grid_gain,
            "driver_finish_consistency": driver_finish_consistency or 4,
            "driver_finish_momentum": mean_or(d_hist, "finish_position", 12) - mean_or(d_hist.tail(3), "finish_position", 12),
            "driver_points_momentum": mean_or(d_hist.tail(5), "points", 0) - mean_or(d_hist, "points", 0),
            "driver_qualifying_strength_recent": mean_or(recent5, "qualifying", 12),
            "driver_qualifying_delta": mean_or(d_hist.tail(8), "qualifying", 12) - mean_or(d_hist.tail(8), "finish_position", 12),

            "team_avg_finish": mean_or(t_hist, "finish_position", 12),
            "team_avg_points": mean_or(t_hist, "points", 0),
            "team_win_rate": mean_or(t_hist, "is_win", 0),
            "team_podium_rate": mean_or(t_hist, "is_podium", 0),
            "team_top10_rate": mean_or(t_hist, "is_top10", 0),
            "team_finish_rate": mean_or(t_hist, "is_finished", 0.85),
            "team_recent_points": mean_or(t_hist.tail(10), "points", mean_or(t_hist, "points", 0)),
            "team_recent_grid_gain": team_recent_grid_gain,
            "team_finish_consistency": team_finish_consistency or 4,
            "team_finish_momentum": mean_or(t_hist, "finish_position", 12) - mean_or(team_recent10, "finish_position", 12),
            "team_points_momentum": mean_or(team_recent10, "points", 0) - mean_or(t_hist, "points", 0),
            "team_qualifying_strength_recent": mean_or(team_recent10, "qualifying", 12),
            "team_reliability_recent": mean_or(team_recent10, "is_finished", 0.85),

            "driver_circuit_avg_finish": mean_or(cd_hist, "finish_position", mean_or(d_hist, "finish_position", 12)),
            "driver_circuit_podium_rate": mean_or(cd_hist, "is_podium", mean_or(d_hist, "is_podium", 0)),
            "driver_circuit_grid_gain": mean_or(cd_hist, "grid", 12) - mean_or(cd_hist, "finish_position", 12),
            "team_circuit_avg_finish": mean_or(ct_hist, "finish_position", mean_or(t_hist, "finish_position", 12)),
            "team_circuit_podium_rate": mean_or(ct_hist, "is_podium", mean_or(t_hist, "is_podium", 0)),
            "team_circuit_grid_gain": mean_or(ct_hist, "grid", 12) - mean_or(ct_hist, "finish_position", 12),
            "career_starts": len(d_hist),
            "team_starts": len(t_hist),
            "circuit_experience": len(cd_hist),
            "driver_experience_log": float(np.log1p(len(d_hist))),
            "team_experience_log": float(np.log1p(len(t_hist))),

            "driver_lap_pace": current_lap_pace,
            "driver_lap_consistency": current_lap_consistency,
            "driver_valid_laps": lap_now.get("valid_laps") or mean_or(recent5, "valid_laps", 0),
            "driver_pace_momentum": mean_or(d_hist, "avg_best_35pct_lap", driver_recent_pace) - current_lap_pace,
            "driver_pace_vs_team_recent": current_lap_pace - team_recent_pace,
            "driver_pit_duration": current_pit_duration,
            "driver_min_pit_duration": pit_now.get("min_pit_duration") or driver_min_pit,
            "driver_pit_vs_team_recent": current_pit_duration - team_recent_pit,
            "driver_pit_stop_count": pit_now.get("pit_stop_count") or mean_or(recent5, "pit_stop_count", 1),
            "team_lap_pace": team_recent_pace,
            "team_lap_consistency": mean_or(team_recent10, "lap_consistency", 3),
            "team_pace_momentum": mean_or(t_hist, "avg_best_35pct_lap", team_recent_pace) - team_recent_pace,
            "team_pace_vs_field_recent": team_recent_pace - field_recent_pace,
            "team_pit_duration": team_recent_pit,
            "team_min_pit_duration": team_min_pit,
            "team_pit_vs_field_recent": team_recent_pit - field_recent_pit,
            "team_pit_stop_count": mean_or(team_recent10, "pit_stop_count", 1),
            "track_avg_pit_stops": mean_or(c_hist, "pit_stop_count", 1),
            "track_avg_lap_consistency": mean_or(c_hist, "lap_consistency", 3),
            "track_lap_pace_baseline": mean_or(c_hist, "avg_best_35pct_lap", field_recent_pace),
            "track_pit_duration_baseline": mean_or(c_hist, "avg_pit_duration", field_recent_pit),
            "track_dnf_rate": 1 - mean_or(c_hist, "is_finished", 0.85),
            "track_overtake_proxy": mean_or(c_hist, "grid", 10) - mean_or(c_hist, "finish_position", 10),
            "track_abs_overtake_proxy": circuit_abs_movement or 3,
            "track_position_sensitivity": track_position_sensitivity,
            "regulation_era_factor": regulation_era_factor(season),
            "season_progress": (safe_float(round_no) or 1) / 24.0,
        }
        rows.append(row)

    df = pd.DataFrame(rows)
    for col in feature_columns:
        if col not in df:
            df[col] = 0
    return df


def ml_predict_probabilities(drivers, race, current_round_data, bundle):
    if not bundle:
        return {}, {"status": "no model bundle available"}
    try:
        feature_columns = bundle["feature_columns"]
        historical_df = historical_feature_context(bundle.get("ml_start_year", ML_START_YEAR), safe_int(race.get("season")) or now_local().year)
        pred_df = build_prediction_feature_rows(drivers, race, current_round_data, historical_df, feature_columns)
        X = pred_df[feature_columns].replace([np.inf, -np.inf], np.nan).fillna(0)

        outputs = {}
        for target, pair in bundle["models"].items():
            rf_prob = pair["rf"].predict_proba(X)[:, 1]
            hgb_prob = pair["hgb"].predict_proba(X)[:, 1]
            if pair.get("et"):
                et_prob = pair["et"].predict_proba(X)[:, 1]
                outputs[target] = 0.44 * rf_prob + 0.34 * hgb_prob + 0.22 * et_prob
            else:
                outputs[target] = 0.55 * rf_prob + 0.45 * hgb_prob
        finish_pred = None
        finish_model = bundle.get("finish_model")
        if finish_model:
            if finish_model.get("et"):
                finish_pred = 0.40 * finish_model["rf"].predict(X) + 0.40 * finish_model["hgb"].predict(X) + 0.20 * finish_model["et"].predict(X)
            else:
                finish_pred = 0.52 * finish_model["rf"].predict(X) + 0.48 * finish_model["hgb"].predict(X)
            finish_pred = np.clip(finish_pred, 1, max(20, len(pred_df)))
        lap_pred = None
        lap_scores = {}
        lap_model = bundle.get("lap_pace_model")
        if lap_model:
            lap_pred = np.clip(lap_model.predict(X), 45, 180)
            lap_raw = {
                row["driver_id"]: lap_pred[idx]
                for idx, row in pred_df.iterrows()
                if safe_float(lap_pred[idx]) is not None
            }
            lap_scores = normalize_scores(lap_raw, reverse=True)

        by_driver = {}
        for idx, row in pred_df.iterrows():
            driver_id = row["driver_id"]
            item = {
                "ml_win_probability": float(outputs.get("win", [0])[idx] * 100),
                "ml_podium_probability": float(outputs.get("podium", [0])[idx] * 100),
                "ml_top10_probability": float(outputs.get("top10", [0])[idx] * 100),
            }
            if finish_pred is not None:
                item["predicted_finish_position"] = float(finish_pred[idx])
                item["ml_finish_position_score"] = score_position(finish_pred[idx], max(20, len(pred_df)))
            if lap_pred is not None:
                item["predicted_lap_pace_seconds"] = float(lap_pred[idx])
                item["ml_lap_time_forecast_score"] = lap_scores.get(driver_id)
            by_driver[driver_id] = item

        return by_driver, {
            "status": "ml predictions generated",
            "feature_rows": pred_df.to_dict(orient="records"),
            "bundle_meta": {k: v for k, v in bundle.items() if k != "models"},
        }
    except Exception as error:
        print(f"ML prediction failed: {error}")
        return {}, {"status": "ml prediction failed", "error": str(error)}


def fetch_historical_same_circuit(target_race, years_back=5):
    circuit_id = target_race.get("Circuit", {}).get("circuitId")
    season = safe_int(target_race.get("season")) or now_local().year
    records = []
    if not circuit_id:
        return records

    for year in range(season, season - years_back - 1, -1):
        for race in fetch_schedule(year):
            if race.get("Circuit", {}).get("circuitId") == circuit_id:
                round_no = race.get("round")
                if round_no:
                    data = fetch_round_data_cached(
                        year,
                        round_no,
                        allow_backfill=True,
                        race=race,
                        training_mode=is_race_past_calendar_cutoff(race),
                    )
                    if data:
                        records.append({"season": year, "round": round_no, "race": race, "data": data})
                break
    return records


def fetch_weather_for_race(race, event_start):
    location = race.get("Circuit", {}).get("Location", {})
    lat = safe_float(location.get("lat"))
    lon = safe_float(location.get("long"))
    base = {
        "source": "Open-Meteo forecast",
        "temperature": "Unavailable",
        "rain": "Unavailable",
        "humidity": "Unavailable",
        "wind": "Unavailable",
        "wind_gust": "Unavailable",
        "cloud_cover": "Unavailable",
        "track_temperature": "Unavailable",
        "rain_score": 0,
        "heat_score": 0,
        "wind_score": 0,
        "impact": "Weather unavailable.",
    }
    if lat is None or lon is None:
        base["source"] = "Unavailable"
        base["impact"] = "Circuit coordinates missing."
        return base

    params = {
        "latitude": lat,
        "longitude": lon,
        "hourly": "temperature_2m,relative_humidity_2m,precipitation_probability,wind_speed_10m,wind_gusts_10m,cloud_cover",
        "forecast_days": 10,
        "timezone": USER_TIMEZONE_NAME,
    }
    response = safe_get("https://api.open-meteo.com/v1/forecast", params=params, timeout=35, use_cache=False)
    if not response:
        base["impact"] = "Open-Meteo request failed or timed out."
        return base

    try:
        data = response.json()
    except json.JSONDecodeError:
        base["impact"] = "Open-Meteo returned non-JSON data."
        return base

    hourly = data.get("hourly", {})
    times = hourly.get("time", [])
    if not times:
        base["impact"] = "No hourly forecast returned."
        return base

    target = event_start.replace(minute=0, second=0, microsecond=0)
    parsed = []
    for item in times:
        try:
            parsed.append(datetime.fromisoformat(item).replace(tzinfo=USER_TIMEZONE))
        except ValueError:
            parsed.append(None)
    valid = [(idx, val) for idx, val in enumerate(parsed) if val is not None]
    if not valid:
        return base

    idx = min(valid, key=lambda pair: abs(pair[1] - target))[0]

    def get(key):
        vals = hourly.get(key, [])
        return vals[idx] if idx < len(vals) else None

    temp = get("temperature_2m")
    rain = get("precipitation_probability")
    humidity = get("relative_humidity_2m")
    wind = get("wind_speed_10m")
    gust = get("wind_gusts_10m")
    cloud = get("cloud_cover")

    temp_num = safe_float(temp)
    rain_score = min(100, safe_float(rain) or 0)
    wind_num = safe_float(gust) or safe_float(wind) or 0
    heat_score = 85 if temp_num and temp_num >= 34 else 60 if temp_num and temp_num >= 29 else 55 if temp_num and temp_num <= 15 else 0
    wind_score = min(100, wind_num * 2.6)

    impacts = []
    if rain_score >= 50:
        impacts.append("high rain risk, mixed strategy possible")
    elif rain_score >= 25:
        impacts.append("moderate rain risk, radar should influence pit timing")
    else:
        impacts.append("dry baseline more likely")
    if heat_score >= 60:
        impacts.append("heat may increase degradation and cooling demand")
    if wind_score >= 60:
        impacts.append("wind may affect braking stability and aero balance")
    if safe_float(cloud) and safe_float(cloud) >= 70:
        impacts.append("cloud cover may reduce track-temperature growth")

    return {
        "source": "Open-Meteo forecast",
        "temperature": f"{temp}°C" if temp is not None else "Unavailable",
        "rain": f"{rain}%" if rain is not None else "Unavailable",
        "humidity": f"{humidity}%" if humidity is not None else "Unavailable",
        "wind": f"{wind} km/h" if wind is not None else "Unavailable",
        "wind_gust": f"{gust} km/h" if gust is not None else "Unavailable",
        "cloud_cover": f"{cloud}%" if cloud is not None else "Unavailable",
        "track_temperature": "Unavailable",
        "rain_score": rain_score,
        "heat_score": heat_score,
        "wind_score": wind_score,
        "impact": "; ".join(impacts),
    }


def fetch_historical_weather_summary(race, years_back=5):
    location = race.get("Circuit", {}).get("Location", {})
    lat = safe_float(location.get("lat"))
    lon = safe_float(location.get("long"))
    race_dt = parse_race_datetime(race)
    if lat is None or lon is None or not race_dt:
        return {}
    samples = []
    for year in range(race_dt.year - years_back, race_dt.year):
        try:
            start_dt = race_dt.replace(year=year)
        except ValueError:
            continue
        params = {
            "latitude": lat,
            "longitude": lon,
            "start_date": start_dt.date().isoformat(),
            "end_date": (start_dt + timedelta(days=1)).date().isoformat(),
            "hourly": "temperature_2m,precipitation,wind_speed_10m,cloud_cover",
            "timezone": USER_TIMEZONE_NAME,
        }
        response = safe_get("https://archive-api.open-meteo.com/v1/archive", params=params, timeout=35)
        if not response:
            continue
        try:
            data = response.json()
        except json.JSONDecodeError:
            continue
        hourly = data.get("hourly", {})
        samples.append({
            "year": year,
            "avg_temp": average(hourly.get("temperature_2m", [])),
            "rain_total": sum(safe_float(x) or 0 for x in hourly.get("precipitation", [])),
            "max_wind": max([safe_float(x) or 0 for x in hourly.get("wind_speed_10m", [])], default=None),
            "avg_cloud": average(hourly.get("cloud_cover", [])),
        })
    return {"source": "Open-Meteo archive", "samples": samples}


def infer_track_profile(race, historical_records, weather_summary, historical_weather=None):
    trait_samples = []
    all_results = []
    for record in historical_records:
        data = record.get("data", {})
        trait = track_traits_from_race_data(data)
        if trait:
            trait_samples.append(trait)
        result_races = data.get("results", [])
        if result_races:
            all_results.extend(result_races[0].get("Results", []))

    avg_overtake = average([x.get("avg_grid_finish_movement") for x in trait_samples])
    avg_stops = average([x.get("avg_pit_stops") for x in trait_samples])
    dnf_rate = average([x.get("dnf_rate") for x in trait_samples])
    lap_consistency = average([x.get("avg_lap_consistency") for x in trait_samples])

    if avg_overtake is None:
        overtaking = "unknown"
    elif avg_overtake >= 5:
        overtaking = "good"
    elif avg_overtake >= 3:
        overtaking = "medium-good"
    elif avg_overtake >= 1.5:
        overtaking = "medium"
    else:
        overtaking = "low-medium"

    if avg_stops is None:
        tyre_stress = "unknown"
    elif avg_stops >= 2:
        tyre_stress = "high"
    elif avg_stops >= 1.45:
        tyre_stress = "medium-high"
    elif avg_stops >= 1:
        tyre_stress = "medium"
    else:
        tyre_stress = "low-medium"

    if dnf_rate is None:
        safety_car = "unknown"
    elif dnf_rate >= 0.25:
        safety_car = "high"
    elif dnf_rate >= 0.15:
        safety_car = "medium-high"
    elif dnf_rate >= 0.08:
        safety_car = "medium"
    else:
        safety_car = "low-medium"

    circuit = race.get("Circuit", {})
    location = circuit.get("Location", {})
    circuit_name = circuit.get("circuitName", "Unknown circuit")
    circuit_id = circuit.get("circuitId", "")
    text = f"{race.get('raceName', '')} {circuit_name} {circuit_id}".lower()

    street = any(k in text for k in ["monaco", "singapore", "marina", "baku", "miami", "jeddah", "vegas"])
    if street:
        track_type = "street or temporary circuit"
    else:
        track_type = "permanent circuit"

    if any(k in text for k in ["monza", "vegas", "baku", "jeddah"]):
        speed_profile = "straight-line-speed dominant"
        car_trait = "low drag efficiency, braking stability, power delivery"
    elif any(k in text for k in ["silverstone", "suzuka", "spa", "qatar", "lusail"]):
        speed_profile = "aero-efficiency dominant"
        car_trait = "high-speed downforce, aero efficiency, tyre load control"
    elif any(k in text for k in ["monaco", "hungaroring", "singapore"]):
        speed_profile = "traction and braking dominant"
        car_trait = "high downforce, slow-corner traction, kerb compliance"
    else:
        speed_profile = "balanced speed profile"
        car_trait = "balanced aero, traction, braking, and tyre management"

    if "straight-line" in speed_profile:
        dominance = "low drag and straight-line speed"
    elif "aero" in speed_profile:
        dominance = "aero efficiency and high-speed downforce"
    elif street and overtaking in {"low", "low-medium", "unknown"}:
        dominance = "track position, downforce, braking stability, and wall confidence"
    elif tyre_stress in {"high", "medium-high"}:
        dominance = "tyre management and thermal control"
    else:
        dominance = "balanced aero, traction, and tyre management"

    if tyre_stress in {"high", "medium-high"}:
        strategy_bias = "two-stop risk if degradation appears in long runs"
    elif overtaking in {"low", "low-medium"}:
        strategy_bias = "track position first, undercut can matter"
    else:
        strategy_bias = "one-stop or two-stop depending on safety car and tyre delta"

    setup = [car_trait]
    if weather_summary.get("rain_score", 0) >= 35:
        setup.append("wet crossover flexibility")
    if weather_summary.get("wind_score", 0) >= 60:
        setup.append("stable aero balance in wind")

    return {
        "race_name": race.get("raceName", "Unknown Grand Prix"),
        "circuit": circuit_name,
        "city": location.get("locality", "Unknown location"),
        "country": location.get("country", "Unknown country"),
        "track_type": track_type,
        "circuit_key": circuit_id,
        "meeting_key": f"{race.get('season')}-{race.get('round')}",
        "dominance": dominance,
        "speed_profile": speed_profile,
        "car_trait": car_trait,
        "overtaking": overtaking,
        "tyre_stress": tyre_stress,
        "safety_car": safety_car,
        "strategy_bias": strategy_bias,
        "setup": "; ".join(setup),
        "dynamic_reasons": {
            "overtaking": f"average grid-to-finish movement around {avg_overtake}" if avg_overtake is not None else "not enough cached historical data yet",
            "tyre_stress": f"historical average around {avg_stops} stops per driver" if avg_stops is not None else "not enough cached pit data yet",
            "safety_car": f"non-finish proxy rate around {dnf_rate * 100:.1f}%" if dnf_rate is not None else "not enough cached result data yet",
            "speed_profile": f"car trait inferred as {car_trait}",
        },
        "dynamic_track_source": {
            "source": "Jolpica full cached history + Open-Meteo + optional FastF1",
            "used_full_race_cache": True,
            "used_open_meteo_archive": bool(historical_weather and historical_weather.get("samples")),
        },
        "dynamic_track_metrics": {
            "historical_races_sampled": len(historical_records),
            "average_overtake_delta": avg_overtake,
            "average_stops_per_driver": avg_stops,
            "dnf_rate": dnf_rate,
            "lap_consistency": lap_consistency,
            "backfill_used_this_run": BACKFILL_BUDGET.used,
            "backfilled_races_this_run": BACKFILL_BUDGET.fetched,
        },
        "historical_weather": historical_weather or {},
    }


def constructor_score_map(constructor_standings):
    raw = {}
    for row in constructor_standings:
        name = row.get("Constructor", {}).get("name")
        points = safe_float(row.get("points"))
        position = safe_int(row.get("position"))
        if name:
            raw[name] = points if points is not None else (100 - position if position else 0)
    return normalize_scores(raw)


def current_result_score_map(results):
    raw = {}
    for row in results:
        driver_id = row.get("Driver", {}).get("driverId")
        pos = safe_int(row.get("positionOrder") or row.get("position"))
        if driver_id and pos:
            raw[driver_id] = score_position(pos)
    return raw


def qualifying_score_map(round_data):
    raw = {}
    races = round_data.get("qualifying", [])
    if not races:
        return raw
    for row in races[0].get("QualifyingResults", []):
        driver_id = row.get("Driver", {}).get("driverId")
        pos = safe_int(row.get("position"))
        if driver_id and pos:
            raw[driver_id] = score_position(pos)
    return raw


def sprint_score_map(round_data):
    raw = {}
    races = round_data.get("sprint", [])
    if not races:
        return raw
    for row in races[0].get("SprintResults", []) or races[0].get("Results", []):
        driver_id = row.get("Driver", {}).get("driverId")
        pos = safe_int(row.get("positionOrder") or row.get("position"))
        if driver_id and pos:
            raw[driver_id] = score_position(pos)
    return raw


def circuit_history_score_map(historical_records):
    raw = {}
    for record in historical_records:
        weight = max(0.35, 1 - (now_local().year - record["season"]) * 0.12)
        result_races = record.get("data", {}).get("results", [])
        if not result_races:
            continue
        for row in result_races[0].get("Results", []):
            driver_id = row.get("Driver", {}).get("driverId")
            pos = safe_int(row.get("positionOrder") or row.get("position"))
            if driver_id and pos:
                raw.setdefault(driver_id, []).append((score_position(pos), weight))
    return {driver_id: weighted_average(vals) for driver_id, vals in raw.items()}


def constructor_circuit_score_map(historical_records):
    raw = {}
    for record in historical_records:
        weight = max(0.35, 1 - (now_local().year - record["season"]) * 0.12)
        result_races = record.get("data", {}).get("results", [])
        if not result_races:
            continue
        for row in result_races[0].get("Results", []):
            team = row.get("Constructor", {}).get("name")
            pos = safe_int(row.get("positionOrder") or row.get("position"))
            if team and pos:
                raw.setdefault(team, []).append((score_position(pos), weight))
    return {team: weighted_average(vals) for team, vals in raw.items()}


def race_pace_score_map(historical_records, current_round_data):
    raw = {}
    records = [{"season": now_local().year, "data": current_round_data, "weight": 1.35}]
    for rec in historical_records:
        records.append({"season": rec["season"], "data": rec.get("data", {}), "weight": max(0.35, 1 - (now_local().year - rec["season"]) * 0.12)})

    for rec in records:
        metrics = driver_lap_metrics_from_data(rec["data"])
        for driver_id, item in metrics.items():
            if item.get("avg_best_35pct"):
                raw.setdefault(driver_id, []).append((item["avg_best_35pct"], rec["weight"]))

    avg_laps = {driver_id: weighted_average(vals) for driver_id, vals in raw.items()}
    return normalize_scores(avg_laps, reverse=True)


def pit_execution_score_maps(historical_records, current_round_data):
    driver_raw = {}
    team_raw = {}

    def constructor_lookup(data):
        lookup = {}
        result_races = data.get("results", [])
        if result_races:
            for row in result_races[0].get("Results", []):
                lookup[row.get("Driver", {}).get("driverId")] = row.get("Constructor", {}).get("name")
        return lookup

    records = [{"season": now_local().year, "data": current_round_data, "weight": 1.35}]
    for rec in historical_records:
        records.append({"season": rec["season"], "data": rec.get("data", {}), "weight": max(0.35, 1 - (now_local().year - rec["season"]) * 0.12)})

    for rec in records:
        metrics = pit_metrics_from_data(rec["data"])
        lookup = constructor_lookup(rec["data"])
        for driver_id, item in metrics.items():
            duration = item.get("avg_pit_duration")
            if duration:
                driver_raw.setdefault(driver_id, []).append((duration, rec["weight"]))
                team = lookup.get(driver_id)
                if team:
                    team_raw.setdefault(team, []).append((duration, rec["weight"]))

    return normalize_scores({d: weighted_average(v) for d, v in driver_raw.items()}, reverse=True), normalize_scores({t: weighted_average(v) for t, v in team_raw.items()}, reverse=True)


def strategy_gain_score_maps(historical_records):
    driver_raw = {}
    team_raw = {}
    for rec in historical_records:
        weight = max(0.35, 1 - (now_local().year - rec["season"]) * 0.12)
        races = rec.get("data", {}).get("results", [])
        if not races:
            continue
        for row in races[0].get("Results", []):
            driver_id = row.get("Driver", {}).get("driverId")
            team = row.get("Constructor", {}).get("name")
            grid = safe_int(row.get("grid"))
            finish = safe_int(row.get("positionOrder") or row.get("position"))
            if driver_id and grid and grid > 0 and finish:
                gain = grid - finish
                driver_raw.setdefault(driver_id, []).append((gain, weight))
                if team:
                    team_raw.setdefault(team, []).append((gain, weight))
    return normalize_scores({d: weighted_average(v) for d, v in driver_raw.items()}), normalize_scores({t: weighted_average(v) for t, v in team_raw.items()})


def reliability_score_map(historical_records):
    raw = {}
    for rec in historical_records:
        weight = max(0.35, 1 - (now_local().year - rec["season"]) * 0.12)
        races = rec.get("data", {}).get("results", [])
        if not races:
            continue
        for row in races[0].get("Results", []):
            driver_id = row.get("Driver", {}).get("driverId")
            status = str(row.get("status", "")).lower()
            if not driver_id:
                continue
            if "finished" in status or "+" in status:
                score = 90
            elif any(x in status for x in ["accident", "collision", "spun"]):
                score = 35
            elif any(x in status for x in ["engine", "gearbox", "hydraulics", "electrical"]):
                score = 45
            else:
                score = 55
            raw.setdefault(driver_id, []).append((score, weight))
    return {d: weighted_average(v) for d, v in raw.items()}


def team_track_fit_score(team, profile, constructor_circuit_score=None):
    team_text = str(team).lower()
    dominance = str(profile.get("dominance", "")).lower()
    speed = str(profile.get("speed_profile", "")).lower()
    tyre = str(profile.get("tyre_stress", "")).lower()
    overtaking = str(profile.get("overtaking", "")).lower()
    score = 50.0
    if constructor_circuit_score is not None:
        score = weighted_average([(score, 0.35), (constructor_circuit_score, 0.65)])
    if "straight-line" in speed and any(k in team_text for k in ["williams", "red bull", "ferrari", "cadillac"]):
        score += 7
    if ("aero" in dominance or "downforce" in dominance) and any(k in team_text for k in ["mclaren", "mercedes", "red bull", "aston martin"]):
        score += 8
    if ("tyre" in dominance or tyre in {"high", "medium-high"}) and any(k in team_text for k in ["mclaren", "ferrari", "mercedes"]):
        score += 7
    if ("track position" in dominance or "low" in overtaking) and any(k in team_text for k in ["ferrari", "mclaren", "mercedes", "red bull"]):
        score += 5
    if "traction" in dominance and any(k in team_text for k in ["red bull", "ferrari", "aston martin", "racing bulls"]):
        score += 5
    return max(0, min(100, score))


def setup_fastf1():
    if fastf1 is None:
        return False
    try:
        FASTF1_CACHE_DIR.mkdir(parents=True, exist_ok=True)
        fastf1.Cache.enable_cache(str(FASTF1_CACHE_DIR))
        return True
    except Exception as error:
        print(f"FastF1 cache setup failed: {error}")
        return False


def load_fastf1_session(season, round_no, code):
    if not setup_fastf1():
        return None
    try:
        session = fastf1.get_session(int(season), int(round_no), code)
        session.load(laps=True, weather=True, messages=False)
        print(f"FastF1 loaded {season} round {round_no} {code}")
        return session
    except Exception as error:
        print(f"FastF1 skipped {season} round {round_no} {code}: {error}")
        return None


def fastf1_enhancement_scores(season, round_no):
    scores = {"fastf1_race_pace": {}, "fastf1_consistency": {}, "fastf1_tyre_stint": {}, "sessions_loaded": []}
    if not setup_fastf1():
        return scores

    for code in FASTF1_SESSION_ORDER:
        session = load_fastf1_session(season, round_no, code)
        if session is None:
            continue
        scores["sessions_loaded"].append(code)
        try:
            laps = session.laps
            if laps is None or laps.empty:
                continue
            clean = laps.copy()
            if "IsAccurate" in clean.columns:
                clean = clean[clean["IsAccurate"] == True]
            if "Deleted" in clean.columns:
                clean = clean[clean["Deleted"] != True]
            if clean.empty:
                continue

            pace_raw = {}
            consistency_raw = {}
            stint_raw = {}
            for driver, group in clean.groupby("Driver"):
                times = []
                for lap_time in group.get("LapTime", []):
                    try:
                        sec = lap_time.total_seconds()
                    except Exception:
                        sec = None
                    if sec and 45 <= sec <= 180:
                        times.append(sec)
                if len(times) >= 4:
                    sample = sorted(times)[:max(4, int(len(times) * 0.35))]
                    pace_raw[str(driver).lower()] = average(sample)
                    consistency_raw[str(driver).lower()] = float(np.std(sample)) if len(sample) > 1 else None
                if "Stint" in group.columns:
                    stint_raw[str(driver).lower()] = float(group.groupby("Stint").size().max())
            scores["fastf1_race_pace"].update(normalize_scores(pace_raw, reverse=True))
            scores["fastf1_consistency"].update(normalize_scores(consistency_raw, reverse=True))
            scores["fastf1_tyre_stint"].update(normalize_scores(stint_raw))
        except Exception as error:
            print(f"FastF1 extraction failed for {code}: {error}")
    return scores


F1_TIMING_HEADERS = {
    "User-Agent": "BestHTTP",
    "Accept": "application/json,text/plain,*/*",
}


def strip_bom(text):
    return str(text or "").lstrip("\ufeff")


def decode_formula1_z_payload(value):
    if not isinstance(value, str):
        return value
    try:
        inflated = zlib.decompress(base64.b64decode(value), -zlib.MAX_WBITS).decode("utf-8")
        return json.loads(inflated)
    except Exception:
        return value


def f1_timing_json(path, optional_404=True):
    url = f"{F1_LIVE_TIMING_STATIC_BASE}/{str(path or '').lstrip('/')}"
    try:
        response = requests.get(url, headers=F1_TIMING_HEADERS, timeout=8)
        if response.status_code in {403, 404} and optional_404:
            return None
        response.raise_for_status()
    except Exception as error:
        if not optional_404:
            print(f"F1 timing feed unavailable: {url} error={error}")
        return None
    try:
        data = json.loads(strip_bom(response.text))
    except Exception:
        return None
    if str(path).endswith(".z.json"):
        return decode_formula1_z_payload(data)
    return data


def openf1_get(endpoint, params=None, optional_404=True):
    if not OPENF1_ENABLED:
        return []
    if OPENF1_REQUEST_SLEEP > 0:
        time.sleep(OPENF1_REQUEST_SLEEP)
    endpoint = "/" + str(endpoint or "").lstrip("/")
    response = safe_get(
        OPENF1_BASE + endpoint,
        params=params or {},
        headers={"User-Agent": "f1-race-intel/3.0 openf1-optional"},
        timeout=12,
        optional_404=optional_404,
    )
    if not response:
        return []
    try:
        data = response.json()
    except Exception:
        return []
    if isinstance(data, dict) and data.get("error"):
        print(f"OpenF1 unavailable for {endpoint}: {data.get('detail') or data.get('error')}")
        return []
    return data if isinstance(data, list) else []


def parse_f1_gmt_offset(value):
    text = str(value or "00:00:00")
    sign = -1 if text.startswith("-") else 1
    parts = text.lstrip("+-").split(":")
    try:
        hours = int(parts[0] or 0)
        minutes = int(parts[1] or 0) if len(parts) > 1 else 0
        seconds = int(parts[2] or 0) if len(parts) > 2 else 0
    except ValueError:
        return timezone.utc
    return timezone(sign * timedelta(hours=hours, minutes=minutes, seconds=seconds))


def f1_session_datetime(session, field="StartDate"):
    value = session.get(field)
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(str(value))
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=parse_f1_gmt_offset(session.get("GmtOffset")))
    return dt.astimezone(USER_TIMEZONE)


def f1_timing_season_index(season):
    data = f1_timing_json(f"{season}/Index.json", optional_404=True)
    return data if isinstance(data, dict) else {}


def f1_meeting_token_score(meeting, race_tokens):
    meeting_text = " ".join([
        str(meeting.get("Name", "")),
        str(meeting.get("OfficialName", "")),
        str(meeting.get("Location", "")),
        str((meeting.get("Country") or {}).get("Name", "")),
        str((meeting.get("Circuit") or {}).get("ShortName", "")),
    ]).lower()
    return sum(1 for token in race_tokens if token in meeting_text)


def find_f1_timing_meeting(index, race):
    meetings = index.get("Meetings", []) or []
    round_no = safe_int(race.get("round"))
    race_tokens = set(tokenize(race_text(race)))
    if round_no:
        numbered = [
            meeting for meeting in meetings
            if safe_int(meeting.get("Number")) == round_no and "testing" not in str(meeting.get("Name", "")).lower()
        ]
        if numbered and f1_meeting_token_score(numbered[0], race_tokens) >= 1:
            return numbered[0]

    best = None
    best_score = -1
    for meeting in meetings:
        if "testing" in str(meeting.get("Name", "")).lower():
            continue
        score = f1_meeting_token_score(meeting, race_tokens)
        if score > best_score:
            best = meeting
            best_score = score
    return best if best_score >= 1 else None


def f1_timing_candidate_sessions(index, race):
    meetings = [m for m in index.get("Meetings", []) or [] if "testing" not in str(m.get("Name", "")).lower()]
    meeting = find_f1_timing_meeting(index, race)
    now_dt = now_local()

    def completed_sessions(source_meeting):
        out = []
        if not source_meeting:
            return out
        for session in source_meeting.get("Sessions", []) or []:
            start = f1_session_datetime(session)
            if not start or start > now_dt + timedelta(minutes=20):
                continue
            text = f"{session.get('Type', '')} {session.get('Name', '')}".lower()
            if any(key in text for key in ["practice", "qualifying", "sprint", "race"]):
                out.append(session)
        return out

    same_meeting = completed_sessions(meeting)
    if same_meeting:
        return sorted(same_meeting, key=lambda s: f1_session_datetime(s) or now_dt)[-8:]

    previous = []
    for item in meetings:
        if meeting and item.get("Key") == meeting.get("Key"):
            continue
        completed = completed_sessions(item)
        if not completed:
            continue
        latest = max((f1_session_datetime(s) or now_dt) for s in completed)
        previous.append((latest, item, completed))
    previous = sorted(previous, key=lambda item: item[0])[-2:]
    sessions = []
    for _, _, completed in previous:
        sessions.extend(completed)
    return sorted(sessions, key=lambda s: f1_session_datetime(s) or now_dt)[-8:]


def f1_session_weight(session):
    text = f"{session.get('Type', '')} {session.get('Name', '')}".lower()
    if "race" in text and "sprint" not in text:
        return 1.0
    if "qualifying" in text and "sprint" not in text:
        return 0.92
    if "sprint" in text and "qualifying" in text:
        return 0.72
    if "sprint" in text:
        return 0.78
    if "practice 3" in text or str(session.get("Number")) == "3":
        return 0.62
    if "practice 2" in text or str(session.get("Number")) == "2":
        return 0.56
    return 0.50


def f1_driver_number_map(driver_list, known_drivers):
    known_by_number = {
        str(d.get("number")).strip(): d
        for d in known_drivers
        if str(d.get("number") or "").strip()
    }
    known_by_surname = {}
    for driver in known_drivers:
        parts = str(driver.get("name", "")).lower().split()
        if parts:
            known_by_surname[parts[-1]] = driver

    mapped = {}
    items = driver_list.items() if isinstance(driver_list, dict) else []
    for number, payload in items:
        if not isinstance(payload, dict):
            continue
        number = str(payload.get("RacingNumber") or number or "").strip()
        known = known_by_number.get(number)
        if not known:
            full_name = str(payload.get("FullName") or payload.get("BroadcastName") or "").lower()
            for surname, candidate in known_by_surname.items():
                if surname and surname in full_name:
                    known = candidate
                    break
        if known:
            mapped[number] = {
                "driver_id": known.get("driver_id"),
                "team": known.get("team") or payload.get("TeamName"),
                "name": known.get("name") or normalize_name(payload.get("FullName")),
            }
    return mapped


def best_speed_average(best_speeds):
    values = []
    if isinstance(best_speeds, dict):
        for key in ["ST", "FL", "I1", "I2"]:
            value = safe_float((best_speeds.get(key) or {}).get("Value"))
            if value is not None:
                values.append(value)
    return average(values)


def best_sector_position_average(sectors):
    positions = []
    if isinstance(sectors, list):
        for sector in sectors:
            positions.append(safe_float((sector or {}).get("Position")))
    return average(positions)


def normalize_driver_feed_lines(feed):
    if isinstance(feed, dict):
        return feed.get("Lines", {}) or {}
    return {}


def f1_timing_session_raw_metrics(session, known_drivers):
    path = str(session.get("Path") or "").strip("/")
    if not path:
        return None

    driver_list = f1_timing_json(f"{path}/DriverList.json") or {}
    number_map = f1_driver_number_map(driver_list, known_drivers)
    if not number_map:
        return None

    timing_data = normalize_driver_feed_lines(f1_timing_json(f"{path}/TimingData.json") or {})
    timing_app = normalize_driver_feed_lines(f1_timing_json(f"{path}/TimingAppData.json") or {})
    timing_stats = normalize_driver_feed_lines(f1_timing_json(f"{path}/TimingStats.json") or {})
    pit_series = f1_timing_json(f"{path}/PitStopSeries.json") or {}
    lap_series = f1_timing_json(f"{path}/LapSeries.json") or {}

    raw = {
        "session_result": {},
        "starting_grid": {},
        "lap_pace": {},
        "sector_position": {},
        "pit_execution": {},
        "stint_strength": {},
        "telemetry_speed": {},
        "position_gain": {},
    }

    for number, mapped in number_map.items():
        driver_id = mapped.get("driver_id")
        if not driver_id:
            continue
        timing = timing_data.get(number, {}) or {}
        app = timing_app.get(number, {}) or {}
        stats = timing_stats.get(number, {}) or {}

        position = safe_int(timing.get("Position") or timing.get("Line") or stats.get("Line"))
        if position:
            raw["session_result"][driver_id] = score_position(position, len(number_map))

        grid_position = safe_int(app.get("GridPos"))
        if grid_position:
            raw["starting_grid"][driver_id] = score_position(grid_position, len(number_map))

        lap_seconds = parse_lap_time_to_seconds(((stats.get("PersonalBestLapTime") or {}).get("Value")))
        stint_laps = []
        stint_lap_times = []
        for stint in app.get("Stints", []) or []:
            stint_laps.append(safe_float(stint.get("TotalLaps")))
            lap_time = parse_lap_time_to_seconds(stint.get("LapTime"))
            if lap_time is not None:
                stint_lap_times.append(lap_time)
        if lap_seconds is None and stint_lap_times:
            lap_seconds = min(stint_lap_times)
        if lap_seconds is not None:
            raw["lap_pace"][driver_id] = lap_seconds

        sector_position = best_sector_position_average(stats.get("BestSectors"))
        if sector_position is not None:
            raw["sector_position"][driver_id] = sector_position

        speed = best_speed_average(stats.get("BestSpeeds"))
        if speed is not None:
            raw["telemetry_speed"][driver_id] = speed

        stint_strength = max([v for v in stint_laps if v is not None], default=None)
        if stint_strength is not None:
            raw["stint_strength"][driver_id] = stint_strength

        pit_times = []
        for item in ((pit_series.get("PitTimes") or {}).get(number) or []):
            pit = (item or {}).get("PitStop") or {}
            pit_time = safe_float(pit.get("PitStopTime"))
            lane_time = safe_float(pit.get("PitLaneTime"))
            pit_times.append(pit_time if pit_time is not None else lane_time)
        pit_avg = average(pit_times)
        if pit_avg is not None:
            raw["pit_execution"][driver_id] = pit_avg

        laps = (lap_series.get(number) or {}).get("LapPosition") if isinstance(lap_series, dict) else None
        if isinstance(laps, list) and laps:
            first = safe_int(laps[0])
            last = safe_int(laps[-1])
            if first and last:
                raw["position_gain"][driver_id] = first - last

    normalized = {
        "timing_session_result": raw["session_result"],
        "timing_starting_grid": raw["starting_grid"],
        "timing_lap_pace": normalize_scores(raw["lap_pace"], reverse=True),
        "timing_sector_performance": normalize_scores(raw["sector_position"], reverse=True),
        "timing_pit_execution": normalize_scores(raw["pit_execution"], reverse=True),
        "timing_stint_strength": normalize_scores(raw["stint_strength"]),
        "timing_telemetry_speed": normalize_scores(raw["telemetry_speed"]),
        "timing_position_gain": normalize_scores(raw["position_gain"]),
    }
    normalized["timing_car_performance"] = {}
    driver_ids = set().union(*[set(v.keys()) for v in normalized.values()]) if normalized else set()
    for driver_id in driver_ids:
        normalized["timing_car_performance"][driver_id] = weighted_average([
            (normalized["timing_lap_pace"].get(driver_id), 0.34),
            (normalized["timing_sector_performance"].get(driver_id), 0.18),
            (normalized["timing_telemetry_speed"].get(driver_id), 0.20),
            (normalized["timing_stint_strength"].get(driver_id), 0.10),
            (normalized["timing_pit_execution"].get(driver_id), 0.08),
            (normalized["timing_session_result"].get(driver_id), 0.10),
        ])
    return normalized


def merge_weighted_score_maps(items):
    merged = {}
    for score_map, weight in items:
        for key, value in (score_map or {}).items():
            if safe_float(value) is None:
                continue
            merged.setdefault(key, []).append((value, weight))
    return {key: weighted_average(values) for key, values in merged.items()}


def openf1_session_datetime(session, field="date_start"):
    value = session.get(field)
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00")).astimezone(USER_TIMEZONE)
    except ValueError:
        return None


def openf1_candidate_sessions(race, limit=6):
    season = safe_int(race.get("season")) or now_local().year
    if season < 2023:
        return []
    sessions = openf1_get("/sessions", {"year": season})
    if not sessions:
        return []
    race_tokens = set(tokenize(race_text(race)))
    round_dt = parse_race_datetime(race)
    now_dt = now_local()

    def score(session):
        text = " ".join([
            str(session.get("session_name", "")),
            str(session.get("session_type", "")),
            str(session.get("circuit_short_name", "")),
            str(session.get("country_name", "")),
            str(session.get("location", "")),
        ]).lower()
        token_score = sum(1 for token in race_tokens if token in text)
        session_dt = openf1_session_datetime(session)
        date_score = 0
        if round_dt and session_dt:
            delta = abs((round_dt.date() - session_dt.date()).days)
            date_score = 8 if delta <= 1 else 4 if delta <= 7 else -min(delta, 20)
        return token_score * 6 + date_score

    candidates = []
    for session in sessions:
        session_dt = openf1_session_datetime(session)
        if not session_dt or session_dt > now_dt + timedelta(minutes=20):
            continue
        text = f"{session.get('session_type', '')} {session.get('session_name', '')}".lower()
        if not any(key in text for key in ["practice", "qualifying", "sprint", "race"]):
            continue
        candidates.append((score(session), session_dt, session))

    candidates = [item for item in candidates if item[0] >= 1]
    candidates.sort(key=lambda item: (item[0], item[1]))
    return [item[2] for item in candidates[-limit:]]


def openf1_driver_number_map(driver_rows, known_drivers):
    by_number = {str(driver.get("number")).strip(): driver for driver in known_drivers if str(driver.get("number") or "").strip()}
    by_surname = {}
    for driver in known_drivers:
        parts = str(driver.get("name", "")).lower().split()
        if parts:
            by_surname[parts[-1]] = driver

    mapped = {}
    for row in driver_rows or []:
        number = str(row.get("driver_number") or "").strip()
        known = by_number.get(number)
        if not known:
            full_name = str(row.get("full_name") or row.get("broadcast_name") or "").lower()
            for surname, candidate in by_surname.items():
                if surname and surname in full_name:
                    known = candidate
                    break
        if known and number:
            mapped[number] = {
                "driver_id": known.get("driver_id"),
                "team": known.get("team") or row.get("team_name"),
                "name": known.get("name") or normalize_name(row.get("full_name")),
                "headshot_url": row.get("headshot_url"),
            }
    return mapped


def openf1_session_raw_metrics(session, known_drivers):
    session_key = session.get("session_key")
    if not session_key:
        return None

    drivers = openf1_get("/drivers", {"session_key": session_key})
    number_map = openf1_driver_number_map(drivers, known_drivers)
    if not number_map:
        return None

    results = openf1_get("/session_result", {"session_key": session_key})
    grids = openf1_get("/starting_grid", {"session_key": session_key})
    laps = openf1_get("/laps", {"session_key": session_key})
    pits = openf1_get("/pit", {"session_key": session_key})
    stints = openf1_get("/stints", {"session_key": session_key})

    raw = {
        "session_result": {},
        "starting_grid": {},
        "lap_pace": {},
        "sector_position": {},
        "pit_execution": {},
        "stint_strength": {},
        "telemetry_speed": {},
        "position_gain": {},
    }
    field_size = max(1, len(number_map))

    for row in results or []:
        mapped = number_map.get(str(row.get("driver_number")))
        if not mapped:
            continue
        driver_id = mapped.get("driver_id")
        position = safe_int(row.get("position"))
        if position:
            raw["session_result"][driver_id] = score_position(position, field_size)

    for row in grids or []:
        mapped = number_map.get(str(row.get("driver_number")))
        if not mapped:
            continue
        position = safe_int(row.get("position") or row.get("grid_position"))
        if position:
            raw["starting_grid"][mapped.get("driver_id")] = score_position(position, field_size)

    laps_by_driver = {}
    for row in laps or []:
        mapped = number_map.get(str(row.get("driver_number")))
        lap_duration = safe_float(row.get("lap_duration"))
        if not mapped or lap_duration is None or lap_duration < 45 or lap_duration > 220 or row.get("is_pit_out_lap"):
            continue
        laps_by_driver.setdefault(mapped.get("driver_id"), []).append(row)

    for driver_id, rows in laps_by_driver.items():
        lap_times = sorted([safe_float(row.get("lap_duration")) for row in rows if safe_float(row.get("lap_duration")) is not None])
        if lap_times:
            best_count = max(1, int(len(lap_times) * 0.35))
            raw["lap_pace"][driver_id] = average(lap_times[:best_count])
        sector_totals = []
        speeds = []
        for row in rows:
            sectors = [safe_float(row.get("duration_sector_1")), safe_float(row.get("duration_sector_2")), safe_float(row.get("duration_sector_3"))]
            if all(value is not None for value in sectors):
                sector_totals.append(sum(sectors))
            for key_name in ["st_speed", "i1_speed", "i2_speed"]:
                value = safe_float(row.get(key_name))
                if value is not None:
                    speeds.append(value)
        if sector_totals:
            raw["sector_position"][driver_id] = average(sorted(sector_totals)[:max(1, int(len(sector_totals) * 0.35))])
        if speeds:
            raw["telemetry_speed"][driver_id] = average(sorted(speeds)[-max(1, int(len(speeds) * 0.20)):])

    pit_by_driver = {}
    for row in pits or []:
        mapped = number_map.get(str(row.get("driver_number")))
        if not mapped:
            continue
        value = safe_float(row.get("pit_duration") or row.get("lane_duration") or row.get("stop_duration"))
        if value is not None:
            pit_by_driver.setdefault(mapped.get("driver_id"), []).append(value)
    for driver_id, values in pit_by_driver.items():
        raw["pit_execution"][driver_id] = average(values)

    stint_by_driver = {}
    for row in stints or []:
        mapped = number_map.get(str(row.get("driver_number")))
        if not mapped:
            continue
        length = safe_float(row.get("stint_length") or ((safe_int(row.get("lap_end")) or 0) - (safe_int(row.get("lap_start")) or 0) + 1))
        if length is not None:
            stint_by_driver.setdefault(mapped.get("driver_id"), []).append(length)
    for driver_id, values in stint_by_driver.items():
        raw["stint_strength"][driver_id] = max(values)

    for driver_id in set(raw["session_result"]) | set(raw["starting_grid"]):
        result_score = raw["session_result"].get(driver_id)
        grid_score = raw["starting_grid"].get(driver_id)
        if result_score is not None and grid_score is not None:
            raw["position_gain"][driver_id] = result_score - grid_score

    normalized = {
        "timing_session_result": raw["session_result"],
        "timing_starting_grid": raw["starting_grid"],
        "timing_lap_pace": normalize_scores(raw["lap_pace"], reverse=True),
        "timing_sector_performance": normalize_scores(raw["sector_position"], reverse=True),
        "timing_pit_execution": normalize_scores(raw["pit_execution"], reverse=True),
        "timing_stint_strength": normalize_scores(raw["stint_strength"]),
        "timing_telemetry_speed": normalize_scores(raw["telemetry_speed"]),
        "timing_position_gain": normalize_scores(raw["position_gain"]),
    }
    normalized["timing_car_performance"] = {}
    driver_ids = set().union(*[set(v.keys()) for v in normalized.values()]) if normalized else set()
    for driver_id in driver_ids:
        normalized["timing_car_performance"][driver_id] = weighted_average([
            (normalized["timing_lap_pace"].get(driver_id), 0.34),
            (normalized["timing_sector_performance"].get(driver_id), 0.18),
            (normalized["timing_telemetry_speed"].get(driver_id), 0.20),
            (normalized["timing_stint_strength"].get(driver_id), 0.08),
            (normalized["timing_pit_execution"].get(driver_id), 0.08),
            (normalized["timing_session_result"].get(driver_id), 0.12),
        ])
    return normalized


def openf1_enhancement_scores(race, known_drivers):
    sessions = openf1_candidate_sessions(race)
    empty = {key: {} for key in [
        "timing_session_result", "timing_starting_grid", "timing_lap_pace",
        "timing_sector_performance", "timing_pit_execution", "timing_stint_strength",
        "timing_telemetry_speed", "timing_position_gain", "timing_car_performance",
    ]}
    if not sessions:
        return {"provider_status": "openf1_no_matching_free_sessions", "sessions": [], **empty}

    per_session = []
    notes = []
    for session in sessions:
        scores = openf1_session_raw_metrics(session, known_drivers)
        if not scores:
            continue
        weight = f1_session_weight({"Type": session.get("session_type"), "Name": session.get("session_name")})
        per_session.append((scores, weight))
        start = openf1_session_datetime(session)
        notes.append({
            "name": session.get("session_name"),
            "type": session.get("session_type"),
            "start": start.isoformat() if start else None,
            "session_key": session.get("session_key"),
            "weight": weight,
        })
    if not per_session:
        return {"provider_status": "openf1_reachable_but_no_driver_metrics", "sessions": notes, **empty}

    keys = list(empty.keys())
    merged = {
        key: merge_weighted_score_maps([(scores.get(key), weight) for scores, weight in per_session])
        for key in keys
    }
    return {
        "provider_status": "openf1_free_historical_timing_used",
        "sessions": notes,
        "driver_scores": merged["timing_car_performance"],
        **merged,
    }


def external_timing_enhancement_scores(race, known_drivers):
    season = safe_int(race.get("season")) or now_local().year
    index = f1_timing_season_index(season)
    sessions = f1_timing_candidate_sessions(index, race)
    openf1_scores = safe_step("OpenF1 timing enhancement", openf1_enhancement_scores, race, known_drivers) or {}

    empty = {
        "meeting": None,
        "sessions": [],
        "driver_scores": {},
        "team_scores": {},
        "weather_traits": {},
        "timing_session_result": {},
        "timing_starting_grid": {},
        "timing_lap_pace": {},
        "timing_sector_performance": {},
        "timing_pit_execution": {},
        "timing_stint_strength": {},
        "timing_telemetry_speed": {},
        "timing_position_gain": {},
        "timing_car_performance": {},
    }

    per_session = []
    session_notes = []
    for session in sessions or []:
        scores = f1_timing_session_raw_metrics(session, known_drivers)
        if not scores:
            continue
        weight = f1_session_weight(session)
        per_session.append((scores, weight))
        start = f1_session_datetime(session)
        session_notes.append({
            "name": session.get("Name"),
            "type": session.get("Type"),
            "start": start.isoformat() if start else None,
            "path": session.get("Path"),
            "weight": weight,
        })

    keys = [
        "timing_session_result",
        "timing_starting_grid",
        "timing_lap_pace",
        "timing_sector_performance",
        "timing_pit_execution",
        "timing_stint_strength",
        "timing_telemetry_speed",
        "timing_position_gain",
        "timing_car_performance",
    ]
    official = {}
    if per_session:
        official = {
            key: merge_weighted_score_maps([(scores.get(key), weight) for scores, weight in per_session])
            for key in keys
        }

    openf1_used = openf1_scores.get("provider_status") == "openf1_free_historical_timing_used"
    if not official and not openf1_used:
        status = "official_f1_timing_no_completed_sessions_yet" if not sessions else "official_f1_timing_feeds_unavailable"
        if openf1_scores.get("provider_status"):
            status = f"{status};{openf1_scores.get('provider_status')}"
        return {**empty, "provider_status": status, "sessions": session_notes + (openf1_scores.get("sessions") or [])}

    merged = {}
    for key in keys:
        merged[key] = merge_weighted_score_maps([
            (official.get(key), 1.0),
            (openf1_scores.get(key), 0.86 if official else 1.0),
        ])

    driver_team = {d.get("driver_id"): d.get("team") for d in known_drivers}
    team_values = {}
    for driver_id, score in merged["timing_car_performance"].items():
        team = driver_team.get(driver_id)
        if team and score is not None:
            team_values.setdefault(team, []).append(score)
    team_scores = {team: average(values) for team, values in team_values.items() if values}
    meeting = find_f1_timing_meeting(index, race)
    status_parts = []
    if official:
        status_parts.append("official_f1_live_timing_static_used")
    if openf1_used:
        status_parts.append("openf1_free_historical_timing_used")

    return {
        "provider_status": "+".join(status_parts) or "timing_sources_unavailable",
        "meeting": meeting.get("Name") if meeting else None,
        "sessions": session_notes + (openf1_scores.get("sessions") or []),
        "driver_scores": merged["timing_car_performance"],
        "team_scores": team_scores,
        "weather_traits": {},
        **merged,
    }


def collect_current_season_constructor_performance(season, current_round):
    team_rows = {}
    if not current_round:
        return {}

    for race in fetch_schedule(season):
        round_no = safe_int(race.get("round"))
        if not round_no or round_no >= safe_int(current_round):
            continue
        data = fetch_round_data_cached(season, round_no, allow_backfill=True)
        if not data or not race_has_results(data):
            continue

        result_race = data["results"][0]
        qualifying_race = data.get("qualifying", [{}])[0] if data.get("qualifying") else {}
        lap_metrics = driver_lap_metrics_from_data(data)
        pit_metrics = pit_metrics_from_data(data)

        q_by_driver = {}
        for q in qualifying_race.get("QualifyingResults", []):
            q_by_driver[q.get("Driver", {}).get("driverId")] = safe_int(q.get("position"))

        for result in result_race.get("Results", []):
            driver_id = result.get("Driver", {}).get("driverId")
            team = result.get("Constructor", {}).get("name")
            finish = safe_int(result.get("positionOrder") or result.get("position"))
            grid = safe_int(result.get("grid"))
            points = safe_float(result.get("points")) or 0
            status = str(result.get("status", "")).lower()
            if not team or not driver_id:
                continue
            lap = lap_metrics.get(driver_id, {})
            pit = pit_metrics.get(driver_id, {})
            reliability_score = 90 if ("finished" in status or "+" in status) else 45
            grid_gain = grid - finish if grid and grid > 0 and finish else None
            team_rows.setdefault(team, []).append({
                "finish_score": score_position(finish),
                "qualifying_score": score_position(q_by_driver.get(driver_id) or grid),
                "points": points,
                "grid_gain": grid_gain,
                "lap_pace": lap.get("avg_best_35pct"),
                "lap_consistency": lap.get("consistency"),
                "pit_duration": pit.get("avg_pit_duration"),
                "reliability": reliability_score,
            })

    raw = {}
    for team, rows in team_rows.items():
        raw[team] = {
            "finish_score": average([r["finish_score"] for r in rows]),
            "qualifying_score": average([r["qualifying_score"] for r in rows]),
            "points_score": average([r["points"] for r in rows]),
            "strategy_score": average([r["grid_gain"] for r in rows]),
            "lap_pace_raw": average([r["lap_pace"] for r in rows]),
            "lap_consistency_raw": average([r["lap_consistency"] for r in rows]),
            "pit_duration_raw": average([r["pit_duration"] for r in rows]),
            "reliability": average([r["reliability"] for r in rows]),
        }

    lap_scores = normalize_scores({t: r["lap_pace_raw"] for t, r in raw.items() if r["lap_pace_raw"] is not None}, reverse=True)
    consistency_scores = normalize_scores({t: r["lap_consistency_raw"] for t, r in raw.items() if r["lap_consistency_raw"] is not None}, reverse=True)
    pit_scores = normalize_scores({t: r["pit_duration_raw"] for t, r in raw.items() if r["pit_duration_raw"] is not None}, reverse=True)
    point_scores = normalize_scores({t: r["points_score"] for t, r in raw.items() if r["points_score"] is not None})
    strategy_scores = normalize_scores({t: r["strategy_score"] for t, r in raw.items() if r["strategy_score"] is not None})

    final = {}
    for team, row in raw.items():
        final[team] = weighted_average([
            (row["finish_score"], 0.20),
            (row["qualifying_score"], 0.16),
            (point_scores.get(team), 0.16),
            (lap_scores.get(team), 0.18),
            (consistency_scores.get(team), 0.08),
            (pit_scores.get(team), 0.08),
            (strategy_scores.get(team), 0.06),
            (row["reliability"], 0.08),
        ])
    return final


def collect_recent_current_season_constructor_form(season, current_round, recent_n=3):
    if not current_round:
        return {}
    completed = []
    for race in fetch_schedule(season):
        round_no = safe_int(race.get("round"))
        if round_no and round_no < safe_int(current_round):
            completed.append((round_no, race))
    completed = sorted(completed, key=lambda x: x[0])[-recent_n:]
    team_scores = {}
    for round_no, race in completed:
        data = fetch_round_data_cached(season, round_no, allow_backfill=True)
        if not data or not race_has_results(data):
            continue
        for result in data["results"][0].get("Results", []):
            team = result.get("Constructor", {}).get("name")
            finish = safe_int(result.get("positionOrder") or result.get("position"))
            points = safe_float(result.get("points")) or 0
            if not team:
                continue
            team_scores.setdefault(team, []).append(weighted_average([(score_position(finish), 0.62), (points, 0.38)]))
    return {team: average(scores) for team, scores in team_scores.items() if scores}

def driver_code_guess(name):
    parts = str(name or "").split()
    if len(parts) >= 2:
        return (parts[0][0] + parts[-1][:3]).lower()
    return str(name or "").lower()[:4]



# -----------------------------
# Official upgrades, regulations, calendar resilience
# -----------------------------

TRUSTED_UPGRADE_SOURCE_DOMAINS = (
    "fia.com",
    "formula1.com",
)

UPGRADE_TRAIT_KEYWORDS = {
    "downforce": ["downforce", "load", "floor", "diffuser", "front wing", "rear wing", "beam wing", "bodywork", "underfloor", "floor edge", "floor fence"],
    "aero_efficiency": ["aero efficiency", "aerodynamic efficiency", "efficiency", "flow", "wake", "sidepod", "engine cover", "coke", "fence", "fences"],
    "straight_line": ["low drag", "drag reduction", "straight", "straightline", "straight-line", "monza", "low-downforce"],
    "traction": ["traction", "rear suspension", "suspension", "mechanical grip", "slow-speed", "low speed", "kerb", "kerbs"],
    "braking": ["brake", "braking", "brake duct", "brake cooling", "front brake", "rear brake"],
    "cooling": ["cooling", "louvre", "louvres", "heat rejection", "exit", "inlet", "radiator", "high altitude"],
    "tyre_management": ["tyre", "tire", "thermal", "degradation", "temperature", "rear tyre", "front tyre"],
    "stability": ["stability", "balance", "sensitivity", "wind", "yaw", "ride height", "porpoising", "bouncing"],
    "power_efficiency": ["power unit", "energy", "ers", "battery", "deployment", "fuel", "sustainable fuel", "compression ratio"],
}

REGULATION_CONTEXTS = {
    "2025": {
        "era": "2025 bodywork flexibility control era",
        "notes": [
            "FIA front and rear wing flexibility checks make aero compliance and load stability more important.",
            "Teams with efficient legal wing load and stable platforms should be less exposed to regulatory disruption.",
        ],
        "boost_traits": ["aero_efficiency", "stability", "downforce"],
    },
    "2026+": {
        "era": "2026+ active-aero and new power-unit era",
        "notes": [
            "The FIA/F1 2026 rules introduce smaller, lighter cars, reduced drag/downforce targets, active aerodynamics, more electrical power, sustainable fuels, and Manual Override Mode.",
            "Prediction should reward efficient aero switching, straight-line efficiency, energy deployment, traction, braking stability, reliability, and driver adaptability.",
        ],
        "boost_traits": ["aero_efficiency", "straight_line", "power_efficiency", "stability", "traction", "braking", "reliability"],
    },
    "2027+": {
        "era": "2027+ evolved 2026 regulation era",
        "notes": [
            "From 2027 onward the FIA compression-ratio control language moves toward operating-condition control, so power-unit reliability and thermal stability remain relevant model traits.",
            "The model keeps 2026-era active aero and power-unit assumptions unless newer regulation text is added through source notes.",
        ],
        "boost_traits": ["power_efficiency", "cooling", "reliability", "aero_efficiency", "stability"],
    },
}

PROMPT_REQUIREMENT_CHECKLIST = [
    "cache_first_backfill_for_github",
    "use_local_full_cache_after_manual_download",
    "f1timing_if_free_and_working_else_fallback",
    "jolpica_fastf1_openmeteo_core",
    "official_f1_live_timing_sector_speed_stint_pit_metrics",
    "openf1_optional_free_historical_timing_crosscheck",
    "neural_lap_time_forecasting",
    "current_season_car_performance",
    "recent_constructor_form",
    "team_upgrade_package_impact",
    "trusted_upgrade_sources",
    "track_traits_downforce_straightline_traction_braking_tyre_overtaking",
    "weather_traits_rain_heat_wind_cloud_historical_weather",
    "driver_skill_form_reliability_circuit_history_recent_results",
    "qualifying_grid_sprint_lap_pace_pit_execution_strategy_gain",
    "f1_regulation_context_2025_2026_2027_and_future_safe",
    "official_calendar_or_jolpica_fallback",
    "season_change_resilience_uses_previous_data_when_current_missing",
    "email_issue_markdown_dashboard_json",
]


def strip_html(html):
    text = re.sub(r"<script[\s\S]*?</script>", " ", html, flags=re.I)
    text = re.sub(r"<style[\s\S]*?</style>", " ", text, flags=re.I)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"&nbsp;", " ", text)
    text = re.sub(r"&amp;", "&", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def candidate_fia_upgrade_urls(race):
    race_name = str(race.get("raceName", ""))
    circuit = race.get("Circuit", {}).get("circuitName", "")
    year = safe_int(race.get("season")) or now_local().year
    candidates = []
    base_terms = []
    race_doc_slug = re.sub(r"[^a-z0-9]+", "_", race_name.lower()).strip("_")
    if race_doc_slug:
        candidates.append(f"https://www.fia.com/system/files/decision-document/{year}_{race_doc_slug}_-_car_presentation_submissions.pdf")
    for source in [race_name, circuit]:
        cleaned = re.sub(r"\b(formula|1|f1|grand|prix|gp|the|de|del|d')\b", " ", source.lower())
        cleaned = re.sub(r"[^a-z0-9]+", " ", cleaned).strip()
        if cleaned:
            base_terms.append(cleaned)
    for term in base_terms:
        slug = make_slug(term)
        candidates.append(f"{FIA_TECH_UPDATE_BASE}/f1-tech-updates-{slug}-grand-prix")
        candidates.append(f"{FIA_TECH_UPDATE_BASE}/f1-tech-updates-{slug}-gp")
    for url in UPGRADE_NEWS_URLS:
        candidates.append(url)
    seen = []
    for url in candidates:
        if url not in seen:
            seen.append(url)
    return seen[:10]


def fetch_text_from_trusted_url(url):
    if not any(domain in url for domain in TRUSTED_UPGRADE_SOURCE_DOMAINS):
        return None
    response = safe_get(url, timeout=25, use_cache=False, optional_404=True)
    if not response:
        return None
    try:
        content_type = response.headers.get("content-type", "").lower()
        if "pdf" in content_type or url.lower().endswith(".pdf"):
            try:
                from pypdf import PdfReader
                reader = PdfReader(io.BytesIO(response.content))
                return "\n".join((page.extract_text() or "") for page in reader.pages[:12]).strip()
            except Exception as error:
                print(f"Could not parse FIA upgrade PDF {url}: {error}")
                return None
        return strip_html(response.text)
    except Exception:
        return None


def classify_upgrade_text(text):
    text_l = str(text or "").lower()
    traits = {}
    components = []
    for trait, keywords in UPGRADE_TRAIT_KEYWORDS.items():
        score = 0
        for keyword in keywords:
            if keyword in text_l:
                score += 12
                components.append(keyword)
        if score:
            traits[trait] = min(100, score)
    if not traits:
        return {}, []
    return traits, sorted(set(components))[:12]


def extract_team_upgrade_sections(text, team_names):
    sections = {}
    lower = text.lower()
    aliases = {
        "red bull racing": ["red bull", "oracle red bull"],
        "mclaren": ["mclaren"],
        "ferrari": ["ferrari", "scuderia ferrari"],
        "mercedes": ["mercedes", "silver arrows"],
        "aston martin": ["aston martin"],
        "alpine": ["alpine"],
        "williams": ["williams"],
        "haas": ["haas"],
        "racing bulls": ["racing bulls", "rb", "visa cash app"],
        "audi": ["audi", "sauber", "kick sauber"],
        "cadillac": ["cadillac"],
    }
    for team in team_names:
        team_key = str(team or "").lower()
        names = [team_key] + aliases.get(team_key, [])
        hits = []
        for name in names:
            if not name:
                continue
            for match in re.finditer(re.escape(name), lower):
                start = max(0, match.start() - 450)
                end = min(len(text), match.end() + 900)
                hits.append(text[start:end])
        if hits:
            sections[team] = " ".join(hits[:3])
    return sections


def trait_alignment_score(traits, profile, weather_summary, regulation_context):
    if not traits:
        return None
    dominance = str(profile.get("dominance", "")).lower()
    speed = str(profile.get("speed_profile", "")).lower()
    tyre = str(profile.get("tyre_stress", "")).lower()
    overtaking = str(profile.get("overtaking", "")).lower()
    rain = safe_float(weather_summary.get("rain_score")) or 0
    heat = safe_float(weather_summary.get("heat_score")) or 0
    wind = safe_float(weather_summary.get("wind_score")) or 0
    weights = {trait: 0.35 for trait in traits}
    if "straight" in speed or "low drag" in dominance:
        weights["straight_line"] = weights.get("straight_line", 0) + 0.9
        weights["aero_efficiency"] = weights.get("aero_efficiency", 0) + 0.45
    if "aero" in dominance or "downforce" in dominance:
        weights["downforce"] = weights.get("downforce", 0) + 0.75
        weights["aero_efficiency"] = weights.get("aero_efficiency", 0) + 0.65
    if "traction" in speed or "track position" in dominance or "low" in overtaking:
        weights["traction"] = weights.get("traction", 0) + 0.55
        weights["braking"] = weights.get("braking", 0) + 0.45
        weights["downforce"] = weights.get("downforce", 0) + 0.45
    if tyre in {"high", "medium-high"}:
        weights["tyre_management"] = weights.get("tyre_management", 0) + 0.65
        weights["cooling"] = weights.get("cooling", 0) + 0.35
    if heat >= 60:
        weights["cooling"] = weights.get("cooling", 0) + 0.7
        weights["tyre_management"] = weights.get("tyre_management", 0) + 0.4
    if wind >= 55:
        weights["stability"] = weights.get("stability", 0) + 0.55
    if rain >= 35:
        weights["stability"] = weights.get("stability", 0) + 0.35
        weights["traction"] = weights.get("traction", 0) + 0.35
    for trait in regulation_context.get("boost_traits", []):
        weights[trait] = weights.get(trait, 0) + 0.3
    return weighted_average([(traits.get(k), weights.get(k, 0.25)) for k in set(traits) | set(weights)])


def regulation_context_for_season(season):
    season = safe_int(season) or now_local().year
    if season >= 2027:
        ctx = dict(REGULATION_CONTEXTS["2026+"])
        ctx["era"] = REGULATION_CONTEXTS["2027+"]["era"]
        ctx["notes"] = REGULATION_CONTEXTS["2026+"]["notes"] + REGULATION_CONTEXTS["2027+"]["notes"]
        ctx["boost_traits"] = sorted(set(REGULATION_CONTEXTS["2026+"]["boost_traits"] + REGULATION_CONTEXTS["2027+"]["boost_traits"]))
        ctx["source_urls"] = ["https://www.fia.com/news/fia-statement-amendments-2026-f1-regulations", "https://www.fia.com/news/new-era-competition-fia-showcases-future-focused-formula-1-regulations-2026-and-beyond"]
        return ctx
    if season == 2026:
        ctx = dict(REGULATION_CONTEXTS["2026+"])
        ctx["source_urls"] = ["https://www.fia.com/news/new-era-competition-fia-showcases-future-focused-formula-1-regulations-2026-and-beyond"]
        return ctx
    if season == 2025:
        ctx = dict(REGULATION_CONTEXTS["2025"])
        ctx["source_urls"] = ["FIA bodywork flexibility directive reporting"]
        return ctx
    return {"era": "stable pre-2026 regulation era", "notes": ["No special regulation-era modifier beyond normal track and car traits."], "boost_traits": [], "source_urls": []}


def regulation_fit_score_for_driver(team, profile, weather_summary, regulation_context, car_performance=None, reliability=None, f1timing_car=None):
    base = weighted_average([
        (team_track_fit_score(team, profile), 0.42),
        (car_performance, 0.30),
        (reliability, 0.16),
        (f1timing_car, 0.12),
    ])
    if base is None:
        base = 50
    boosts = regulation_context.get("boost_traits", [])
    dominance = str(profile.get("dominance", "")).lower()
    speed = str(profile.get("speed_profile", "")).lower()
    if "straight_line" in boosts and "straight" in speed:
        base += 4
    if "aero_efficiency" in boosts and ("aero" in dominance or "downforce" in dominance):
        base += 4
    if "power_efficiency" in boosts and "straight" in speed:
        base += 2
    if "cooling" in boosts and (safe_float(weather_summary.get("heat_score")) or 0) >= 60:
        base += 3
    return max(0, min(100, base))


def fetch_upgrade_package_context(race, drivers, profile, weather_summary, regulation_context):
    if not UPGRADES_ENABLED:
        return {"provider_status": "disabled", "sources": [], "team_scores": {}, "team_traits": {}, "notes": []}
    teams = sorted(set(d.get("team") for d in drivers if d.get("team")))
    sources = []
    team_traits = {team: {} for team in teams}
    notes = []
    for url in candidate_fia_upgrade_urls(race):
        text = fetch_text_from_trusted_url(url)
        if not text or len(text) < 400:
            continue
        sources.append(url)
        sections = extract_team_upgrade_sections(text, teams)
        for team, section in sections.items():
            traits, components = classify_upgrade_text(section)
            if not traits:
                continue
            merged = team_traits.setdefault(team, {})
            for trait, value in traits.items():
                merged[trait] = max(merged.get(trait, 0), value)
            notes.append({"team": team, "source": url, "components": components, "excerpt": section[:420]})
    team_scores = {}
    for team, traits in team_traits.items():
        score = trait_alignment_score(traits, profile, weather_summary, regulation_context)
        if score is not None:
            # Conservative cap: upgrades can move predictions, but they must not overwhelm race pace, grid, or car data.
            team_scores[team] = max(40, min(88, score))
    status = "official_upgrade_data_used" if team_scores else "no_current_official_upgrade_data_found"
    return {"provider_status": status, "sources": sources, "team_scores": team_scores, "team_traits": team_traits, "notes": notes[:20]}


def official_calendar_context_for_season(season, race=None):
    ctx = {"enabled": OFFICIAL_CALENDAR_ENABLED, "source": "Jolpica/ICS primary", "official_url": None, "status": "not_checked", "race_name_seen": False}
    if not OFFICIAL_CALENDAR_ENABLED:
        ctx["status"] = "disabled"
        return ctx
    url = OFFICIAL_F1_CALENDAR_URL.format(year=season)
    ctx["official_url"] = url
    response = safe_get(url, timeout=25, use_cache=False, optional_404=True)
    if not response:
        ctx["status"] = "official_f1_calendar_unavailable_using_ics_jolpica"
        return ctx
    text = strip_html(response.text).lower()
    race_name = str((race or {}).get("raceName", "")).lower()
    ctx["status"] = "official_f1_calendar_page_reachable"
    ctx["race_name_seen"] = bool(race_name and any(token in text for token in tokenize(race_name)))
    return ctx


def fetch_latest_available_standings_with_fallback(season):
    for year in range(safe_int(season) or now_local().year, ML_START_YEAR - 1, -1):
        drivers = fetch_driver_standings(year)
        constructors = fetch_constructor_standings(year)
        if drivers and constructors:
            return drivers, constructors, {"standings_season_used": year, "fallback_used": year != season}
    return [], [], {"standings_season_used": None, "fallback_used": True}

def get_prediction_stage(current_round_data, event_start):
    has_qualifying = bool(current_round_data.get("qualifying"))
    has_results = bool(current_round_data.get("results"))
    if has_results and now_local() > event_start:
        return "post-race-data", "Post-race data, historical update"
    if has_qualifying:
        return "post-qualifying", "Post-qualifying prediction"
    if event_start - now_local() <= timedelta(days=3):
        return "race-weekend", "Race-weekend prediction"
    return "pre-weekend", "Pre-weekend prediction"


def get_prediction_weights(profile, weather_summary, stage, regulation_context=None, upgrade_context=None):
    overtaking = str(profile.get("overtaking", "unknown")).lower()
    tyre = str(profile.get("tyre_stress", "unknown")).lower()
    dominance = str(profile.get("dominance", "")).lower()
    speed = str(profile.get("speed_profile", "")).lower()
    rain = weather_summary.get("rain_score", 0)
    heat = weather_summary.get("heat_score", 0)
    wind = weather_summary.get("wind_score", 0)
    regulation_context = regulation_context or {}
    upgrade_context = upgrade_context or {}

    weights = {
        "ml_win_probability": 0.08,
        "ml_podium_probability": 0.12,
        "ml_top10_probability": 0.06,
        "ml_finish_position_score": 0.08,
        "ml_lap_time_forecast_score": 0.05,
        "transparent_racecraft_score": 0.05,
        "driver_form": 0.07,
        "driver_skill": 0.06,
        "car_performance": 0.09,
        "constructor_form": 0.07,
        "recent_result": 0.05,
        "qualifying": 0.08,
        "circuit_history": 0.07,
        "race_pace": 0.07,
        "pit_execution": 0.05,
        "team_strategy": 0.05,
        "reliability": 0.04,
        "team_track_fit": 0.06,
        "weather_adaptation": 0.04,
        "track_trait_fit": 0.05,
        "sprint_performance": 0.03,
        "current_season_car_performance": 0.06,
        "current_season_recent_form": 0.04,
        "timing_session_result": 0.04,
        "timing_starting_grid": 0.04,
        "timing_lap_pace": 0.05,
        "timing_sector_performance": 0.04,
        "timing_pit_execution": 0.03,
        "timing_stint_strength": 0.03,
        "timing_telemetry_speed": 0.04,
        "timing_position_gain": 0.02,
        "timing_car_performance": 0.07,
        "upgrade_package_impact": 0.05,
        "regulation_fit": 0.04,
        "calendar_confidence": 0.01,
        "fastf1_race_pace": 0.06,
        "fastf1_consistency": 0.03,
        "fastf1_tyre_stint": 0.02,
    }

    if stage == "post-qualifying":
        weights["qualifying"] += 0.08
        weights["ml_podium_probability"] += 0.03
        weights["ml_finish_position_score"] += 0.03
        weights["ml_lap_time_forecast_score"] += 0.02
    elif stage == "race-weekend":
        weights["fastf1_race_pace"] += 0.05
        weights["fastf1_consistency"] += 0.03
    else:
        weights["driver_form"] += 0.03
        weights["car_performance"] += 0.03
        weights["circuit_history"] += 0.02

    if "low" in overtaking:
        weights["qualifying"] += 0.08
        weights["pit_execution"] += 0.03
        weights["team_strategy"] += 0.03
    if "good" in overtaking:
        weights["race_pace"] += 0.04
        weights["team_strategy"] += 0.03
    if tyre in {"high", "medium-high"} or heat >= 60:
        weights["race_pace"] += 0.04
        weights["pit_execution"] += 0.03
        weights["fastf1_tyre_stint"] += 0.03
    if rain >= 35:
        weights["reliability"] += 0.05
        weights["weather_adaptation"] += 0.07
        weights["team_strategy"] += 0.04
    if wind >= 60:
        weights["reliability"] += 0.03
        weights["weather_adaptation"] += 0.03
    if "straight-line" in speed or "aero" in dominance or "downforce" in dominance:
        weights["car_performance"] += 0.04
        weights["team_track_fit"] += 0.04
        weights["track_trait_fit"] += 0.03
    if regulation_context.get("boost_traits"):
        weights["regulation_fit"] += 0.04
        weights["car_performance"] += 0.02
    if upgrade_context.get("team_scores"):
        weights["upgrade_package_impact"] += 0.05
        weights["track_trait_fit"] += 0.02

    total = sum(max(0, value) for value in weights.values())
    return {key: max(0, value) / total for key, value in weights.items()}


def rank_prediction(drivers, constructor_standings, last_results, current_round_data, historical_records, profile, weather_summary, ml_outputs, fastf1_scores, timing_scores, upgrade_context, regulation_context, calendar_context, season, current_round, stage):
    weights = get_prediction_weights(profile, weather_summary, stage, regulation_context, upgrade_context)

    driver_points = {d["driver_id"]: d["points"] for d in drivers}
    driver_form = normalize_scores(driver_points)
    constructor_form = constructor_score_map(constructor_standings)
    current_season_car = collect_current_season_constructor_performance(season, current_round)
    recent_current_season_car = collect_recent_current_season_constructor_form(season, current_round)
    timing_team_scores = timing_scores.get("team_scores", {}) if timing_scores else {}
    upgrade_team_scores = upgrade_context.get("team_scores", {}) if upgrade_context else {}

    for team in set(constructor_form) | set(current_season_car) | set(recent_current_season_car) | set(timing_team_scores) | set(upgrade_team_scores):
        constructor_form[team] = weighted_average([
            (constructor_form.get(team), 0.38),
            (current_season_car.get(team), 0.30),
            (recent_current_season_car.get(team), 0.18),
            (timing_team_scores.get(team), 0.12),
            (upgrade_team_scores.get(team), 0.08),
        ])

    recent = current_result_score_map(last_results)
    qualifying = qualifying_score_map(current_round_data)
    sprint = sprint_score_map(current_round_data)
    circuit = circuit_history_score_map(historical_records)
    race_pace = race_pace_score_map(historical_records, current_round_data)
    driver_pit, team_pit = pit_execution_score_maps(historical_records, current_round_data)
    driver_strategy, team_strategy_map = strategy_gain_score_maps(historical_records)
    reliability = reliability_score_map(historical_records)
    constructor_circuit = constructor_circuit_score_map(historical_records)

    predictions = []
    for driver in drivers:
        driver_id = driver["driver_id"]
        team = driver["team"]
        code = driver_code_guess(driver["name"])
        ml = ml_outputs.get(driver_id, {})

        f1timing_driver_car = timing_scores.get("timing_car_performance", {}).get(driver_id) if timing_scores else None
        upgrade_score = upgrade_team_scores.get(team)
        track_fit = team_track_fit_score(team, profile, constructor_circuit.get(team))
        car_performance = weighted_average([
            (constructor_form.get(team), 0.42),
            (current_season_car.get(team), 0.20),
            (recent_current_season_car.get(team), 0.10),
            (constructor_circuit.get(team), 0.08),
            (track_fit, 0.08),
            (f1timing_driver_car, 0.08),
            (upgrade_score, 0.08),
        ])
        pit_execution = weighted_average([(driver_pit.get(driver_id), 0.45), (team_pit.get(team), 0.55)])
        team_strategy = weighted_average([(driver_strategy.get(driver_id), 0.45), (team_strategy_map.get(team), 0.4), (team_pit.get(team), 0.15)])
        driver_skill = weighted_average([
            (driver_form.get(driver_id), 0.4),
            (circuit.get(driver_id), 0.25),
            (race_pace.get(driver_id), 0.2),
            (reliability.get(driver_id), 0.15),
        ])
        weather_adaptation = weighted_average([
            (reliability.get(driver_id), 0.35),
            (circuit.get(driver_id), 0.25),
            (race_pace.get(driver_id), 0.20),
            (team_strategy, 0.20),
        ])
        track_trait_fit = weighted_average([
            (track_fit, 0.5),
            (car_performance, 0.35),
            (pit_execution, 0.15),
        ])
        regulation_fit = regulation_fit_score_for_driver(team, profile, weather_summary, regulation_context, car_performance, reliability.get(driver_id), f1timing_driver_car)
        calendar_confidence = 80 if calendar_context.get("status") == "official_f1_calendar_page_reachable" else 55
        transparent_racecraft = weighted_average([
            (driver_skill, 0.22),
            (car_performance, 0.24),
            (qualifying.get(driver_id), 0.12),
            (circuit.get(driver_id), 0.11),
            (race_pace.get(driver_id), 0.10),
            (pit_execution, 0.08),
            (team_strategy, 0.07),
            (reliability.get(driver_id), 0.06),
        ])

        component_scores = {
            "ml_win_probability": ml.get("ml_win_probability"),
            "ml_podium_probability": ml.get("ml_podium_probability"),
            "ml_top10_probability": ml.get("ml_top10_probability"),
            "ml_finish_position_score": ml.get("ml_finish_position_score"),
            "ml_lap_time_forecast_score": ml.get("ml_lap_time_forecast_score"),
            "transparent_racecraft_score": transparent_racecraft,
            "driver_form": driver_form.get(driver_id),
            "driver_skill": driver_skill,
            "car_performance": car_performance,
            "constructor_form": constructor_form.get(team),
            "current_season_car_performance": current_season_car.get(team),
            "current_season_recent_form": recent_current_season_car.get(team),
            "timing_session_result": timing_scores.get("timing_session_result", {}).get(driver_id) if timing_scores else None,
            "timing_starting_grid": timing_scores.get("timing_starting_grid", {}).get(driver_id) if timing_scores else None,
            "timing_lap_pace": timing_scores.get("timing_lap_pace", {}).get(driver_id) if timing_scores else None,
            "timing_sector_performance": timing_scores.get("timing_sector_performance", {}).get(driver_id) if timing_scores else None,
            "timing_pit_execution": timing_scores.get("timing_pit_execution", {}).get(driver_id) if timing_scores else None,
            "timing_stint_strength": timing_scores.get("timing_stint_strength", {}).get(driver_id) if timing_scores else None,
            "timing_telemetry_speed": timing_scores.get("timing_telemetry_speed", {}).get(driver_id) if timing_scores else None,
            "timing_position_gain": timing_scores.get("timing_position_gain", {}).get(driver_id) if timing_scores else None,
            "timing_car_performance": timing_scores.get("timing_car_performance", {}).get(driver_id) if timing_scores else None,
            "upgrade_package_impact": upgrade_score,
            "regulation_fit": regulation_fit,
            "calendar_confidence": calendar_confidence,
            "recent_result": recent.get(driver_id),
            "qualifying": qualifying.get(driver_id),
            "circuit_history": circuit.get(driver_id),
            "race_pace": race_pace.get(driver_id),
            "pit_execution": pit_execution,
            "team_strategy": team_strategy,
            "reliability": reliability.get(driver_id),
            "team_track_fit": track_fit,
            "weather_adaptation": weather_adaptation,
            "track_trait_fit": track_trait_fit,
            "sprint_performance": sprint.get(driver_id),
            "fastf1_race_pace": fastf1_scores.get("fastf1_race_pace", {}).get(code),
            "fastf1_consistency": fastf1_scores.get("fastf1_consistency", {}).get(code),
            "fastf1_tyre_stint": fastf1_scores.get("fastf1_tyre_stint", {}).get(code),
        }

        score = weighted_average([(component_scores.get(k), w) for k, w in weights.items()]) or 0
        available_weight = sum(w for k, w in weights.items() if component_scores.get(k) is not None)
        confidence = min(100, max(0, available_weight * 100))

        reasons = sorted(
            [(k, v) for k, v in component_scores.items() if v is not None],
            key=lambda item: item[1] * weights.get(item[0], 0),
            reverse=True,
        )
        reason_names = [PREDICTION_LABELS.get(k, k) for k, v in reasons[:5] if v >= 35] or ["limited cached data evidence"]

        predictions.append({
            "name": driver["name"],
            "team": team,
            "driver_id": driver_id,
            "score": round(score, 2),
            "confidence": round(confidence, 1),
            "reason": "; ".join(reason_names),
            "component_scores": {k: round(v, 2) if v is not None else None for k, v in component_scores.items()},
            "predicted_finish_position": round(ml.get("predicted_finish_position"), 2) if ml.get("predicted_finish_position") is not None else None,
            "predicted_lap_pace_seconds": round(ml.get("predicted_lap_pace_seconds"), 3) if ml.get("predicted_lap_pace_seconds") is not None else None,
            "image": None,
            "team_colour": None,
        })

    predictions.sort(key=lambda item: (item["score"], item["confidence"]), reverse=True)
    top10 = predictions[:10]
    text = "\n".join(
        f"{idx}. {item['name']}, score {item['score']:.1f}, confidence {item['confidence']:.0f}%, {item['reason']}"
        for idx, item in enumerate(top10, start=1)
    )
    model = {
        "source": "Hybrid full-data cache model: Jolpica full history + official Formula 1 live timing static feeds + optional OpenF1 free historical timing + FastF1 + Open-Meteo + ICS/F1 calendar",
        "logic": "Stacked racecraft ensemble: RF/HGB/ExtraTrees win/podium/top10 classifiers, RF/HGB/ExtraTrees finish-position regressor, neural lap-time forecaster, transparent driver/team/circuit formula, official/OpenF1 timing sectors/speeds/stints/pits, recency-weighted form, qualifying/grid strength, track traits, weather traits, tyre strategy, sprint, reliability, upgrades, and regulation-era modifiers",
        "prediction_stage": stage,
        "weights": {k: round(v, 4) for k, v in weights.items()},
        "available_components": {
            "ml_outputs": len(ml_outputs),
            "ml_finish_position": sum(1 for item in ml_outputs.values() if item.get("predicted_finish_position") is not None),
            "ml_lap_time_forecast": sum(1 for item in ml_outputs.values() if item.get("predicted_lap_pace_seconds") is not None),
            "driver_form": len(driver_form),
            "constructor_form": len(constructor_form),
            "current_season_car_performance": len(current_season_car),
            "current_season_recent_form": len(recent_current_season_car),
            "timing_provider_status": timing_scores.get("provider_status") if timing_scores else "not_used",
            "timing_car_performance": len(timing_scores.get("timing_car_performance", {})) if timing_scores else 0,
            "timing_telemetry_speed": len(timing_scores.get("timing_telemetry_speed", {})) if timing_scores else 0,
            "timing_sector_performance": len(timing_scores.get("timing_sector_performance", {})) if timing_scores else 0,
            "upgrade_provider_status": upgrade_context.get("provider_status") if upgrade_context else "not_used",
            "upgrade_package_impact": len(upgrade_team_scores),
            "regulation_era": regulation_context.get("era"),
            "official_calendar_status": calendar_context.get("status"),
            "recent_result": len(recent),
            "qualifying": len(qualifying),
            "sprint": len(sprint),
            "circuit_history": len(circuit),
            "race_pace": len(race_pace),
            "pit_execution_drivers": len(driver_pit),
            "strategy_drivers": len(driver_strategy),
            "reliability": len(reliability),
            "fastf1_sessions_loaded": fastf1_scores.get("sessions_loaded", []),
            "backfill_used_this_run": BACKFILL_BUDGET.used,
        },
    }
    return text, top10, model


def get_dynamic_team_fit(top10, constructor_standings):
    scores = {}
    for team, score in constructor_score_map(constructor_standings).items():
        scores[team] = scores.get(team, 0) + score * 0.45
    for idx, item in enumerate(top10):
        team = item.get("team") or "Unknown Team"
        scores[team] = scores.get(team, 0) + (10 - idx) * 8
    return [team for team, _ in sorted(scores.items(), key=lambda item: item[1], reverse=True)[:5]]


def pit_window_from_profile(profile, weather_summary):
    rain = weather_summary.get("rain_score", 0)
    tyre = profile.get("tyre_stress", "unknown")
    if rain >= 50:
        return "Delay fixed dry-tyre stops. Watch radar and react to rain onset."
    if tyre == "high":
        return "Lap 14-24 for aggressive two-stop, lap 22-32 for conservative one-stop."
    if tyre == "medium-high":
        return "Lap 16-28, with safety car flexibility."
    if tyre == "medium":
        return "Lap 18-32 for normal dry strategy."
    if tyre == "low-medium":
        return "Lap 24-40 if track position is secure."
    return "Unavailable until more cached pit-stop history is available."



def notification_status(event):
    """
    Predictions are generated on every run.
    Email and GitHub Issue notifications are gated to avoid spam.

    Notifications are allowed when:
    - FORCE_NOTIFY=true, or
    - the matched upcoming calendar event is within NOTIFICATION_WINDOW_HOURS.
    """
    if FORCE_NOTIFY:
        return {
            "allowed": True,
            "reason": "FORCE_NOTIFY=true",
            "hours_until_event": None,
        }

    start = event.get("start") if event else None
    if start is None:
        return {
            "allowed": False,
            "reason": "No event start time found.",
            "hours_until_event": None,
        }

    hours_until = (start - now_local()).total_seconds() / 3600

    if 0 <= hours_until <= NOTIFICATION_WINDOW_HOURS:
        return {
            "allowed": True,
            "reason": f"Event starts within {NOTIFICATION_WINDOW_HOURS} hours.",
            "hours_until_event": round(hours_until, 2),
        }

    if hours_until < 0:
        return {
            "allowed": False,
            "reason": "Matched event has already started or passed.",
            "hours_until_event": round(hours_until, 2),
        }

    return {
        "allowed": False,
        "reason": f"Event is more than {NOTIFICATION_WINDOW_HOURS} hours away.",
        "hours_until_event": round(hours_until, 2),
    }


def notification_status_for_events(events):
    if FORCE_NOTIFY:
        return {
            "allowed": True,
            "reason": "FORCE_NOTIFY=true",
            "hours_until_event": None,
            "matched_event": None,
        }

    if not events:
        return {
            "allowed": False,
            "reason": "No Sprint/Race output target was selected.",
            "hours_until_event": None,
            "matched_event": None,
        }

    statuses = []
    for event in events:
        status = notification_status(event)
        status["matched_event"] = event.get("title")
        statuses.append(status)

    allowed = [status for status in statuses if status.get("allowed")]
    if allowed:
        allowed.sort(key=lambda item: item.get("hours_until_event") if item.get("hours_until_event") is not None else 9999)
        return allowed[0]

    future_statuses = [status for status in statuses if status.get("hours_until_event") is not None and status.get("hours_until_event") >= 0]
    if future_statuses:
        future_statuses.sort(key=lambda item: item.get("hours_until_event"))
        status = future_statuses[0]
        return {
            "allowed": False,
            "reason": f"Nearest Sprint/Race target is more than {NOTIFICATION_WINDOW_HOURS} hours away.",
            "hours_until_event": status.get("hours_until_event"),
            "matched_event": status.get("matched_event"),
        }

    return statuses[0]


def maybe_send_outputs(title, briefing, event_or_events):
    """
    Always generate and commit dashboard data.
    Only send email and update GitHub issue inside notification window.
    """
    events = event_or_events if isinstance(event_or_events, list) else [event_or_events]
    status = notification_status_for_events(events)
    print(f"Notification gate: allowed={status['allowed']} reason={status['reason']} hours_until_event={status['hours_until_event']} matched_event={status.get('matched_event')}")

    if not status["allowed"]:
        return status

    safe_step("Create or update issue", create_or_update_issue, title, briefing)
    safe_step("Send email", send_email, title, briefing)
    return status


def generate_briefing(event, race, profile, weather, top10_text, prediction_model, team_fit, upgrade_context, regulation_context, calendar_context):
    """
    Clean public briefing.

    The full model still runs internally. This output is deliberately short so
    email, GitHub Issue, Markdown, and the website stay readable.
    """
    target_type = prediction_model.get("output_target_type", classify_output_target_event(event))
    title_prefix = "Sprint" if target_type == "sprint" else "Race" if target_type == "race" else "F1"
    title = f"F1 {title_prefix} Briefing: {event['title']}"
    start_str = event["start"].strftime("%A, %d %B %Y, %I:%M %p %Z")

    top_prediction = top10_text if top10_text else "Prediction unavailable until enough data is cached."

    team_text = "\n".join(
        f"{idx + 1}. {team}" for idx, team in enumerate((team_fit or [])[:5])
    ) if team_fit else "Unavailable"

    upgrade_scores = upgrade_context.get("team_scores") or {}
    upgrade_traits = upgrade_context.get("team_traits") or {}
    upgrade_lines = []
    for team, score in sorted(upgrade_scores.items(), key=lambda item: item[1], reverse=True)[:3]:
        traits = upgrade_traits.get(team, {})
        useful_traits = [trait.replace("_", " ") for trait, value in traits.items() if value]
        trait_text = ", ".join(useful_traits[:3]) if useful_traits else "no clear trait match"
        upgrade_lines.append(f"- {team}: {score:.1f}/100, {trait_text}")
    if not upgrade_lines:
        upgrade_lines = ["- No trusted upgrade-package signal found for this event."]

    weights = prediction_model.get("weights", {}) or {}
    top_weights = sorted(weights.items(), key=lambda item: item[1], reverse=True)[:5]
    model_lines = [
        f"- {key.replace('_', ' ')}: {value * 100:.1f}%"
        for key, value in top_weights
    ] or ["- Weight audit unavailable"]

    available = prediction_model.get("available_components", {}) or {}
    source_lines = [
        f"- Stage: {prediction_model.get('prediction_stage_label', 'Unknown')}",
        f"- ML model: {'loaded' if prediction_model.get('ml_model_loaded') else 'fallback mode'}",
        f"- F1 timing: {available.get('timing_provider_status', available.get('f1timing_status', 'fallback if unavailable'))}",
        f"- FastF1 sessions: {available.get('fastf1_sessions_loaded', [])}",
        f"- Calendar check: {calendar_context.get('status', 'not checked')}",
    ]
    metrics = ((prediction_model.get("ml_model_meta") or {}).get("metrics") or {})
    finish_metrics = metrics.get("finish_position") or {}
    lap_metrics = metrics.get("neural_lap_time_forecast") or {}
    rank_metrics = finish_metrics.get("ranking") or metrics.get("win_probability_ranking") or {}

    def pct(value):
        value = safe_float(value)
        return f"{value * 100:.1f}%" if value is not None else "n/a"

    def num(value, digits=2):
        value = safe_float(value)
        return f"{value:.{digits}f}" if value is not None else "n/a"

    quality_lines = [
        f"- Finish-position MAE: {num(finish_metrics.get('mae'))}; RMSE: {num(finish_metrics.get('rmse'))}",
        f"- Neural lap-time MAE: {num(lap_metrics.get('mae_seconds'))}s; RMSE: {num(lap_metrics.get('rmse_seconds'))}s",
        f"- Backtest winner hit: {pct(rank_metrics.get('winner_hit'))}; top-3 recall: {pct(rank_metrics.get('top3_recall'))}; top-5 recall: {pct(rank_metrics.get('top5_recall'))}",
        f"- Win model AUC/Brier: {num((metrics.get('win') or {}).get('auc'), 3)} / {num((metrics.get('win') or {}).get('brier'), 3)}",
        f"- Podium model AUC/Brier: {num((metrics.get('podium') or {}).get('auc'), 3)} / {num((metrics.get('podium') or {}).get('brier'), 3)}",
    ] if metrics else ["- Model quality metrics unavailable until the next retrain."]

    regulation_notes = regulation_context.get("notes", []) or []
    regulation_text = "\n".join(f"- {note}" for note in regulation_notes[:2]) if regulation_notes else "- No special regulation modifier beyond normal model traits."

    briefing = f"""# {title}

Generated: {now_local().strftime("%A, %d %B %Y, %I:%M %p %Z")}

## Event

- Target: {title_prefix}
- Start: {start_str}
- Circuit: {profile['circuit']}
- Location: {profile['city']}, {profile['country']}

## Prediction

{top_prediction}

## Track and weather

- Key car trait: {profile['car_trait']}
- Track profile: {profile['speed_profile']}
- Overtaking: {profile['overtaking']}
- Tyre stress: {profile['tyre_stress']}
- Safety car/DNF risk proxy: {profile['safety_car']}
- Weather: {weather['temperature']}, rain {weather['rain']}, wind {weather['wind']}
- Weather impact: {weather['impact']}

## Strategy

- Baseline: {profile['strategy_bias']}
- Pit window: {pit_window_from_profile(profile, weather)}
- Main risk: tyre drop-off, safety-car timing, traffic after pit stop, and weather crossover.

## Team fit

{team_text}

## Upgrade impact

{chr(10).join(upgrade_lines)}

## Regulation context

Era: {regulation_context.get('era')}

{regulation_text}

## Main model signals

{chr(10).join(model_lines)}

## Model accuracy audit

{chr(10).join(quality_lines)}

## Source status

{chr(10).join(source_lines)}

---

Predictions are estimates, not guaranteed race results.
"""
    return title, briefing


def save_markdown(event, briefing):
    BRIEFINGS_DIR.mkdir(exist_ok=True)
    date = event["start"].strftime("%Y-%m-%d")
    slug = make_slug(event["title"])
    path = BRIEFINGS_DIR / f"{date}-{slug}.md"
    path.write_text(briefing, encoding="utf-8")
    return path


def save_run_status(status, details):
    BRIEFINGS_DIR.mkdir(exist_ok=True)
    path = BRIEFINGS_DIR / "latest-run-status.md"
    path.write_text(f"# F1 Race Intel Run Status\n\nGenerated: {now_local().strftime('%A, %d %B %Y, %I:%M %p %Z')}\n\nStatus: {status}\n\n## Details\n\n{details}\n", encoding="utf-8")
    return path


def update_index(event, race, profile, weather, markdown_path, title, top10, team_fit, prediction_model, upgrade_context, regulation_context, calendar_context):
    index_path = BRIEFINGS_DIR / "index.json"
    entry = {
        "title": title,
        "path": str(markdown_path.relative_to(BASE_DIR)).replace("\\", "/"),
        "generated": now_local().strftime("%Y-%m-%d %H:%M %Z"),
        "generated_iso": now_local().isoformat(),
        "start_iso": event["start"].isoformat(),
        "start": event["start"].strftime("%A, %d %B %Y, %I:%M %p %Z"),
        "event_title": event["title"],
        "location": event["location"],
        "jolpica_race": race,
        "circuit": profile["circuit"],
        "city": profile["city"],
        "country": profile["country"],
        "circuit_key": profile["circuit_key"],
        "meeting_key": profile["meeting_key"],
        "track_type": profile["track_type"],
        "dominance": profile["dominance"],
        "speed_profile": profile["speed_profile"],
        "car_trait": profile["car_trait"],
        "overtaking": profile["overtaking"],
        "tyre_stress": profile["tyre_stress"],
        "safety_car": profile["safety_car"],
        "strategy_bias": profile["strategy_bias"],
        "pit_window": pit_window_from_profile(profile, weather),
        "setup": profile["setup"],
        "team_fit": team_fit,
        "weather": weather,
        "top10": top10,
        "prediction_model": prediction_model,
        "upgrade_context": upgrade_context,
        "regulation_context": regulation_context,
        "official_calendar_context": calendar_context,
        "prompt_requirement_checklist": PROMPT_REQUIREMENT_CHECKLIST,
        "dynamic_track_source": profile["dynamic_track_source"],
        "dynamic_track_metrics": profile["dynamic_track_metrics"],
        "dynamic_reasons": profile["dynamic_reasons"],
    }
    if index_path.exists():
        try:
            data = json.loads(index_path.read_text(encoding="utf-8"))
            briefings = data.get("briefings", []) if isinstance(data, dict) else data
            if not isinstance(briefings, list):
                briefings = []
        except Exception:
            briefings = []
    else:
        briefings = []

    briefings = [x for x in briefings if x.get("path") != entry["path"]]
    briefings.insert(0, entry)
    briefings = briefings[:60]
    index_path.write_text(json.dumps({"briefings": briefings}, indent=2, ensure_ascii=False), encoding="utf-8")
    return index_path


def save_debug(payload):
    path = DATA_CACHE_DIR / "latest-model-debug.json"
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    return path


def md_value(value, fallback="-"):
    if value is None or value == "":
        return fallback
    return str(value)


def md_num(value, digits=3, fallback="-"):
    value = safe_float(value)
    if value is None:
        return fallback
    return f"{value:.{digits}f}"


def md_pct(value, fallback="-"):
    value = safe_float(value)
    if value is None:
        return fallback
    return f"{value * 100:.1f}%"


def metric_rows_for_report(metrics):
    rows = []
    for target in ["win", "podium", "top10"]:
        item = metrics.get(target) or {}
        rows.append(f"| {target} | AUC | {md_num(item.get('auc'))} |")
        rows.append(f"| {target} | Brier | {md_num(item.get('brier'))} |")
        rows.append(f"| {target} | Validation rows | {md_value(item.get('validation_rows'))} |")

    finish = metrics.get("finish_position") or {}
    rows.extend([
        f"| finish_position | MAE | {md_num(finish.get('mae'))} |",
        f"| finish_position | RMSE | {md_num(finish.get('rmse'))} |",
        f"| finish_position | Validation rows | {md_value(finish.get('validation_rows'))} |",
    ])
    ranking = finish.get("ranking") or metrics.get("win_probability_ranking") or {}
    for key in ["winner_hit", "top3_recall", "top5_recall", "top10_recall", "exact_position_accuracy"]:
        rows.append(f"| ranking | {key} | {md_pct(ranking.get(key))} |")
    rows.append(f"| ranking | mean_position_error | {md_num(ranking.get('mean_position_error'))} |")

    lap = metrics.get("neural_lap_time_forecast") or {}
    rows.extend([
        f"| neural_lap_time_forecast | MAE seconds | {md_num(lap.get('mae_seconds'))} |",
        f"| neural_lap_time_forecast | RMSE seconds | {md_num(lap.get('rmse_seconds'))} |",
        f"| neural_lap_time_forecast | Validation rows | {md_value(lap.get('validation_rows'))} |",
    ])
    if lap.get("status"):
        rows.append(f"| neural_lap_time_forecast | Status | {md_value(lap.get('status'))} |")
    return rows


def race_line(label, race):
    if not race:
        return f"- {label}: -"
    return (
        f"- {label}: {md_value(race.get('race_id'))} | {md_value(race.get('race_name'))} | "
        f"{md_value(race.get('status'))} | scheduled {md_value(race.get('scheduled_at'))}"
    )


def save_model_status_report(bundle=None, mode=None, payloads=None, errors=None):
    meta = read_model_meta()
    decision = (bundle or {}).get("training_decision") or model_retrain_status(False)
    readiness = decision.get("readiness") or latest_result_readiness()
    metrics = (bundle or {}).get("metrics") or meta.get("metrics") or {}
    feature_columns = (bundle or {}).get("feature_columns") or meta.get("feature_columns") or []
    bundle_size_mb = MODEL_BUNDLE_PATH.stat().st_size / (1024 * 1024) if MODEL_BUNDLE_PATH.exists() else None
    selected_targets = payloads or []

    action = (bundle or {}).get("training_action") or meta.get("training_action") or decision.get("action")
    reasons = (bundle or {}).get("training_decision", {}).get("reasons") or meta.get("training_reasons") or decision.get("reasons") or []
    reason_text = ", ".join(reasons) if reasons else "none"
    target_lines = [
        f"- {payload.get('target_type')}: {payload.get('event', {}).get('title')} ({payload.get('event', {}).get('start')})"
        for payload in selected_targets
    ] or ["- No Sprint/Race target generated in this run."]
    error_lines = [f"- {error}" for error in (errors or [])] or ["- None"]

    content = f"""# F1 Race Intel Model Status

Generated: {now_local().strftime("%A, %d %B %Y, %I:%M %p %Z")}

This file is regenerated by the workflow on every successful run. It records the latest model version, accuracy audit, result-readiness state, and automatic/manual workflow behavior.

## Current Model

- Schema version: `{MODEL_SCHEMA_VERSION}`
- Training action this run: `{md_value(action)}`
- Retrain decision before this run: `{md_value(decision.get('action'))}`
- Retrain reasons: {reason_text}
- Trained at: {md_value((bundle or {}).get('trained_at') or meta.get('trained_at'))}
- ML start year: {md_value((bundle or {}).get('ml_start_year') or meta.get('ml_start_year'))}
- Latest completed race included by model: `{md_value((bundle or {}).get('latest_completed_race_id') or meta.get('latest_completed_race_id'))}`
- Latest completed race currently available in API: `{md_value(readiness.get('latest_completed_race_id'))}`
- Raw training rows: {md_value(meta.get('rows_raw'))}
- Feature rows: {md_value(meta.get('rows_features'))}
- Feature count: {len(feature_columns)}
- Model bundle size: {md_num(bundle_size_mb, 1)} MB
- Backfill used this run: {md_value(meta.get('backfill_used_this_run', BACKFILL_BUDGET.used))}

## Result Readiness

- Readiness status: `{md_value(readiness.get('status'))}`
- Final-results delay: {md_value(readiness.get('final_results_delay_hours'))} hours after the scheduled GP race start
{race_line("Latest API result", readiness.get("latest_completed_race"))}
{race_line("Waiting for delay", readiness.get("waiting_for_delay"))}
{race_line("Past cutoff but API still missing results", readiness.get("waiting_for_api_results"))}
{race_line("Next race", readiness.get("next_race"))}

Retrain rule: the workflow does not train on a just-finished GP until the configured delay has passed and Jolpica returns actual `Results` rows. After the cutoff, the final-result check bypasses the stale HTTP cache so newly published results can trigger retraining on the next scheduled run.

## Accuracy Audit

| Target | Metric | Value |
| --- | --- | --- |
{chr(10).join(metric_rows_for_report(metrics))}

## Last Run Output

- Output mode: `{md_value(mode)}`
- Selected targets:
{chr(10).join(target_lines)}
- Errors:
{chr(10).join(error_lines)}

## Automatic Workflow Behavior

- Runs daily and more often across race weekends, including Monday checks for post-race results.
- Restores FastF1, OpenF1/HTTP, full-race, and saved-model caches.
- Installs dependencies, compiles `f1_briefing.py`, and runs unit tests before generating outputs.
- Checks whether a new completed GP result exists in Jolpica after `FINAL_RESULTS_DELAY_HOURS`.
- Retrains automatically when the model is missing, the schema changes, `FORCE_RETRAIN=true`, or a new completed GP result is available.
- Uses official Formula 1 live timing first, then optional OpenF1 free historical sessions as an extra timing cross-check when reachable.
- Waits and keeps the current model when a GP is just over but the result delay has not passed or the API still has no final `Results` rows.
- Generates Sprint/Race-only predictions, updates briefings, `briefings/index.json`, `data_cache/latest-model-debug.json`, and this file.
- Sends email/GitHub issue output only when the notification gate opens or `FORCE_NOTIFY=true`.
- Uploads generated artifacts for inspection.

## Manual Workflow Controls

- `force_retrain`: retrain even if no new race result exists.
- `full_data_backfill_limit`: fetch more uncached historical races in that run.
- `lookahead_days`: search further ahead in the calendar.
- `output_mode`: choose `auto`, `weekend`, `today`, or `next`.
- `send_email`: allow or suppress email sending.
- `force_notify`: send email/GitHub issue output outside the normal notification window.
- `notification_window_hours`: change how close to the event notifications are allowed.

Local equivalent: run `.venv/bin/python f1_briefing.py --force-retrain` or set the same environment variables before running.
"""
    MODEL_STATUS_PATH.write_text(content, encoding="utf-8")
    return MODEL_STATUS_PATH


def markdown_to_email_html(markdown):
    def esc_html(value):
        return str(value or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    lines = str(markdown or "").splitlines()
    html = []
    list_open = False

    def close_list():
        nonlocal list_open
        if list_open:
            html.append("</ul>")
            list_open = False

    for raw in lines:
        line = raw.strip()
        if not line:
            close_list()
            continue
        if line.startswith("# "):
            close_list()
            html.append(f"<h1>{esc_html(line[2:])}</h1>")
        elif line.startswith("## "):
            close_list()
            html.append(f"<h2>{esc_html(line[3:])}</h2>")
        elif line.startswith("- "):
            if not list_open:
                html.append("<ul>")
                list_open = True
            html.append(f"<li>{esc_html(line[2:])}</li>")
        elif re.match(r"^\d+\.\s", line):
            close_list()
            html.append(f"<p class='prediction'>{esc_html(line)}</p>")
        elif line.startswith("---"):
            close_list()
            html.append("<hr>")
        else:
            close_list()
            html.append(f"<p>{esc_html(line)}</p>")
    close_list()
    body = "\n".join(html)
    return f"""<html><body>
<style>
body{{margin:0;background:#08080a;color:#f8f5ef;font-family:Arial,Helvetica,sans-serif;line-height:1.55}}
.wrap{{max-width:760px;margin:0 auto;padding:28px}}
h1{{font-size:30px;line-height:1.05;margin:0 0 18px;color:#fff;text-transform:uppercase}}
h2{{font-size:18px;margin:28px 0 10px;color:#ff3b30}}
p,.prediction,li{{font-size:14px;color:#e7dfd6}}
.prediction{{padding:10px 12px;border-left:3px solid #e10600;background:#151518;border-radius:6px}}
ul{{padding-left:20px}}
hr{{border:0;border-top:1px solid #34343a;margin:26px 0}}
</style>
<div class="wrap">{body}</div>
</body></html>"""


def send_email(subject, body):
    if not EMAIL_ENABLED:
        print("Email disabled.")
        return False
    try:
        msg = MIMEMultipart("alternative")
        msg["From"] = EMAIL_ADDRESS
        msg["To"] = EMAIL_TO
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain", "utf-8"))
        msg.attach(MIMEText(markdown_to_email_html(body), "html", "utf-8"))
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(EMAIL_ADDRESS, EMAIL_APP_PASSWORD)
            server.send_message(msg)
        print("Email sent.")
        return True
    except Exception as error:
        print(f"Email failed: {error}")
        return False


def github_api(method, endpoint, payload=None):
    if not GITHUB_REPOSITORY or not GITHUB_TOKEN:
        print("GitHub API variables missing. Skipping issue update.")
        return None
    url = f"https://api.github.com/repos/{GITHUB_REPOSITORY}{endpoint}"
    headers = {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    response = requests.request(method, url, headers=headers, json=payload, timeout=30)
    if response.status_code >= 400:
        print(f"GitHub API error {response.status_code}: {response.text}")
        response.raise_for_status()
    return response.json() if response.text else None


def ensure_issue_label():
    try:
        github_api("POST", "/labels", {"name": "f1-briefing", "description": "Automated F1 briefing", "color": "e10600"})
    except requests.HTTPError as error:
        if error.response is not None and error.response.status_code == 422:
            return
        raise


def create_or_update_issue(title, body):
    ensure_issue_label()
    existing = github_api("GET", "/issues?state=open&labels=f1-briefing&per_page=100")
    if existing:
        for issue in existing:
            if issue.get("title") == title:
                github_api("PATCH", f"/issues/{issue['number']}", {"body": body})
                print(f"Updated issue #{issue['number']}.")
                return
    github_api("POST", "/issues", {"title": title, "body": body, "labels": ["f1-briefing"]})
    print("Created issue.")


def commit_and_push(paths):
    paths = [Path(p) for p in paths if p]
    subprocess.run(["git", "config", "user.name", "github-actions[bot]"], check=True)
    subprocess.run(["git", "config", "user.email", "41898282+github-actions[bot]@users.noreply.github.com"], check=True)

    for path in paths:
        if path.exists():
            subprocess.run(["git", "add", str(path)], check=True)

    # Include full-race cache files generated this run.
    if FULL_RACE_CACHE_DIR.exists():
        subprocess.run(["git", "add", str(FULL_RACE_CACHE_DIR)], check=True)

    diff = subprocess.run(["git", "diff", "--cached", "--quiet"])
    if diff.returncode == 0:
        print("No file changes to commit.")
        return
    subprocess.run(["git", "commit", "-m", "Update F1 full-data model and briefing"], check=True)
    subprocess.run(["git", "push"], check=True)
    print("Committed and pushed generated data.")


def write_skip_outputs(subject, details):
    status_path = save_run_status("Skipped", details)
    safe_step("Commit status", commit_and_push, [status_path])
    safe_step("Issue status", create_or_update_issue, "F1 Race Intel Status", details)
    safe_step("Email status", send_email, subject, details)


def build_single_output_payload(event, bundle):
    """
    Builds one compact output payload for a Sprint or Race target.

    Practice, qualifying, sprint qualifying, FastF1, F1 timing, weather, upgrades,
    and historical data may be used as inputs, but only Sprint/Race targets are
    exposed as output.
    """
    target_type = classify_output_target_event(event)
    if target_type not in {"sprint", "race"}:
        return {
            "ok": False,
            "event": event,
            "error": f"Skipping non-output event: {event.get('title')}",
        }

    race = find_best_race(event)
    if not race:
        return {
            "ok": False,
            "event": event,
            "error": f"Could not match Jolpica race for {event.get('title')}",
        }

    season = safe_int(race.get("season")) or event["start"].year
    round_no = race.get("round")

    current_round_data = fetch_round_data_cached(
        season,
        round_no,
        allow_backfill=False,
        force_fetch=True,
        race=race,
        training_mode=False,
    )

    driver_standings, constructor_standings, standings_context = fetch_latest_available_standings_with_fallback(season)
    last_results = fetch_last_results(season)
    historical_records = fetch_historical_same_circuit(race, years_back=5)

    if not driver_standings:
        return {
            "ok": False,
            "event": event,
            "race": race,
            "error": f"Matched {race.get('raceName')} but driver standings are unavailable.",
        }

    drivers = standings_to_drivers(driver_standings)
    weather = fetch_weather_for_race(race, event["start"])
    historical_weather = safe_step("Historical weather", fetch_historical_weather_summary, race, 5) or {}
    profile = infer_track_profile(race, historical_records, weather, historical_weather)
    regulation_context = regulation_context_for_season(season) if F1_REGULATIONS_ENABLED else {"era": "disabled", "notes": [], "boost_traits": []}
    upgrade_context = fetch_upgrade_package_context(race, drivers, profile, weather, regulation_context)
    calendar_context = official_calendar_context_for_season(season, race)

    stage, stage_label = get_prediction_stage(current_round_data, event["start"])

    # Make the target explicit. The same round data may contain qualifying or sprint results,
    # but output is restricted to sprint/race.
    if target_type == "sprint":
        stage_label = f"Sprint prediction, {stage_label}"
    elif target_type == "race":
        stage_label = f"Race prediction, {stage_label}"

    ml_outputs, ml_debug = ml_predict_probabilities(drivers, race, current_round_data, bundle)
    timing_scores = safe_step("External timing enhancement", external_timing_enhancement_scores, race, drivers) or {"provider_status": "failed"}
    fastf1_scores = safe_step("FastF1 enhancement", fastf1_enhancement_scores, season, round_no) or {"sessions_loaded": []}

    top10_text, top10, prediction_model = rank_prediction(
        drivers=drivers,
        constructor_standings=constructor_standings,
        last_results=last_results,
        current_round_data=current_round_data,
        historical_records=historical_records,
        profile=profile,
        weather_summary=weather,
        ml_outputs=ml_outputs,
        fastf1_scores=fastf1_scores,
        timing_scores=timing_scores,
        upgrade_context=upgrade_context,
        regulation_context=regulation_context,
        calendar_context=calendar_context,
        season=season,
        current_round=round_no,
        stage=stage,
    )

    prediction_model["prediction_stage_label"] = stage_label
    prediction_model["output_target_type"] = target_type
    prediction_model["ml_model_loaded"] = bool(bundle)
    prediction_model["ml_model_meta"] = {
        "trained_at": bundle.get("trained_at") if bundle else None,
        "latest_completed_race_id": bundle.get("latest_completed_race_id") if bundle else None,
        "metrics": bundle.get("metrics") if bundle else None,
    }

    team_fit = get_dynamic_team_fit(top10, constructor_standings)
    title, briefing = generate_briefing(
        event,
        race,
        profile,
        weather,
        top10_text,
        prediction_model,
        team_fit,
        upgrade_context,
        regulation_context,
        calendar_context,
    )

    return {
        "ok": True,
        "event": event,
        "race": race,
        "season": season,
        "round_no": round_no,
        "target_type": target_type,
        "title": title,
        "briefing": briefing,
        "profile": profile,
        "weather": weather,
        "historical_weather": historical_weather,
        "top10_text": top10_text,
        "top10": top10,
        "team_fit": team_fit,
        "prediction_model": prediction_model,
        "ml_debug": ml_debug,
        "timing_scores": timing_scores,
        "fastf1_scores": fastf1_scores,
        "upgrade_context": upgrade_context,
        "regulation_context": regulation_context,
        "calendar_context": calendar_context,
        "standings_context": standings_context,
    }


def strip_briefing_heading(briefing):
    lines = str(briefing or "").splitlines()
    if lines and lines[0].startswith("# "):
        lines = lines[1:]
    # Remove duplicate generated line from subsections; combined report already has one.
    cleaned = []
    for line in lines:
        if line.startswith("Generated:"):
            continue
        cleaned.append(line)
    return "\n".join(cleaned).strip()


def combine_weekend_briefings(report_event, payloads, mode):
    if not payloads:
        return "F1 Race Intel: No Sprint/Race output target found", ""

    if len(payloads) == 1:
        return payloads[0]["title"], payloads[0]["briefing"]

    targets = "\n".join(
        f"- {payload['target_type'].title()}: {payload['event']['title']} at {payload['event']['start'].strftime('%A, %d %B %Y, %I:%M %p %Z')}"
        for payload in payloads
    )

    sections = []
    for payload in payloads:
        heading = f"## {payload['target_type'].title()} Target: {payload['event']['title']}"
        sections.append(f"{heading}\n\n{strip_briefing_heading(payload['briefing'])}")

    title = report_event["title"]
    briefing = f"""# {title}

Generated: {now_local().strftime("%A, %d %B %Y, %I:%M %p %Z")}

Output mode: {mode}

This briefing deliberately outputs only Sprint and Race predictions. Practice, Qualifying, Sprint Qualifying, weather, upgrades, F1 timing, OpenF1, FastF1, Jolpica, track traits, regulations, and historical cache data are used as supporting inputs only.

## Output targets

{targets}

---

{chr(10).join(sections)}

---

Generated by F1 Race Intel. Predictions are model estimates, not guaranteed race results.
"""
    return title, briefing


def run(force_retrain=False):
    ensure_dirs()
    require_env_vars()

    bundle = safe_step("Train/load full-data ML model", train_ml_model, force_retrain)
    if not bundle:
        bundle = load_ml_bundle()

    calendar = fetch_ics_calendar()
    mode, target_events = select_output_events(calendar)
    model_status_path = save_model_status_report(bundle, mode=mode)

    if not target_events:
        details = (
            f"No Sprint/Race output target selected.\\n\\n"
            f"Output mode: {mode}\\n"
            f"Reason: Manual runs use weekend mode; scheduled runs use today mode. "
            f"Practice, Qualifying, and Sprint Qualifying are ignored as direct outputs."
        )
        print(details)
        status_path = save_run_status("Skipped", details)
        model_status_path = save_model_status_report(bundle, mode=mode)
        safe_step("Commit status", commit_and_push, [status_path, model_status_path])
        return

    print("Selected output targets:")
    for event in target_events:
        print(f"- {event.get('target_type')}: {event.get('title')} at {event.get('start')}")

    payloads = []
    errors = []

    for event in target_events:
        payload = build_single_output_payload(event, bundle)
        if payload.get("ok"):
            payloads.append(payload)
        else:
            errors.append(payload.get("error", "Unknown target generation error"))
            print(f"Target skipped: {payload.get('error')}")

    if not payloads:
        details = "No Sprint/Race target could be generated.\\n\\n" + "\\n".join(f"- {error}" for error in errors)
        print(details)
        status_path = save_run_status("Skipped", details)
        model_status_path = save_model_status_report(bundle, mode=mode, errors=errors)
        safe_step("Commit status", commit_and_push, [status_path, model_status_path])
        return

    report_event = make_report_event([payload["event"] for payload in payloads], mode)
    title, briefing = combine_weekend_briefings(report_event, payloads, mode)

    primary = payloads[-1] if any(payload["target_type"] == "race" for payload in payloads) else payloads[0]
    markdown_path = save_markdown(report_event, briefing)
    index_path = update_index(
        report_event,
        primary["race"],
        primary["profile"],
        primary["weather"],
        markdown_path,
        title,
        primary["top10"],
        primary["team_fit"],
        primary["prediction_model"],
        primary["upgrade_context"],
        primary["regulation_context"],
        primary["calendar_context"],
    )

    generated_targets = ", ".join(f"{payload['target_type']}={payload['event']['title']}" for payload in payloads)
    status_details = (
        f"Generated Sprint/Race-only F1 briefing.\\n\\n"
        f"Output mode: {mode}\\n"
        f"Targets: {generated_targets}\\n"
        f"Backfill used this run: {BACKFILL_BUDGET.used}\\n"
        f"Errors: {'; '.join(errors) if errors else 'None'}"
    )
    status_path = save_run_status("Success", status_details)

    debug_path = save_debug({
        "generated_at": now_local().isoformat(),
        "output_mode": mode,
        "selected_targets": [
            {
                "title": payload["event"].get("title"),
                "target_type": payload["target_type"],
                "start": payload["event"].get("start"),
            }
            for payload in payloads
        ],
        "primary_target": primary["event"],
        "race": primary["race"],
        "payloads": payloads,
        "errors": errors,
        "notification_gate": notification_status_for_events([payload["event"] for payload in payloads]),
        "backfill": {
            "limit": BACKFILL_BUDGET.limit,
            "used": BACKFILL_BUDGET.used,
            "races": BACKFILL_BUDGET.fetched,
        },
    })
    model_status_path = save_model_status_report(bundle, mode=mode, payloads=payloads, errors=errors)

    paths = [
        markdown_path,
        index_path,
        status_path,
        debug_path,
        model_status_path,
        MODEL_BUNDLE_PATH,
        MODEL_META_PATH,
        DATA_CACHE_DIR / "ml_full_race_results_raw.csv",
        DATA_CACHE_DIR / "ml_full_race_features.csv",
    ]

    safe_step("Commit generated files", commit_and_push, paths)
    maybe_send_outputs(title, briefing, [payload["event"] for payload in payloads])

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--force-retrain", action="store_true")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    force = args.force_retrain or os.getenv("FORCE_RETRAIN", "false").lower() == "true"
    run(force_retrain=force)
