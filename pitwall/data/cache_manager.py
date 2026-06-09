"""Cache manifest and atomic cache helpers for PitWall data sources."""

from __future__ import annotations

import gzip
import json
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from typing import Any, Callable


Manifest = dict[str, Any]


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_manifest(path: Path) -> Manifest:
    if not path.exists() or path.stat().st_size <= 2:
        return {"schema_version": 1, "updated_at": None, "entries": {}}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {"schema_version": 1, "updated_at": None, "entries": {}}
    if not isinstance(data, dict):
        return {"schema_version": 1, "updated_at": None, "entries": {}}
    data.setdefault("schema_version", 1)
    data.setdefault("entries", {})
    return data


def atomic_write_json(path: Path, payload: Manifest) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
    json.loads(tmp.read_text(encoding="utf-8"))
    tmp.replace(path)
    return path


def file_checksum(path: Path) -> str | None:
    if not path.exists() or not path.is_file():
        return None
    digest = sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def manifest_file_path(file_path: Path, manifest_path: Path) -> str:
    """Store portable manifest paths when the cache lives inside the repo."""
    try:
        manifest_parent = manifest_path.resolve().parent
        repo_root = manifest_parent.parent if manifest_parent.name == "data_cache" else manifest_parent
        return str(file_path.resolve().relative_to(repo_root))
    except Exception:
        return str(file_path)


def parse_json_or_gzip(path: Path) -> Any:
    if path.suffix == ".gz":
        with gzip.open(path, "rt", encoding="utf-8") as handle:
            return json.load(handle)
    return json.loads(path.read_text(encoding="utf-8"))


def validate_json_cache(path: Path, required_top_level_keys: list[str] | None = None) -> tuple[bool, str, Any | None]:
    if not path.exists():
        return False, "missing", None
    if path.stat().st_size <= 2:
        return False, "empty", None
    try:
        payload = parse_json_or_gzip(path)
    except Exception as error:
        return False, f"corrupt: {error}", None
    if required_top_level_keys and isinstance(payload, dict):
        missing = [key for key in required_top_level_keys if key not in payload]
        if missing:
            return False, f"schema_invalid_missing_{','.join(missing)}", payload
    return True, "valid", payload


def record_cache_event(
    manifest_path: Path,
    *,
    cache_key: str,
    source: str,
    file_path: Path,
    status: str,
    action: str,
    reason: str,
    coverage: dict[str, Any] | None = None,
    schema_version: str | int | None = None,
    validation_status: str = "unknown",
) -> Manifest:
    manifest = load_manifest(manifest_path)
    entries = manifest.setdefault("entries", {})
    stat_size = file_path.stat().st_size if file_path.exists() else 0
    entries[cache_key] = {
        "source": source,
        "file_path": manifest_file_path(file_path, manifest_path),
        "last_checked_at": utc_now_iso(),
        "last_fetched_time": utc_now_iso() if action == "refreshed" else entries.get(cache_key, {}).get("last_fetched_time"),
        "data_coverage_range": coverage or entries.get(cache_key, {}).get("data_coverage_range"),
        "schema_version": schema_version,
        "checksum": file_checksum(file_path),
        "file_size": stat_size,
        "freshness_status": status,
        "latest_run_action": action,
        "reason": reason,
        "validation_status": validation_status,
    }
    manifest["updated_at"] = utc_now_iso()
    atomic_write_json(manifest_path, manifest)
    return manifest


def cache_aware_json_loader(
    *,
    cache_key: str,
    source: str,
    file_path: Path,
    manifest_path: Path,
    fetcher: Callable[[], Any],
    writer: Callable[[Any], Path],
    validator: Callable[[Path], tuple[bool, str, Any | None]] | None = None,
    force_refresh: bool = False,
    required: bool = True,
) -> Any:
    validator = validator or (lambda path: validate_json_cache(path))
    valid, reason, payload = validator(file_path)
    if valid and not force_refresh:
        record_cache_event(
            manifest_path,
            cache_key=cache_key,
            source=source,
            file_path=file_path,
            status="fresh",
            action="reused",
            reason="cache_valid",
            validation_status=reason,
        )
        return payload

    try:
        fetched = fetcher()
    except Exception:
        if payload is not None and not required:
            record_cache_event(
                manifest_path,
                cache_key=cache_key,
                source=source,
                file_path=file_path,
                status="stale_fallback",
                action="fallback_reused",
                reason=reason,
                validation_status="optional_fetch_failed",
            )
            return payload
        raise

    written = writer(fetched)
    valid_after, reason_after, payload_after = validator(written)
    if not valid_after:
        raise ValueError(f"refreshed cache is invalid for {cache_key}: {reason_after}")
    record_cache_event(
        manifest_path,
        cache_key=cache_key,
        source=source,
        file_path=written,
        status="fresh",
        action="refreshed",
        reason="force_refresh" if force_refresh else reason,
        validation_status=reason_after,
    )
    return payload_after
