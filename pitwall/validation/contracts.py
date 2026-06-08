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
    "rank_score",
    "confidence",
    "win_probability",
    "podium_probability",
    "top10_probability",
    "predicted_position",
    "probability",
    "prediction_trust",
    "points_probability",
    "fastest_lap_probability",
    "position_range",
    "expected_strategy",
    "explanation",
    "source_notes",
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


def _as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def validate_prediction_row(row: dict[str, Any], *, path: str = "row") -> list[str]:
    errors: list[str] = []
    missing = sorted(REQUIRED_ROW_KEYS - set(row.keys()))
    if missing:
        errors.append(f"{path} missing required keys: {', '.join(missing)}")
    if not str(row.get("driver_id") or "").strip():
        errors.append(f"{path} has blank driver_id")
    for key in ["rank", "score", "rank_score", "confidence", "win_probability", "podium_probability", "top10_probability", "predicted_position", "probability", "points_probability", "fastest_lap_probability"]:
        value = row.get(key)
        try:
            number = float(value)
        except (TypeError, ValueError):
            errors.append(f"{path}.{key} is not numeric")
            continue
        if key != "rank" and not 0 <= number <= 1000:
            errors.append(f"{path}.{key} outside expected range")
    if "prediction_trust_score" in row:
        try:
            trust = float(row.get("prediction_trust_score"))
        except (TypeError, ValueError):
            errors.append(f"{path}.prediction_trust_score is not numeric")
        else:
            if not 0 <= trust <= 100:
                errors.append(f"{path}.prediction_trust_score outside 0-100 range")
    if "ai_explanation" in row and not isinstance(row.get("ai_explanation"), dict):
        errors.append(f"{path}.ai_explanation is not an object")
    if "position_range" in row and not isinstance(row.get("position_range"), list):
        errors.append(f"{path}.position_range is not a list")
    for key in ["expected_strategy", "explanation", "source_notes"]:
        if key in row and not isinstance(row.get(key), dict):
            errors.append(f"{path}.{key} is not an object")
    if "model_disagreement_level" in row and row.get("model_disagreement_level") not in {"low", "medium", "high"}:
        errors.append(f"{path}.model_disagreement_level is invalid")
    return errors


def validate_model_comparison(value: Any, *, path: str = "model_comparison") -> list[str]:
    errors: list[str] = []
    item = _as_dict(value)
    if not item:
        return [f"{path} is missing or not an object"]
    for key in ["champion", "challenger", "promotion_decision", "metrics"]:
        if not isinstance(item.get(key), dict):
            errors.append(f"{path}.{key} is missing or not an object")
    if "warnings" in item and not isinstance(item.get("warnings"), list):
        errors.append(f"{path}.warnings is not a list")
    return errors


def validate_actual_result_comparison(value: Any, *, path: str = "actual_result_comparison") -> list[str]:
    errors: list[str] = []
    item = _as_dict(value)
    if not item:
        return [f"{path} is missing or not an object"]
    status = item.get("status")
    if status not in {"available", "pending", "unavailable", "incomplete", "source_stale", "source_failed", "not_yet_raced"}:
        errors.append(f"{path}.status is invalid")
    for key in ["race", "predicted_winner", "actual_winner", "metrics"]:
        if not isinstance(item.get(key), dict):
            errors.append(f"{path}.{key} is missing or not an object")
    for key in ["predicted_podium", "actual_podium", "predicted_top10", "actual_top10", "driver_position_errors", "source_health", "warnings"]:
        if not isinstance(item.get(key), list):
            errors.append(f"{path}.{key} is missing or not a list")
    for key in ["podium_recall", "top10_recall"]:
        value = item.get(key)
        if value is not None:
            try:
                float(value)
            except (TypeError, ValueError):
                errors.append(f"{path}.{key} is not numeric or null")
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
    full_ids = {str(row.get("driver_id")) for row in full_grid if isinstance(row, dict)}
    top_ids = {str(row.get("driver_id")) for row in top10 if isinstance(row, dict)}
    if not top_ids.issubset(full_ids):
        errors.append("latest.top10 is not a subset of latest.full_grid")
    full_schema = {key for row in full_grid if isinstance(row, dict) for key in row.keys()}
    for idx, row in enumerate(full_grid, start=1):
        if isinstance(row, dict) and set(row.keys()) != full_schema:
            errors.append(f"latest.full_grid[{idx}] schema differs from other driver rows")
            break
    if errors:
        raise ContractValidationError("; ".join(errors))
    if "race_intelligence_summary" in latest and not isinstance(latest.get("race_intelligence_summary"), dict):
        raise ContractValidationError("latest.race_intelligence_summary is not an object")
    if "changed_since_last_run" in latest and not isinstance(latest.get("changed_since_last_run"), dict):
        raise ContractValidationError("latest.changed_since_last_run is not an object")
    errors.extend(validate_model_comparison(contract.get("model_comparison") or latest.get("model_comparison")))
    errors.extend(validate_actual_result_comparison(contract.get("actual_result_comparison") or latest.get("actual_result_comparison")))
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
    model_comparison_errors = validate_model_comparison(model_status.get("model_comparison"), path="model-status.model_comparison")
    if model_comparison_errors:
        raise ContractValidationError("; ".join(model_comparison_errors))
    return {
        "ok": True,
        "schema_version": frontend.get("schema_version"),
        "prediction_data_version": frontend.get("prediction_data_version"),
        "briefing_count": len(index.get("briefings", [])),
        "debug_payload_count": len(debug.get("payloads", [])),
        "model_version": model_status.get("model_version") or model_status.get("schema_version"),
        **summary,
    }
