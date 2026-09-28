"""Append-only, atomic forecast and evaluation files for persistent deployments."""

import json
from pathlib import Path

from pitwall.data.jolpica import DataUnavailable, digest, instant
from pitwall.io.atomic import atomic_write_json
from pitwall.models.ranking import evaluate, validate_prediction


def read_records(directory: Path) -> list[dict]:
    records = []
    for file in sorted(directory.glob("*.json")):
        try:
            record = json.loads(file.read_text())
            if not isinstance(record, dict):
                raise DataUnavailable(f"Ledger record is not an object: {file.name}")
            records.append(record)
        except (OSError, ValueError) as exc:
            raise DataUnavailable(f"Corrupt ledger record: {file.name}") from exc
    return records


def append_record(directory: Path, key: str, record: dict) -> dict:
    import os
    import tempfile

    directory.mkdir(parents=True, exist_ok=True)
    target = directory / f"{digest(key)}.json"
    # Hard-link publication is atomic and refuses to overwrite an existing record,
    # including two concurrent writers. Writes use the project's JSON atomic writer.
    with tempfile.TemporaryDirectory(dir=directory) as tmp:
        staged = Path(tmp) / "record.json"
        atomic_write_json(staged, record)
        try:
            os.link(staged, target)
        except FileExistsError:
            existing = json.loads(target.read_text())
            if existing != record:
                raise DataUnavailable("Attempt to overwrite an immutable record")
    return record


def capture(directory: Path, prediction: dict) -> dict:
    if not instant(prediction["data_cutoff"]) <= instant(prediction["generated_at"]) < instant(prediction["event"]["start_at"]):
        raise DataUnavailable("Forecast cutoff/capture must precede the race")
    validate_prediction(prediction)
    return append_record(directory, prediction["prediction_id"], prediction)


def compare(directory: Path, prediction: dict, event: dict, actual: list[dict], source: dict, now) -> dict:
    validate_prediction(prediction)
    if event["id"] != prediction["race_id"]:
        raise DataUnavailable("Result belongs to another race")
    if now <= instant(event["start_at"]) or instant(prediction["generated_at"]) >= instant(event["start_at"]):
        raise DataUnavailable("Invalid prediction/result chronology")
    metrics = evaluate(prediction["full_grid"], actual)
    # Corrections are a new evaluation revision, preserving the previous evidence.
    key = digest([prediction["prediction_id"], actual])
    record = {"evaluation_id": key, "prediction_id": prediction["prediction_id"], "race_id": event["id"],
              "evaluated_at": now.isoformat(), "model_version": prediction["model_version"],
              "result_hash": digest(actual), "source": source, "metrics": metrics, "actual": actual}
    for existing in read_records(directory):
        if existing["evaluation_id"] == key:
            return existing
    return append_record(directory, key, record)


def evaluated_dataset(predictions: list[dict], evaluations: list[dict]) -> list[dict]:
    """One final captured forecast per race; latest result revision wins.

    This selection prevents frequently regenerated forecasts from weighting one
    race repeatedly. The immutable source records remain intact.
    """
    latest = {}
    for prediction in sorted(predictions, key=lambda p: instant(p["generated_at"])):
        latest[prediction["race_id"]] = prediction
    rows = []
    for prediction in latest.values():
        matching = [e for e in evaluations if e["prediction_id"] == prediction["prediction_id"]]
        if not matching:
            continue
        evaluation = max(matching, key=lambda e: instant(e["evaluated_at"]))
        rows.append({"event": prediction["event"], "prediction_id": prediction["prediction_id"],
                     "model_version": prediction["model_version"], "feature_version": prediction["feature_version"],
                     "data_cutoff": prediction["data_cutoff"], "captured_at": prediction["generated_at"],
                     "qualifying": prediction["inputs"]["qualifying"], "results": evaluation["actual"],
                     "metrics": evaluation["metrics"], "result_source": evaluation["source"],
                     "evaluation_id": evaluation["evaluation_id"]})
    return sorted(rows, key=lambda r: instant(r["event"]["start_at"]))
