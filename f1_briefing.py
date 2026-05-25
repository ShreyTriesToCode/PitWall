import os
import re
import json
import time
import gzip
import io
import zlib
import base64
import random
import smtplib
import argparse
import subprocess
import sqlite3
from concurrent.futures import ThreadPoolExecutor, as_completed, TimeoutError
from functools import lru_cache
from pathlib import Path
from datetime import datetime, timedelta, timezone
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from hashlib import sha256

import joblib
import numpy as np
import pandas as pd
import requests
from icalendar import Calendar, Event
from dateutil import tz
from sklearn.ensemble import ExtraTreesClassifier, ExtraTreesRegressor, RandomForestClassifier, RandomForestRegressor, HistGradientBoostingClassifier, HistGradientBoostingRegressor
from sklearn.metrics import roc_auc_score, brier_score_loss, mean_absolute_error, ndcg_score
from sklearn.neural_network import MLPRegressor
from sklearn.pipeline import make_pipeline
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler
from scipy.stats import spearmanr

try:
    import fastf1
except Exception:
    fastf1 = None

try:
    import lightgbm as lgb
except Exception:
    lgb = None

try:
    import xgboost as xgb
except Exception:
    xgb = None

try:
    import shap
except Exception:
    shap = None

try:
    from pitwall.data.f1db import f1db_metadata, f1db_status
    from pitwall.data.fia_documents import fetch_fia_document_text as pitwall_fetch_fia_document_text
    from pitwall.data.relbench_f1 import relbench_metadata, relbench_status
    from pitwall.features import strategy as pitwall_strategy
    from pitwall.models import contract as pitwall_contract
    from pitwall.models import simulation as pitwall_simulation
    from pitwall import storage as pitwall_storage
except Exception:
    f1db_metadata = None
    f1db_status = None
    pitwall_fetch_fia_document_text = None
    relbench_metadata = None
    relbench_status = None
    pitwall_strategy = None
    pitwall_contract = None
    pitwall_simulation = None
    pitwall_storage = None


F1_ICS_URL = os.getenv("F1_ICS_URL", "").strip()

EMAIL_ENABLED = os.getenv("EMAIL_ENABLED", "false").lower() == "true"
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
FULL_DATA_BACKFILL_LIMIT = int(os.getenv("FULL_DATA_BACKFILL_LIMIT", "0"))
JOLPICA_REQUEST_SLEEP = float(os.getenv("JOLPICA_REQUEST_SLEEP", "1.2"))

BASE_DIR = Path(__file__).resolve().parent
BRIEFINGS_DIR = BASE_DIR / "briefings"
DATA_CACHE_DIR = BASE_DIR / "data_cache"
HTTP_CACHE_DIR = Path(os.getenv("HTTP_CACHE_DIR", DATA_CACHE_DIR / "http"))
FULL_RACE_CACHE_DIR = Path(os.getenv("FULL_RACE_CACHE_DIR", DATA_CACHE_DIR / "full_races"))
FASTF1_CACHE_DIR = Path(os.getenv("FASTF1_CACHE_DIR", BASE_DIR / "fastf1_cache"))
MODEL_DIR = Path(os.getenv("MODEL_DIR", BASE_DIR / "models" / "saved_models"))
MODEL_ARTIFACTS_DIR = Path(os.getenv("MODEL_ARTIFACTS_DIR", BASE_DIR / "model_artifacts"))
SOURCE_REGISTRY_DIR = DATA_CACHE_DIR / "source_registry"
FIA_DOCUMENT_CACHE_DIR = Path(os.getenv("FIA_DOCUMENT_CACHE_DIR", DATA_CACHE_DIR / "fia-documents"))
_FIA_REFRESHED_SEASONS = set()

MODEL_BUNDLE_PATH = MODEL_DIR / "f1_hybrid_full_data_bundle.pkl"
MODEL_META_PATH = MODEL_DIR / "f1_hybrid_full_data_meta.json"
MODEL_STATUS_PATH = BASE_DIR / "MODEL_STATUS.md"
MODEL_SCHEMA_VERSION = "2026.05-high-accuracy-v5"
PREDICTION_DATA_VERSION = "2026.05-race-control-contract-v2"
MODEL_STATUS_JSON_PATH = DATA_CACHE_DIR / "model-status.json"
BACKTEST_HISTORY_PATH = DATA_CACHE_DIR / "backtest-history.json"
MODEL_CORRECTIONS_PATH = DATA_CACHE_DIR / "model_corrections.json"
PITWALL_DB_PATH = Path(os.getenv("PITWALL_DB_PATH", DATA_CACHE_DIR / "pitwall.db"))
FEATURES_DIR = DATA_CACHE_DIR / "features"
MODEL_INPUT_SNAPSHOT_DIR = DATA_CACHE_DIR / "model-input-snapshots"

JOLPICA_BASE = "https://api.jolpi.ca/ergast/f1"
F1_LIVE_TIMING_STATIC_BASE = os.getenv("F1_LIVE_TIMING_STATIC_BASE", "https://livetiming.formula1.com/static").rstrip("/")
OPENF1_BASE = os.getenv("OPENF1_BASE", "https://api.openf1.org/v1").rstrip("/")
OPENF1_ENABLED = os.getenv("OPENF1_ENABLED", "true").lower() == "true"
OPENF1_ACCESS_TOKEN = os.getenv("OPENF1_ACCESS_TOKEN", os.getenv("OPENF1_TOKEN", "")).strip()
OPENF1_USERNAME = os.getenv("OPENF1_USERNAME", "").strip()
OPENF1_PASSWORD = os.getenv("OPENF1_PASSWORD", "").strip()
OPENF1_REQUEST_SLEEP = float(os.getenv("OPENF1_REQUEST_SLEEP", "0.45"))
OPENF1_OPTIONAL_ONLY = os.getenv("OPENF1_OPTIONAL_ONLY", "true").lower() == "true"
UPGRADES_ENABLED = os.getenv("UPGRADES_ENABLED", "true").lower() == "true"
F1_REGULATIONS_ENABLED = os.getenv("F1_REGULATIONS_ENABLED", "true").lower() == "true"
OFFICIAL_CALENDAR_ENABLED = os.getenv("OFFICIAL_CALENDAR_ENABLED", "true").lower() == "true"
FIA_TECH_UPDATE_BASE = os.getenv("FIA_TECH_UPDATE_BASE", "https://www.fia.com/news").rstrip("/")
OFFICIAL_F1_CALENDAR_URL = os.getenv("OFFICIAL_F1_CALENDAR_URL", "https://www.formula1.com/en/racing/{year}")
TARGET_SEASON = os.getenv("TARGET_SEASON", "auto").strip()
SOURCE_DISCOVERY_ENABLED = os.getenv("SOURCE_DISCOVERY_ENABLED", "true").lower() == "true"
REFRESH_SOURCE_REGISTRY = os.getenv("REFRESH_SOURCE_REGISTRY", "false").lower() == "true"
FIA_DOCUMENTS_ENABLED = os.getenv("FIA_DOCUMENTS_ENABLED", "true").lower() == "true"
FIA_DOCUMENTS_BASE_URL = os.getenv("FIA_DOCUMENTS_BASE_URL", "https://www.fia.com/documents/championships/fia-formula-one-world-championship-14").rstrip("/")
FIA_DOCUMENTS_SEASON_URL = os.getenv("FIA_DOCUMENTS_SEASON_URL", "").strip()
REFRESH_FIA_DOCUMENTS = os.getenv("REFRESH_FIA_DOCUMENTS", "false").lower() == "true"
FORCE_REPARSE_FIA_DOCUMENTS = os.getenv("FORCE_REPARSE_FIA_DOCUMENTS", "false").lower() == "true"
FORCE_REDOWNLOAD_FIA_DOCUMENTS = os.getenv("FORCE_REDOWNLOAD_FIA_DOCUMENTS", "false").lower() == "true"
FIA_DOCUMENT_CACHE_TTL_MINUTES = int(os.getenv("FIA_DOCUMENT_CACHE_TTL_MINUTES", "60"))
FIA_REQUEST_SLEEP_SECONDS = float(os.getenv("FIA_REQUEST_SLEEP_SECONDS", "1.0"))
MAX_FIA_DOCUMENTS_PER_RUN = int(os.getenv("MAX_FIA_DOCUMENTS_PER_RUN", "0"))
MAX_FIA_PDFS_DOWNLOAD_PER_RUN = int(os.getenv("MAX_FIA_PDFS_DOWNLOAD_PER_RUN", "0"))
KEEP_FIA_PDFS = os.getenv("KEEP_FIA_PDFS", "false").lower() == "true"
FIA_DOCUMENT_USER_AGENT = os.getenv("FIA_DOCUMENT_USER_AGENT", "Mozilla/5.0 (compatible; PitWall/3.0; +https://github.com/ShreyTriesToCode/PitWall)")
FIA_DOCUMENT_REFERER = os.getenv("FIA_DOCUMENT_REFERER", FIA_DOCUMENTS_BASE_URL)
FIA_DOCUMENT_STRICT_DOWNLOADS = os.getenv("FIA_DOCUMENT_STRICT_DOWNLOADS", "false").lower() == "true"
FORMULA1_CALENDAR_BASE_URL = os.getenv("FORMULA1_CALENDAR_BASE_URL", "https://www.formula1.com/en/racing").rstrip("/")
FORMULA1_SEASON_URL = os.getenv("FORMULA1_SEASON_URL", "").strip()
JOLPICA_ENABLED = os.getenv("JOLPICA_ENABLED", "true").lower() == "true"
FASTF1_ENABLED = os.getenv("FASTF1_ENABLED", "true").lower() == "true"
FASTF1_SESSION_LOAD_TIMEOUT_SECONDS = int(os.getenv("FASTF1_SESSION_LOAD_TIMEOUT_SECONDS", "90"))
SESSION_INGESTION_ENABLED = os.getenv("SESSION_INGESTION_ENABLED", "true").lower() == "true"
SESSION_RESULT_DELAY_MINUTES = int(os.getenv("SESSION_RESULT_DELAY_MINUTES", "30"))
PRACTICE_RESULT_DELAY_MINUTES = int(os.getenv("PRACTICE_RESULT_DELAY_MINUTES", "20"))
QUALIFYING_RESULT_DELAY_MINUTES = int(os.getenv("QUALIFYING_RESULT_DELAY_MINUTES", "30"))
SPRINT_QUALIFYING_RESULT_DELAY_MINUTES = int(os.getenv("SPRINT_QUALIFYING_RESULT_DELAY_MINUTES", "30"))
SPRINT_RESULT_DELAY_MINUTES = int(os.getenv("SPRINT_RESULT_DELAY_MINUTES", "45"))
RACE_RESULT_DELAY_HOURS = int(os.getenv("RACE_RESULT_DELAY_HOURS", "8"))
SESSION_RETRY_INTERVAL_MINUTES = int(os.getenv("SESSION_RETRY_INTERVAL_MINUTES", "20"))
MAX_SESSION_RETRIES = int(os.getenv("MAX_SESSION_RETRIES", "8"))
FORCE_SESSION_INGEST = os.getenv("FORCE_SESSION_INGEST", "false").lower() == "true"
TARGET_EVENT = os.getenv("TARGET_EVENT", "").strip()
TARGET_SESSION = os.getenv("TARGET_SESSION", "").strip()
DRY_RUN_SESSION_INGEST = os.getenv("DRY_RUN_SESSION_INGEST", "false").lower() == "true"
LIVE_TIMING_ENABLED = os.getenv("LIVE_TIMING_ENABLED", "true").lower() == "true"
LIVE_STALE_AFTER_SECONDS = int(os.getenv("LIVE_STALE_AFTER_SECONDS", "60"))
DISABLE_LIVE_MODE = os.getenv("DISABLE_LIVE_MODE", "false").lower() == "true"
TIMING_REPLAY_MODE_ALLOWED = os.getenv("TIMING_REPLAY_MODE_ALLOWED", "true").lower() == "true"
USE_SOCIAL_UPGRADE_SOURCES = os.getenv("USE_SOCIAL_UPGRADE_SOURCES", "false").lower() == "true"
UPGRADE_MAX_WEIGHT_PRE_RUNNING = float(os.getenv("UPGRADE_MAX_WEIGHT_PRE_RUNNING", "0.08"))
UPGRADE_MAX_WEIGHT_POST_PRACTICE = float(os.getenv("UPGRADE_MAX_WEIGHT_POST_PRACTICE", "0.05"))
UPGRADE_MAX_WEIGHT_POST_QUALIFYING = float(os.getenv("UPGRADE_MAX_WEIGHT_POST_QUALIFYING", "0.03"))
ENABLE_RACE_SIMULATION = os.getenv("ENABLE_RACE_SIMULATION", "true").lower() == "true"
RACE_SIMULATION_RUNS = int(os.getenv("RACE_SIMULATION_RUNS", "10000"))
GITHUB_ACTIONS_RACE_SIMULATION_RUNS = int(os.getenv("GITHUB_ACTIONS_RACE_SIMULATION_RUNS", "1000"))
TRAINING_MODE = os.getenv("TRAINING_MODE", "auto")
MODEL_TRAINING_MAX_SECONDS = int(os.getenv("MODEL_TRAINING_MAX_SECONDS", "900"))
ENABLE_FEATURE_ABLATION = os.getenv("ENABLE_FEATURE_ABLATION", "false").lower() == "true"
ENABLE_HYPERPARAMETER_SEARCH = os.getenv("ENABLE_HYPERPARAMETER_SEARCH", "false").lower() == "true"
MAX_TRAINING_RACES = os.getenv("MAX_TRAINING_RACES", "auto")
MODEL_LIGHT_MODE = os.getenv("MODEL_LIGHT_MODE", "false").lower() == "true"
LATEST_RUN_STATUS_PATH = Path(os.getenv("LATEST_RUN_STATUS_PATH", DATA_CACHE_DIR / "latest-run-status.json"))
USE_LAST_VALID_CONTRACT_ON_ERROR = os.getenv("USE_LAST_VALID_CONTRACT_ON_ERROR", "true").lower() == "true"
SKIP_NETWORK_TESTS = os.getenv("SKIP_NETWORK_TESTS", "true").lower() == "true"
SUPABASE_URL = os.getenv("SUPABASE_URL", "").strip()
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", os.getenv("SUPABASE_KEY", "")).strip()
UPGRADE_NEWS_URLS = [u.strip() for u in os.getenv("UPGRADE_NEWS_URLS", "").split(",") if u.strip()]
JOLPICA_HEADERS = {
    "User-Agent": "pitwall/3.0 cache-first full-data model",
    "Accept": "application/json",
}

FASTF1_SESSION_ORDER = ["R", "Q", "SQ", "S", "FP3", "FP2", "FP1"]
OPENF1_LAST_STATUS = {"status": "not_checked", "auth_required": False, "errors": []}

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
    "fia_starting_grid": "FIA starting grid",
    "fia_qualifying_classification": "FIA qualifying classification",
    "fia_sprint_classification": "FIA sprint classification",
    "fia_session_classification": "FIA session classification",
    "timing_car_performance": "official timing car performance",
    "fastf1_race_pace": "FastF1 clean-lap pace",
    "fastf1_consistency": "FastF1 consistency",
    "fastf1_tyre_stint": "FastF1 tyre/stint evidence",
}

SESSION_TYPE_ALIASES = {
    "practice 1": "fp1",
    "free practice 1": "fp1",
    "fp1": "fp1",
    "practice 2": "fp2",
    "free practice 2": "fp2",
    "fp2": "fp2",
    "practice 3": "fp3",
    "free practice 3": "fp3",
    "fp3": "fp3",
    "sprint qualifying": "sprint_qualifying",
    "sprint shootout": "sprint_qualifying",
    "sq": "sprint_qualifying",
    "sprint": "sprint",
    "qualifying": "qualifying",
    "grand prix": "race",
    "race": "race",
}

STAGE_ORDER = [
    "pre_weekend",
    "post_fp1",
    "post_fp2",
    "post_fp3",
    "post_sprint_qualifying",
    "post_sprint",
    "post_qualifying",
    "pre_race",
    "live_adjusted",
    "post_race_audited",
]

FEATURE_STAGE_MATRIX = {
    "historical_form": "pre_weekend",
    "constructor_form": "pre_weekend",
    "fia_upgrades": "pre_weekend",
    "pu_documents": "pre_weekend",
    "weather": "pre_weekend",
    "fp1_pace": "post_fp1",
    "fp2_pace": "post_fp2",
    "fp3_pace": "post_fp3",
    "sprint_qualifying_position": "post_sprint_qualifying",
    "sprint_result": "post_sprint",
    "qualifying_position": "post_qualifying",
    "final_grid": "pre_race",
    "live_timing": "live_adjusted",
    "race_result": "post_race_audited",
    "finish_position": "post_race_audited",
    "points": "post_race_audited",
    "is_win": "post_race_audited",
    "is_podium": "post_race_audited",
    "is_top10": "post_race_audited",
}


class BackfillBudget:
    def __init__(self, limit):
        self.limit = int(limit)
        self.used = 0
        self.fetched = []

    def can_fetch(self):
        if self.limit <= 0:
            return True
        return self.used < self.limit

    def mark(self, key):
        self.used += 1
        self.fetched.append(key)


BACKFILL_BUDGET = BackfillBudget(FULL_DATA_BACKFILL_LIMIT)
_RESULT_READINESS_CACHE = None


def ensure_dirs():
    for path in [
        BRIEFINGS_DIR,
        DATA_CACHE_DIR,
        HTTP_CACHE_DIR,
        FULL_RACE_CACHE_DIR,
        FASTF1_CACHE_DIR,
        MODEL_DIR,
        MODEL_ARTIFACTS_DIR,
        FEATURES_DIR,
        MODEL_INPUT_SNAPSHOT_DIR,
        SOURCE_REGISTRY_DIR,
        FIA_DOCUMENT_CACHE_DIR,
    ]:
        path.mkdir(parents=True, exist_ok=True)


def public_path(value):
    if value in (None, ""):
        return value
    text = str(value)
    try:
        path = Path(text)
        if path.is_absolute():
            try:
                return str(path.relative_to(BASE_DIR))
            except ValueError:
                return path.name
    except Exception:
        pass
    base = str(BASE_DIR)
    if base and base in text:
        return text.replace(base + os.sep, "").replace(base, "")
    return text


def sanitize_public_paths(value):
    """Strip absolute local workspace paths from generated public artifacts."""

    if isinstance(value, dict):
        return {key: sanitize_public_paths(val) for key, val in value.items()}
    if isinstance(value, list):
        return [sanitize_public_paths(item) for item in value]
    if isinstance(value, str) and str(BASE_DIR) in value:
        return public_path(value)
    return value


def init_pitwall_db():
    ensure_dirs()
    if pitwall_storage is None:
        raise RuntimeError("pitwall.storage import failed")
    return pitwall_storage.init_pitwall_db(PITWALL_DB_PATH)


def sqlite_upsert_prediction(entry):
    try:
        if pitwall_storage is None:
            raise RuntimeError("pitwall.storage import failed")
        pitwall_storage.sqlite_upsert_prediction(PITWALL_DB_PATH, entry, generated_at=now_local().isoformat())
    except Exception as error:
        print(f"SQLite prediction store skipped: {error}")


def sqlite_insert_run_status(status_type, payload):
    try:
        if pitwall_storage is None:
            raise RuntimeError("pitwall.storage import failed")
        pitwall_storage.sqlite_insert_run_status(PITWALL_DB_PATH, status_type, payload, created_at=now_local().isoformat())
    except Exception as error:
        print(f"SQLite run-status store skipped: {error}")


def supabase_sync_status():
    if pitwall_storage is None:
        if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
            return {"enabled": False, "status": "not_configured"}
        return {"enabled": True, "status": "configured_optional_manual_sync"}
    return pitwall_storage.supabase_sync_status(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)


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


CONSTRUCTOR_ALIASES = {
    "mercedes amg": "Mercedes",
    "mercedes amg petronas": "Mercedes",
    "mercedes amg petronas f1 team": "Mercedes",
    "mercedes amg petronas formula one team": "Mercedes",
    "mercedes": "Mercedes",
    "scuderia ferrari": "Ferrari",
    "scuderia ferrari hp": "Ferrari",
    "ferrari": "Ferrari",
    "mclaren formula 1 team": "McLaren",
    "mclaren f1 team": "McLaren",
    "mclaren mastercard f1 team": "McLaren",
    "mclaren": "McLaren",
    "oracle red bull racing": "Red Bull",
    "red bull racing": "Red Bull",
    "red bull": "Red Bull",
    "aston martin aramco f1 team": "Aston Martin",
    "aston martin aramco formula one team": "Aston Martin",
    "aston martin": "Aston Martin",
    "racing point": "Aston Martin",
    "force india": "Aston Martin",
    "bwt alpine f1 team": "Alpine",
    "bwt alpine formula one team": "Alpine",
    "alpine f1 team": "Alpine",
    "alpine": "Alpine",
    "renault": "Alpine",
    "williams racing": "Williams",
    "atlassian williams f1 team": "Williams",
    "williams": "Williams",
    "moneygram haas f1 team": "Haas",
    "tgr haas f1 team": "Haas",
    "haas f1 team": "Haas",
    "haas": "Haas",
    "visa cash app racing bulls formula one team": "RB F1 Team",
    "visa cash app rb formula one team": "RB F1 Team",
    "racing bulls": "RB F1 Team",
    "rb f1 team": "RB F1 Team",
    "rb": "RB F1 Team",
    "alphatauri": "RB F1 Team",
    "toro rosso": "RB F1 Team",
    "kick sauber": "Sauber",
    "stake f1 team kick sauber": "Sauber",
    "sauber": "Sauber",
    "alfa romeo": "Sauber",
    "audi": "Audi",
    "cadillac f1 team": "Cadillac",
    "cadillac": "Cadillac",
}


def canonical_constructor_name(name):
    text = str(name or "").strip()
    if not text:
        return "Unknown Team"
    key = re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()
    return CONSTRUCTOR_ALIASES.get(key, text)


def clamp(value, low=0.0, high=100.0, fallback=None):
    value = safe_float(value)
    if value is None:
        return fallback
    return max(low, min(high, value))


def pct_value(value):
    value = safe_float(value)
    if value is None:
        return None
    return round(clamp(value, 0, 100, 0), 2)


def stable_hash(payload):
    return sha256(json.dumps(payload, sort_keys=True, default=str).encode("utf-8")).hexdigest()


def text_level(value):
    text = str(value or "").lower()
    if "very high" in text:
        return 90
    if "medium-high" in text or "high-medium" in text:
        return 72
    if "high" in text:
        return 82
    if "medium-good" in text:
        return 68
    if "medium" in text:
        return 54
    if "low-medium" in text:
        return 38
    if "low" in text:
        return 26
    return 50


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
        return 0.6
    if season <= 2025:
        return 0.9
    return 1.0


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


def weighted_average_with_coverage(items):
    total = 0.0
    available_weight = 0.0
    possible_weight = 0.0
    for value, weight in items:
        weight = safe_float(weight) or 0.0
        if weight <= 0:
            continue
        possible_weight += weight
        value = safe_float(value)
        if value is None:
            continue
        total += value * weight
        available_weight += weight
    value = total / available_weight if available_weight else None
    coverage = available_weight / possible_weight if possible_weight else 0.0
    return value, coverage


def weighted_average_penalized(items, min_coverage=0.65, neutral=50.0):
    value, coverage = weighted_average_with_coverage(items)
    if value is None:
        return None
    if coverage >= min_coverage:
        return value
    penalty = max(0.0, min(1.0, coverage / max(0.01, min_coverage)))
    return neutral + (value - neutral) * penalty


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


def prepare_feature_matrix(df, feature_columns, imputer=None, fit=False):
    raw = df[feature_columns].replace([np.inf, -np.inf], np.nan).copy()
    missing = raw.isna().astype(float).add_prefix("is_missing__")
    if fit or imputer is None:
        imputer = SimpleImputer(strategy="median")
        values = imputer.fit_transform(raw)
    else:
        values = imputer.transform(raw)
    filled = pd.DataFrame(values, columns=feature_columns, index=df.index)
    matrix = pd.concat([filled, missing], axis=1)
    return matrix, imputer


def feature_matrix_columns(feature_columns):
    return list(feature_columns) + [f"is_missing__{col}" for col in feature_columns]


def feature_columns_hash(feature_columns):
    return sha256(json.dumps(list(feature_columns), sort_keys=True).encode("utf-8")).hexdigest()[:16]


def season_sample_weights(df):
    weights = []
    for season in df.get("season", []):
        season = safe_int(season) or 0
        if season >= 2026:
            weights.append(3.0)
        elif season == 2025:
            weights.append(2.0)
        elif season == 2024:
            weights.append(1.5)
        elif season >= 2022:
            weights.append(1.2)
        else:
            weights.append(1.0)
    return np.asarray(weights, dtype=float)


def select_feature_columns_by_importance(train_df, feature_columns, max_features=42):
    mandatory = {
        "grid_position", "qualifying_position", "sprint_position",
        "missing_grid", "missing_qualifying", "missing_sprint_position", "missing_lap_pace", "missing_pit_data",
        "driver_recent3_finish", "driver_avg_finish", "team_avg_finish", "team_recent_points",
        "track_dnf_rate", "track_position_sensitivity", "regulation_era_factor", "season_progress",
    }
    if len(feature_columns) <= max_features:
        return feature_columns, {"method": "not_needed", "selected_count": len(feature_columns), "dropped": []}
    try:
        probe_X = train_df[feature_columns].replace([np.inf, -np.inf], np.nan)
        probe_X = probe_X.fillna(probe_X.median(numeric_only=True)).fillna(0)
        probe_y = train_df["finish_position"].astype(float)
        probe = RandomForestRegressor(
            n_estimators=180,
            max_depth=10,
            min_samples_leaf=5,
            max_features="sqrt",
            random_state=214,
            n_jobs=-1,
        )
        probe.fit(probe_X, probe_y, sample_weight=season_sample_weights(train_df))
        importances = dict(zip(feature_columns, probe.feature_importances_))
        ranked = [name for name, _ in sorted(importances.items(), key=lambda item: item[1], reverse=True)]
        selected = []
        for name in list(mandatory) + ranked:
            if name in feature_columns and name not in selected:
                selected.append(name)
            if len(selected) >= max_features:
                break
        dropped = [name for name in feature_columns if name not in selected]
        return selected, {
            "method": "random_forest_importance_top_features",
            "selected_count": len(selected),
            "dropped": dropped,
            "top_importances": {k: round(float(importances.get(k, 0)), 6) for k in ranked[:20]},
        }
    except Exception as error:
        return feature_columns, {"method": "failed_keep_all", "error": str(error), "selected_count": len(feature_columns), "dropped": []}


