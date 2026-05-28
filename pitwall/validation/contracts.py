"""Validation for generated PitWall JSON artifacts."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class ContractValidationError(RuntimeError):
    """Raised when a generated JSON contract is missing or unsafe for the UI."""


REQUIRED_ROW_KEYS = {
    "driver_id",
    "name",
    "team",
    "rank",
    "score",
    "confidence",
    "win_probability",
    "podium_probability",
    "top10_probability",
}


def _read_json(path: Path) -> Any:
    if not path.exists():
        raise ContractValidationError(f"{path} is missing")
    if path.stat().st_size <= 2:
        raise ContractValidationError(f"{path} is empty or blank")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise ContractValidationError(f"{path} is invalid JSON: {error}") from error


def _as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def validate_prediction_row(row: dict[str, Any], *, path: str = "row") -> list[str]:
    errors: list[str] = []
    missing = sorted(REQUIRED_ROW_KEYS - set(row.keys()))
    if missing:
        errors.append(f"{path} missing required keys: {', '.join(missing)}")
    if not str(row.get("driver_id") or "").strip():
        errors.append(f"{path} has blank driver_id")
    for key in ["rank", "score", "confidence", "win_probability", "podium_probability", "top10_probability"]:
        value = row.get(key)
        try:
            number = float(value)
        except (TypeError, ValueError):
            errors.append(f"{path}.{key} is not numeric")
            continue
        if key != "rank" and not 0 <= number <= 1000:
            errors.append(f"{path}.{key} outside expected range")
    return errors


def validate_frontend_contract(contract: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    latest = contract.get("latest")
    if not isinstance(latest, dict):
        errors.append("latest is missing or not an object")
        latest = {}
    top10 = _as_list(latest.get("top10") or latest.get("top_10"))
    full_grid = _as_list(latest.get("full_grid") or latest.get("all_predictions"))
    all_predictions = _as_list(latest.get("all_predictions") or latest.get("full_grid"))
    if not top10:
        errors.append("latest.top10 is missing or empty")
    if len(full_grid) < len(top10):
        errors.append("latest.full_grid is missing or smaller than top10")
    if len(all_predictions) < len(top10):
        errors.append("latest.all_predictions is missing or smaller than top10")
    for idx, row in enumerate(top10, start=1):
        if not isinstance(row, dict):
            errors.append(f"latest.top10[{idx}] is not an object")
            continue
        errors.extend(validate_prediction_row(row, path=f"latest.top10[{idx}]"))
    for idx, row in enumerate(full_grid, start=1):
        if not isinstance(row, dict):
            errors.append(f"latest.full_grid[{idx}] is not an object")
            continue
        errors.extend(validate_prediction_row(row, path=f"latest.full_grid[{idx}]"))
    ids = [row.get("driver_id") for row in full_grid if isinstance(row, dict)]
    if len(ids) != len(set(ids)):
        errors.append("latest.full_grid contains duplicate driver_id values")
    if errors:
        raise ContractValidationError("; ".join(errors))
    return {
        "latest_top10_count": len(top10),
        "latest_full_grid_count": len(full_grid),
        "latest_all_predictions_count": len(all_predictions),
    }


def validate_contract_files(base_dir: Path | str = ".") -> dict[str, Any]:
    base = Path(base_dir)
    frontend = _read_json(base / "data_cache" / "frontend-contract.json")
    index = _read_json(base / "briefings" / "index.json")
    debug = _read_json(base / "data_cache" / "latest-model-debug.json")
    model_status = _read_json(base / "data_cache" / "model-status.json")

    summary = validate_frontend_contract(frontend)
    if not _as_list(index.get("briefings") if isinstance(index, dict) else None):
        raise ContractValidationError("briefings/index.json missing non-empty briefings")
    if not _as_list(debug.get("payloads") if isinstance(debug, dict) else None):
        raise ContractValidationError("data_cache/latest-model-debug.json missing payloads")
    if not isinstance(model_status, dict) or not (model_status.get("model_version") or model_status.get("schema_version")):
        raise ContractValidationError("data_cache/model-status.json missing model version/schema")
    if not isinstance(model_status.get("metrics"), dict) or not model_status.get("metrics"):
        raise ContractValidationError("data_cache/model-status.json missing metrics")
    return {
        "ok": True,
        "schema_version": frontend.get("schema_version"),
        "prediction_data_version": frontend.get("prediction_data_version"),
        "briefing_count": len(index.get("briefings", [])),
        "debug_payload_count": len(debug.get("payloads", [])),
        "model_version": model_status.get("model_version") or model_status.get("schema_version"),
        **summary,
    }