def env_value(env, key, default=""):
    if env is not None and key in env:
        return env.get(key) or default
    return os.getenv(key, default)


def resolve_target_season(env=None, now=None):
    value = str(env_value(env, "TARGET_SEASON", TARGET_SEASON or "auto")).strip().lower()
    current = now or now_local()
    if value and value != "auto":
        parsed = safe_int(value)
        if parsed:
            return parsed
    # Keep auto conservative: current calendar year. Operators can override when
    # FIA/F1 publish the next season early.
    return current.year


def normalize_session_type(name):
    text = re.sub(r"\s+", " ", str(name or "").replace("_", " ")).strip().lower()
    if "race director" in text:
        return None
    if "sprint" in text and ("qualifying" in text or "shootout" in text or text == "sq"):
        return "sprint_qualifying"
    if "sprint" in text:
        return "sprint"
    if "qualifying" in text:
        return "qualifying"
    for key, value in SESSION_TYPE_ALIASES.items():
        if key in text:
            return value
    return SESSION_TYPE_ALIASES.get(text)


def formula1_season_url(season, env=None):
    explicit = env_value(env, "FORMULA1_SEASON_URL", FORMULA1_SEASON_URL).strip()
    if explicit:
        return explicit
    base = env_value(env, "FORMULA1_CALENDAR_BASE_URL", FORMULA1_CALENDAR_BASE_URL).rstrip("/")
    return f"{base}/{season}"


def extract_formula1_event_slugs(html, season):
    slugs = []
    pattern = re.compile(r'href=["\']([^"\']*/en/racing/%s/[^"\']+)["\']' % re.escape(str(season)), re.I)
    for href in pattern.findall(html or ""):
        slug = href.rstrip("/").split("/")[-1].split("?")[0].split("#")[0]
        if slug and slug not in slugs and slug not in {"racing", str(season)}:
            slugs.append(slug)
    return slugs


def resolve_fia_season_url(season, env=None, championship_html=None):
    explicit = env_value(env, "FIA_DOCUMENTS_SEASON_URL", FIA_DOCUMENTS_SEASON_URL).strip()
    default_year_url = "https://www.fia.com/documents/championships/fia-formula-one-world-championship-14/season/season-2026-2072" if safe_int(season) == 2026 else ""
    year_specific = env_value(env, f"FIA_DOCUMENTS_SEASON_URL_{season}", default_year_url).strip()
    base = env_value(env, "FIA_DOCUMENTS_BASE_URL", FIA_DOCUMENTS_BASE_URL).rstrip("/")
    if explicit:
        return {"url": explicit, "status": "configured", "source": "FIA_DOCUMENTS_SEASON_URL", "confidence": 1.0}
    if year_specific:
        return {"url": year_specific, "status": "configured", "source": f"FIA_DOCUMENTS_SEASON_URL_{season}", "confidence": 1.0}

    html = championship_html
    if html is None and SOURCE_DISCOVERY_ENABLED:
        response = safe_get(base, timeout=25, optional_404=True, use_cache=not REFRESH_SOURCE_REGISTRY)
        html = response.text if response is not None else ""

    candidates = []
    for href, label in re.findall(r'<a[^>]+href=["\']([^"\']+)["\'][^>]*>(.*?)</a>', html or "", flags=re.I | re.S):
        clean_label = strip_html(label)
        text = f"{href} {clean_label}".lower()
        if str(season) not in text:
            continue
        if "season" not in text and "formula" not in text:
            continue
        url = href if href.startswith("http") else f"https://www.fia.com{href if href.startswith('/') else '/' + href}"
        candidates.append(url)
    if candidates:
        return {"url": candidates[0], "status": "discovered", "source": "fia_championship_documents_page", "confidence": 0.82}
    return {
        "url": None,
        "status": "pending_unavailable",
        "source": "not_discovered",
        "confidence": 0.0,
        "warning": f"No FIA season document page discovered for {season}; no URL was fabricated.",
    }


def build_source_registry(season=None, env=None, cache_dir=None, championship_html=None, formula1_html=None, now=None):
    ensure_dirs()
    season = safe_int(season) or resolve_target_season(env, now=now)
    timestamp = (now or now_local()).isoformat()
    base_cache = Path(cache_dir) if cache_dir is not None else DATA_CACHE_DIR
    registry_dir = base_cache / "source_registry"
    registry_dir.mkdir(parents=True, exist_ok=True)
    previous_path = registry_dir / f"{season}.json"

    fia = resolve_fia_season_url(season, env=env, championship_html=championship_html)
    f1_url = formula1_season_url(season, env=env)
    slugs = extract_formula1_event_slugs(formula1_html or "", season)
    registry = {
        "schema_version": "source-registry-v1",
        "season": season,
        "target_season_mode": env_value(env, "TARGET_SEASON", TARGET_SEASON or "auto"),
        "discovered_at": timestamp,
        "last_checked_at": timestamp,
        "fia_championship_identifier": "fia-formula-one-world-championship-14",
        "fia_base_championship_documents_url": env_value(env, "FIA_DOCUMENTS_BASE_URL", FIA_DOCUMENTS_BASE_URL).rstrip("/"),
        "fia_season_document_url": fia.get("url"),
        "formula1_season_url": f1_url,
        "formula1_event_urls": [f"{f1_url.rstrip('/')}/{slug}" for slug in slugs],
        "jolpica_season_endpoint": f"{JOLPICA_BASE}/{season}.json",
        "ics_calendar_source": F1_ICS_URL or None,
        "discovered_event_slugs": slugs,
        "discovered_fia_event_groups": [],
        "fia_source_discovery_status": fia.get("status"),
        "source_discovery_status": "available" if fia.get("url") or slugs else "partial",
        "fallback_source_used": None if fia.get("url") else "formula1_jolpica_ics_cache",
        "errors": [],
        "warnings": [fia.get("warning")] if fia.get("warning") else [],
        "previous_valid_registry_path": public_path(previous_path) if previous_path.exists() else None,
        "cache_status": "refresh" if REFRESH_SOURCE_REGISTRY else ("hit" if previous_path.exists() else "miss"),
        "source_health": {
            "fia_decision_documents": {"available": bool(fia.get("url")), "status": fia.get("status"), "confidence": fia.get("confidence", 0)},
            "formula1_calendar": {"available": True, "status": "configured", "confidence": 0.75},
            "jolpica": {"available": JOLPICA_ENABLED, "status": "configured", "confidence": 0.70},
            "fastf1": {"available": FASTF1_ENABLED, "status": "configured", "confidence": 0.65},
            "openf1": {"available": OPENF1_ENABLED, "status": "configured", "confidence": 0.65},
        },
    }
    (registry_dir / f"{season}.json").write_text(json.dumps(registry, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    (registry_dir / "source_registry.json").write_text(json.dumps(registry, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    return registry


def classify_fia_document_type(title):
    text = re.sub(r"\s+", " ", str(title or "")).strip().lower()
    if "recall" in text or "recalled" in text:
        return "recalled_document"
    if "car presentation" in text:
        return "car_presentation_submissions"
    if "sprint qualifying" in text and "classification" in text:
        return "sprint_qualifying_classification"
    if "sprint" in text and "starting grid" in text:
        return "sprint_starting_grid"
    if "sprint" in text and "classification" in text:
        return "sprint_classification"
    if ("free practice 1" in text or "practice 1" in text or "fp1" in text) and "classification" in text:
        return "free_practice_classification"
    if ("free practice 2" in text or "practice 2" in text or "fp2" in text) and "classification" in text:
        return "free_practice_classification"
    if ("free practice 3" in text or "practice 3" in text or "fp3" in text) and "classification" in text:
        return "free_practice_classification"
    if "qualifying" in text and "classification" in text:
        return "qualifying_classification"
    if "starting grid" in text or "provisional grid" in text or "final grid" in text:
        return "starting_grid"
    if "race classification" in text or ("classification" in text and "race" in text):
        return "race_classification"
    if "timetable" in text or "schedule" in text:
        return "timetable"
    if "race director" in text and ("note" in text or "event" in text):
        return "race_director_notes"
    if "circuit map" in text:
        return "circuit_map"
    if "pirelli" in text:
        return "pirelli_preview"
    if "entry list" in text:
        return "entry_list"
    if "self scrutineering" in text:
        return "self_scrutineering"
    if "scrutineering" in text:
        return "scrutineering"
    if "new pu" in text or "new power unit" in text:
        return "new_pu_elements"
    if "pu elements used" in text or "power unit elements used" in text:
        return "pu_elements_used"
    if "power unit information" in text or "pu information" in text:
        return "power_unit_information"
    if "deleted lap" in text:
        return "deleted_lap_times"
    if "summons" in text:
        return "summons"
    if "decision" in text:
        return "decision"
    if "infringement" in text:
        return "infringement"
    if "post-race checks" in text or "post race checks" in text:
        return "post_race_checks"
    if "competition note" in text:
        return "competition_notes"
    if "procedure" in text:
        return "procedure"
    if "event note" in text:
        return "event_notes"
    if "reconnaissance" in text:
        return "reconnaissance_laps"
    if "pit lane start" in text:
        return "pit_lane_start"
    if "107" in text:
        return "107_percent"
    if "unsafe release" in text:
        return "unsafe_release"
    if "impeding" in text:
        return "impeding"
    if "parc" in text and "ferme" in text:
        return "parc_ferme"
    return "unknown"


def parse_fia_timestamp(text):
    raw = strip_html(text or "")
    iso_match = re.search(r'datetime=["\']([^"\']+)["\']', text or "", flags=re.I)
    if iso_match:
        try:
            return datetime.fromisoformat(iso_match.group(1).replace("Z", "+00:00")).astimezone(timezone.utc).isoformat()
        except Exception:
            pass
    match = re.search(r"(\d{1,2})[./-](\d{1,2})[./-](\d{2,4}).{0,20}?(\d{1,2}):(\d{2})", raw)
    if not match:
        return None
    day, month, year, hour, minute = match.groups()
    year = int(year)
    if year < 100:
        year += 2000
    try:
        cet = timezone(timedelta(hours=1))
        return datetime(year, int(month), int(day), int(hour), int(minute), tzinfo=cet).astimezone(timezone.utc).isoformat()
    except ValueError:
        return None


def parse_fia_document_index(html, season, season_url):
    docs = []
    current_event = "season"
    event_pattern = re.compile(r"<h[1-6][^>]*>(.*?)</h[1-6]>", flags=re.I | re.S)
    events = [(m.start(), strip_html(m.group(1))) for m in event_pattern.finditer(html or "")]
    links = list(re.finditer(r'<a[^>]+href=["\']([^"\']+)["\'][^>]*>(.*?)</a>', html or "", flags=re.I | re.S))
    for link in links:
        href, label_html = link.group(1), link.group(2)
        title = strip_html(label_html)
        href_lower = href.lower()
        title_lower = title.lower()
        real_document_link = (
            ".pdf" in href_lower
            or "decision-document" in href_lower
            or "/system/files/" in href_lower
            or "/file/" in href_lower
        )
        generic_titles = {"documents", "travel documents", "tourism travel documents", "travel documents and idps"}
        if not title or title_lower in generic_titles or not real_document_link:
            continue
        for _, event_name in [item for item in events if item[0] < link.start()]:
            if event_name:
                current_event = event_name
        source_url = href if href.startswith("http") else f"https://www.fia.com{href if href.startswith('/') else '/' + href}"
        inferred_event = current_event
        event_match = re.search(r"20\d{2}[_-]([a-z0-9_-]+?grand[_-]prix)", source_url, flags=re.I)
        if event_match:
            inferred_event = normalize_name(event_match.group(1).replace("_", " ").replace("-", " "))
        if make_slug(inferred_event) in {"filter-by", "documents", "season"} and "grand prix" in title_lower:
            title_event = re.search(r"([A-Za-z ]+ Grand Prix)", title, flags=re.I)
            if title_event:
                inferred_event = normalize_name(title_event.group(1))
        around = (html or "")[link.end():link.end() + 500]
        published_at = parse_fia_timestamp(around)
        doc_no = re.search(r"\b(?:doc(?:ument)?\.?\s*)?(\d{1,3})\b", title, flags=re.I)
        doc = {
            "season": safe_int(season),
            "event_slug": make_slug(inferred_event),
            "event_name": inferred_event,
            "document_id": stable_hash({"season": season, "url": source_url})[:16],
            "document_number": safe_int(doc_no.group(1)) if doc_no else None,
            "title": title,
            "normalized_title": make_slug(title),
            "document_type": classify_fia_document_type(title),
            "published_date": published_at[:10] if published_at else None,
            "published_time": published_at[11:16] if published_at else None,
            "published_at_utc": published_at,
            "source_url": source_url,
            "local_pdf_path": None,
            "local_text_path": None,
            "local_parsed_json_path": None,
            "recalled": "recall" in title.lower(),
            "superseded_by": None,
            "hash": stable_hash({"title": title, "url": source_url, "published_at": published_at}),
            "first_seen_at": now_local().isoformat(),
            "last_checked_at": now_local().isoformat(),
            "parse_status": "indexed",
            "parse_error": None,
            "source_confidence": 1.0,
            "cache_status": "miss",
            "season_url": season_url,
        }
        docs.append(doc)
    return docs


def fia_season_index_path(season):
    return FIA_DOCUMENT_CACHE_DIR / str(season) / "season_index.json"


def load_fia_season_index(season):
    path = fia_season_index_path(season)
    if not path.exists():
        return {"documents": [], "cache_status": "miss"}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        payload["cache_status"] = "hit"
        return payload
    except Exception as error:
        return {"documents": [], "cache_status": "error", "error": str(error)}


def fetch_fia_season_index(season, registry=None, refresh=False):
    ensure_dirs()
    registry = registry or load_or_build_source_registry(season)
    path = fia_season_index_path(season)
    cached = load_fia_season_index(season)
    if path.exists() and not refresh and not REFRESH_FIA_DOCUMENTS:
        try:
            age_minutes = (time.time() - path.stat().st_mtime) / 60
            if age_minutes < FIA_DOCUMENT_CACHE_TTL_MINUTES:
                return cached
        except Exception:
            pass
    url = registry.get("fia_season_document_url")
    if not url or not FIA_DOCUMENTS_ENABLED:
        payload = {
            "season": season,
            "season_url": url,
            "documents": cached.get("documents", []),
            "status": "pending_unavailable" if not url else "disabled",
            "cache_status": cached.get("cache_status", "miss"),
            "checked_at": now_local().isoformat(),
            "errors": [] if url else ["fia_season_url_unavailable"],
        }
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
        return payload
    if FIA_REQUEST_SLEEP_SECONDS > 0:
        time.sleep(FIA_REQUEST_SLEEP_SECONDS)
    response = safe_get(url, timeout=30, optional_404=True, use_cache=False)
    if not response:
        cached["status"] = "unavailable_using_cached_index" if cached.get("documents") else "unavailable"
        cached.setdefault("errors", []).append("fia_index_fetch_failed")
        return cached
    documents = parse_fia_document_index(response.text, season=season, season_url=url)
    previous = {doc.get("source_url"): doc for doc in cached.get("documents", [])}
    changed = []
    reused = []
    indexed_documents = documents[:MAX_FIA_DOCUMENTS_PER_RUN] if MAX_FIA_DOCUMENTS_PER_RUN > 0 else documents
    for doc in indexed_documents:
        old = previous.get(doc.get("source_url"))
        if old and old.get("hash") == doc.get("hash") and not FORCE_REPARSE_FIA_DOCUMENTS and not FORCE_REDOWNLOAD_FIA_DOCUMENTS:
            doc.update({
                "local_pdf_path": old.get("local_pdf_path"),
                "local_text_path": old.get("local_text_path"),
                "local_parsed_json_path": old.get("local_parsed_json_path"),
                "parse_status": old.get("parse_status", "indexed"),
                "cache_status": "hit",
                "first_seen_at": old.get("first_seen_at", doc.get("first_seen_at")),
            })
            reused.append(doc.get("document_id"))
        else:
            doc["cache_status"] = "miss"
            changed.append(doc.get("document_id"))
    payload = {
        "season": season,
        "season_url": url,
        "status": "available",
        "checked_at": now_local().isoformat(),
        "documents": documents,
        "cache_status": "refresh" if refresh or REFRESH_FIA_DOCUMENTS else "revalidated",
        "documents_changed": changed,
        "documents_reused": reused,
        "errors": [],
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    return payload


def extract_pdf_text(pdf_bytes):
    try:
        from pypdf import PdfReader
        reader = PdfReader(io.BytesIO(pdf_bytes))
        return "\n".join(page.extract_text() or "" for page in reader.pages)
    except Exception as error:
        raise RuntimeError(f"pdf_text_extraction_failed: {error}") from error


def fetch_fia_document_text(document, text_path, parsed_path, pdf_path):
    if pitwall_fetch_fia_document_text is None:
        raise RuntimeError("pitwall.data.fia_documents import failed")
    return pitwall_fetch_fia_document_text(
        document,
        text_path,
        parsed_path,
        pdf_path,
        extract_pdf_text=extract_pdf_text,
        strip_html=strip_html,
        keep_pdf=KEEP_FIA_PDFS,
        timeout=45,
        strict_downloads=FIA_DOCUMENT_STRICT_DOWNLOADS,
    )


def parse_fia_document_text(document, text):
    doc_type = document.get("document_type") or classify_fia_document_type(document.get("title"))
    parsed = {
        "document_id": document.get("document_id"),
        "document_type": doc_type,
        "source_url": document.get("source_url"),
        "parser_version": "fia-parser-v1",
        "parsed_at": now_local().isoformat(),
        "confidence": 0.55,
        "classification": [],
        "upgrades": [],
        "pu_features": {},
        "infringements": {},
        "raw_text_excerpt": (text or "")[:1200],
    }
    if "classification" in doc_type or doc_type in {"starting_grid", "sprint_starting_grid"}:
        parsed["classification"] = extract_fia_classification_rows(text)
        parsed["confidence"] = 0.72 if parsed["classification"] else 0.35
    if doc_type == "car_presentation_submissions":
        parsed["upgrades"] = extract_car_presentation_updates(text, event_name=document.get("event_name"), source_url=document.get("source_url"))
        parsed["confidence"] = 1.0 if parsed["upgrades"] else 0.45
    if doc_type in {"new_pu_elements", "pu_elements_used", "power_unit_information"}:
        parsed["pu_features"] = extract_pu_features(text)
        parsed["confidence"] = 1.0 if parsed["pu_features"] else 0.45
    if doc_type in {"deleted_lap_times", "infringement", "summons", "decision", "unsafe_release", "impeding", "parc_ferme"}:
        parsed["infringements"] = extract_infringement_features(text)
        parsed["confidence"] = 0.78
    return parsed


def document_cache_slug(document):
    title_slug = make_slug(document.get("title") or document.get("document_id") or "document")
    doc_no = document.get("document_number")
    prefix = f"doc-{doc_no}-" if doc_no is not None else ""
    return (prefix + title_slug)[:140] or str(document.get("document_id") or "document")


def refresh_fia_documents_for_season(season, registry=None, refresh=False):
    season = safe_int(season) or resolve_target_season()
    registry = registry or load_or_build_source_registry(season)
    index_payload = fetch_fia_season_index(season, registry=registry, refresh=refresh)
    documents = index_payload.get("documents") if isinstance(index_payload, dict) else []
    if not isinstance(documents, list):
        documents = []
    downloaded = 0
    parsed = 0
    skipped = 0
    errors = list(index_payload.get("errors", []) if isinstance(index_payload, dict) else [])
    updated_documents = []

    indexed_documents = documents[:MAX_FIA_DOCUMENTS_PER_RUN] if MAX_FIA_DOCUMENTS_PER_RUN > 0 else documents
    for document in indexed_documents:
        doc = dict(document)
        event_slug = doc.get("event_slug") or "season"
        slug = document_cache_slug(doc)
        event_dir = FIA_DOCUMENT_CACHE_DIR / str(season) / event_slug
        text_path = event_dir / "text" / f"{slug}.txt"
        parsed_path = event_dir / "parsed" / f"{slug}.json"
        pdf_path = event_dir / "pdfs" / f"{slug}.pdf"
        doc["local_text_path"] = public_path(text_path)
        doc["local_parsed_json_path"] = public_path(parsed_path)
        doc["local_pdf_path"] = public_path(pdf_path) if KEEP_FIA_PDFS else None

        can_reuse = (
            text_path.exists()
            and parsed_path.exists()
            and not FORCE_REPARSE_FIA_DOCUMENTS
            and not FORCE_REDOWNLOAD_FIA_DOCUMENTS
            and doc.get("cache_status") == "hit"
        )
        if can_reuse:
            doc["parse_status"] = doc.get("parse_status") or "parsed"
            doc["cache_status"] = "hit"
            skipped += 1
            updated_documents.append(doc)
            continue

        download_limit_reached = MAX_FIA_PDFS_DOWNLOAD_PER_RUN > 0 and downloaded >= MAX_FIA_PDFS_DOWNLOAD_PER_RUN
        if download_limit_reached and not (text_path.exists() and FORCE_REPARSE_FIA_DOCUMENTS):
            doc["parse_status"] = doc.get("parse_status") or "indexed_pending_download_limit"
            skipped += 1
            updated_documents.append(doc)
            continue

        try:
            text = None
            fetch_result = None
            if text_path.exists() and FORCE_REPARSE_FIA_DOCUMENTS and not FORCE_REDOWNLOAD_FIA_DOCUMENTS:
                text = text_path.read_text(encoding="utf-8")
            else:
                if FIA_REQUEST_SLEEP_SECONDS > 0:
                    time.sleep(FIA_REQUEST_SLEEP_SECONDS)
                fetch_result = fetch_fia_document_text(doc, text_path, parsed_path, pdf_path)
                text = fetch_result.get("text")
                doc["http_status"] = fetch_result.get("http_status")
                if fetch_result.get("parse_status") == "downloaded":
                    downloaded += 1
                if text is None:
                    doc["parse_status"] = fetch_result.get("parse_status") or "error"
                    doc["parse_error"] = fetch_result.get("error") or "fia_document_download_failed"
                    doc["cache_status"] = fetch_result.get("cache_status") or "miss"
                    if doc["parse_status"] in {"forbidden", "not_found"}:
                        errors.append(f"{doc.get('title')}: {doc['parse_error']}")
                    updated_documents.append(doc)
                    continue
            if text is not None:
                text_path.parent.mkdir(parents=True, exist_ok=True)
                text_path.write_text(text or "", encoding="utf-8")
            parsed_doc = parse_fia_document_text(doc, text or "")
            parsed_path.parent.mkdir(parents=True, exist_ok=True)
            parsed_path.write_text(json.dumps(parsed_doc, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
            if fetch_result and fetch_result.get("parse_status", "").startswith("stale_cache_"):
                doc["parse_status"] = fetch_result.get("parse_status")
                doc["parse_error"] = fetch_result.get("error")
                doc["cache_status"] = "stale"
                errors.append(f"{doc.get('title')}: {fetch_result.get('error')}")
            else:
                doc["parse_status"] = "parsed"
                doc["parse_error"] = None
                doc["cache_status"] = "miss" if fetch_result and fetch_result.get("parse_status") == "downloaded" else "reparsed"
            doc["hash"] = stable_hash({"metadata": doc.get("hash"), "text": (text or "")[:10000]})
            parsed += 1
        except Exception as error:
            doc["parse_status"] = "error"
            doc["parse_error"] = str(error)
            errors.append(f"{doc.get('title')}: {error}")
        updated_documents.append(doc)

    if isinstance(index_payload, dict):
        index_payload["documents"] = updated_documents + documents[len(updated_documents):]
        index_payload["documents_downloaded"] = downloaded
        index_payload["documents_parsed"] = parsed
        index_payload["documents_skipped"] = skipped
        index_payload["errors"] = errors[:50]
        index_payload["checked_at"] = now_local().isoformat()
        path = fia_season_index_path(season)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(index_payload, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    _FIA_REFRESHED_SEASONS.add(season)
    return index_payload


def extract_fia_classification_rows(text):
    rows = []
    for raw_line in (text or "").splitlines():
        line = re.sub(r"\s+", " ", raw_line).strip()
        if not re.match(r"^\d{1,2}\s+\d{1,3}\s+", line):
            continue
        parts = line.split()
        position = safe_int(parts[0])
        number = parts[1]
        lap_or_gap_index = None
        for idx, token in enumerate(parts[2:], start=2):
            if re.match(r"^(?:\d+:)?\d{1,2}\.\d{3}$", token) or re.match(r"^\+\d", token):
                lap_or_gap_index = idx
                break
        if lap_or_gap_index is None:
            continue
        name_tokens = parts[2:lap_or_gap_index]
        # FIA rows often include uppercase surnames and then a multi-word team.
        driver_tokens = []
        for token in name_tokens:
            driver_tokens.append(token)
            if token.isupper() and len(driver_tokens) >= 2:
                break
        team_tokens = name_tokens[len(driver_tokens):]
        metric = parts[lap_or_gap_index]
        rows.append({
            "position": position,
            "driver_number": number,
            "driver_name": normalize_name(" ".join(driver_tokens)),
            "team": " ".join(team_tokens) or None,
            "best_lap_time": metric if ":" in metric or re.match(r"^\d{1,2}\.\d{3}$", metric) else None,
            "gap": metric if metric.startswith("+") else None,
            "laps_completed": safe_int(parts[-1]),
            "raw": line,
            "parser_confidence": 0.72,
        })
    return rows


UPGRADE_COMPONENT_TRAITS = {
    "front wing": ["aero_balance", "downforce", "flow_conditioning", "corner_entry_stability", "low_speed_balance"],
    "rear wing": ["drag", "straight_line_speed", "local_load", "drs_efficiency", "rear_stability"],
    "beam wing": ["diffuser_interaction", "drag", "rear_load", "straight_line_efficiency"],
    "floor edge": ["sealing", "aero_efficiency", "stability", "tyre_management"],
    "floor": ["downforce", "aero_efficiency", "platform_stability", "tyre_management", "high_speed_load"],
    "diffuser": ["rear_load", "aero_efficiency", "platform_sensitivity"],
    "sidepod": ["cooling", "flow_conditioning", "aero_efficiency"],
    "coke": ["rear_flow_conditioning", "cooling", "drag"],
    "engine cover": ["cooling", "rear_flow", "heat_rejection"],
    "bodywork": ["flow_conditioning", "cooling", "aero_efficiency"],
    "brake duct": ["brake_cooling", "tyre_temperature_control", "braking_stability"],
    "front corner": ["brake_cooling", "flow_conditioning", "tyre_wake_control"],
    "rear corner": ["brake_cooling", "diffuser_feed", "rear_stability"],
    "suspension": ["platform_stability", "flow_conditioning", "diffuser_feed", "mechanical_grip"],
    "cooling louvres": ["heat_management", "cooling_range"],
    "halo winglet": ["local_flow_conditioning", "aero_efficiency"],
    "mirrors": ["flow_conditioning", "drag"],
}


def extract_car_presentation_updates(text, event_name=None, source_url=None):
    updates = []
    teams = [
        "Red Bull", "Ferrari", "Mercedes", "McLaren", "Aston Martin", "Alpine", "Williams",
        "Haas", "RB", "Racing Bulls", "Sauber", "Audi", "Cadillac",
    ]
    lines = [re.sub(r"\s+", " ", line).strip() for line in (text or "").splitlines() if line.strip()]
    blob = "\n".join(lines)
    for team in teams:
        for match in re.finditer(rf"\b{re.escape(team)}\b(.{{0,260}})", blob, flags=re.I):
            excerpt = match.group(0)
            lower = excerpt.lower()
            components = [component for component in UPGRADE_COMPONENT_TRAITS if component in lower]
            if not components and "no update" in lower:
                continue
            traits = sorted({trait for component in components for trait in UPGRADE_COMPONENT_TRAITS[component]})
            if components or traits:
                updates.append({
                    "team": normalize_name(team),
                    "component": components[0] if components else "unknown",
                    "components": components,
                    "primary_reason_for_update": "performance" if "performance" in lower else "reliability" if "reliability" in lower else "unknown",
                    "geometric_difference": excerpt[:180],
                    "description": excerpt[:260],
                    "event": event_name,
                    "source_url": source_url,
                    "confidence_score": 1.0,
                    "raw_excerpt": excerpt,
                    "traits": traits,
                })
    return updates


def extract_pu_features(text):
    features = {}
    for raw_line in (text or "").splitlines():
        line = re.sub(r"\s+", " ", raw_line).strip()
        match = re.match(r"^(\d{1,3})\s+(.+)$", line)
        if not match:
            continue
        number = match.group(1)
        lower = match.group(2).lower()
        if not any(token in lower for token in ["ice", "tc", "mgu", "es", "ce", "exhaust", "pu-anc", "pu anc"]):
            continue
        features[number] = {
            "new_ice": bool(re.search(r"\bice\b", lower)),
            "new_tc": bool(re.search(r"\btc\b|turbo", lower)),
            "new_mgu_h": bool(re.search(r"mgu[-\s]?h", lower)),
            "new_mgu_k": bool(re.search(r"mgu[-\s]?k", lower)),
            "new_es": bool(re.search(r"\bes\b|energy store", lower)),
            "new_ce": bool(re.search(r"\bce\b|control electronics", lower)),
            "new_exhaust": "exhaust" in lower,
            "new_pu_anc": "pu-anc" in lower or "pu anc" in lower,
            "component_count_used": None,
            "component_limit_margin": None,
            "reliability_boost": 8 if "new" in lower else 0,
            "grid_penalty_risk": 20 if "penalty" in lower or "exceeded" in lower else 5,
            "pu_change_reason_text": line,
            "source_confidence": 1.0,
        }
    return features


def extract_infringement_features(text):
    lower = str(text or "").lower()
    grid_penalty = re.search(r"(\d+)\s+(?:place|grid)", lower)
    penalty_points_match = re.search(r"(\d+)\s+penalty point", lower)
    return {
        "deleted_lap_count": len(re.findall(r"deleted lap|lap time deleted", lower)),
        "deleted_fastest_lap_flag": "fastest lap" in lower and "deleted" in lower,
        "qualifying_lap_deleted_flag": "qualifying" in lower and "deleted" in lower,
        "infringement_count": len(re.findall(r"infringement|breach|failed to follow|unsafe release|impeding|speeding", lower)),
        "penalty_points": safe_int(penalty_points_match.group(1)) if penalty_points_match else None,
        "grid_penalty_places": safe_int(grid_penalty.group(1)) if grid_penalty else 0,
        "pit_lane_start_flag": "pit lane start" in lower,
        "back_of_grid_flag": "back of the grid" in lower or "back-of-grid" in lower,
        "confidence_penalty": 12 if any(token in lower for token in ["summons", "investigation", "pending"]) else 0,
        "discipline_risk_score": 65 if any(token in lower for token in ["impeding", "unsafe", "track limits"]) else 35,
        "steward_decision_summary": strip_html(text or "")[:300],
        "source_document_ids": [],
    }


def parse_datetime_utc(value):
    if not value:
        return None
    if isinstance(value, datetime):
        return value.astimezone(timezone.utc) if value.tzinfo else value.replace(tzinfo=timezone.utc)
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00")).astimezone(timezone.utc)
    except Exception:
        return None


def session_delay_minutes(session_type):
    normalized = normalize_session_type(session_type) or str(session_type or "").lower()
    if normalized in {"fp1", "fp2", "fp3"}:
        return PRACTICE_RESULT_DELAY_MINUTES
    if normalized == "sprint_qualifying":
        return SPRINT_QUALIFYING_RESULT_DELAY_MINUTES
    if normalized == "sprint":
        return SPRINT_RESULT_DELAY_MINUTES
    if normalized == "qualifying":
        return QUALIFYING_RESULT_DELAY_MINUTES
    if normalized == "race":
        return RACE_RESULT_DELAY_HOURS * 60
    return SESSION_RESULT_DELAY_MINUTES


def evaluate_session_lifecycle(session, now=None, data_available=False, retries=None):
    now = now or datetime.now(timezone.utc)
    start = parse_datetime_utc(session.get("official_start_time_utc") or session.get("start") or session.get("date_start"))
    end = parse_datetime_utc(session.get("official_end_time_utc") or session.get("end") or session.get("date_end"))
    if start and not end:
        end = start + timedelta(hours=2)
    session_type = normalize_session_type(session.get("session_type") or session.get("session_name")) or session.get("session_type")
    delay = timedelta(minutes=session_delay_minutes(session_type))
    attempts = safe_int(retries if retries is not None else session.get("ingestion_attempts")) or 0
    out = dict(session)
    out.setdefault("session_type", session_type)
    out["last_checked_at"] = now.isoformat()
    if not SESSION_INGESTION_ENABLED:
        out["status"] = "unavailable"
        out["source_confidence"] = 0
        return out
    if start and now < start:
        out["status"] = "scheduled"
        out["next_check_at"] = start.isoformat()
    elif start and end and start <= now <= end:
        out["status"] = "live" if data_available else "active_without_live_data"
        out["next_check_at"] = (now + timedelta(minutes=SESSION_RETRY_INTERVAL_MINUTES)).isoformat()
    elif end and now < end + delay and not FORCE_SESSION_INGEST:
        out["status"] = "completed"
        out["next_check_at"] = (end + delay).isoformat()
    elif data_available or FORCE_SESSION_INGEST:
        out["status"] = "data_ingested"
        out["data_available_at"] = now.isoformat()
    elif attempts >= MAX_SESSION_RETRIES:
        out["status"] = "unavailable"
        out["next_check_at"] = None
    else:
        out["status"] = "waiting_for_api_data"
        out["next_check_at"] = (now + timedelta(minutes=SESSION_RETRY_INTERVAL_MINUTES)).isoformat()
    out["freshness_score"] = 90 if out["status"] in {"live", "data_ingested"} else 55 if out["status"] in {"completed", "waiting_for_api_data"} else 30
    return out


def audit_feature_leakage(stage, feature_columns):
    stage_index = STAGE_ORDER.index(stage) if stage in STAGE_ORDER else 0
    blocked = []
    for feature in feature_columns or []:
        key = str(feature)
        min_stage = None
        for pattern, allowed_stage in FEATURE_STAGE_MATRIX.items():
            if pattern in {"finish_position", "points", "is_win", "is_podium", "is_top10"}:
                matched = key == pattern
            else:
                matched = key == pattern or key.endswith(f"_{pattern}") or key.startswith(f"{pattern}_")
            if matched:
                min_stage = allowed_stage
                break
        if min_stage and STAGE_ORDER.index(min_stage) > stage_index:
            blocked.append(key)
    target_like = [f for f in feature_columns or [] if str(f) in {"finish_position", "points", "is_win", "is_podium", "is_top10"}]
    blocked = sorted(set(blocked + target_like))
    return {
        "passed": not blocked,
        "stage": stage,
        "blocked_features": blocked,
        "checked_feature_count": len(feature_columns or []),
    }


def stage_prediction_weights(stage, track_traits=None, weather=None):
    track_traits = track_traits or {}
    weather = weather or {}
    base = {
        "historical_driver_form": 0.15,
        "constructor_form": 0.18,
        "circuit_history": 0.12,
        "track_traits": 0.12,
        "current_season_car_performance": 0.18,
        "weather": 0.08,
        "fia_upgrades": 0.10,
        "reliability": 0.07,
        "practice_pace": 0.0,
        "sprint_qualifying": 0.0,
        "sprint_result": 0.0,
        "qualifying_grid": 0.0,
        "racecraft_overtaking": 0.0,
        "tyre_degradation": 0.0,
    }
    if stage in {"post_fp1", "post_fp2", "post_fp3", "post_practice"}:
        base.update({"practice_pace": 0.20, "track_traits": 0.08, "constructor_form": 0.12, "current_season_car_performance": 0.15, "fia_upgrades": 0.08, "reliability": 0.07})
    elif stage == "post_sprint_qualifying":
        base.update({"sprint_qualifying": 0.25, "practice_pace": 0.15, "racecraft_overtaking": 0.10, "constructor_form": 0.10, "track_traits": 0.08, "fia_upgrades": 0.05})
    elif stage == "post_sprint":
        base.update({"sprint_result": 0.20, "sprint_qualifying": 0.15, "practice_pace": 0.12, "racecraft_overtaking": 0.10, "tyre_degradation": 0.10, "constructor_form": 0.10, "reliability": 0.08, "fia_upgrades": 0.04})
    elif stage in {"post_qualifying", "pre_race"}:
        base.update({"qualifying_grid": 0.30, "practice_pace": 0.15, "constructor_form": 0.15, "historical_driver_form": 0.10, "track_traits": 0.08, "circuit_history": 0.07, "weather": 0.06, "fia_upgrades": UPGRADE_MAX_WEIGHT_POST_QUALIFYING, "reliability": 0.04})
    elif stage == "live_adjusted":
        base.update({"qualifying_grid": 0.22, "practice_pace": 0.12, "live_timing": 0.18, "reliability": 0.08, "weather": 0.08, "fia_upgrades": 0.02})
    if "low" in str(track_traits.get("overtaking", "")).lower():
        base["qualifying_grid"] = base.get("qualifying_grid", 0) + 0.06
    if "high" in str(track_traits.get("tyre_stress", "")).lower():
        base["tyre_degradation"] = base.get("tyre_degradation", 0) + 0.04
    if safe_float(weather.get("rain_probability")) and safe_float(weather.get("rain_probability")) >= 0.35:
        base["weather"] += 0.05
        base["reliability"] += 0.03
    cap = UPGRADE_MAX_WEIGHT_PRE_RUNNING
    if stage in {"post_fp1", "post_fp2", "post_fp3", "post_practice"}:
        cap = UPGRADE_MAX_WEIGHT_POST_PRACTICE
    elif stage in {"post_qualifying", "pre_race", "live_adjusted", "post_race_audited"}:
        cap = UPGRADE_MAX_WEIGHT_POST_QUALIFYING
    base["fia_upgrades"] = min(base.get("fia_upgrades", 0), cap)
    clean = {k: max(0.0, safe_float(v) or 0.0) for k, v in base.items()}
    total = sum(clean.values()) or 1.0
    return {k: v / total for k, v in clean.items()}


def normalize_race_probabilities(rows):
    return pitwall_simulation.normalize_race_probabilities(rows)


def simulate_race_outcomes(rows, runs=None, seed=42):
    return pitwall_simulation.simulate_race_outcomes(
        rows,
        runs=runs,
        seed=seed,
        default_runs=RACE_SIMULATION_RUNS,
        github_actions_runs=GITHUB_ACTIONS_RACE_SIMULATION_RUNS,
        enabled=ENABLE_RACE_SIMULATION,
    )


def confidence_label(value):
    return pitwall_simulation.confidence_label(value)


def probability_from_score(score, low=1.0, high=18.0):
    return pitwall_simulation.probability_from_score(score, low=low, high=high)


def strategy_profile_for_row(row, profile=None, weather=None):
    return pitwall_strategy.strategy_profile_for_row(row, profile, weather)


def detect_strategy_context_annotations(strategy_context=None, weather_context=None):
    return pitwall_strategy.detect_strategy_context_annotations(strategy_context, weather_context)


def explanation_for_prediction_row(row, profile=None, weather=None):
    return pitwall_contract.explanation_for_prediction_row(row, profile, weather)


def race_factors_from_context(profile=None, weather=None, source_health=None):
    return pitwall_contract.race_factors_from_context(profile, weather, source_health)


def uncertainty_for_prediction(row, source_health=None, stage=None):
    evidence = row.get("evidence_status") or {}
    missing_count = len(evidence.get("missing") or [])
    source_score = safe_float((source_health or {}).get("overall_score")) or 65
    stage_penalty = 22 if stage in {None, "pre_weekend"} else 14 if str(stage).startswith("post_fp") else 8
    uncertainty = clamp(100 - (safe_float(row.get("confidence")) or 50) + missing_count * 4 + (100 - source_score) * 0.25 + stage_penalty, 0, 100, 45)
    reasons = []
    if missing_count:
        reasons.append("missing_data")
    if source_score < 60:
        reasons.append("source_health_limited")
    if stage in {None, "pre_weekend"}:
        reasons.append("pre_session_uncertainty")
    return {
        "model_uncertainty": round(clamp(100 - (safe_float(row.get("model_agreement_score")) or 55), 0, 100, 40), 2),
        "data_uncertainty": min(100, missing_count * 12),
        "source_uncertainty": round(100 - source_score, 2),
        "stage_uncertainty": stage_penalty,
        "weather_uncertainty": 0,
        "reliability_uncertainty": round(100 - (safe_float(row.get("reliability")) or 60), 2),
        "upgrade_uncertainty": 20 if "fia upgrades" not in " ".join(row.get("reason_tags") or []).lower() else 8,
        "total_uncertainty": round(uncertainty, 2),
        "uncertainty_reasons": reasons,
        "prediction_risk_level": "High" if uncertainty >= 65 else "Medium" if uncertainty >= 40 else "Low",
    }


def timing_freshness_status(last_updated=None, now=None, session_end=None, has_fresh_packets=False, source="Formula1LiveTiming"):
    now = now or datetime.now(timezone.utc)
    last = parse_datetime_utc(last_updated)
    end = parse_datetime_utc(session_end)
    age = (now - last).total_seconds() if last else None
    if DISABLE_LIVE_MODE or not LIVE_TIMING_ENABLED:
        mode = "unavailable"
        reason = "live timing disabled"
    elif end and now > end:
        mode = "archive"
        reason = "session ended"
    elif not has_fresh_packets:
        mode = "delayed" if TIMING_REPLAY_MODE_ALLOWED else "unavailable"
        reason = "no fresh timing packets"
    elif age is None or age > LIVE_STALE_AFTER_SECONDS:
        mode = "stale"
        reason = "timing packets are older than freshness threshold"
    else:
        mode = "live"
        reason = ""
    return {
        "live_timing_status": "Live" if mode == "live" else mode.title(),
        "timing_mode": mode,
        "timing_source": source,
        "timing_last_updated_at": last.isoformat() if last else None,
        "timing_freshness_seconds": round(age, 2) if age is not None else None,
        "is_genuinely_live": mode == "live",
        "live_fallback_reason": reason,
    }


def require_env_vars():
    missing = []
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
    raw = url + "?" + json.dumps(params or {}, sort_keys=True, default=str)
    return sha256(raw.encode("utf-8")).hexdigest()[:32]


def polite_sleep():
    if JOLPICA_REQUEST_SLEEP > 0:
        time.sleep(JOLPICA_REQUEST_SLEEP)


def response_looks_json(response):
    content_type = response.headers.get("content-type", "").lower()
    if "json" in content_type:
        return True
    try:
        json.loads(response.text)
        return True
    except Exception:
        return False


def atomic_write_bytes(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f"{path.name}.{os.getpid()}.{time.time_ns()}.tmp")
    tmp.write_bytes(content)
    os.replace(tmp, path)


def safe_get(url, params=None, timeout=30, headers=None, optional_404=False, use_cache=True, return_on_statuses=None, request_sleep=0.0):
    ensure_dirs()
    cache_path = HTTP_CACHE_DIR / f"{cache_key_for_url(url, params)}.json"
    return_on_statuses = set(return_on_statuses or [])

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

    slept_for_request = False
    for attempt in range(4):
        try:
            if request_sleep and not slept_for_request:
                time.sleep(request_sleep)
                slept_for_request = True
            response = requests.get(url, params=params or {}, headers=headers or {}, timeout=timeout)

            if response.status_code == 404 and optional_404:
                print(f"Optional endpoint not available: {url}")
                return None

            if response.status_code in return_on_statuses:
                print(f"GET returned handled status {response.status_code}: {url}")
                return response

            if response.status_code == 429:
                retry_after = response.headers.get("Retry-After")
                try:
                    wait = float(retry_after) if retry_after else 5 + attempt * 5
                except (TypeError, ValueError):
                    wait = 5 + attempt * 5
                print(f"Rate limited. Waiting {wait}s before retry.")
                time.sleep(wait)
                continue

            response.raise_for_status()

            if use_cache and response_looks_json(response):
                atomic_write_bytes(cache_path, response.content)

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

    response = safe_get(
        JOLPICA_BASE + endpoint,
        params=params,
        headers=JOLPICA_HEADERS,
        optional_404=optional_404,
        use_cache=use_cache,
        request_sleep=JOLPICA_REQUEST_SLEEP,
    )
    if not response:
        return {}
    try:
        data = response.json()
    except json.JSONDecodeError:
        print(f"Jolpica returned non-JSON for {endpoint}")
        return {}
    print(f"Jolpica OK: {endpoint}")
    return data


def jolpica_laps_races(season, round_no, use_cache=True):
    races_by_key = {}
    offset = 0
    limit = 100
    total = None
    while total is None or offset < total:
        data = jolpica_get(
            f"/{season}/{round_no}/laps",
            params={"limit": limit, "offset": offset},
            optional_404=True,
            use_cache=use_cache,
        )
        mrdata = data.get("MRData", {}) if isinstance(data, dict) else {}
        try:
            total = int(mrdata.get("total") or 0)
            current_offset = int(mrdata.get("offset") or offset)
            current_limit = int(mrdata.get("limit") or limit)
        except (TypeError, ValueError):
            total = None
            current_offset = offset
            current_limit = limit
        races = mrdata_list(data, "RaceTable", "Races")
        if not races:
            break
        for race in races:
            key = (race.get("season"), race.get("round"), race.get("raceName"))
            target = races_by_key.setdefault(key, {**race, "Laps": []})
            target["Laps"].extend(race.get("Laps", []) or [])
        if total is None:
            break
        offset = current_offset + max(1, current_limit)
    return list(races_by_key.values())


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


@lru_cache(maxsize=16)
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
    def fetch_endpoint(key, endpoint, optional=True):
        data = jolpica_get(endpoint, optional_404=optional, use_cache=use_cache)
        return key, mrdata_list(data, "RaceTable", "Races")

    endpoints = {
        "results": (f"/{season}/{round_no}/results", False),
        "qualifying": (f"/{season}/{round_no}/qualifying", True),
        "pitstops": (f"/{season}/{round_no}/pitstops", True),
        "sprint": (f"/{season}/{round_no}/sprint", True),
        "sprint_qualifying": (f"/{season}/{round_no}/sprint/qualifying", True),
    }
    results = {"laps": []}
    with ThreadPoolExecutor(max_workers=6) as executor:
        futures = {
            executor.submit(fetch_endpoint, key, endpoint, optional): key
            for key, (endpoint, optional) in endpoints.items()
        }
        futures[executor.submit(jolpica_laps_races, season, round_no, use_cache)] = "laps"
        for future in as_completed(futures):
            key = futures[future]
            try:
                value = future.result()
                if key == "laps":
                    results[key] = value
                else:
                    fetched_key, rows = value
                    results[fetched_key] = rows
            except Exception as error:
                print(f"Jolpica round endpoint failed for {season}-{round_no} {key}: {error}")
                results[key] = []
    for key in ["results", "qualifying", "pitstops", "laps", "sprint", "sprint_qualifying"]:
        results.setdefault(key, [])
    return results


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
    if not url:
        print("F1_ICS_URL not set; using Jolpica schedule fallback calendar.")
        return build_jolpica_fallback_calendar(resolve_target_season())
    if url.startswith("webcal://"):
        url = "https://" + url.replace("webcal://", "", 1)
    if not url.startswith(("http://", "https://")):
        raise RuntimeError("F1_ICS_URL must be a normal HTTP URL.")
    ensure_dirs()
    cache_path = HTTP_CACHE_DIR / f"ics-{cache_key_for_url(url)}.ics"
    if cache_path.exists():
        try:
            age = time.time() - cache_path.stat().st_mtime
            if age < 6 * 3600:
                calendar = Calendar.from_ical(cache_path.read_bytes())
                if get_f1_calendar_events(calendar):
                    return calendar
        except Exception:
            pass
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        calendar = Calendar.from_ical(response.content)
        if get_f1_calendar_events(calendar):
            atomic_write_bytes(cache_path, response.content)
            return calendar
        print("F1_ICS_URL returned no usable F1 events; using Jolpica schedule fallback calendar.")
    except Exception as error:
        print(f"F1_ICS_URL fetch/parse failed; using Jolpica schedule fallback calendar: {error}")
        if cache_path.exists():
            try:
                calendar = Calendar.from_ical(cache_path.read_bytes())
                if get_f1_calendar_events(calendar):
                    print("Using stale cached ICS calendar after fetch failure.")
                    return calendar
            except Exception:
                pass
    return build_jolpica_fallback_calendar(resolve_target_season())


def build_jolpica_fallback_calendar(season):
    calendar = Calendar()
    calendar.add("prodid", "-//PitWall Jolpica fallback calendar//pitwall//")
    calendar.add("version", "2.0")
    for race in fetch_schedule(season):
        start = parse_race_datetime(race)
        if not start:
            continue
        event = Event()
        event.add("summary", f"{race.get('raceName', 'Formula 1 Grand Prix')} Race")
        event.add("location", (((race.get("Circuit") or {}).get("Location") or {}).get("country") or "Formula 1"))
        event.add("description", f"Formula 1 round {race.get('round')} generated from Jolpica schedule fallback.")
        event.add("dtstart", start)
        event.add("dtend", start + timedelta(hours=2))
        calendar.add_component(event)
    return calendar


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
        team = canonical_constructor_name(constructors[0].get("name") if constructors else "Unknown Team")
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
    all_pitstops = []
    for pit_race in data.get("pitstops", []) or []:
        all_pitstops.extend(pit_race.get("PitStops", []) or [])
    all_stints = data.get("stints", []) or data.get("Stints", []) or []
    race_control_events = data.get("race_control", []) or data.get("raceControl", []) or data.get("race_control_messages", []) or []
    weather_context = data.get("weather", {}) if isinstance(data.get("weather", {}), dict) else {}

    race_id = f"{season}-{round_no}"
    circuit = race.get("Circuit", {})
    circuit_id = circuit.get("circuitId")
    race_dt = parse_race_datetime(race)
    field_size = len(result_races[0].get("Results", [])) or 20

    for result in result_races[0].get("Results", []):
        driver = result.get("Driver", {})
        constructor = result.get("Constructor", {})
        driver_id = driver.get("driverId")
        team = canonical_constructor_name(constructor.get("name"))
        pos = safe_int(result.get("positionOrder") or result.get("position"))
        grid = safe_int(result.get("grid"))
        status = str(result.get("status", ""))

        if not driver_id or not team or not pos:
            continue

        dm = lap_metrics.get(driver_id, {})
        pm = pit_metrics.get(driver_id, {})
        fastest_lap_seconds = parse_lap_time_to_seconds(((result.get("FastestLap") or {}).get("Time") or {}).get("time"))
        strategy_context = pitwall_strategy.build_strategy_context_for_driver(
            driver_id,
            pitstops=all_pitstops,
            stints=all_stints,
            race_control=race_control_events,
            weather=weather_context,
            lap_metrics=dm,
        )

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
            "grid": ((field_size + 1) if grid == 0 else grid) if grid is not None and grid >= 0 else q_positions.get(driver_id),
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
            "strategy_context": strategy_context,
            "strategy_annotations": strategy_context.get("annotations", []),
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

    missing_source_cols = ["grid", "qualifying", "sprint_position", "avg_best_35pct_lap", "lap_consistency", "avg_pit_duration", "min_pit_duration"]
    for col in missing_source_cols:
        df[f"missing_{col}"] = pd.to_numeric(df.get(col), errors="coerce").isna().astype(int)

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

        recent3 = d_hist.tail(3)
        recent5 = d_hist.tail(5)
        recent10 = d_hist.tail(10)
        team_recent5 = t_hist.tail(5)
        team_recent10 = t_hist.tail(10)
        teammate_recent10 = t_hist[t_hist["driver_id"] != race["driver_id"]].tail(10)
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
        team_pit_std5 = safe_std(team_recent5["avg_pit_duration"]) if len(team_recent5) and "avg_pit_duration" in team_recent5 else None
        target_lap_pace = safe_float(race.get("avg_best_35pct_lap")) or safe_float(race.get("best_clean_lap"))
        teammate_finish_delta = mean_or(recent5, "finish_position", 12) - mean_or(teammate_recent10, "finish_position", mean_or(team_recent10, "finish_position", 12))
        teammate_qualifying_delta = mean_or(recent5, "qualifying", 12) - mean_or(teammate_recent10, "qualifying", mean_or(team_recent10, "qualifying", 12))
        teammate_pace_delta = driver_recent_pace - mean_or(teammate_recent10, "avg_best_35pct_lap", team_recent_pace)
        teammate_points_delta = mean_or(recent5, "points", 0) - mean_or(teammate_recent10, "points", mean_or(team_recent10, "points", 0))
        driver_recent_dnf_rate = 1 - mean_or(recent5, "is_finished", mean_or(d_hist, "is_finished", 0.85))
        team_recent_dnf_rate = 1 - mean_or(team_recent10, "is_finished", mean_or(t_hist, "is_finished", 0.85))

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
            "insufficient_driver_history": 1 if len(d_hist) < 3 else 0,
            "insufficient_team_history": 1 if len(t_hist) < 3 else 0,
            "rookie_prior": 1 if len(d_hist) == 0 else 0,
            "missing_grid": race.get("missing_grid", 0),
            "missing_qualifying": race.get("missing_qualifying", 0),
            "missing_sprint_position": race.get("missing_sprint_position", 0),
            "missing_lap_pace": max(race.get("missing_avg_best_35pct_lap", 0), race.get("missing_lap_consistency", 0)),
            "missing_pit_data": max(race.get("missing_avg_pit_duration", 0), race.get("missing_min_pit_duration", 0)),

            "driver_avg_finish": d_hist["finish_position"].mean(),
            "driver_median_finish": d_hist["finish_position"].median(),
            "driver_avg_points": d_hist["points"].mean(),
            "driver_win_rate": d_hist["is_win"].mean(),
            "driver_podium_rate": d_hist["is_podium"].mean(),
            "driver_top10_rate": d_hist["is_top10"].mean(),
            "driver_finish_rate": d_hist["is_finished"].mean(),
            "driver_recent3_finish": recent3["finish_position"].mean(),
            "driver_recent5_finish": recent5["finish_position"].mean(),
            "driver_recent10_finish": recent10["finish_position"].mean(),
            "driver_recent3_points": recent3["points"].mean(),
            "driver_recent5_points": recent5["points"].mean(),
            "driver_recent10_points": recent10["points"].mean(),
            "driver_recent5_podium_rate": recent5["is_podium"].mean(),
            "driver_recent_grid_gain": driver_recent_grid_gain,
            "driver_finish_consistency": driver_finish_consistency or 4,
            "driver_finish_momentum": mean_or(d_hist, "finish_position", 12) - mean_or(recent3, "finish_position", 12),
            "driver_points_momentum": mean_or(recent5, "points", 0) - mean_or(d_hist, "points", 0),
            "driver_qualifying_strength_recent": mean_or(recent5, "qualifying", 12),
            "driver_qualifying_delta": mean_or(d_hist.tail(8), "qualifying", 12) - mean_or(d_hist.tail(8), "finish_position", 12),
            "driver_recent_dnf_rate": driver_recent_dnf_rate,
            "driver_teammate_finish_delta": teammate_finish_delta,
            "driver_teammate_qualifying_delta": teammate_qualifying_delta,
            "driver_teammate_pace_delta": teammate_pace_delta,
            "driver_teammate_points_delta": teammate_points_delta,
            "teammate_sample_size": len(teammate_recent10),

            "team_avg_finish": t_hist["finish_position"].mean(),
            "team_avg_points": t_hist["points"].mean(),
            "team_win_rate": t_hist["is_win"].mean(),
            "team_podium_rate": t_hist["is_podium"].mean(),
            "team_top10_rate": t_hist["is_top10"].mean(),
            "team_finish_rate": t_hist["is_finished"].mean(),
            "team_recent_points": team_recent10["points"].mean(),
            "team_recent5_points": team_recent5["points"].mean(),
            "team_recent10_finish": team_recent10["finish_position"].mean(),
            "team_recent_grid_gain": team_recent_grid_gain,
            "team_finish_consistency": team_finish_consistency or 4,
            "team_finish_momentum": mean_or(t_hist, "finish_position", 12) - mean_or(team_recent10, "finish_position", 12),
            "team_points_momentum": mean_or(team_recent10, "points", 0) - mean_or(t_hist, "points", 0),
            "team_qualifying_strength_recent": mean_or(team_recent10, "qualifying", 12),
            "team_reliability_recent": mean_or(team_recent10, "is_finished", 0.85),
            "team_recent_dnf_rate": team_recent_dnf_rate,

            "driver_circuit_avg_finish": mean_or(cd_hist, "finish_position", d_hist["finish_position"].mean()),
            "driver_circuit_podium_rate": mean_or(cd_hist, "is_podium", d_hist["is_podium"].mean()),
            "driver_circuit_grid_gain": mean_or(cd_hist, "grid", 12) - mean_or(cd_hist, "finish_position", 12),
            "team_circuit_avg_finish": mean_or(ct_hist, "finish_position", t_hist["finish_position"].mean()),
            "team_circuit_podium_rate": mean_or(ct_hist, "is_podium", t_hist["is_podium"].mean()),
            "team_circuit_grid_gain": mean_or(ct_hist, "grid", 12) - mean_or(ct_hist, "finish_position", 12),
            "driver_circuit_vs_constructor": mean_or(cd_hist, "finish_position", mean_or(d_hist, "finish_position", 12)) - mean_or(ct_hist, "finish_position", mean_or(t_hist, "finish_position", 12)),

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
            "team_pit_std5": team_pit_std5 or 4,
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
        "insufficient_driver_history", "insufficient_team_history", "rookie_prior",
        "missing_grid", "missing_qualifying", "missing_sprint_position", "missing_lap_pace", "missing_pit_data",
        "driver_avg_finish", "driver_median_finish", "driver_avg_points",
        "driver_win_rate", "driver_podium_rate", "driver_top10_rate", "driver_finish_rate",
        "driver_recent3_finish", "driver_recent5_finish", "driver_recent10_finish",
        "driver_recent3_points", "driver_recent5_points", "driver_recent10_points", "driver_recent5_podium_rate",
        "driver_recent_grid_gain", "driver_finish_consistency", "driver_finish_momentum",
        "driver_points_momentum", "driver_qualifying_strength_recent", "driver_qualifying_delta",
        "driver_recent_dnf_rate", "driver_teammate_finish_delta", "driver_teammate_qualifying_delta",
        "driver_teammate_pace_delta", "driver_teammate_points_delta", "teammate_sample_size",
        "team_avg_finish", "team_avg_points", "team_win_rate", "team_podium_rate",
        "team_top10_rate", "team_finish_rate", "team_recent_points", "team_recent5_points", "team_recent10_finish",
        "team_recent_grid_gain", "team_finish_consistency", "team_finish_momentum",
        "team_points_momentum", "team_qualifying_strength_recent", "team_reliability_recent", "team_recent_dnf_rate",
        "driver_circuit_avg_finish", "driver_circuit_podium_rate", "driver_circuit_grid_gain",
        "team_circuit_avg_finish", "team_circuit_podium_rate", "team_circuit_grid_gain", "driver_circuit_vs_constructor",
        "career_starts", "team_starts", "circuit_experience", "driver_experience_log", "team_experience_log",
        "driver_lap_pace", "driver_lap_consistency", "driver_valid_laps", "driver_pace_momentum",
        "driver_pace_vs_team_recent", "driver_pit_duration", "driver_min_pit_duration",
        "driver_pit_vs_team_recent", "driver_pit_stop_count",
        "team_lap_pace", "team_lap_consistency", "team_pace_momentum", "team_pace_vs_field_recent",
        "team_pit_duration", "team_min_pit_duration", "team_pit_std5", "team_pit_vs_field_recent", "team_pit_stop_count",
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


def optional_dataset_source_statuses():
    statuses = {}
    if f1db_status is not None:
        try:
            statuses["f1db"] = f1db_status()
        except Exception as error:
            statuses["f1db"] = {
                "source_name": "F1DB",
                "source_type": "historical_dataset",
                "enabled": os.getenv("F1DB_ENABLED", "false").lower() == "true",
                "available": False,
                "status": "error",
                "confidence": 0.2,
                "error": str(error),
            }
    else:
        statuses["f1db"] = {"source_name": "F1DB", "available": False, "status": "adapter_import_failed", "confidence": 0.2}
    if relbench_status is not None:
        try:
            statuses["relbench_f1"] = relbench_status(download=False)
        except Exception as error:
            statuses["relbench_f1"] = {
                "source_name": "RelBench rel-f1",
                "source_type": "offline_relational_benchmark",
                "enabled": os.getenv("RELBENCH_F1_ENABLED", "false").lower() == "true",
                "available": False,
                "status": "error",
                "confidence": 0.2,
                "error": str(error),
            }
    else:
        statuses["relbench_f1"] = {"source_name": "RelBench rel-f1", "available": False, "status": "adapter_import_failed", "confidence": 0.2}
    return statuses


def write_model_artifacts(meta=None):
    ensure_dirs()
    meta = meta or read_model_meta()
    metrics = meta.get("metrics") or {}
    feature_selection = meta.get("feature_selection") or {}
    feature_columns = meta.get("feature_columns") or []
    ranking = (metrics.get("finish_position") or {}).get("ranking") or {}
    oot = metrics.get("out_of_time_test") or {}
    oot_spearman = safe_float((oot.get("ranking") or {}).get("spearman"))
    drift_threshold = float(os.getenv("DRIFT_SPEARMAN_THRESHOLD", "0.55"))
    drift_status = "insufficient_out_of_time_history"
    if oot_spearman is not None:
        drift_status = "retrain_recommended" if oot_spearman < drift_threshold else "stable"
    dataset_sources = optional_dataset_source_statuses()
    evaluation = {
        "schema_version": MODEL_SCHEMA_VERSION,
        "generated_at": now_local().isoformat(),
        "trained_at": meta.get("trained_at"),
        "validation_split": metrics.get("validation_split") or meta.get("validation_split") or {},
        "metrics": {
            "winner_accuracy": ranking.get("winner_hit"),
            "top3_recall": ranking.get("top3_recall"),
            "top3_precision": ranking.get("top3_precision"),
            "top10_recall": ranking.get("top10_recall"),
            "top10_precision": ranking.get("top10_precision"),
            "spearman_rank_correlation": ranking.get("spearman"),
            "ndcg_at_3": ranking.get("ndcg_at_3"),
            "ndcg_at_10": ranking.get("ndcg_at_10"),
            "finish_mae": (metrics.get("finish_position") or {}).get("mae"),
            "finish_rmse": (metrics.get("finish_position") or {}).get("rmse"),
            "lap_delta_mae": (metrics.get("lap_time_delta_forecast") or {}).get("mae_seconds"),
            "lap_delta_rmse": (metrics.get("lap_time_delta_forecast") or {}).get("rmse_seconds"),
            "win_brier": (metrics.get("win") or {}).get("brier"),
            "podium_brier": (metrics.get("podium") or {}).get("brier"),
            "top10_brier": (metrics.get("top10") or {}).get("brier"),
        },
        "out_of_time_test": oot,
        "baselines": metrics.get("baselines") or {},
        "promotion_decision": model_promotion_decision(meta.get("training_decision") or {}, metrics),
        "drift_monitor": {
            "metric": "out_of_time_spearman_proxy",
            "threshold": drift_threshold,
            "latest_value": oot_spearman,
            "status": drift_status,
            "note": "Race-level rolling drift is exported when enough post-race correction history exists; this proxy prevents silent degradation meanwhile.",
        },
        "dataset_sources": dataset_sources,
    }
    feature_importance = {
        "schema_version": MODEL_SCHEMA_VERSION,
        "generated_at": now_local().isoformat(),
        "feature_count": len(feature_columns),
        "feature_columns_hash": meta.get("feature_columns_hash") or feature_columns_hash(feature_columns),
        "feature_columns": feature_columns,
        "feature_selection": feature_selection,
        "top_importances": feature_selection.get("top_importances") or {},
        "method": feature_selection.get("method", "not_available"),
    }
    training_metadata = {
        "schema_version": MODEL_SCHEMA_VERSION,
        "generated_at": now_local().isoformat(),
        "trained_at": meta.get("trained_at"),
        "model_schema_version": meta.get("model_schema_version") or MODEL_SCHEMA_VERSION,
        "ml_start_year": meta.get("ml_start_year"),
        "rows_raw": meta.get("rows_raw"),
        "rows_features": meta.get("rows_features"),
        "latest_completed_race_id": meta.get("latest_completed_race_id"),
        "feature_columns_hash": meta.get("feature_columns_hash"),
        "optional_ml_backends": meta.get("optional_ml_backends") or {"lightgbm": lgb is not None, "xgboost": xgb is not None, "shap": shap is not None},
        "training_action": meta.get("training_action"),
        "training_reasons": meta.get("training_reasons"),
        "imputation": meta.get("imputation"),
        "dataset_sources": dataset_sources,
    }
    artifacts = {
        "evaluation.json": evaluation,
        "feature_importance.json": feature_importance,
        "training_metadata.json": training_metadata,
    }
    for filename, payload in artifacts.items():
        (MODEL_ARTIFACTS_DIR / filename).write_text(json.dumps(payload, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    return artifacts


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
    if meta and not meta.get("feature_columns_hash"):
        reasons.append("feature_schema_hash_missing")

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
        "top3_precision": [],
        "top5_recall": [],
        "top5_precision": [],
        "top10_recall": [],
        "top10_precision": [],
        "ndcg_at_3": [],
        "ndcg_at_10": [],
        "spearman": [],
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
            hit_rate = len(actual & predicted) / max(1, len(actual))
            metrics[key].append(hit_rate)
            metrics[key.replace("recall", "precision")].append(hit_rate)

        try:
            relevance = (len(group) + 1 - group["finish_position"].astype(float)).to_numpy()[None, :]
            predicted_score = (len(group) + 1 - group["predicted_finish_position"].astype(float)).to_numpy()[None, :]
            metrics["ndcg_at_3"].append(float(ndcg_score(relevance, predicted_score, k=min(3, len(group)))))
            metrics["ndcg_at_10"].append(float(ndcg_score(relevance, predicted_score, k=min(10, len(group)))))
        except Exception:
            pass

        try:
            rho = spearmanr(group["finish_position"].astype(float), group["predicted_finish_position"].astype(float)).correlation
            if np.isfinite(rho):
                metrics["spearman"].append(float(rho))
        except Exception:
            pass

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


def baseline_validation_metrics(valid_df):
    baselines = {}
    candidates = {
        "grid_order": valid_df.get("grid_position"),
        "qualifying_only": valid_df.get("qualifying_position"),
        "driver_recent_form": valid_df.get("driver_recent3_finish"),
        "constructor_form": valid_df.get("team_avg_finish"),
        "driver_championship_form": valid_df.get("driver_avg_points"),
    }
    for name, values in candidates.items():
        if values is None:
            continue
        series = pd.to_numeric(values, errors="coerce")
        if name in {"driver_championship_form"}:
            race_pred = []
            for _, group in valid_df.assign(_baseline=series).groupby("race_id"):
                ranked = group["_baseline"].rank(method="first", ascending=False)
                race_pred.extend(ranked.reindex(group.index).tolist())
            pred = np.array(race_pred, dtype=float)
        else:
            pred = series.fillna(series.median() if pd.notna(series.median()) else 12).to_numpy(dtype=float)
        try:
            mae = mean_absolute_error(valid_df["finish_position"].astype(float), np.clip(pred, 1, 24))
        except Exception:
            mae = None
        baselines[name] = {
            "finish_mae": float(mae) if mae is not None else None,
            "ranking": ranking_validation_metrics(valid_df, np.clip(pred, 1, 24)),
        }
    return baselines


def chronological_group_split(feature_df):
    race_order = (
        feature_df[["race_id", "season", "round"]]
        .drop_duplicates()
        .sort_values(["season", "round"])
        .reset_index(drop=True)
    )
    train_ids = set(race_order[race_order["season"] <= 2021]["race_id"])
    validation_ids = set(race_order[(race_order["season"] >= 2022) & (race_order["season"] <= 2024)]["race_id"])
    test_ids = set(race_order[race_order["season"] >= 2025]["race_id"])
    method = "season_grouped_train_2018_2021_validate_2022_2024_test_2025_plus"
    if len(train_ids) < 20 or len(validation_ids) < 15:
        validation_race_count = max(12, min(30, int(round(len(race_order) * 0.28))))
        validation_ids = set(race_order.tail(validation_race_count)["race_id"])
        train_ids = set(race_order[~race_order["race_id"].isin(validation_ids)]["race_id"])
        test_ids = set()
        method = "chronological_grouped_by_race_expanded_validation"
    train_df = feature_df[feature_df["race_id"].isin(train_ids)].copy()
    valid_df = feature_df[feature_df["race_id"].isin(validation_ids)].copy()
    test_df = feature_df[feature_df["race_id"].isin(test_ids)].copy()
    return train_df, valid_df, {
        "method": method,
        "train_races": int(train_df["race_id"].nunique()),
        "validation_races": int(valid_df["race_id"].nunique()),
        "test_races": int(test_df["race_id"].nunique()),
        "validation_rows": int(len(valid_df)),
        "test_rows": int(len(test_df)),
        "validation_race_ids": list(race_order[race_order["race_id"].isin(validation_ids)]["race_id"]),
        "test_race_ids": list(race_order[race_order["race_id"].isin(test_ids)]["race_id"]),
        "train_seasons": sorted([int(x) for x in train_df["season"].dropna().unique()]),
        "validation_seasons": sorted([int(x) for x in valid_df["season"].dropna().unique()]),
        "test_seasons": sorted([int(x) for x in test_df["season"].dropna().unique()]),
    }


def carve_calibration_split(train_df):
    if train_df.empty or "race_id" not in train_df:
        return train_df, pd.DataFrame(), {"calibration_races": 0, "status": "unavailable"}
    race_order = (
        train_df[["race_id", "season", "round"]]
        .drop_duplicates()
        .sort_values(["season", "round"])
        .reset_index(drop=True)
    )
    if len(race_order) < 10:
        return train_df, pd.DataFrame(), {"calibration_races": 0, "status": "insufficient_grouped_races"}
    calibration_count = max(2, min(5, int(round(len(race_order) * 0.12))))
    calibration_ids = set(race_order.tail(calibration_count)["race_id"])
    core_train_df = train_df[~train_df["race_id"].isin(calibration_ids)].copy()
    calibration_df = train_df[train_df["race_id"].isin(calibration_ids)].copy()
    if len(core_train_df) < 60 or len(calibration_df) < 20:
        return train_df, pd.DataFrame(), {"calibration_races": 0, "status": "insufficient_rows_after_group_split"}
    return core_train_df, calibration_df, {
        "calibration_races": int(calibration_df["race_id"].nunique()),
        "calibration_race_ids": list(race_order.tail(calibration_count)["race_id"]),
        "status": "empirical_probability_calibration_split",
    }


def fit_probability_calibrator(probabilities, targets, bins=8):
    probs = np.asarray(probabilities, dtype=float)
    y = np.asarray(targets, dtype=float)
    valid = np.isfinite(probs) & np.isfinite(y)
    probs = np.clip(probs[valid], 0.0, 1.0)
    y = y[valid]
    if len(probs) < 30 or len(np.unique(y)) < 2:
        return {
            "method": "identity_insufficient_calibration_data",
            "rows": int(len(probs)),
            "positive_rate": float(np.mean(y)) if len(y) else None,
        }
    unique_probs = np.unique(probs)
    bin_count = max(3, min(bins, len(unique_probs), len(probs) // 8))
    edges = np.unique(np.quantile(probs, np.linspace(0, 1, bin_count + 1)))
    if len(edges) < 3:
        return {
            "method": "identity_low_probability_spread",
            "rows": int(len(probs)),
            "positive_rate": float(np.mean(y)),
        }
    centers = []
    observed = []
    counts = []
    for low, high in zip(edges[:-1], edges[1:]):
        mask = (probs >= low) & (probs <= high if high == edges[-1] else probs < high)
        if not mask.any():
            continue
        centers.append(float(np.mean(probs[mask])))
        observed.append(float(np.mean(y[mask])))
        counts.append(int(mask.sum()))
    if len(centers) < 2:
        return {
            "method": "identity_insufficient_bins",
            "rows": int(len(probs)),
            "positive_rate": float(np.mean(y)),
        }
    order = np.argsort(centers)
    centers = [centers[i] for i in order]
    observed = [observed[i] for i in order]
    counts = [counts[i] for i in order]
    calibrated = np.interp(probs, centers, observed, left=observed[0], right=observed[-1])
    return {
        "method": "empirical_quantile_bins",
        "rows": int(len(probs)),
        "centers": centers,
        "observed_rates": observed,
        "counts": counts,
        "brier_before": float(brier_score_loss(y.astype(int), probs)),
        "brier_after": float(brier_score_loss(y.astype(int), np.clip(calibrated, 0.0, 1.0))),
    }


def apply_probability_calibrator(probabilities, calibrator):
    probs = np.asarray(probabilities, dtype=float)
    if not calibrator or calibrator.get("method") != "empirical_quantile_bins":
        return np.clip(probs, 0.0, 1.0)
    centers = np.asarray(calibrator.get("centers") or [], dtype=float)
    observed = np.asarray(calibrator.get("observed_rates") or [], dtype=float)
    if len(centers) < 2 or len(observed) != len(centers):
        return np.clip(probs, 0.0, 1.0)
    return np.clip(np.interp(probs, centers, observed, left=observed[0], right=observed[-1]), 0.0, 1.0)


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

    train_df, valid_df, validation_split = chronological_group_split(feature_df)
    train_df, calibration_df, calibration_split = carve_calibration_split(train_df)
    validation_split.update(calibration_split)
    if len(train_df) < 60 or len(valid_df) < 20:
        print("Grouped chronological validation split is too small. Keeping current model bundle.")
        existing = load_ml_bundle()
        if existing:
            existing["training_action"] = "loaded_current_model_validation_split_too_small"
            existing["training_decision"] = retrain_decision
            return existing
        raise RuntimeError("Insufficient grouped race data for leakage-safe training and no existing model bundle is available.")

    feature_columns, feature_selection = select_feature_columns_by_importance(train_df, feature_columns)
    X_train, feature_imputer = prepare_feature_matrix(train_df, feature_columns, fit=True)
    X_valid, _ = prepare_feature_matrix(valid_df, feature_columns, imputer=feature_imputer)
    test_df = feature_df[feature_df["race_id"].isin(set(validation_split.get("test_race_ids") or []))].copy()
    X_test = None
    if not test_df.empty:
        X_test, _ = prepare_feature_matrix(test_df, feature_columns, imputer=feature_imputer)
    X_calibration = None
    if not calibration_df.empty:
        X_calibration, _ = prepare_feature_matrix(calibration_df, feature_columns, imputer=feature_imputer)
    training_feature_columns = feature_matrix_columns(feature_columns)

    targets = {"win": "is_win", "podium": "is_podium", "top10": "is_top10"}
    models = {}
    metrics = {}
    validation_probabilities = {}
    probability_calibrators = {}
    train_weights = season_sample_weights(train_df)
    calibration_weights = season_sample_weights(calibration_df) if not calibration_df.empty else None

    for name, target_col in targets.items():
        y_train = train_df[target_col].astype(int)
        y_valid = valid_df[target_col].astype(int)

        rf = RandomForestClassifier(
            n_estimators=280,
            max_depth=12,
            min_samples_leaf=5,
            max_features="sqrt",
            random_state=42,
            n_jobs=-1,
            class_weight="balanced_subsample",
        )
        et = ExtraTreesClassifier(
            n_estimators=260,
            max_depth=12,
            min_samples_leaf=5,
            max_features="sqrt",
            random_state=84,
            n_jobs=-1,
            class_weight="balanced",
        )
        hgb = HistGradientBoostingClassifier(
            max_iter=180,
            learning_rate=0.055,
            max_leaf_nodes=31,
            max_depth=5,
            l2_regularization=0.1,
            random_state=42,
        )
        lgb_model = None
        xgb_model = None
        if lgb is not None:
            lgb_model = lgb.LGBMClassifier(
                n_estimators=420,
                learning_rate=0.05,
                max_depth=6,
                num_leaves=31,
                subsample=0.8,
                colsample_bytree=0.7,
                reg_lambda=0.1,
                objective="binary",
                random_state=126,
                n_jobs=-1,
                verbose=-1,
            )
        if xgb is not None:
            xgb_model = xgb.XGBClassifier(
                n_estimators=420,
                eta=0.05,
                max_depth=6,
                subsample=0.8,
                colsample_bytree=0.7,
                reg_lambda=1.0,
                objective="binary:logistic",
                eval_metric="logloss",
                random_state=168,
                n_jobs=-1,
            )

        rf.fit(X_train, y_train, sample_weight=train_weights)
        et.fit(X_train, y_train, sample_weight=train_weights)
        hgb.fit(X_train, y_train, sample_weight=train_weights)
        if lgb_model is not None:
            lgb_model.fit(X_train, y_train, sample_weight=train_weights)
        if xgb_model is not None:
            xgb_model.fit(X_train, y_train, sample_weight=train_weights)

        if X_calibration is not None and not calibration_df.empty:
            y_calibration = calibration_df[target_col].astype(int)
            cal_parts = [
                (rf.predict_proba(X_calibration)[:, 1], 0.32),
                (hgb.predict_proba(X_calibration)[:, 1], 0.28),
                (et.predict_proba(X_calibration)[:, 1], 0.18),
            ]
            if lgb_model is not None:
                cal_parts.append((lgb_model.predict_proba(X_calibration)[:, 1], 0.14))
            if xgb_model is not None:
                cal_parts.append((xgb_model.predict_proba(X_calibration)[:, 1], 0.08))
            weight_sum = sum(weight for _, weight in cal_parts)
            cal_prob = sum(prob * (weight / weight_sum) for prob, weight in cal_parts)
            probability_calibrators[name] = fit_probability_calibrator(cal_prob, y_calibration)
        else:
            probability_calibrators[name] = {"method": "identity_no_calibration_split", "rows": 0}

        valid_parts = [
            (rf.predict_proba(X_valid)[:, 1], 0.32),
            (hgb.predict_proba(X_valid)[:, 1], 0.28),
            (et.predict_proba(X_valid)[:, 1], 0.18),
        ]
        if lgb_model is not None:
            valid_parts.append((lgb_model.predict_proba(X_valid)[:, 1], 0.14))
        if xgb_model is not None:
            valid_parts.append((xgb_model.predict_proba(X_valid)[:, 1], 0.08))
        weight_sum = sum(weight for _, weight in valid_parts)
        raw_prob = sum(prob * (weight / weight_sum) for prob, weight in valid_parts)
        prob = apply_probability_calibrator(raw_prob, probability_calibrators.get(name))

        try:
            auc = roc_auc_score(y_valid, prob)
        except Exception:
            auc = None
        try:
            brier = brier_score_loss(y_valid, prob)
        except Exception:
            brier = None
        try:
            raw_brier = brier_score_loss(y_valid, raw_prob)
        except Exception:
            raw_brier = None

        models[name] = {"rf": rf, "hgb": hgb, "et": et, "lgb": lgb_model, "xgb": xgb_model}
        metrics[name] = {
            "auc": auc,
            "brier": brier,
            "raw_brier": raw_brier,
            "calibration_method": probability_calibrators.get(name, {}).get("method"),
            "validation_rows": len(valid_df),
        }
        validation_probabilities[name] = prob

    y_train_finish = train_df["finish_position"].astype(float)
    y_valid_finish = valid_df["finish_position"].astype(float)
    rf_finish = RandomForestRegressor(
        n_estimators=340,
        max_depth=12,
        min_samples_leaf=5,
        max_features="sqrt",
        random_state=42,
        n_jobs=-1,
    )
    et_finish = ExtraTreesRegressor(
        n_estimators=320,
        max_depth=12,
        min_samples_leaf=5,
        max_features="sqrt",
        random_state=84,
        n_jobs=-1,
    )
    hgb_finish = HistGradientBoostingRegressor(
        max_iter=230,
        learning_rate=0.045,
        max_leaf_nodes=31,
        max_depth=5,
        l2_regularization=0.1,
        random_state=42,
    )
    lgb_finish = None
    if lgb is not None:
        lgb_finish = lgb.LGBMRegressor(
            n_estimators=460,
            learning_rate=0.045,
            max_depth=6,
            num_leaves=31,
            subsample=0.8,
            colsample_bytree=0.7,
            reg_lambda=0.1,
            random_state=252,
            n_jobs=-1,
            verbose=-1,
        )
    rf_finish.fit(X_train, y_train_finish, sample_weight=train_weights)
    et_finish.fit(X_train, y_train_finish, sample_weight=train_weights)
    hgb_finish.fit(X_train, y_train_finish, sample_weight=train_weights)
    if lgb_finish is not None:
        lgb_finish.fit(X_train, y_train_finish, sample_weight=train_weights)
    finish_parts = [
        (rf_finish.predict(X_valid), 0.30),
        (hgb_finish.predict(X_valid), 0.38),
        (et_finish.predict(X_valid), 0.18),
    ]
    if lgb_finish is not None:
        finish_parts.append((lgb_finish.predict(X_valid), 0.14))
    finish_weight_sum = sum(weight for _, weight in finish_parts)
    finish_pred = sum(pred * (weight / finish_weight_sum) for pred, weight in finish_parts)
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
    if X_test is not None and len(test_df) >= 20:
        test_parts = [
            (rf_finish.predict(X_test), 0.30),
            (hgb_finish.predict(X_test), 0.38),
            (et_finish.predict(X_test), 0.18),
        ]
        if lgb_finish is not None:
            test_parts.append((lgb_finish.predict(X_test), 0.14))
        test_weight_sum = sum(weight for _, weight in test_parts)
        test_finish_pred = np.clip(sum(pred * (weight / test_weight_sum) for pred, weight in test_parts), 1, 24)
        metrics["out_of_time_test"] = {
            "rows": len(test_df),
            "races": int(test_df["race_id"].nunique()),
            "seasons": sorted([int(x) for x in test_df["season"].dropna().unique()]),
            "finish_mae": float(mean_absolute_error(test_df["finish_position"].astype(float), test_finish_pred)),
            "ranking": ranking_validation_metrics(test_df, test_finish_pred),
            "baselines": baseline_validation_metrics(test_df),
        }
    if "win" in validation_probabilities:
        win_prob_finish_proxy = 1 + (1 - validation_probabilities["win"]) * 19
        metrics["win_probability_ranking"] = ranking_validation_metrics(valid_df, win_prob_finish_proxy)

    lap_pace_model = None
    lap_pace_model_kind = None
    lap_train_df = train_df[pd.to_numeric(train_df.get("target_lap_pace"), errors="coerce").notna()].copy()
    lap_valid_df = valid_df[pd.to_numeric(valid_df.get("target_lap_pace"), errors="coerce").notna()].copy()
    if len(lap_train_df) >= 80 and len(lap_valid_df) >= 20:
        X_lap_train, _ = prepare_feature_matrix(lap_train_df, feature_columns, imputer=feature_imputer)
        X_lap_valid, _ = prepare_feature_matrix(lap_valid_df, feature_columns, imputer=feature_imputer)
        train_baseline = pd.to_numeric(lap_train_df["track_lap_pace_baseline"], errors="coerce").fillna(pd.to_numeric(lap_train_df["target_lap_pace"], errors="coerce").median())
        valid_baseline = pd.to_numeric(lap_valid_df["track_lap_pace_baseline"], errors="coerce").fillna(pd.to_numeric(lap_valid_df["target_lap_pace"], errors="coerce").median())
        y_lap_train_raw = pd.to_numeric(lap_train_df["target_lap_pace"], errors="coerce").astype(float)
        y_lap_valid = pd.to_numeric(lap_valid_df["target_lap_pace"], errors="coerce").astype(float)
        y_lap_train = y_lap_train_raw - train_baseline
        if lgb is not None:
            lap_pace_model = lgb.LGBMRegressor(
                n_estimators=360,
                learning_rate=0.04,
                max_depth=5,
                num_leaves=24,
                subsample=0.85,
                colsample_bytree=0.75,
                reg_lambda=0.15,
                random_state=294,
                n_jobs=-1,
                verbose=-1,
            )
            lap_pace_model_kind = "lightgbm_lap_delta"
        else:
            lap_pace_model = HistGradientBoostingRegressor(
                max_iter=260,
                learning_rate=0.045,
                max_depth=5,
                max_leaf_nodes=31,
                l2_regularization=0.1,
                random_state=294,
            )
            lap_pace_model_kind = "hist_gradient_boosting_lap_delta"
        lap_pace_model.fit(X_lap_train, y_lap_train, sample_weight=season_sample_weights(lap_train_df))
        lap_delta_pred = np.clip(lap_pace_model.predict(X_lap_valid), -8, 8)
        lap_pred = np.clip(valid_baseline.to_numpy(dtype=float) + lap_delta_pred, 45, 180)
        metrics["lap_time_delta_forecast"] = {
            "model": lap_pace_model_kind,
            "target": "target_lap_pace_minus_circuit_baseline",
            "mae_seconds": float(mean_absolute_error(y_lap_valid, lap_pred)),
            "rmse_seconds": float(np.sqrt(np.mean((np.array(y_lap_valid) - lap_pred) ** 2))),
            "validation_rows": len(lap_valid_df),
        }
    else:
        metrics["lap_time_delta_forecast"] = {
            "status": "insufficient_lap_time_rows",
            "train_rows": len(lap_train_df),
            "validation_rows": len(lap_valid_df),
        }
    metrics["neural_lap_time_forecast"] = {
        **metrics["lap_time_delta_forecast"],
        "deprecated_name": True,
        "replacement": "lap_time_delta_forecast",
    }

    baseline_metrics = baseline_validation_metrics(valid_df)
    finish_mae = safe_float(metrics.get("finish_position", {}).get("mae"))
    metrics["baselines"] = baseline_metrics
    metrics["validation_split"] = validation_split
    metrics["feature_matrix"] = {
        "base_feature_count": len(feature_columns),
        "model_feature_count": len(training_feature_columns),
        "missingness_indicators": len(training_feature_columns) - len(feature_columns),
        "imputation": "median_with_explicit_missingness_flags",
    }
    if finish_mae is not None:
        metrics["finish_position"]["beats_baselines"] = {
            name: bool(safe_float(row.get("finish_mae")) is not None and finish_mae <= safe_float(row.get("finish_mae")))
            for name, row in baseline_metrics.items()
        }

    latest_id = latest_completed_race_id()
    bundle = {
        "models": models,
        "finish_model": {"rf": rf_finish, "hgb": hgb_finish, "et": et_finish, "lgb": lgb_finish},
        "lap_pace_model": lap_pace_model,
        "lap_pace_model_kind": lap_pace_model_kind,
        "feature_imputer": feature_imputer,
        "model_feature_columns": training_feature_columns,
        "probability_calibrators": probability_calibrators,
        "feature_columns": feature_columns,
        "feature_columns_hash": feature_columns_hash(feature_columns),
        "trained_at": now_local().isoformat(),
        "ml_start_year": ML_START_YEAR,
        "latest_completed_race_id": latest_id,
        "metrics": metrics,
        "model_schema_version": MODEL_SCHEMA_VERSION,
        "training_action": "retrained_model",
        "training_decision": retrain_decision,
        "feature_selection": feature_selection,
        "optional_ml_backends": {"lightgbm": lgb is not None, "xgboost": xgb is not None, "shap": shap is not None},
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
        "feature_columns_hash": feature_columns_hash(feature_columns),
        "model_feature_columns": training_feature_columns,
        "feature_selection": feature_selection,
        "optional_ml_backends": {"lightgbm": lgb is not None, "xgboost": xgb is not None, "shap": shap is not None},
        "validation_split": validation_split,
        "probability_calibration": {k: {kk: vv for kk, vv in v.items() if kk not in {"centers", "observed_rates"}} for k, v in probability_calibrators.items()},
        "imputation": {
            "method": "median_with_missingness_indicators",
            "values": {col: safe_float(value) for col, value in zip(feature_columns, feature_imputer.statistics_)},
        },
        "backfill_used_this_run": BACKFILL_BUDGET.used,
        "backfilled_races_this_run": BACKFILL_BUDGET.fetched,
        "training_action": "retrained_model",
        "training_reasons": retrain_decision.get("reasons", []),
        "result_readiness": retrain_decision.get("readiness", {}),
    }
    MODEL_META_PATH.write_text(json.dumps(meta, indent=2), encoding="utf-8")
    write_model_artifacts(meta)

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


def build_prediction_feature_rows(drivers, race, current_round_data, historical_df, feature_columns, stage="pre_weekend"):
    season = safe_int(race.get("season")) or now_local().year
    round_no = safe_int(race.get("round")) or 0
    circuit_id = race.get("Circuit", {}).get("circuitId")

    qualifying_allowed = stage in {"post_qualifying", "pre_race", "live_adjusted", "post_race_audited"}
    sprint_allowed = stage in {"post_sprint", "post_qualifying", "pre_race", "live_adjusted", "post_race_audited"}
    current_session_features_allowed = stage in {"post_fp1", "post_fp2", "post_fp3", "post_sprint_qualifying", "post_sprint", "post_qualifying", "pre_race", "live_adjusted"}

    q_positions = {}
    if qualifying_allowed and current_round_data.get("qualifying"):
        for q in current_round_data["qualifying"][0].get("QualifyingResults", []):
            q_positions[q.get("Driver", {}).get("driverId")] = safe_int(q.get("position"))

    sprint_positions = {}
    if sprint_allowed and current_round_data.get("sprint"):
        for s in current_round_data["sprint"][0].get("SprintResults", []) or current_round_data["sprint"][0].get("Results", []):
            sprint_positions[s.get("Driver", {}).get("driverId")] = safe_int(s.get("positionOrder") or s.get("position"))

    current_laps = driver_lap_metrics_from_data(current_round_data) if current_session_features_allowed else {}
    current_pits = pit_metrics_from_data(current_round_data) if current_session_features_allowed else {}

    rows = []
    for driver in drivers:
        driver_id = driver["driver_id"]
        team = canonical_constructor_name(driver["team"])
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

        recent3 = d_hist.tail(3)
        recent5 = d_hist.tail(5)
        recent10 = d_hist.tail(10)
        team_recent5 = t_hist.tail(5)
        team_recent10 = t_hist.tail(10)
        teammate_recent10 = t_hist[t_hist["driver_id"] != driver_id].tail(10) if len(t_hist) else pd.DataFrame()
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
        team_pit_std5 = safe_std(pd.to_numeric(team_recent5["avg_pit_duration"], errors="coerce")) if len(team_recent5) and "avg_pit_duration" in team_recent5 else None
        teammate_finish_delta = mean_or(recent5, "finish_position", 12) - mean_or(teammate_recent10, "finish_position", mean_or(team_recent10, "finish_position", 12))
        teammate_qualifying_delta = mean_or(recent5, "qualifying", 12) - mean_or(teammate_recent10, "qualifying", mean_or(team_recent10, "qualifying", 12))
        teammate_pace_delta = driver_recent_pace - mean_or(teammate_recent10, "avg_best_35pct_lap", team_recent_pace)
        teammate_points_delta = mean_or(recent5, "points", 0) - mean_or(teammate_recent10, "points", mean_or(team_recent10, "points", 0))
        driver_recent_dnf_rate = 1 - mean_or(recent5, "is_finished", mean_or(d_hist, "is_finished", 0.85))
        team_recent_dnf_rate = 1 - mean_or(team_recent10, "is_finished", mean_or(t_hist, "is_finished", 0.85))

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
            "grid_position": q_positions.get(driver_id) if q_positions.get(driver_id) is not None else np.nan,
            "qualifying_position": q_positions.get(driver_id) if q_positions.get(driver_id) is not None else np.nan,
            "sprint_position": sprint_positions.get(driver_id) if sprint_positions.get(driver_id) is not None else np.nan,
            "insufficient_driver_history": 1 if len(d_hist) < 3 else 0,
            "insufficient_team_history": 1 if len(t_hist) < 3 else 0,
            "rookie_prior": 1 if len(d_hist) == 0 else 0,
            "missing_grid": 0 if q_positions.get(driver_id) is not None else 1,
            "missing_qualifying": 0 if q_positions.get(driver_id) is not None else 1,
            "missing_sprint_position": 0 if sprint_positions.get(driver_id) is not None else 1,
            "missing_lap_pace": 0 if lap_now.get("avg_best_35pct") is not None else 1,
            "missing_pit_data": 0 if pit_now.get("avg_pit_duration") is not None else 1,

            "driver_avg_finish": mean_or(d_hist, "finish_position", 12),
            "driver_median_finish": float(pd.to_numeric(d_hist["finish_position"], errors="coerce").median()) if len(d_hist) else 12,
            "driver_avg_points": mean_or(d_hist, "points", 0),
            "driver_win_rate": mean_or(d_hist, "is_win", 0),
            "driver_podium_rate": mean_or(d_hist, "is_podium", 0),
            "driver_top10_rate": mean_or(d_hist, "is_top10", 0),
            "driver_finish_rate": mean_or(d_hist, "is_finished", 0.85),
            "driver_recent3_finish": mean_or(recent3, "finish_position", mean_or(d_hist, "finish_position", 12)),
            "driver_recent5_finish": mean_or(recent5, "finish_position", mean_or(d_hist, "finish_position", 12)),
            "driver_recent10_finish": mean_or(recent10, "finish_position", mean_or(d_hist, "finish_position", 12)),
            "driver_recent3_points": mean_or(recent3, "points", mean_or(d_hist, "points", 0)),
            "driver_recent5_points": mean_or(recent5, "points", mean_or(d_hist, "points", 0)),
            "driver_recent10_points": mean_or(recent10, "points", mean_or(d_hist, "points", 0)),
            "driver_recent5_podium_rate": mean_or(recent5, "is_podium", mean_or(d_hist, "is_podium", 0)),
            "driver_recent_grid_gain": driver_recent_grid_gain,
            "driver_finish_consistency": driver_finish_consistency or 4,
            "driver_finish_momentum": mean_or(d_hist, "finish_position", 12) - mean_or(d_hist.tail(3), "finish_position", 12),
            "driver_points_momentum": mean_or(d_hist.tail(5), "points", 0) - mean_or(d_hist, "points", 0),
            "driver_qualifying_strength_recent": mean_or(recent5, "qualifying", 12),
            "driver_qualifying_delta": mean_or(d_hist.tail(8), "qualifying", 12) - mean_or(d_hist.tail(8), "finish_position", 12),
            "driver_recent_dnf_rate": driver_recent_dnf_rate,
            "driver_teammate_finish_delta": teammate_finish_delta,
            "driver_teammate_qualifying_delta": teammate_qualifying_delta,
            "driver_teammate_pace_delta": teammate_pace_delta,
            "driver_teammate_points_delta": teammate_points_delta,
            "teammate_sample_size": len(teammate_recent10),

            "team_avg_finish": mean_or(t_hist, "finish_position", 12),
            "team_avg_points": mean_or(t_hist, "points", 0),
            "team_win_rate": mean_or(t_hist, "is_win", 0),
            "team_podium_rate": mean_or(t_hist, "is_podium", 0),
            "team_top10_rate": mean_or(t_hist, "is_top10", 0),
            "team_finish_rate": mean_or(t_hist, "is_finished", 0.85),
            "team_recent_points": mean_or(t_hist.tail(10), "points", mean_or(t_hist, "points", 0)),
            "team_recent5_points": mean_or(team_recent5, "points", mean_or(t_hist, "points", 0)),
            "team_recent10_finish": mean_or(team_recent10, "finish_position", mean_or(t_hist, "finish_position", 12)),
            "team_recent_grid_gain": team_recent_grid_gain,
            "team_finish_consistency": team_finish_consistency or 4,
            "team_finish_momentum": mean_or(t_hist, "finish_position", 12) - mean_or(team_recent10, "finish_position", 12),
            "team_points_momentum": mean_or(team_recent10, "points", 0) - mean_or(t_hist, "points", 0),
            "team_qualifying_strength_recent": mean_or(team_recent10, "qualifying", 12),
            "team_reliability_recent": mean_or(team_recent10, "is_finished", 0.85),
            "team_recent_dnf_rate": team_recent_dnf_rate,

            "driver_circuit_avg_finish": mean_or(cd_hist, "finish_position", mean_or(d_hist, "finish_position", 12)),
            "driver_circuit_podium_rate": mean_or(cd_hist, "is_podium", mean_or(d_hist, "is_podium", 0)),
            "driver_circuit_grid_gain": mean_or(cd_hist, "grid", 12) - mean_or(cd_hist, "finish_position", 12),
            "team_circuit_avg_finish": mean_or(ct_hist, "finish_position", mean_or(t_hist, "finish_position", 12)),
            "team_circuit_podium_rate": mean_or(ct_hist, "is_podium", mean_or(t_hist, "is_podium", 0)),
            "team_circuit_grid_gain": mean_or(ct_hist, "grid", 12) - mean_or(ct_hist, "finish_position", 12),
            "driver_circuit_vs_constructor": mean_or(cd_hist, "finish_position", mean_or(d_hist, "finish_position", 12)) - mean_or(ct_hist, "finish_position", mean_or(t_hist, "finish_position", 12)),
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
            "team_pit_std5": team_pit_std5 or 4,
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


def ml_predict_probabilities(drivers, race, current_round_data, bundle, stage="pre_weekend"):
    if not bundle:
        return {}, {"status": "no model bundle available"}
    try:
        feature_columns = bundle["feature_columns"]
        historical_df = historical_feature_context(bundle.get("ml_start_year", ML_START_YEAR), safe_int(race.get("season")) or now_local().year)
        pred_df = build_prediction_feature_rows(drivers, race, current_round_data, historical_df, feature_columns, stage=stage)
        feature_imputer = bundle.get("feature_imputer")
        if feature_imputer is not None:
            X, _ = prepare_feature_matrix(pred_df, feature_columns, imputer=feature_imputer)
        else:
            X = pred_df[feature_columns].replace([np.inf, -np.inf], np.nan).fillna(0)

        outputs = {}
        raw_outputs = {}
        calibrators = bundle.get("probability_calibrators") or {}
        for target, pair in bundle["models"].items():
            parts = [
                (pair["rf"].predict_proba(X)[:, 1], 0.32),
                (pair["hgb"].predict_proba(X)[:, 1], 0.28),
            ]
            if pair.get("et"):
                parts.append((pair["et"].predict_proba(X)[:, 1], 0.18))
            if pair.get("lgb") is not None:
                parts.append((pair["lgb"].predict_proba(X)[:, 1], 0.14))
            if pair.get("xgb") is not None:
                parts.append((pair["xgb"].predict_proba(X)[:, 1], 0.08))
            weight_sum = sum(weight for _, weight in parts)
            raw = sum(prob * (weight / weight_sum) for prob, weight in parts)
            raw_outputs[target] = raw
            outputs[target] = apply_probability_calibrator(raw, calibrators.get(target))
        finish_pred = None
        finish_model = bundle.get("finish_model")
        if finish_model:
            parts = [
                (finish_model["rf"].predict(X), 0.30),
                (finish_model["hgb"].predict(X), 0.38),
            ]
            if finish_model.get("et"):
                parts.append((finish_model["et"].predict(X), 0.18))
            if finish_model.get("lgb") is not None:
                parts.append((finish_model["lgb"].predict(X), 0.14))
            weight_sum = sum(weight for _, weight in parts)
            finish_pred = sum(pred * (weight / weight_sum) for pred, weight in parts)
            finish_pred = np.clip(finish_pred, 1, max(20, len(pred_df)))
        lap_pred = None
        lap_scores = {}
        lap_model = bundle.get("lap_pace_model")
        if lap_model:
            lap_raw_pred = lap_model.predict(X)
            if str(bundle.get("lap_pace_model_kind") or "").endswith("lap_delta"):
                baselines = pd.to_numeric(pred_df.get("track_lap_pace_baseline"), errors="coerce").fillna(pd.to_numeric(pred_df.get("driver_lap_pace"), errors="coerce").median()).to_numpy(dtype=float)
                lap_pred = np.clip(baselines + np.clip(lap_raw_pred, -8, 8), 45, 180)
            else:
                lap_pred = np.clip(lap_raw_pred, 45, 180)
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
                "uncalibrated_ml_win_probability": float(raw_outputs.get("win", [0])[idx] * 100),
                "uncalibrated_ml_podium_probability": float(raw_outputs.get("podium", [0])[idx] * 100),
                "uncalibrated_ml_top10_probability": float(raw_outputs.get("top10", [0])[idx] * 100),
                "calibration_method": {
                    key: (calibrators.get(key) or {}).get("method", "identity")
                    for key in ["win", "podium", "top10"]
                },
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
        name = canonical_constructor_name(row.get("Constructor", {}).get("name"))
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
    def load():
        session = fastf1.get_session(int(season), int(round_no), code)
        session.load(laps=True, weather=True, messages=False)
        return session
    executor = None
    try:
        executor = ThreadPoolExecutor(max_workers=1)
        future = executor.submit(load)
        session = future.result(timeout=FASTF1_SESSION_LOAD_TIMEOUT_SECONDS)
        executor.shutdown(wait=False, cancel_futures=True)
        print(f"FastF1 loaded {season} round {round_no} {code}")
        return session
    except TimeoutError:
        try:
            executor.shutdown(wait=False, cancel_futures=True)
        except Exception:
            pass
        print(f"FastF1 timed out after {FASTF1_SESSION_LOAD_TIMEOUT_SECONDS}s for {season} round {round_no} {code}")
        return None
    except Exception as error:
        try:
            executor.shutdown(wait=False, cancel_futures=True)
        except Exception:
            pass
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
    global OPENF1_LAST_STATUS
    if not OPENF1_ENABLED:
        OPENF1_LAST_STATUS = {"status": "disabled", "auth_required": False, "errors": []}
        return []
    if OPENF1_REQUEST_SLEEP > 0:
        time.sleep(OPENF1_REQUEST_SLEEP)
    endpoint = "/" + str(endpoint or "").lstrip("/")
    headers = {
        "User-Agent": "pitwall/3.0 openf1-optional",
        "Accept": "application/json",
    }
    if OPENF1_ACCESS_TOKEN:
        headers["Authorization"] = f"Bearer {OPENF1_ACCESS_TOKEN}"
    elif OPENF1_USERNAME and OPENF1_PASSWORD:
        raw = f"{OPENF1_USERNAME}:{OPENF1_PASSWORD}".encode("utf-8")
        headers["Authorization"] = "Basic " + base64.b64encode(raw).decode("ascii")
    response = safe_get(
        OPENF1_BASE + endpoint,
        params=params or {},
        headers=headers,
        timeout=12,
        optional_404=optional_404,
        return_on_statuses={401, 403},
    )
    if not response:
        OPENF1_LAST_STATUS = {
            "status": "unavailable",
            "auth_required": False,
            "errors": (OPENF1_LAST_STATUS.get("errors") or [])[-5:] + [f"{endpoint}: request_failed"],
        }
        return []
    if response.status_code in {401, 403}:
        detail = ""
        try:
            payload = response.json()
            detail = str(payload.get("detail") or payload.get("message") or payload.get("error") or "")
        except Exception:
            detail = str(response.text or "")[:280]
        status = "auth_required" if response.status_code == 401 else "forbidden"
        live_restricted = "live f1 session" in detail.lower() or "authenticated users" in detail.lower()
        OPENF1_LAST_STATUS = {
            "status": "live_session_auth_required" if live_restricted else status,
            "auth_required": response.status_code == 401 and not bool(OPENF1_ACCESS_TOKEN or (OPENF1_USERNAME and OPENF1_PASSWORD)),
            "status_code": response.status_code,
            "endpoint": endpoint,
            "message": detail or ("Set OPENF1_ACCESS_TOKEN for authenticated OpenF1 endpoints." if response.status_code == 401 and not (OPENF1_ACCESS_TOKEN or (OPENF1_USERNAME and OPENF1_PASSWORD)) else "OpenF1 rejected the configured credentials or endpoint."),
            "live_session_restricted": live_restricted,
            "errors": (OPENF1_LAST_STATUS.get("errors") or [])[-5:] + [f"{endpoint}: {response.status_code}"],
        }
        return []
    try:
        data = response.json()
    except Exception:
        OPENF1_LAST_STATUS = {
            "status": "malformed_response",
            "auth_required": False,
            "endpoint": endpoint,
            "errors": (OPENF1_LAST_STATUS.get("errors") or [])[-5:] + [f"{endpoint}: non_json"],
        }
        return []
    if isinstance(data, dict) and data.get("error"):
        print(f"OpenF1 unavailable for {endpoint}: {data.get('detail') or data.get('error')}")
        OPENF1_LAST_STATUS = {
            "status": "api_error",
            "auth_required": False,
            "endpoint": endpoint,
            "message": data.get("detail") or data.get("error"),
            "errors": (OPENF1_LAST_STATUS.get("errors") or [])[-5:] + [f"{endpoint}: {data.get('error')}"],
        }
        return []
    OPENF1_LAST_STATUS = {
        "status": "ok",
        "auth_required": False,
        "endpoint": endpoint,
        "rows": len(data) if isinstance(data, list) else None,
        "authenticated": bool(OPENF1_ACCESS_TOKEN or (OPENF1_USERNAME and OPENF1_PASSWORD)),
        "errors": OPENF1_LAST_STATUS.get("errors", [])[-5:],
    }
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
    if OPENF1_OPTIONAL_ONLY and not OPENF1_ACCESS_TOKEN and not (OPENF1_USERNAME and OPENF1_PASSWORD):
        empty = {key: {} for key in [
            "timing_session_result", "timing_starting_grid", "timing_lap_pace",
            "timing_sector_performance", "timing_pit_execution", "timing_stint_strength",
            "timing_telemetry_speed", "timing_position_gain", "timing_car_performance",
        ]}
        return {
            "provider_status": "openf1_skipped_optional_no_token",
            "openf1_status": {
                "status": "skipped_optional_no_token",
                "auth_required": True,
                "message": "OpenF1 is optional. FIA documents, F1 timing/static feeds, FastF1, and Jolpica are used for grid/session data unless OPENF1_ACCESS_TOKEN is configured.",
            },
            "sessions": [],
            **empty,
        }
    sessions = openf1_candidate_sessions(race)
    empty = {key: {} for key in [
        "timing_session_result", "timing_starting_grid", "timing_lap_pace",
        "timing_sector_performance", "timing_pit_execution", "timing_stint_strength",
        "timing_telemetry_speed", "timing_position_gain", "timing_car_performance",
    ]}
    if not sessions:
        status = OPENF1_LAST_STATUS.get("status")
        provider = "openf1_auth_required" if status in {"auth_required", "forbidden", "live_session_auth_required"} else "openf1_no_matching_free_sessions"
        return {"provider_status": provider, "openf1_status": dict(OPENF1_LAST_STATUS), "sessions": [], **empty}

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
        status = OPENF1_LAST_STATUS.get("status")
        provider = "openf1_auth_required" if status in {"auth_required", "forbidden", "live_session_auth_required"} else "openf1_reachable_but_no_driver_metrics"
        return {"provider_status": provider, "openf1_status": dict(OPENF1_LAST_STATUS), "sessions": notes, **empty}

    keys = list(empty.keys())
    merged = {
        key: merge_weighted_score_maps([(scores.get(key), weight) for scores, weight in per_session])
        for key in keys
    }
    return {
        "provider_status": "openf1_free_historical_timing_used",
        "openf1_status": dict(OPENF1_LAST_STATUS),
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
    has_sprint = bool(current_round_data.get("sprint"))
    if has_results and now_local() > event_start:
        return "post_race_audited", "Post-race audited"
    if has_qualifying:
        return "post_qualifying", "Post-qualifying prediction"
    if has_sprint:
        return "post_sprint", "Post-sprint race-weekend prediction"
    if event_start - now_local() <= timedelta(days=3):
        return "post_fp1", "Practice-aware race-weekend prediction"
    return "pre_weekend", "Pre-weekend prediction"


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

    if stage == "post_qualifying":
        weights["qualifying"] += 0.08
        weights["ml_podium_probability"] += 0.03
        weights["ml_finish_position_score"] += 0.03
        weights["ml_lap_time_forecast_score"] += 0.02
    elif stage in {"post_practice", "post_fp1", "post_fp2", "post_fp3", "pre_race", "live_adjusted"}:
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


def finish_points_for_position(position):
    points = {
        1: 25,
        2: 18,
        3: 15,
        4: 12,
        5: 10,
        6: 8,
        7: 6,
        8: 4,
        9: 2,
        10: 1,
    }
    position = safe_int(position)
    return points.get(position, 0)


def data_quality_checks_for_driver(driver_id, component_scores, current_round_data, stage, ml):
    missing = []
    penalties = {}
    if not current_round_data.get("qualifying"):
        missing.append("qualifying")
        penalties["missing_qualifying"] = 14 if stage in {"post_qualifying", "pre_race", "live_adjusted"} else 5
    if not current_round_data.get("laps"):
        missing.append("practice_or_lap_pace")
        penalties["missing_practice_pace"] = 6 if stage in {"post_practice", "post_fp1", "post_fp2", "post_fp3", "post_qualifying", "pre_race"} else 3
    if not current_round_data.get("pitstops"):
        missing.append("pit_stop_data")
        penalties["missing_pit_stop_data"] = 4
    if not ml:
        missing.append("model_bundle_or_driver_features")
        penalties["missing_ml_outputs"] = 18
    if component_scores.get("predicted_lap_pace_seconds") is None and component_scores.get("ml_lap_time_forecast_score") is None:
        penalties["missing_lap_forecast"] = 4
    invalid_probability = any(
        pct_value(component_scores.get(key)) is None
        for key in ["ml_win_probability", "ml_podium_probability", "ml_top10_probability"]
    )
    if invalid_probability:
        missing.append("calibrated_probabilities")
        penalties["missing_probability_calibration"] = 10
    return {
        "available": sorted(set([
            key for key, value in component_scores.items()
            if value is not None and key not in {"predicted_lap_pace_seconds"}
        ])),
        "missing": sorted(set(missing)),
        "penalties": penalties,
        "penalty_total": round(sum(penalties.values()), 2),
    }


def model_agreement_from_components(component_scores):
    groups = {
        "ml": weighted_average([
            (component_scores.get("ml_win_probability"), 0.25),
            (component_scores.get("ml_podium_probability"), 0.35),
            (component_scores.get("ml_top10_probability"), 0.20),
            (component_scores.get("ml_finish_position_score"), 0.20),
        ]),
        "racecraft": weighted_average([
            (component_scores.get("transparent_racecraft_score"), 0.35),
            (component_scores.get("driver_skill"), 0.25),
            (component_scores.get("race_pace"), 0.20),
            (component_scores.get("pit_execution"), 0.20),
        ]),
        "timing": weighted_average([
            (component_scores.get("timing_lap_pace"), 0.30),
            (component_scores.get("timing_sector_performance"), 0.25),
            (component_scores.get("timing_car_performance"), 0.25),
            (component_scores.get("fastf1_race_pace"), 0.20),
        ]),
        "weather": weighted_average([
            (component_scores.get("weather_adaptation"), 0.60),
            (component_scores.get("reliability"), 0.40),
        ]),
        "scenario": weighted_average([
            (component_scores.get("team_strategy"), 0.30),
            (component_scores.get("team_track_fit"), 0.30),
            (component_scores.get("track_trait_fit"), 0.25),
            (component_scores.get("regulation_fit"), 0.15),
        ]),
    }
    values = [v for v in groups.values() if v is not None]
    if len(values) < 2:
        return 55.0, ["not_enough_model_views"], groups
    spread = max(values) - min(values)
    agreement = clamp(100 - spread * 1.15, 0, 100, 55)
    flags = []
    if spread >= 28:
        flags.append("model_views_disagree")
    if groups.get("ml") is not None and groups.get("racecraft") is not None and abs(groups["ml"] - groups["racecraft"]) >= 24:
        flags.append("ml_vs_racecraft_split")
    if groups.get("timing") is not None and groups.get("scenario") is not None and abs(groups["timing"] - groups["scenario"]) >= 24:
        flags.append("timing_vs_scenario_split")
    return round(agreement, 2), flags, {k: round(v, 2) if v is not None else None for k, v in groups.items()}


def reason_tags_from_components(component_scores, limit=5):
    reasons = sorted(
        [(k, v) for k, v in component_scores.items() if v is not None],
        key=lambda item: item[1],
        reverse=True,
    )
    return [PREDICTION_LABELS.get(k, k).replace("official ", "").replace("ML ", "") for k, v in reasons[:limit] if v >= 55]


def weakness_tags_from_components(component_scores, evidence):
    weak = [
        PREDICTION_LABELS.get(k, k).replace("official ", "").replace("ML ", "")
        for k, v in component_scores.items()
        if v is not None and safe_float(v) < 44
    ][:4]
    missing = evidence.get("missing", [])[:3]
    return weak + [f"missing {item.replace('_', ' ')}" for item in missing]


def enrich_prediction_item(item, rank, field_size, current_round_data, profile, weather_summary, stage):
    component_scores = item.get("component_scores") or {}
    ml = {
        key: component_scores.get(key)
        for key in ["ml_win_probability", "ml_podium_probability", "ml_top10_probability", "ml_finish_position_score"]
        if component_scores.get(key) is not None
    }
    evidence = data_quality_checks_for_driver(item.get("driver_id"), component_scores, current_round_data, stage, ml)
    agreement_score, disagreement_flags, model_views = model_agreement_from_components(component_scores)
    predicted_finish = safe_float(item.get("predicted_finish_position")) or rank
    confidence = clamp(item.get("confidence"), 0, 100, 50)
    interval = max(1, int(round(4.5 - confidence / 30)))
    best_case = max(1, int(round(predicted_finish - interval)))
    worst_case = min(field_size, int(round(predicted_finish + interval + (evidence["penalty_total"] / 18))))
    reliability = weighted_average([
        (component_scores.get("reliability"), 0.45),
        (component_scores.get("team_finish_rate"), 0.15),
        (100 - evidence["penalty_total"], 0.20),
        (agreement_score, 0.20),
    ]) or confidence
    overtaking_level = text_level(profile.get("overtaking"))
    straight_mode = weighted_average([
        (component_scores.get("car_performance"), 0.30),
        (component_scores.get("track_trait_fit"), 0.25),
        (component_scores.get("regulation_fit"), 0.25),
        (100 if "straight" in str(profile.get("speed_profile", "")).lower() else 55, 0.20),
    ]) or 55
    corner_mode = weighted_average([
        (component_scores.get("team_track_fit"), 0.35),
        (component_scores.get("car_performance"), 0.25),
        (100 if "downforce" in str(profile.get("dominance", "")).lower() else 58, 0.20),
        (component_scores.get("weather_adaptation"), 0.20),
    ]) or 55
    active_aero = weighted_average([(straight_mode, 0.52), (corner_mode, 0.48)]) or 55
    energy_boost = weighted_average([
        (component_scores.get("regulation_fit"), 0.30),
        (component_scores.get("timing_telemetry_speed"), 0.22),
        (component_scores.get("car_performance"), 0.22),
        (component_scores.get("team_strategy"), 0.16),
        (overtaking_level, 0.10),
    ]) or 55
    attack = weighted_average([
        (component_scores.get("race_pace"), 0.22),
        (component_scores.get("timing_lap_pace"), 0.20),
        (energy_boost, 0.24),
        (overtaking_level, 0.16),
        (component_scores.get("team_strategy"), 0.18),
    ]) or energy_boost
    defend_risk = 100 - (weighted_average([
        (component_scores.get("qualifying"), 0.25),
        (component_scores.get("reliability"), 0.25),
        (energy_boost, 0.20),
        (component_scores.get("pit_execution"), 0.15),
        (component_scores.get("team_strategy"), 0.15),
    ]) or 55)
    win_probability = pct_value(component_scores.get("ml_win_probability"))
    podium_probability = pct_value(component_scores.get("ml_podium_probability"))
    top10_probability = pct_value(component_scores.get("ml_top10_probability"))
    expected_points = weighted_average([
        (finish_points_for_position(round(predicted_finish)), 0.55),
        ((podium_probability or 0) * 0.18, 0.20),
        ((top10_probability or 0) * 0.05, 0.25),
    ])
    item.update({
        "rank": rank,
        "previous_rank": rank,
        "rank_delta": 0,
        "confidence_delta": 0,
        "reliability": round(clamp(reliability, 0, 100, confidence), 2),
        "reason_tags": reason_tags_from_components(component_scores),
        "weakness_tags": weakness_tags_from_components(component_scores, evidence),
        "win_probability": win_probability,
        "podium_probability": podium_probability,
        "top10_probability": top10_probability,
        "best_case_finish": best_case,
        "likely_finish": int(round(predicted_finish)),
        "worst_case_finish": worst_case,
        "finish_interval_low": best_case,
        "finish_interval_high": worst_case,
        "model_agreement_score": agreement_score,
        "model_views": model_views,
        "disagreement_flags": disagreement_flags,
        "disagreement_reason": ", ".join(flag.replace("_", " ") for flag in disagreement_flags) if disagreement_flags else "Model views broadly aligned",
        "evidence_status": evidence,
        "missing_data_penalties": evidence["penalties"],
        "attack_potential_score": round(clamp(attack, 0, 100, 55), 2),
        "defend_risk_score": round(clamp(defend_risk, 0, 100, 45), 2),
        "energy_boost_advantage_score": round(clamp(energy_boost, 0, 100, 55), 2),
        "boost_attack_score": round(clamp(weighted_average([(energy_boost, 0.55), (attack, 0.45)]), 0, 100, 55), 2),
        "boost_defend_score": round(clamp(100 - defend_risk, 0, 100, 55), 2),
        "energy_deployment_risk": round(clamp(100 - energy_boost + evidence["penalty_total"] * 0.8, 0, 100, 40), 2),
        "overtake_eligibility_proxy": round(clamp(weighted_average([(attack, 0.55), (overtaking_level, 0.45)]), 0, 100, 55), 2),
        "active_aero_suitability_score": round(clamp(active_aero, 0, 100, 55), 2),
        "straight_mode_advantage": round(clamp(straight_mode, 0, 100, 55), 2),
        "corner_mode_advantage": round(clamp(corner_mode, 0, 100, 55), 2),
        "aero_switching_adaptability": round(clamp(weighted_average([(straight_mode, 0.5), (corner_mode, 0.5), (reliability, 0.2)]), 0, 100, 55), 2),
        "expected_points": round(safe_float(expected_points) or 0, 2),
        "top10_safety_score": round(clamp(weighted_average([(top10_probability, 0.55), (reliability, 0.30), (agreement_score, 0.15)]), 0, 100, 50), 2),
        "dark_horse_flag": bool(rank >= 6 and (podium_probability or 0) >= 18 and confidence >= 55),
        "bust_risk_flag": bool(rank <= 5 and (confidence < 55 or reliability < 58 or disagreement_flags)),
        "short_explanation": item.get("reason") or "Model estimate based on currently available race data.",
    })
    item.setdefault("predicted_finish", item.get("predicted_finish_position") or item.get("likely_finish"))
    item.setdefault("points_probability", item.get("top10_probability"))
    item.setdefault("fastest_lap_probability", probability_from_score(weighted_average([
        (component_scores.get("race_pace"), 0.35),
        (component_scores.get("timing_lap_pace"), 0.25),
        (component_scores.get("qualifying"), 0.20),
        (item.get("score"), 0.20),
    ]) or item.get("score"), low=0.8, high=16.0))
    item.setdefault("dnf_probability", round(clamp(100 - (safe_float(item.get("reliability")) or 70), 2, 45, 12), 2))
    item.setdefault("classified_finish_probability", round(100 - item["dnf_probability"], 2))
    item.setdefault("position_range", [item.get("best_case_finish"), item.get("worst_case_finish")])
    item.setdefault("expected_strategy", strategy_profile_for_row(item, profile, weather_summary))
    item.setdefault("strategy_annotations", detect_strategy_context_annotations(item.get("strategy_context"), weather_summary))
    item.setdefault("explanation", explanation_for_prediction_row(item, profile, weather_summary))
    item.setdefault("confidence_label", confidence_label(item.get("confidence")))
    item.setdefault("data_freshness", {"stage": stage, "source_health_status": "pending_source_snapshot"})
    item.setdefault("source_notes", {"source_health": "pending_source_snapshot", "warnings": evidence.get("missing", [])})
    return item


def add_teammate_prediction_gaps(predictions):
    by_team = {}
    for item in predictions:
        by_team.setdefault(item.get("team") or "Unknown", []).append(item)
    for teammates in by_team.values():
        teammates.sort(key=lambda x: x.get("rank") or 99)
        for item in teammates:
            other = next((mate for mate in teammates if mate is not item), None)
            item["teammate_prediction_gap"] = round(abs((item.get("score") or 0) - (other.get("score") or 0)), 2) if other else None
            item["teammate_reference"] = other.get("name") if other else None
    return predictions


def source_status(score, label):
    score = clamp(score, 0, 100, 0)
    if score >= 75:
        state = "Available"
    elif score >= 50:
        state = "Fallback"
    elif score >= 25:
        state = "Stale"
    else:
        state = "Missing"
    return {"source": label, "score": round(score, 2), "status": state}


def build_source_health_snapshot(current_round_data=None, timing_scores=None, fastf1_scores=None, upgrade_context=None, calendar_context=None, ml_outputs=None):
    current_round_data = current_round_data or {}
    timing_scores = timing_scores or {}
    fastf1_scores = fastf1_scores or {}
    upgrade_context = upgrade_context or {}
    calendar_context = calendar_context or {}
    openf1_status = str((timing_scores or {}).get("provider_status") or "")
    if "auth_required" in openf1_status or "forbidden" in openf1_status:
        openf1_score = 30
    elif "openf1" in openf1_status:
        openf1_score = 70
    else:
        openf1_score = 48
    dataset_sources = optional_dataset_source_statuses()
    f1db_score = 82 if (dataset_sources.get("f1db") or {}).get("available") else 35
    relbench_score = 70 if (dataset_sources.get("relbench_f1") or {}).get("available") else 30
    sources = [
        source_status(88 if timing_scores.get("provider_status") not in {None, "failed"} else 42, "F1 timing/static feed"),
        source_status(82 if current_round_data.get("results") or current_round_data.get("qualifying") else 62, "Jolpica"),
        source_status(openf1_score, "OpenF1"),
        source_status(78 if fastf1_scores.get("sessions_loaded") else 42, "FastF1"),
        source_status(76 if current_round_data is not None else 50, "Open-Meteo"),
        source_status(74 if upgrade_context.get("sources") else 45, "FIA/F1 upgrade/regulation sources"),
        source_status(92 if current_round_data is not None else 52, "Local cache"),
        source_status(86 if ml_outputs else 40, "Model bundle"),
        source_status(82 if calendar_context.get("status") else 55, "Calendar"),
        source_status(f1db_score, "F1DB historical dataset"),
        source_status(relbench_score, "RelBench rel-f1 benchmark"),
    ]
    average_score = average([item["score"] for item in sources]) or 0
    return {
        "generated_at": now_local().isoformat(),
        "overall_score": round(average_score, 2),
        "status": source_status(average_score, "Overall")["status"],
        "sources": sources,
        "api_notes": {
            "openf1": timing_scores.get("openf1_status") or dict(OPENF1_LAST_STATUS),
            "f1db": dataset_sources.get("f1db"),
            "relbench_f1": dataset_sources.get("relbench_f1"),
        },
    }


def sanitize_source_health(health):
    if not isinstance(health, dict):
        return health
    out = dict(health)
    sources = []
    for item in health.get("sources", []) or []:
        row = dict(item)
        if row.get("source") == "F1 Live Timing":
            row["source"] = "F1 timing/static feed"
        sources.append(row)
    out["sources"] = sources
    return out


def sanitize_timing_source_labels(value):
    """Normalize legacy generated labels so archive/static timing is not presented as live."""
    replacements = {
        "F1 Live Timing": "F1 timing/static feed",
        "official Formula 1 live timing static feeds": "official Formula 1 timing/static feeds",
    }
    if isinstance(value, dict):
        return {k: sanitize_timing_source_labels(v) for k, v in value.items()}
    if isinstance(value, list):
        return [sanitize_timing_source_labels(v) for v in value]
    if isinstance(value, str):
        out = value
        for old, new in replacements.items():
            out = out.replace(old, new)
        return out
    return value


def scenario_rankings(predictions, profile, weather_summary):
    definitions = {
        "baseline": {"label": "Baseline", "weights": {"score": 1.0}},
        "rain": {"label": "Rain", "weights": {"score": 0.42, "weather_adaptation": 0.30, "reliability": 0.18, "team_strategy": 0.10}},
        "safety_car": {"label": "Safety Car", "weights": {"score": 0.45, "pit_execution": 0.22, "team_strategy": 0.22, "attack_potential_score": 0.11}},
        "high_tyre_degradation": {"label": "High Tyre Degradation", "weights": {"score": 0.40, "race_pace": 0.22, "pit_execution": 0.22, "reliability": 0.16}},
        "low_overtaking": {"label": "Low Overtaking", "weights": {"score": 0.36, "qualifying": 0.30, "defend_inverse": 0.18, "track_trait_fit": 0.16}},
    }
    if text_level(weather_summary.get("wind", "")) >= 45 or safe_float(weather_summary.get("wind_score")):
        definitions["high_wind"] = {"label": "High Wind", "weights": {"score": 0.42, "weather_adaptation": 0.32, "reliability": 0.18, "active_aero_suitability_score": 0.08}}

    out = {}
    for key, definition in definitions.items():
        rows = []
        for item in predictions:
            components = item.get("component_scores") or {}
            values = []
            for metric_key, weight in definition["weights"].items():
                if metric_key == "score":
                    value = item.get("score")
                elif metric_key == "defend_inverse":
                    value = 100 - (item.get("defend_risk_score") or 50)
                else:
                    value = item.get(metric_key, components.get(metric_key))
                values.append((value, weight))
            score = weighted_average(values) or item.get("score") or 0
            rows.append({
                "driver_id": item.get("driver_id"),
                "name": item.get("name"),
                "team": item.get("team"),
                "scenario_score": round(score, 2),
            })
        rows.sort(key=lambda x: x["scenario_score"], reverse=True)
        out[key] = {
            "label": definition["label"],
            "top10": [{**row, "rank": idx} for idx, row in enumerate(rows[:10], start=1)],
            "notes": scenario_note(key, profile, weather_summary),
        }
    return out


def scenario_note(key, profile, weather_summary):
    notes = {
        "baseline": "Current model stack with no scenario shock applied.",
        "rain": "Weights weather adaptation, reliability, and team strategy more heavily.",
        "safety_car": "Weights pit execution, strategy flexibility, and attack potential.",
        "high_tyre_degradation": "Weights race pace, pit execution, and reliability for tyre-stress races.",
        "low_overtaking": "Weights qualifying, track position, and defending strength.",
        "high_wind": "Weights weather adaptation, reliability, and Active Aero suitability.",
    }
    return notes.get(key, "Scenario output derived from available model components.")


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

        weighted_items = [(component_scores.get(k), w) for k, w in weights.items()]
        score = weighted_average_penalized(weighted_items, min_coverage=0.65, neutral=50.0) or 0
        _, component_coverage = weighted_average_with_coverage(weighted_items)
        available_weight = sum(w for k, w in weights.items() if component_scores.get(k) is not None)
        confidence = min(100, max(0, available_weight * 100 * max(0.25, component_coverage)))

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
            "component_coverage": round(component_coverage, 3),
            "predicted_finish_position": round(ml.get("predicted_finish_position"), 2) if ml.get("predicted_finish_position") is not None else None,
            "predicted_lap_pace_seconds": round(ml.get("predicted_lap_pace_seconds"), 3) if ml.get("predicted_lap_pace_seconds") is not None else None,
            "image": None,
            "team_colour": None,
        })

    predictions.sort(key=lambda item: (item["score"], item["confidence"]), reverse=True)
    field_size = max(20, len(predictions))
    predictions = [
        enrich_prediction_item(item, idx, field_size, current_round_data, profile, weather_summary, stage)
        for idx, item in enumerate(predictions, start=1)
    ]
    predictions = add_teammate_prediction_gaps(predictions)
    full_grid = predictions
    top10 = full_grid[:10]
    text = "\n".join(
        f"{idx}. {item['name']}, score {item['score']:.1f}, confidence {item['confidence']:.0f}%, {item['reason']}"
        for idx, item in enumerate(top10, start=1)
    )
    source_health = build_source_health_snapshot(
        current_round_data=current_round_data,
        timing_scores=timing_scores,
        fastf1_scores=fastf1_scores,
        upgrade_context=upgrade_context,
        calendar_context=calendar_context,
        ml_outputs=ml_outputs,
    )
    model = {
        "source": "Hybrid full-data cache model: Jolpica full history + official Formula 1 timing/static feeds + optional OpenF1 free historical timing + FastF1 + Open-Meteo + ICS/F1 calendar",
        "logic": "Stacked racecraft ensemble: RF/HGB/ExtraTrees win/podium/top10 classifiers, RF/HGB/ExtraTrees finish-position regressor, neural lap-time forecaster, transparent driver/team/circuit formula, official/OpenF1 timing sectors/speeds/stints/pits, recency-weighted form, qualifying/grid strength, track traits, weather traits, tyre strategy, sprint, reliability, upgrades, and regulation-era modifiers",
        "prediction_stage": stage,
        "prediction_data_version": PREDICTION_DATA_VERSION,
        "model_version": MODEL_SCHEMA_VERSION,
        "schema_version": MODEL_SCHEMA_VERSION,
        "weights": {k: round(v, 4) for k, v in weights.items()},
        "source_health_snapshot": source_health,
        "scenarios": scenario_rankings(full_grid, profile, weather_summary),
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
    return text, top10, full_grid, model


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
    path.write_text(f"# PitWall Run Status\n\nGenerated: {now_local().strftime('%A, %d %B %Y, %I:%M %p %Z')}\n\nStatus: {status}\n\n## Details\n\n{details}\n", encoding="utf-8")
    ensure_dirs()
    registry = load_or_build_source_registry(resolve_target_season())
    json_payload = {
        "schema_version": "pitwall-run-status-v1",
        "generated_at": now_local().isoformat(),
        "status": status,
        "details": details,
        "source_discovery": registry,
        "fia_index_refresh": {"enabled": FIA_DOCUMENTS_ENABLED, "status": registry.get("fia_source_discovery_status")},
        "cache_hits": {"source_registry": registry.get("cache_status") == "hit"},
        "cache_misses": {"fia_documents": not bool(registry.get("fia_season_document_url"))},
        "documents_parsed": 0,
        "documents_skipped": 0,
        "parse_failures": [],
        "sessions_detected": [],
        "sessions_waiting_for_data": [],
        "predictions_regenerated": status == "Success" and "Generated" in str(details),
        "model_retraining": "forced" if os.getenv("FORCE_RETRAIN", "false").lower() == "true" else "auto",
        "frontend_contracts_written": (DATA_CACHE_DIR / "frontend-contract.json").exists(),
        "timing_freshness": timing_freshness_status(source="Generated contract"),
        "warnings": registry.get("warnings", []),
        "errors": registry.get("errors", []),
    }
    json_payload = sanitize_public_paths(json_payload)
    LATEST_RUN_STATUS_PATH.parent.mkdir(parents=True, exist_ok=True)
    LATEST_RUN_STATUS_PATH.write_text(json.dumps(json_payload, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    sqlite_insert_run_status("latest_run_status", json_payload)
    return path


def build_strategy_contract(profile, weather, top10=None, prediction_model=None):
    top10 = top10 or []
    prediction_model = prediction_model or {}
    rain_score = safe_float(weather.get("rain_score")) or text_level(weather.get("rain"))
    safety_score = text_level(profile.get("safety_car"))
    tyre_score = text_level(profile.get("tyre_stress"))
    overtaking_score = text_level(profile.get("overtaking"))
    chaos = weighted_average([(rain_score, 0.30), (safety_score, 0.30), (tyre_score, 0.25), (100 - overtaking_score, 0.15)]) or 50
    return {
        "risk_meter": round(clamp(chaos, 0, 100, 50), 2),
        "strategy_chaos_score": round(clamp(chaos, 0, 100, 50), 2),
        "circuit_difficulty_score": round(clamp(weighted_average([(tyre_score, 0.35), (100 - overtaking_score, 0.25), (safety_score, 0.20), (text_level(profile.get("track_type")), 0.20)]), 0, 100, 50), 2),
        "track_evolution_indicator": "High" if tyre_score >= 70 else "Medium" if tyre_score >= 45 else "Low",
        "clean_air_dirty_air_impact": "High" if overtaking_score <= 40 else "Medium",
        "qualifying_importance_score": round(clamp(100 - overtaking_score + 20, 0, 100, 65), 2),
        "pit_window": pit_window_from_profile(profile, weather),
        "tyre_degradation_model": {
            "score": round(clamp(tyre_score, 0, 100, 50), 2),
            "label": profile.get("tyre_stress", "unknown"),
            "basis": "Historical stint, tyre stress, track temperature, and pit-stop profile where available.",
        },
        "pit_execution_model": sorted([
            {
                "driver": item.get("name"),
                "team": item.get("team"),
                "score": item.get("component_scores", {}).get("pit_execution"),
            }
            for item in top10
        ], key=lambda x: x.get("score") or 0, reverse=True)[:8],
        "rain_beneficiaries": (prediction_model.get("scenarios") or {}).get("rain", {}).get("top10", [])[:5],
        "safety_car_beneficiaries": (prediction_model.get("scenarios") or {}).get("safety_car", {}).get("top10", [])[:5],
        "active_aero": {
            "straight_mode": "low-drag straight configuration",
            "corner_mode": "high-downforce corner configuration",
            "average_suitability": round(average([item.get("active_aero_suitability_score") for item in top10]) or 0, 2),
        },
        "energy_deployment": {
            "title": "2026 Boost / Overtake Mode Intelligence",
            "average_boost_advantage": round(average([item.get("energy_boost_advantage_score") for item in top10]) or 0, 2),
            "attack_defend_logic": "Attack/Defend output uses pace, tyre stress, track position, Boost proxy, and overtaking difficulty.",
        },
        "decision_log": [
            "Model checks source health and missing critical data before ranking.",
            "Scenario layer reweights real component scores for rain, safety car, tyre degradation, and low-overtaking cases.",
            "2026 layer uses Boost, Overtake Mode, energy deployment, and Active Aero terminology with fallback proxies when exact data is unavailable.",
        ],
    }


def actual_result_from_race(race):
    results = race.get("Results") if isinstance(race, dict) else None
    if not results:
        return None
    rows = []
    for result in results:
        driver = result.get("Driver", {})
        constructor = result.get("Constructor", {})
        rows.append({
            "position": safe_int(result.get("positionOrder") or result.get("position")),
            "driver_id": driver.get("driverId"),
            "name": " ".join([driver.get("givenName", ""), driver.get("familyName", "")]).strip() or driver.get("driverId"),
            "team": canonical_constructor_name(constructor.get("name")),
            "status": result.get("status"),
            "points": safe_float(result.get("points")),
        })
    rows = [row for row in rows if row.get("position")]
    rows.sort(key=lambda row: row["position"])
    return {"winner": rows[0] if rows else None, "classification": rows}


def correction_summary_for_entry(race_id):
    if MODEL_CORRECTIONS_PATH.exists():
        try:
            data = json.loads(MODEL_CORRECTIONS_PATH.read_text(encoding="utf-8"))
            for item in data.get("corrections", []):
                if item.get("race_id") == race_id:
                    return item.get("summary") or item
        except Exception:
            pass
    return {
        "status": "Pending",
        "biggest_model_surprise": None,
        "biggest_model_miss": None,
        "learning_notes": "Waiting for official result before audit.",
    }


def save_model_input_snapshot(prediction_id, payload, input_data_hash):
    ensure_dirs()
    path = MODEL_INPUT_SNAPSHOT_DIR / f"{make_slug(prediction_id)}.json"
    path.write_text(json.dumps({
        "prediction_id": prediction_id,
        "input_data_hash": input_data_hash,
        "saved_at": now_local().isoformat(),
        "features_used": payload,
    }, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    return path


def update_index(event, race, profile, weather, markdown_path, title, top10, team_fit, prediction_model, upgrade_context, regulation_context, calendar_context, full_grid=None):
    index_path = BRIEFINGS_DIR / "index.json"
    season = safe_int(race.get("season")) or event["start"].year
    round_no = safe_int(race.get("round")) or 0
    race_id = f"{season}-{round_no}-{make_slug(race.get('raceName') or title)}"
    target_type = prediction_model.get("output_target_type", classify_output_target_event(event))
    stage = prediction_model.get("prediction_stage") or "pre_weekend"
    generated_iso = now_local().isoformat()
    prediction_id = f"{race_id}-{target_type}-{stage}-{stable_hash({'top10': top10, 'generated': generated_iso})[:12]}"
    full_grid = list(full_grid or top10 or [])
    input_payload = {
        "race": race,
        "profile": profile,
        "weather": weather,
        "top10": top10,
        "full_grid": full_grid,
        "prediction_model": prediction_model,
        "team_fit": team_fit,
    }
    input_data_hash = stable_hash(input_payload)
    source_health = prediction_model.get("source_health_snapshot") or build_source_health_snapshot()
    for item in full_grid:
        item.setdefault("prediction_id", prediction_id)
        item.setdefault("race_id", race_id)
        item.setdefault("season", season)
        item.setdefault("round", round_no)
        item.setdefault("target_type", target_type)
        item.setdefault("stage", stage)
        item.setdefault("model_version", MODEL_SCHEMA_VERSION)
        item.setdefault("schema_version", MODEL_SCHEMA_VERSION)
        item.setdefault("generated_at", generated_iso)
        item.setdefault("input_data_hash", input_data_hash)
        item.setdefault("prediction_data_version", PREDICTION_DATA_VERSION)
    entry = {
        "title": title,
        "path": str(markdown_path.relative_to(BASE_DIR)).replace("\\", "/"),
        "generated": now_local().strftime("%Y-%m-%d %H:%M %Z"),
        "generated_iso": generated_iso,
        "start_iso": event["start"].isoformat(),
        "start": event["start"].strftime("%A, %d %B %Y, %I:%M %p %Z"),
        "event_title": event["title"],
        "location": event["location"],
        "jolpica_race": race,
        "race_id": race_id,
        "prediction_id": prediction_id,
        "race_name": race.get("raceName") or title,
        "season": season,
        "round": round_no,
        "target_type": target_type,
        "stage": stage,
        "prediction_stage": stage,
        "model_version": MODEL_SCHEMA_VERSION,
        "schema_version": MODEL_SCHEMA_VERSION,
        "prediction_data_version": PREDICTION_DATA_VERSION,
        "input_data_hash": input_data_hash,
        "source_health_snapshot": source_health,
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
        "full_grid": full_grid,
        "all_predictions": full_grid,
        "prediction_model": prediction_model,
        "strategy": build_strategy_contract(profile, weather, top10, prediction_model),
        "source_health": source_health,
        "source_status": source_health,
        "scenarios": prediction_model.get("scenarios") or scenario_rankings(top10, profile, weather),
        "model_metrics": ((prediction_model.get("ml_model_meta") or {}).get("metrics") or {}),
        "correction_summary": correction_summary_for_entry(race_id),
        "actual_result": actual_result_from_race(race),
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
    save_model_input_snapshot(prediction_id, input_payload, input_data_hash)
    generate_frontend_contract_files({"briefings": briefings})
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

    content = f"""# PitWall Model Status

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
- Uses official Formula 1 timing/static feeds first, then optional OpenF1 free historical sessions as an extra timing cross-check when reachable.
- Discovers the active source registry for the target season and marks future FIA pages pending instead of inventing URLs.
- Checks FIA decision-document index/cache incrementally and surfaces parse/cache health in JSON contracts.
- Tracks session lifecycle states after FP/Sprint/Qualifying/Race and exposes waiting states when APIs or documents lag.
- Labels timing as Live only when freshness checks pass; stale/archive/latest fallback data is not presented as live telemetry.
- Waits and keeps the current model when a GP is just over but the result delay has not passed or the API still has no final `Results` rows.
- Generates Sprint/Race-only predictions, updates briefings, `briefings/index.json`, `data_cache/latest-model-debug.json`, and this file.
- Generates frontend contracts: `data_cache/frontend-contract.json`, `data_cache/model-status.json`, `data_cache/backtest-history.json`, `data_cache/model_corrections.json`, and `data_cache/features/*.json`.
- Keeps champion/challenger model promotion gated by validation metrics, source health, unit tests, output contracts, and artifact save checks.
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
- `target_season`, `target_event`, `target_session`: focus season/event/session discovery or ingestion.
- `refresh_source_registry`, `refresh_fia_documents`: refresh official source discovery and FIA index metadata.
- `force_reparse_fia_documents`, `force_redownload_fia_documents`: rebuild FIA parsed outputs or redownload PDFs when explicitly requested.
- `force_session_ingest`, `dry_run_session_ingest`: override or preview session ingestion.
- `disable_live_mode`: force timing surfaces away from true live labels.
- `enable_feature_ablation`, `enable_hyperparameter_search`: opt into heavier manual model diagnostics.

Local equivalent: run `.venv/bin/python f1_briefing.py --force-retrain` or set the same environment variables before running.
"""
    MODEL_STATUS_PATH.write_text(content, encoding="utf-8")
    save_model_status_json(bundle=bundle, mode=mode, payloads=payloads, errors=errors, readiness=readiness, metrics=metrics, feature_columns=feature_columns, bundle_size_mb=bundle_size_mb, decision=decision)
    return MODEL_STATUS_PATH


def metric_get(metrics, target, key):
    return (metrics.get(target) or {}).get(key)


def save_model_status_json(bundle=None, mode=None, payloads=None, errors=None, readiness=None, metrics=None, feature_columns=None, bundle_size_mb=None, decision=None):
    ensure_dirs()
    meta = read_model_meta()
    readiness = readiness or latest_result_readiness()
    metrics = metrics or (bundle or {}).get("metrics") or meta.get("metrics") or {}
    feature_columns = feature_columns or (bundle or {}).get("feature_columns") or meta.get("feature_columns") or []
    decision = decision or (bundle or {}).get("training_decision") or model_retrain_status(False)
    ranking = (metrics.get("finish_position") or {}).get("ranking") or metrics.get("win_probability_ranking") or {}
    baselines = metrics.get("baselines") or {}
    validation_split = metrics.get("validation_split") or meta.get("validation_split") or {}
    lap_metrics = metrics.get("lap_time_delta_forecast") or metrics.get("neural_lap_time_forecast") or {}
    registry = load_or_build_source_registry(resolve_target_season())
    leakage = audit_feature_leakage("pre_weekend", feature_columns)
    dataset_sources = optional_dataset_source_statuses()
    payload = {
        "schema_version": MODEL_SCHEMA_VERSION,
        "model_version": MODEL_SCHEMA_VERSION,
        "prediction_data_version": PREDICTION_DATA_VERSION,
        "generated_at": now_local().isoformat(),
        "trained_at": (bundle or {}).get("trained_at") or meta.get("trained_at"),
        "latest_completed_race_included": (bundle or {}).get("latest_completed_race_id") or meta.get("latest_completed_race_id"),
        "latest_available_api_result": readiness.get("latest_completed_race_id"),
        "feature_count": len(feature_columns),
        "feature_columns": feature_columns,
        "model_bundle_size_mb": round(bundle_size_mb, 2) if bundle_size_mb is not None else None,
        "metrics": {
            "win_auc": metric_get(metrics, "win", "auc"),
            "win_brier": metric_get(metrics, "win", "brier"),
            "podium_auc": metric_get(metrics, "podium", "auc"),
            "podium_brier": metric_get(metrics, "podium", "brier"),
            "top10_auc": metric_get(metrics, "top10", "auc"),
            "top10_brier": metric_get(metrics, "top10", "brier"),
            "finish_position_mae": metric_get(metrics, "finish_position", "mae"),
            "finish_position_rmse": metric_get(metrics, "finish_position", "rmse"),
            "winner_hit_rate": ranking.get("winner_hit"),
            "top3_recall": ranking.get("top3_recall"),
            "top5_recall": ranking.get("top5_recall"),
            "top10_recall": ranking.get("top10_recall"),
            "spearman_rank_correlation": ranking.get("spearman"),
            "ndcg_at_3": ranking.get("ndcg_at_3"),
            "ndcg_at_10": ranking.get("ndcg_at_10"),
            "exact_position_accuracy": ranking.get("exact_position_accuracy"),
            "mean_position_error": ranking.get("mean_position_error"),
            "lap_time_mae": lap_metrics.get("mae_seconds"),
            "lap_time_rmse": lap_metrics.get("rmse_seconds"),
        },
        "raw_metrics": metrics,
        "validation": {
            "grouped_split_method": validation_split.get("method", "chronological_race_group_split"),
            "race_grouped": True,
            "rolling_validation": True,
            "train_races": validation_split.get("train_races"),
            "validation_races": validation_split.get("validation_races"),
            "validation_rows": validation_split.get("validation_rows"),
            "test_races": validation_split.get("test_races"),
            "train_seasons": validation_split.get("train_seasons"),
            "validation_seasons": validation_split.get("validation_seasons"),
            "test_seasons": validation_split.get("test_seasons"),
            "leakage_check": leakage,
            "warning": "Historical fallback metrics may be used when saved bundle metadata predates this schema.",
        },
        "baseline_comparison": {
            "grid_order_baseline": {"status": "tracked", **(baselines.get("grid_order") or {})},
            "constructor_standings_baseline": {"status": "tracked", **(baselines.get("constructor_form") or {})},
            "driver_championship_baseline": {"status": "tracked", **(baselines.get("driver_championship_form") or {})},
            "recent_3_race_form_baseline": {"status": "tracked", **(baselines.get("driver_recent_form") or {})},
            "qualifying_only_baseline": {"status": "tracked_after_qualifying", **(baselines.get("qualifying_only") or {})},
            "practice_pace_only_baseline": {"status": "tracked_after_practice"},
            "old_hybrid_hand_weighted_baseline": {"status": "retained_as_fallback"},
        },
        "calibration": {
            "method": "empirical_quantile_bins_plus_race_level_probability_normalization",
            "targets": ["win", "podium", "top10"],
            "status": "available_when_predictions_generated",
            "details": meta.get("probability_calibration") or {k: (v or {}).get("calibration_method") for k, v in metrics.items() if k in {"win", "podium", "top10"}},
        },
        "feature_ablation": {
            "enabled": ENABLE_FEATURE_ABLATION,
            "groups": ["grid/qualifying", "driver form", "team form", "circuit history", "practice pace", "sprint signals", "weather", "FIA upgrades", "PU/reliability", "FIA documents", "FastF1", "OpenF1"],
            "status": "manual_only" if not ENABLE_FEATURE_ABLATION else "enabled",
        },
        "source_registry": registry,
        "dataset_sources": dataset_sources,
        "fia_ingestion": fia_document_summary(registry),
        "source_health": latest_source_health_from_index(),
        "correction_log_summary": correction_log_summary(),
        "champion_challenger": champion_challenger_status(decision, metrics),
        "promotion_decision": model_promotion_decision(decision, metrics),
        "readiness_state": readiness,
        "mode": mode,
        "selected_targets": [
            {
                "target_type": payload.get("target_type"),
                "title": payload.get("event", {}).get("title"),
                "start": payload.get("event", {}).get("start"),
            }
            for payload in (payloads or [])
        ],
        "errors": errors or [],
        "limitations": [
            "Live race adjustments only become official model output when timing data is genuinely fresh and generated contracts are refreshed.",
            "Timing fallback and archived data are labelled as replay/archive, never live telemetry.",
            "2026 Boost and Active Aero fields are explainable proxies until full 2026+ timing and technical evidence exists.",
            "Post-race corrections remain pending until official result rows are available after the configured delay.",
            "F1 predictions cannot be guaranteed because crashes, red flags, failures, penalties, strategy, weather, and source delays are inherently uncertain.",
        ],
    }
    payload = sanitize_public_paths(payload)
    MODEL_STATUS_JSON_PATH.write_text(json.dumps(payload, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    write_model_artifacts({
        **meta,
        "metrics": metrics,
        "feature_columns": feature_columns,
        "feature_columns_hash": meta.get("feature_columns_hash") or feature_columns_hash(feature_columns),
        "training_decision": decision,
    })
    return MODEL_STATUS_JSON_PATH


def latest_index_data():
    index_path = BRIEFINGS_DIR / "index.json"
    if not index_path.exists():
        return {"briefings": []}
    try:
        data = json.loads(index_path.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            return data
        return {"briefings": data if isinstance(data, list) else []}
    except Exception:
        return {"briefings": []}


def latest_source_health_from_index():
    briefings = latest_index_data().get("briefings", [])
    for briefing in briefings:
        health = briefing.get("source_health") or briefing.get("source_health_snapshot") or (briefing.get("prediction_model") or {}).get("source_health_snapshot")
        if health:
            return sanitize_source_health(health)
    return sanitize_source_health(build_source_health_snapshot())


def correction_log_summary():
    if MODEL_CORRECTIONS_PATH.exists():
        try:
            data = json.loads(MODEL_CORRECTIONS_PATH.read_text(encoding="utf-8"))
            corrections = data.get("corrections", [])
            return {
                "count": len(corrections),
                "latest": corrections[0] if corrections else None,
                "status": data.get("status", "Available" if corrections else "Pending"),
            }
        except Exception:
            pass
    return {"count": 0, "latest": None, "status": "Pending"}


def champion_challenger_status(decision, metrics):
    return {
        "champion_model": MODEL_SCHEMA_VERSION,
        "challenger_model": f"{MODEL_SCHEMA_VERSION}-challenger",
        "status": "challenger_pending_validation" if decision.get("action") in {"retrain", "force_retrain"} else "champion_retained",
        "acceptance_rules": [
            "finish-position MAE must not regress beyond threshold",
            "top-3 and top-10 recall must not drop beyond threshold",
            "Brier score must not worsen beyond threshold",
            "critical data sources and output contracts must pass validation",
        ],
    }


def model_promotion_decision(decision, metrics):
    finish = metrics.get("finish_position") or {}
    ranking = finish.get("ranking") or metrics.get("win_probability_ranking") or {}
    baselines = metrics.get("baselines") or {}
    beats = finish.get("beats_baselines") or {}
    blockers = []
    if safe_float(finish.get("mae")) is None:
        blockers.append("finish_position_mae_missing")
    if safe_float(ranking.get("top3_recall")) is None:
        blockers.append("top3_recall_missing")
    for required in ["grid_order", "qualifying_only", "constructor_form"]:
        if required in baselines and beats.get(required) is not True:
            blockers.append(f"did_not_beat_{required}_baseline")
    out_of_time = metrics.get("out_of_time_test") or {}
    oot_ranking = out_of_time.get("ranking") or {}
    oot_baselines = out_of_time.get("baselines") or {}
    oot_mae = safe_float(out_of_time.get("finish_mae"))
    for required in ["grid_order", "qualifying_only", "constructor_form"]:
        baseline = oot_baselines.get(required) or {}
        baseline_mae = safe_float(baseline.get("finish_mae"))
        if oot_mae is not None and baseline_mae is not None and oot_mae > baseline_mae:
            blockers.append(f"out_of_time_did_not_beat_{required}_finish_mae")
        baseline_ranking = baseline.get("ranking") or {}
        for metric_name, tolerance in [("winner_hit", 0.0), ("top3_recall", 0.02), ("top10_recall", 0.02), ("spearman", 0.02)]:
            model_value = safe_float(oot_ranking.get(metric_name))
            baseline_value = safe_float(baseline_ranking.get(metric_name))
            if model_value is not None and baseline_value is not None and model_value + tolerance < baseline_value:
                blockers.append(f"out_of_time_did_not_beat_{required}_{metric_name}")
    if blockers:
        return {"decision": "hold_champion", "blockers": sorted(set(blockers)), "baseline_gate": beats}
    return {"decision": "promote_if_tests_passed", "blockers": [], "baseline_gate": beats}


def load_or_build_source_registry(season):
    ensure_dirs()
    path = SOURCE_REGISTRY_DIR / f"{season}.json"
    if path.exists() and not REFRESH_SOURCE_REGISTRY:
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            pass
    # Contract generation must not require live network. Use configured/default
    # URLs and mark missing future FIA pages as pending.
    return build_source_registry(season, championship_html="", formula1_html="")


def build_session_timeline_from_race(race, source_url=None):
    season = safe_int(race.get("season")) or resolve_target_season()
    round_no = safe_int(race.get("round")) or 0
    event_slug = make_slug(race.get("raceName"))
    fields = [
        ("FirstPractice", "FP1", "fp1"),
        ("SecondPractice", "FP2", "fp2"),
        ("ThirdPractice", "FP3", "fp3"),
        ("SprintQualifying", "Sprint Qualifying", "sprint_qualifying"),
        ("Sprint", "Sprint", "sprint"),
        ("Qualifying", "Qualifying", "qualifying"),
        ("Race", "Race", "race"),
    ]
    sessions = []
    now_utc = datetime.now(timezone.utc)
    for field, name, session_type in fields:
        payload = race if field == "Race" else race.get(field) or {}
        date = payload.get("date") or (race.get("date") if field == "Race" else None)
        time_value = payload.get("time") or (race.get("time") if field == "Race" else None) or "00:00:00Z"
        start = parse_datetime_utc(f"{date}T{time_value}" if date else None)
        if not start:
            continue
        duration_minutes = 90 if session_type == "race" else 60 if session_type.startswith("fp") else 75 if session_type == "qualifying" else 45
        end = start + timedelta(minutes=duration_minutes)
        sessions.append(evaluate_session_lifecycle({
            "season": season,
            "round": round_no,
            "event_name": race.get("raceName"),
            "event_slug": event_slug,
            "session_name": name,
            "session_type": session_type,
            "official_start_time_local": start.astimezone(USER_TIMEZONE).isoformat(),
            "official_end_time_local": end.astimezone(USER_TIMEZONE).isoformat(),
            "official_start_time_utc": start.isoformat(),
            "official_end_time_utc": end.isoformat(),
            "source_url": source_url,
            "source_type": "jolpica_schedule_fallback",
            "source_confidence": 0.62,
            "source_conflicts": [],
            "ingested_document_ids": [],
            "ingested_api_sources": [],
            "inferred": True,
        }, now=now_utc, data_available=False))
    return sessions


def sanitize_session_timeline_for_stage(session_timeline, stage):
    order = {
        "pre_weekend": [],
        "post_fp1": ["fp1"],
        "post_fp2": ["fp1", "fp2"],
        "post_fp3": ["fp1", "fp2", "fp3"],
        "post_sprint_qualifying": ["fp1", "sprint_qualifying"],
        "post_sprint": ["fp1", "sprint_qualifying", "sprint"],
        "post_qualifying": ["fp1", "fp2", "fp3", "sprint_qualifying", "sprint", "qualifying"],
        "pre_race": ["fp1", "fp2", "fp3", "sprint_qualifying", "sprint", "qualifying"],
        "live_adjusted": ["fp1", "fp2", "fp3", "sprint_qualifying", "sprint", "qualifying"],
        "post_race_audited": ["fp1", "fp2", "fp3", "sprint_qualifying", "sprint", "qualifying", "race"],
    }
    completed = set(order.get(stage or "pre_weekend", []))
    sanitized = []
    for session in session_timeline or []:
        row = dict(session)
        session_type = row.get("session_type")
        if session_type in completed:
            row["status"] = "data_ingested"
            row.setdefault("data_available_at", row.get("last_checked_at") or now_local().isoformat())
            api_sources = set(row.get("ingested_api_sources") or [])
            api_sources.add("stage_contract")
            row["ingested_api_sources"] = sorted(api_sources)
        sanitized.append(row)
    return sanitized


def session_contract_state(session_timeline):
    last_ingested = next((s for s in reversed(session_timeline or []) if s.get("status") == "data_ingested"), None)
    next_session = next((s for s in session_timeline or [] if s.get("status") not in {"data_ingested", "archive"}), None)
    pending = [
        s for s in session_timeline or []
        if s.get("status") in {"completed", "waiting_for_api_data", "active_without_live_data", "delayed", "stale"}
    ]
    return {
        "last_ingested_session": last_ingested,
        "next_session_to_ingest": next_session,
        "pending_session_checks": pending,
        "session_data_delay_status": "waiting" if pending else "clear",
        "session_official_status": "partial" if session_timeline else "unavailable",
    }


def fia_document_summary(registry=None, entry=None):
    registry = registry or {}
    season = safe_int((entry or {}).get("season")) or safe_int(registry.get("season")) or resolve_target_season()
    season_index = FIA_DOCUMENT_CACHE_DIR / str(season) / "season_index.json"
    should_refresh = FIA_DOCUMENTS_ENABLED and (not season_index.exists() or (REFRESH_FIA_DOCUMENTS and season not in _FIA_REFRESHED_SEASONS))
    if should_refresh:
        try:
            refresh_fia_documents_for_season(season, registry=registry, refresh=REFRESH_FIA_DOCUMENTS)
        except Exception as error:
            print(f"FIA document refresh failed, using cached summary if available: {error}")
    docs = []
    parse_errors = []
    cache_hits = 0
    cache_misses = 0
    if season_index.exists():
        try:
            payload = json.loads(season_index.read_text(encoding="utf-8"))
            docs = payload.get("documents") if isinstance(payload, dict) else payload
            docs = docs if isinstance(docs, list) else []
            cache_hits += 1
        except Exception as error:
            parse_errors.append(str(error))
    else:
        cache_misses += 1
    by_type = {}
    for doc in docs:
        by_type[doc.get("document_type") or "unknown"] = by_type.get(doc.get("document_type") or "unknown", 0) + 1
        if doc.get("parse_error"):
            parse_errors.append(doc.get("parse_error"))
    return {
        "fia_documents_enabled": FIA_DOCUMENTS_ENABLED,
        "fia_season_url": registry.get("fia_season_document_url"),
        "fia_source_discovery_status": registry.get("fia_source_discovery_status") or "not_checked",
        "fia_documents_available": bool(docs),
        "fia_latest_document": docs[0] if docs else None,
        "fia_document_count": len(docs),
        "fia_documents_by_type": by_type,
        "fia_session_timetable": [],
        "fia_upgrade_summary": {"updates": [], "status": "pending_fia_document_parse" if not docs else "available"},
        "fia_pu_summary": {"drivers": {}, "status": "pending_fia_document_parse" if not docs else "available"},
        "fia_infringement_summary": {"items": [], "status": "pending_fia_document_parse" if not docs else "available"},
        "latest_fia_ingested_at": None,
        "fia_parse_errors": parse_errors[:20],
        "fia_cache_hits": cache_hits,
        "fia_cache_misses": cache_misses,
    }


def enrich_predictions_with_quality_outputs(rows, source_health=None, stage=None):
    normalized = normalize_race_probabilities(rows or [])
    simulation = simulate_race_outcomes(normalized, runs=GITHUB_ACTIONS_RACE_SIMULATION_RUNS if os.getenv("GITHUB_ACTIONS") else min(RACE_SIMULATION_RUNS, 1000))
    sim_by_driver = {row.get("driver_id"): row for row in simulation.get("drivers", [])}
    for row in normalized:
        uncertainty = uncertainty_for_prediction(row, source_health=source_health, stage=stage)
        row.setdefault("uncertainty", uncertainty)
        row.setdefault("uncertainty_score", uncertainty["total_uncertainty"])
        row.setdefault("prediction_confidence", row.get("confidence"))
        row.setdefault("confidence_interval_low", row.get("best_case_finish"))
        row.setdefault("confidence_interval_high", row.get("worst_case_finish"))
        row.setdefault("uncertainty_reasons", uncertainty["uncertainty_reasons"])
        row.setdefault("low_confidence_reason", ", ".join(uncertainty["uncertainty_reasons"]) if uncertainty["uncertainty_reasons"] else None)
        row.setdefault("cannot_know_factors", [
            "safety cars, red flags, crashes, weather shifts, mechanical issues, and late FIA decisions can change outcomes",
        ])
        row.setdefault("prediction_risk_level", uncertainty["prediction_risk_level"])
        row.setdefault("recommended_interpretation", "Use as calibrated probabilities and uncertainty-aware ranking, not a guarantee.")
        row.setdefault("dnf_probability", round(clamp(100 - (safe_float(row.get("reliability")) or 70), 2, 45, 12), 2))
        row.setdefault("classified_finish_probability", round(100 - row["dnf_probability"], 2))
        sim = sim_by_driver.get(row.get("driver_id")) or {}
        row.setdefault("simulation", sim)
    return normalized, simulation


def normalize_entry_contract(entry):
    prediction_model = entry.get("prediction_model") or {}
    race = entry.get("jolpica_race") or {}
    season = safe_int(entry.get("season") or race.get("season")) or safe_int(now_local().year)
    round_no = safe_int(entry.get("round") or race.get("round")) or 0
    race_id = entry.get("race_id") or f"{season}-{round_no}-{make_slug(race.get('raceName') or entry.get('title'))}"
    stage = entry.get("stage") or prediction_model.get("prediction_stage") or "pre_weekend"
    target_type = entry.get("target_type") or prediction_model.get("output_target_type") or "race"
    prediction_id = entry.get("prediction_id") or f"{race_id}-{target_type}-{stage}"
    def normalize_prediction_items(items, limit=None):
        normalized = []
        seen = set()
        for idx, item in enumerate(items or [], start=1):
            enriched = dict(item)
            driver_key = enriched.get("driver_id") or enriched.get("name")
            if driver_key in seen:
                continue
            seen.add(driver_key)
            enriched.setdefault("rank", idx)
            enriched.setdefault("previous_rank", enriched.get("rank") or idx)
            enriched.setdefault("rank_delta", 0)
            enriched.setdefault("confidence_delta", 0)
            enriched.setdefault("prediction_id", prediction_id)
            enriched.setdefault("race_id", race_id)
            enriched.setdefault("season", season)
            enriched.setdefault("round", round_no)
            enriched.setdefault("target_type", target_type)
            enriched.setdefault("stage", stage)
            enriched.setdefault("model_version", entry.get("model_version") or MODEL_SCHEMA_VERSION)
            enriched.setdefault("schema_version", entry.get("schema_version") or MODEL_SCHEMA_VERSION)
            enriched.setdefault("generated_at", entry.get("generated_iso"))
            enriched.setdefault("input_data_hash", entry.get("input_data_hash") or stable_hash(item))
            enriched.setdefault("prediction_data_version", PREDICTION_DATA_VERSION)
            components = enriched.get("component_scores") or {}
            for out_key, comp_key in [
                ("win_probability", "ml_win_probability"),
                ("podium_probability", "ml_podium_probability"),
                ("top10_probability", "ml_top10_probability"),
                ("reliability", "reliability"),
            ]:
                enriched.setdefault(out_key, pct_value(components.get(comp_key)))
            predicted = safe_float(enriched.get("predicted_finish_position")) or safe_float(enriched.get("rank")) or idx
            enriched.setdefault("predicted_finish_position", round(predicted, 2))
            enriched.setdefault("best_case_finish", max(1, int(round(predicted - 2))))
            enriched.setdefault("likely_finish", int(round(predicted)))
            enriched.setdefault("worst_case_finish", min(22, int(round(predicted + 3))))
            enriched.setdefault("finish_interval_low", enriched["best_case_finish"])
            enriched.setdefault("finish_interval_high", enriched["worst_case_finish"])
            enriched.setdefault("reason_tags", reason_tags_from_components(components))
            enriched.setdefault("weakness_tags", weakness_tags_from_components(components, {"missing": []}))
            enriched.setdefault("model_agreement_score", model_agreement_from_components(components)[0])
            enriched.setdefault("disagreement_flags", [])
            enriched.setdefault("evidence_status", {"available": [k for k, v in components.items() if v is not None], "missing": [], "penalties": {}, "penalty_total": 0})
            enriched.setdefault("missing_data_penalties", {})
            enriched.setdefault("attack_potential_score", pct_value(components.get("race_pace")) or pct_value(enriched.get("score")) or 50)
            enriched.setdefault("defend_risk_score", 100 - (pct_value(components.get("reliability")) or 50))
            enriched.setdefault("energy_boost_advantage_score", pct_value(components.get("regulation_fit")) or 55)
            enriched.setdefault("active_aero_suitability_score", pct_value(components.get("track_trait_fit")) or 55)
            enriched.setdefault("expected_points", finish_points_for_position(enriched.get("likely_finish")))
            enriched.setdefault("top10_safety_score", weighted_average([(enriched.get("top10_probability"), 0.6), (enriched.get("reliability"), 0.4)]) or 50)
            enriched.setdefault("dark_horse_flag", False)
            enriched.setdefault("bust_risk_flag", False)
            enriched.setdefault("predicted_finish", enriched.get("predicted_finish_position"))
            enriched.setdefault("points_probability", enriched.get("top10_probability"))
            fastest_lap_score = weighted_average([
                (components.get("race_pace"), 0.35),
                (components.get("timing_lap_pace"), 0.25),
                (components.get("qualifying"), 0.20),
                (enriched.get("score"), 0.20),
            ])
            enriched.setdefault("fastest_lap_probability", probability_from_score(fastest_lap_score or enriched.get("score"), low=0.8, high=16.0))
            enriched.setdefault("position_range", [enriched.get("best_case_finish"), enriched.get("worst_case_finish")])
            enriched.setdefault("expected_strategy", strategy_profile_for_row(enriched, entry, entry.get("weather") or {}))
            enriched.setdefault("strategy_annotations", detect_strategy_context_annotations(enriched.get("strategy_context"), entry.get("weather") or {}))
            enriched.setdefault("explanation", explanation_for_prediction_row(enriched, entry, entry.get("weather") or {}))
            enriched.setdefault("confidence_label", confidence_label(enriched.get("confidence")))
            enriched.setdefault("data_freshness", {
                "generated_at": entry.get("generated_iso"),
                "stage": stage,
                "timing_mode": entry.get("timing_mode"),
                "source_health_status": source_health.get("status"),
            })
            enriched.setdefault("source_notes", {
                "source_health": source_health.get("status"),
                "source_score": source_health.get("overall_score"),
                "warnings": (entry.get("source_registry") or {}).get("warnings", []),
            })
            normalized.append(enriched)
            if limit and len(normalized) >= limit:
                break
        return normalized

    source_health = sanitize_source_health(
        entry.get("source_health")
        or entry.get("source_health_snapshot")
        or prediction_model.get("source_health_snapshot")
        or build_source_health_snapshot()
    )
    full_grid = normalize_prediction_items(entry.get("full_grid") or entry.get("all_predictions") or entry.get("top10") or [])
    full_grid, simulation = enrich_predictions_with_quality_outputs(full_grid, source_health=source_health, stage=stage)
    top10 = normalize_prediction_items(entry.get("top10") or full_grid[:10], limit=10)
    top10, _ = enrich_predictions_with_quality_outputs(top10, source_health=source_health, stage=stage)
    if not full_grid:
        full_grid = top10
    registry = entry.get("source_registry") or load_or_build_source_registry(season)
    fia_summary = fia_document_summary(registry, entry)
    contract_warnings = []
    for warning_source in [
        entry.get("warnings"),
        (entry.get("source_registry") or {}).get("warnings", []),
        source_health.get("warnings", []),
        fia_summary.get("fia_parse_errors", []),
    ]:
        for warning in warning_source or []:
            if warning and warning not in contract_warnings:
                contract_warnings.append(warning)
    if contract_warnings:
        for row in full_grid + top10:
            notes = row.setdefault("source_notes", {})
            row_warnings = list(notes.get("warnings") or [])
            for warning in contract_warnings[:8]:
                if warning not in row_warnings:
                    row_warnings.append(warning)
            notes["warnings"] = row_warnings
    session_timeline = entry.get("session_timeline") or build_session_timeline_from_race(race, registry.get("formula1_season_url")) if race else []
    session_timeline = sanitize_session_timeline_for_stage(session_timeline, stage)
    session_state = session_contract_state(session_timeline)
    timing = entry.get("timing_status") or timing_freshness_status(
        last_updated=entry.get("generated_iso"),
        now=now_local().astimezone(timezone.utc),
        session_end=entry.get("start_iso"),
        has_fresh_packets=False,
        source="Generated contract",
    )
    effective_weights = entry.get("effective_model_weights") or prediction_model.get("stage_weights") or stage_prediction_weights(stage, entry, entry.get("weather") or {})
    return {
        **entry,
        "race_id": race_id,
        "prediction_id": prediction_id,
        "race_name": entry.get("race_name") or race.get("raceName") or entry.get("title"),
        "season": season,
        "round": round_no,
        "target_type": target_type,
        "stage": stage,
        "prediction_stage": stage,
        "model_version": entry.get("model_version") or MODEL_SCHEMA_VERSION,
        "schema_version": entry.get("schema_version") or MODEL_SCHEMA_VERSION,
        "prediction_data_version": PREDICTION_DATA_VERSION,
        "source_registry": registry,
        "session_timeline": session_timeline,
        **session_state,
        "effective_model_weights": {k: round(v, 4) for k, v in effective_weights.items()},
        "source_health": source_health,
        "source_status": entry.get("source_status") or source_health,
        "source_conflicts": entry.get("source_conflicts") or [],
        "model_limitations": [
            "Predictions are uncertainty-aware estimates, not guaranteed outcomes.",
            "Missing FIA documents, delayed APIs, weather shifts, race control, and mechanical failures reduce confidence.",
        ],
        "timing_mode": timing.get("timing_mode"),
        "is_genuinely_live": timing.get("is_genuinely_live"),
        **timing,
        **fia_summary,
        "session_feature_contributions": entry.get("session_feature_contributions") or {},
        "driver_prediction_explanations": entry.get("driver_prediction_explanations") or {},
        "team_prediction_explanations": entry.get("team_prediction_explanations") or {},
        "calibration_status": entry.get("calibration_status") or {"method": "race_level_probability_normalization", "status": "available"},
        "probability_normalization_status": {
            "win_sum": round(sum(safe_float(row.get("win_probability")) or 0 for row in full_grid), 4),
            "podium_sum": round(sum(safe_float(row.get("podium_probability")) or 0 for row in full_grid), 4),
            "top10_sum": round(sum(safe_float(row.get("top10_probability")) or 0 for row in full_grid), 4),
            "status": "normalized",
        },
        "missing_data_penalties": {row.get("driver_id"): row.get("missing_data_penalties", {}) for row in full_grid},
        "confidence_breakdown": {
            "average_confidence": round(average([row.get("confidence") for row in full_grid]) or 0, 2),
            "average_uncertainty": round(average([row.get("uncertainty_score") for row in full_grid]) or 0, 2),
            "source_health_score": source_health.get("overall_score"),
        },
        "dnf_survival": {row.get("driver_id"): {"dnf_probability": row.get("dnf_probability"), "classified_finish_probability": row.get("classified_finish_probability")} for row in full_grid},
        "simulation": simulation,
        "race_factors": entry.get("race_factors") or race_factors_from_context(entry, entry.get("weather") or {}, source_health),
        "scenario_predictions": entry.get("scenario_predictions") or prediction_model.get("scenarios") or {},
        "uncertainty_outputs": {row.get("driver_id"): row.get("uncertainty") for row in full_grid},
        "upgrade_impact_contribution": entry.get("upgrade_context") or {},
        "regulation_proxy_contribution": entry.get("regulation_context") or {},
        "scenarios": entry.get("scenarios") or prediction_model.get("scenarios") or scenario_rankings(full_grid, entry, entry.get("weather") or {}),
        "strategy": entry.get("strategy") or build_strategy_contract(entry, entry.get("weather") or {}, top10, prediction_model),
        "model_metrics": entry.get("model_metrics") or ((prediction_model.get("ml_model_meta") or {}).get("metrics") or {}),
        "correction_summary": entry.get("correction_summary") or correction_summary_for_entry(race_id),
        "actual_result": entry.get("actual_result"),
        "warnings": contract_warnings,
        "top10": top10,
        "top_10": top10,
        "full_grid": full_grid,
        "all_predictions": full_grid,
    }


def build_archive_contract(briefings):
    archive = []
    for entry in briefings:
        top = (entry.get("top10") or [{}])[0]
        actual = entry.get("actual_result")
        actual_winner = (actual or {}).get("winner") if isinstance(actual, dict) else None
        accuracy = None
        if actual_winner and top.get("driver_id"):
            accuracy = 1.0 if actual_winner.get("driver_id") == top.get("driver_id") else 0.0
        archive.append({
            "race_id": entry.get("race_id"),
            "prediction_id": entry.get("prediction_id"),
            "title": entry.get("title"),
            "race_name": entry.get("race_name"),
            "season": entry.get("season"),
            "round": entry.get("round"),
            "path": entry.get("path"),
            "generated_iso": entry.get("generated_iso"),
            "start_iso": entry.get("start_iso"),
            "stage": entry.get("stage"),
            "prediction_stage": entry.get("prediction_stage"),
            "model_version": entry.get("model_version"),
            "top_pick": top.get("name"),
            "top_pick_team": top.get("team"),
            "confidence": top.get("confidence"),
            "actual_winner": actual_winner.get("name") if actual_winner else None,
            "accuracy": accuracy,
            "correction_summary": entry.get("correction_summary"),
            "briefing": entry,
        })
    return archive


def generate_feature_store(briefings):
    ensure_dirs()
    race_features = []
    driver_features = []
    team_acc = {}
    session_features = []
    for entry in briefings:
        race_features.append({
            "race_id": entry.get("race_id"),
            "prediction_id": entry.get("prediction_id"),
            "season": entry.get("season"),
            "round": entry.get("round"),
            "circuit": entry.get("circuit"),
            "city": entry.get("city"),
            "country": entry.get("country"),
            "track_type": entry.get("track_type"),
            "overtaking": entry.get("overtaking"),
            "tyre_stress": entry.get("tyre_stress"),
            "safety_car": entry.get("safety_car"),
            "weather": entry.get("weather"),
            "strategy": entry.get("strategy"),
        })
        session_features.append({
            "race_id": entry.get("race_id"),
            "target_type": entry.get("target_type"),
            "stage": entry.get("stage"),
            "start_iso": entry.get("start_iso"),
            "source_health": entry.get("source_health"),
        })
        for item in entry.get("full_grid") or entry.get("top10") or []:
            driver_features.append({
                "race_id": entry.get("race_id"),
                "prediction_id": entry.get("prediction_id"),
                "driver_id": item.get("driver_id"),
                "name": item.get("name"),
                "team": item.get("team"),
                "rank": item.get("rank"),
                "score": item.get("score"),
                "confidence": item.get("confidence"),
                "component_scores": item.get("component_scores"),
                "evidence_status": item.get("evidence_status"),
            })
            team = item.get("team") or "Unknown"
            team_acc.setdefault(team, []).append(item)
    team_features = []
    for team, items in team_acc.items():
        team_features.append({
            "team": team,
            "expected_team_points": round(sum(safe_float(item.get("expected_points")) or 0 for item in items), 2),
            "average_score": round(average([item.get("score") for item in items]) or 0, 2),
            "average_confidence": round(average([item.get("confidence") for item in items]) or 0, 2),
            "average_active_aero_suitability": round(average([item.get("active_aero_suitability_score") for item in items]) or 0, 2),
            "average_energy_boost_advantage": round(average([item.get("energy_boost_advantage_score") for item in items]) or 0, 2),
            "drivers": [item.get("name") for item in items],
        })
    for name, data in [
        ("race_features.json", race_features),
        ("driver_features.json", driver_features),
        ("team_features.json", team_features),
        ("session_features.json", session_features),
    ]:
        (FEATURES_DIR / name).write_text(json.dumps(data, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
        try:
            init_pitwall_db()
            with sqlite3.connect(PITWALL_DB_PATH) as conn:
                conn.execute(
                    """
                    INSERT INTO feature_snapshots(feature_id, created_at, feature_version, payload_json)
                    VALUES (?, ?, ?, ?)
                    ON CONFLICT(feature_id) DO UPDATE SET
                        created_at=excluded.created_at,
                        feature_version=excluded.feature_version,
                        payload_json=excluded.payload_json
                    """,
                    (name, now_local().isoformat(), MODEL_SCHEMA_VERSION, json.dumps(data, ensure_ascii=False, default=str)),
                )
                conn.commit()
        except Exception as error:
            print(f"SQLite feature snapshot skipped for {name}: {error}")


def generate_correction_log(briefings):
    corrections = []
    for entry in briefings:
        actual = entry.get("actual_result")
        if not actual:
            continue
        actual_rows = {row.get("driver_id"): row for row in actual.get("classification", [])}
        errors = []
        for item in entry.get("top10") or []:
            row = actual_rows.get(item.get("driver_id"))
            if not row:
                continue
            predicted = safe_int(item.get("likely_finish") or item.get("rank"))
            actual_pos = safe_int(row.get("position"))
            if predicted and actual_pos:
                errors.append({
                    "driver_id": item.get("driver_id"),
                    "name": item.get("name"),
                    "predicted_position": predicted,
                    "actual_position": actual_pos,
                    "position_error": abs(predicted - actual_pos),
                })
        errors.sort(key=lambda row: row["position_error"], reverse=True)
        corrections.append({
            "race_id": entry.get("race_id"),
            "prediction_id": entry.get("prediction_id"),
            "actual_result": actual,
            "predicted_result": entry.get("top10"),
            "errors": errors,
            "summary": {
                "status": "Available",
                "biggest_model_surprise": errors[0] if errors else None,
                "biggest_model_miss": errors[0] if errors else None,
                "weak_feature_groups": ["scenario volatility", "race execution"] if errors else [],
                "correction_suggestions": ["Review features that underweighted final classification movement."] if errors else [],
                "learning_notes": "Correction generated from official result rows.",
            },
            "retrain_status": "queued_for_controlled_champion_challenger_cycle",
        })
    payload = {
        "schema_version": MODEL_SCHEMA_VERSION,
        "generated_at": now_local().isoformat(),
        "status": "Available" if corrections else "Pending",
        "corrections": corrections,
    }
    payload = sanitize_public_paths(payload)
    MODEL_CORRECTIONS_PATH.write_text(json.dumps(payload, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    return payload


def generate_backtest_history(briefings):
    meta = read_model_meta()
    metrics = meta.get("metrics") or {}
    rows = []
    for entry in briefings:
        top = (entry.get("top10") or [{}])[0]
        rows.append({
            "race_id": entry.get("race_id"),
            "prediction_id": entry.get("prediction_id"),
            "race_name": entry.get("race_name"),
            "season": entry.get("season"),
            "round": entry.get("round"),
            "stage": entry.get("stage"),
            "model_version": entry.get("model_version"),
            "top_pick": top.get("name"),
            "top_pick_confidence": top.get("confidence"),
            "finish_position_mae": (metrics.get("finish_position") or {}).get("mae"),
            "finish_position_rmse": (metrics.get("finish_position") or {}).get("rmse"),
            "winner_hit_rate": ((metrics.get("finish_position") or {}).get("ranking") or metrics.get("win_probability_ranking") or {}).get("winner_hit"),
            "top3_recall": ((metrics.get("finish_position") or {}).get("ranking") or metrics.get("win_probability_ranking") or {}).get("top3_recall"),
            "top10_recall": ((metrics.get("finish_position") or {}).get("ranking") or metrics.get("win_probability_ranking") or {}).get("top10_recall"),
        })
    payload = {
        "schema_version": MODEL_SCHEMA_VERSION,
        "generated_at": now_local().isoformat(),
        "history": rows,
    }
    payload = sanitize_public_paths(payload)
    BACKTEST_HISTORY_PATH.write_text(json.dumps(payload, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    return payload


def generate_frontend_contract_files(index_data=None):
    ensure_dirs()
    data = index_data or latest_index_data()
    briefings = [normalize_entry_contract(entry) for entry in data.get("briefings", [])]
    for entry in briefings:
        sqlite_upsert_prediction(entry)
    latest = briefings[0] if briefings else None
    season = safe_int((latest or {}).get("season")) or resolve_target_season()
    registry = (latest or {}).get("source_registry") or load_or_build_source_registry(season)
    fia_summary = fia_document_summary(registry, latest)
    timing = {
        "live_timing_status": (latest or {}).get("live_timing_status", "Unavailable"),
        "timing_mode": (latest or {}).get("timing_mode", "unavailable"),
        "timing_source": (latest or {}).get("timing_source"),
        "timing_last_updated_at": (latest or {}).get("timing_last_updated_at"),
        "timing_freshness_seconds": (latest or {}).get("timing_freshness_seconds"),
        "is_genuinely_live": (latest or {}).get("is_genuinely_live", False),
        "live_fallback_reason": (latest or {}).get("live_fallback_reason", "No generated live timing status yet."),
    }
    contract = {
        "schema_version": MODEL_SCHEMA_VERSION,
        "prediction_data_version": PREDICTION_DATA_VERSION,
        "generated_at": now_local().isoformat(),
        "season": season,
        "target_event": (latest or {}).get("race_name"),
        "prediction_stage": (latest or {}).get("prediction_stage"),
        "previous_prediction_stage": None,
        "session_timeline": (latest or {}).get("session_timeline", []),
        "last_ingested_session": (latest or {}).get("last_ingested_session"),
        "next_session_to_ingest": (latest or {}).get("next_session_to_ingest"),
        "pending_session_checks": (latest or {}).get("pending_session_checks", []),
        "session_data_delay_status": (latest or {}).get("session_data_delay_status", "unknown"),
        "session_official_status": (latest or {}).get("session_official_status", "unknown"),
        "effective_model_weights": (latest or {}).get("effective_model_weights", {}),
        "source_registry": registry,
        "dataset_sources": optional_dataset_source_statuses(),
        "source_health": (latest or {}).get("source_health") or latest_source_health_from_index(),
        "source_conflicts": (latest or {}).get("source_conflicts", []),
        "model_limitations": (latest or {}).get("model_limitations", []),
        **fia_summary,
        **timing,
        "briefings": briefings,
        "latest": latest,
        "archive": build_archive_contract(briefings),
        "model_status": json.loads(MODEL_STATUS_JSON_PATH.read_text(encoding="utf-8")) if MODEL_STATUS_JSON_PATH.exists() else None,
        "storage": {"sqlite_path": str(PITWALL_DB_PATH.relative_to(BASE_DIR)) if PITWALL_DB_PATH.is_relative_to(BASE_DIR) else str(PITWALL_DB_PATH), "supabase": supabase_sync_status()},
    }
    contract = sanitize_public_paths(sanitize_timing_source_labels(contract))
    (DATA_CACHE_DIR / "frontend-contract.json").write_text(json.dumps(contract, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    generate_feature_store(briefings)
    corrections = generate_correction_log(briefings)
    backtest = generate_backtest_history(briefings)
    if MODEL_STATUS_JSON_PATH.exists():
        try:
            model_status = json.loads(MODEL_STATUS_JSON_PATH.read_text(encoding="utf-8"))
            model_status["correction_log_summary"] = {
                "count": len(corrections.get("corrections", [])),
                "status": corrections.get("status"),
            }
            model_status["backtest_history_count"] = len(backtest.get("history", []))
            MODEL_STATUS_JSON_PATH.write_text(json.dumps(model_status, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
        except Exception:
            pass
    return contract


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
    if os.getenv("AUTO_COMMIT_ENABLED", "false").lower() != "true":
        print("Auto commit disabled. Set AUTO_COMMIT_ENABLED=true to let f1_briefing.py commit generated files.")
        return
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
    safe_step("Issue status", create_or_update_issue, "PitWall Status", details)
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

    ml_outputs, ml_debug = ml_predict_probabilities(drivers, race, current_round_data, bundle, stage=stage)
    timing_scores = safe_step("External timing enhancement", external_timing_enhancement_scores, race, drivers) or {"provider_status": "failed"}
    fastf1_scores = safe_step("FastF1 enhancement", fastf1_enhancement_scores, season, round_no) or {"sessions_loaded": []}

    top10_text, top10, full_grid, prediction_model = rank_prediction(
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
        "full_grid": full_grid,
        "all_predictions": full_grid,
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
        return "PitWall: No Sprint/Race output target found", ""

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

Generated by PitWall. Predictions are model estimates, not guaranteed race results.
"""
    return title, briefing


def run(force_retrain=False):
    ensure_dirs()
    require_env_vars()
    target_season = resolve_target_season()
    source_registry = safe_step("Discover season source registry", load_or_build_source_registry, target_season)
    if FIA_DOCUMENTS_ENABLED:
        safe_step(
            "Refresh FIA decision-document cache",
            refresh_fia_documents_for_season,
            target_season,
            source_registry,
            REFRESH_FIA_DOCUMENTS,
        )

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
        safe_step("Generate frontend contracts", generate_frontend_contract_files)
        safe_step("Commit status", commit_and_push, [
            status_path,
            model_status_path,
            MODEL_STATUS_JSON_PATH,
            BACKTEST_HISTORY_PATH,
            MODEL_CORRECTIONS_PATH,
            DATA_CACHE_DIR / "frontend-contract.json",
            FEATURES_DIR,
        ])
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
        safe_step("Generate frontend contracts", generate_frontend_contract_files)
        safe_step("Commit status", commit_and_push, [
            status_path,
            model_status_path,
            MODEL_STATUS_JSON_PATH,
            BACKTEST_HISTORY_PATH,
            MODEL_CORRECTIONS_PATH,
            DATA_CACHE_DIR / "frontend-contract.json",
            FEATURES_DIR,
        ])
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
        primary.get("full_grid"),
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
    safe_step("Refresh frontend contracts after model status", generate_frontend_contract_files)

    paths = [
        markdown_path,
        index_path,
        status_path,
        debug_path,
        model_status_path,
        MODEL_STATUS_JSON_PATH,
        BACKTEST_HISTORY_PATH,
        MODEL_CORRECTIONS_PATH,
        DATA_CACHE_DIR / "frontend-contract.json",
        FEATURES_DIR,
        MODEL_INPUT_SNAPSHOT_DIR,
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
