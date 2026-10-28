"""Explicitly experimental fitted forecasts, isolated from the production baseline."""
import json

import numpy as np

from pitwall.data.jolpica import DataUnavailable, digest, instant
from pitwall.models.race_model import features
from pitwall.models.ranking import evaluate
from pitwall.models.ledger import append_record, read_records

MODELS = {"pre_qualifying": "pre-race-form-ridge-v1", "post_qualifying": "prior-form-ridge-v1"}


def infer(artifact, event, entrants, history, stage):
    if artifact["model_version"] != MODELS.get(stage):
        raise DataUnavailable("Unsupported experimental model/stage")
    if instant(artifact["training_data_cutoff"]) >= instant(event["start_at"]):
        raise DataUnavailable("Model training reaches the target race")
    x = features(event, entrants, history, qualifying_available=stage == "post_qualifying")
    if stage == "pre_qualifying":
        x = x[:, 1:]
    missing = np.isnan(x)
    medians = np.asarray(artifact["imputation_medians"], dtype=float)
    values = np.where(missing, medians, x)
    indicators = artifact["missing_indicators"]
    if indicators:
        values = np.concatenate([values, missing[:, indicators].astype(float)], axis=1)
    scores = ((values - artifact["scaler_mean"]) / artifact["scaler_scale"]) @ artifact["coefficients"] + artifact["intercept"]
    if not np.isfinite(scores).all():
        raise DataUnavailable("Non-finite model output")
    rows = [{"driver_id": q["driver_id"], "name": q["name"], "team": q["team"],
             "qualifying_position": q["position"] if stage == "post_qualifying" else None,
             "ranking_score": float(score)} for q, score in zip(entrants, scores, strict=True)]
    rows.sort(key=lambda r: (r["ranking_score"], r["qualifying_position"] or 0, r["driver_id"]))
    return [{**row, "rank": i + 1} for i, row in enumerate(rows)]


def compact_history(event, entrants, history):
    """Keep only race records used by each prior-five feature, with source values intact."""
    ordered = sorted([r for r in history if instant(r["event"]["start_at"]) < instant(event["start_at"])],
                     key=lambda r: instant(r["event"]["start_at"]))
    needed = set()
    for entrant in entrants:
        for field, key, value in [("results", "driver_id", entrant["driver_id"]),
                                  ("qualifying", "driver_id", entrant["driver_id"]),
                                  ("results", "team", entrant["team"])]:
            matches = [r for r in ordered if any(row[key] == value for row in r.get(field, []))]
            needed.update(r["event"]["id"] for r in matches[-5:])
    return [{"event": r["event"], "results": r.get("results", []), "qualifying": r.get("qualifying", [])}
            for r in ordered if r["event"]["id"] in needed]


def make_forecast(event, entrants, history, report, sources, now, stage, field_source):
    if now >= instant(event["start_at"]):
        raise DataUnavailable("Cannot create an experimental forecast after race start")
    if stage == "post_qualifying" and any(s["name"] == "Qualifying" and s.get("start_at") and instant(s["start_at"]) > now for s in event.get("sessions", [])):
        raise DataUnavailable("Qualifying is scheduled in the future")
    if not sources or any(instant(s["retrieved_at"]) > now for s in sources):
        raise DataUnavailable("Forecast source timestamps exceed capture")
    artifact = report["artifact"]
    if digest(artifact) != report["artifact_hash"]:
        raise DataUnavailable("Model artifact integrity failure")
    history = compact_history(event, entrants, history)
    grid = infer(artifact, event, entrants, history, stage)
    model_json = json.dumps(artifact, sort_keys=True, separators=(",", ":"), allow_nan=False)
    inputs = {"entrants": entrants, "history": history, "stage": stage, "model_json": model_json,
              "model_hash": report["artifact_hash"], "field_source": field_source}
    identity = digest({"event": event, "inputs": inputs})
    return {"prediction_id": digest([event["id"], artifact["model_version"], identity]),
            "race_id": event["id"], "event": event, "season": event["season"], "round": event["round"],
            "model_version": artifact["model_version"], "feature_version": artifact["feature_version"],
            "training_data_cutoff": artifact["training_data_cutoff"], "generated_at": now.isoformat(),
            "data_cutoff": max((s["retrieved_at"] for s in sources), key=instant), "input_hash": identity,
            "sources": sources, "inputs": inputs, "stage": stage, "status": "EXPERIMENTAL",
            "entry_status": "QUALIFYING_FIELD" if stage == "post_qualifying" else "PROJECTED_FROM_LAST_RESULT",
            "objective": "final_classification_rank", "target_type": "race", "full_grid": grid, "top10": grid[:10],
            "validation": {"period": report["validation_period"], "baseline": report["baseline"],
                           "candidate": report["candidate"], "promoted": False,
                           "note": "Retrospective reconstruction; no demonstrated superiority to qualifying order."}}


def validate_forecast(p):
    try:
        inputs = p["inputs"]
        artifact = json.loads(inputs["model_json"])
        expected_entry = "PROJECTED_FROM_LAST_RESULT" if p["stage"] == "pre_qualifying" else "QUALIFYING_FIELD"
        if inputs["stage"] != p["stage"] or p["entry_status"] != expected_entry:
            raise DataUnavailable("Experimental stage/entry disclosure mismatch")
        field = inputs["field_source"]
        if p["stage"] == "pre_qualifying":
            previous = next((r for r in inputs["history"] if r["event"]["id"] == field["event"]["id"]), None)
            if not previous or field["kind"] != "previous_classification" or inputs["entrants"] != [
                {key: r[key] for key in ("driver_id", "name", "team")} for r in previous["results"]
            ]:
                raise DataUnavailable("Projected field differs from its published prior classification")
        elif field["kind"] != "qualifying" or field["event"]["id"] != p["race_id"]:
            raise DataUnavailable("Qualifying field belongs to another event")
        if digest(artifact) != inputs["model_hash"]:
            raise DataUnavailable("Experimental artifact hash mismatch")
        if not instant(p["training_data_cutoff"]) < instant(p["generated_at"]) < instant(p["event"]["start_at"]):
            raise DataUnavailable("Experimental capture/training chronology invalid")
        times = [instant(s["retrieved_at"]) for s in p["sources"]]
        if max(times) != instant(p["data_cutoff"]) or max(times) > instant(p["generated_at"]):
            raise DataUnavailable("Experimental source cutoff mismatch")
        identity = digest({"event": p["event"], "inputs": inputs})
        grid = infer(artifact, p["event"], inputs["entrants"], inputs["history"], p["stage"])
        if (p["input_hash"] != identity or p["prediction_id"] != digest([p["race_id"], p["model_version"], identity])
                or p["race_id"] != p["event"]["id"] or p["model_version"] != artifact["model_version"]
                or p["feature_version"] != artifact["feature_version"] or p["training_data_cutoff"] != artifact["training_data_cutoff"]
                or len(p["full_grid"]) != len(grid) or p["top10"] != p["full_grid"][:10] or p["status"] != "EXPERIMENTAL"):
            raise DataUnavailable("Experimental forecast integrity mismatch")
        # BLAS accumulation can differ by a few ulps between publisher platforms.
        # Driver order and all discrete fields must still match exactly.
        for actual, expected in zip(p["full_grid"], grid, strict=True):
            if any(actual.get(key) != value for key, value in expected.items() if key != "ranking_score") or not np.isclose(actual["ranking_score"], expected["ranking_score"], rtol=0, atol=1e-12):
                raise DataUnavailable("Experimental model output mismatch")
    except (KeyError, TypeError, ValueError, IndexError) as exc:
        raise DataUnavailable("Invalid experimental forecast") from exc
    return p


def capture(directory, prediction):
    validate_forecast(prediction)
    return append_record(directory, prediction["prediction_id"], prediction)


def compare(directory, prediction, event, actual, source, now):
    validate_forecast(prediction)
    if event["id"] != prediction["race_id"] or now <= instant(event["start_at"]):
        raise DataUnavailable("Experimental result identity/chronology mismatch")
    metrics = evaluate(prediction["full_grid"], actual)
    key = digest([prediction["prediction_id"], actual])
    for existing in read_records(directory):
        if existing["evaluation_id"] == key:
            return existing
    return append_record(directory, key, {"evaluation_id": key, "prediction_id": prediction["prediction_id"],
                         "race_id": event["id"], "model_version": prediction["model_version"], "stage": prediction["stage"],
                         "evaluated_at": now.isoformat(), "metrics": metrics, "actual": actual, "source": source})


def publish_experimental(root, provider, current, latest_result, clock):
    from pitwall.data.jolpica import classification, race_event, races
    from pitwall.models.backtest import historical_dataset

    directory = root / "data_cache/experimental-ledger"
    records = read_records(directory / "predictions")
    evaluations = read_records(directory / "evaluations")
    warnings, forecast = [], None
    event = current.get("event") if current else None
    if event and current["state"] == "UPCOMING":
        try:
            if not all((root / f"data_cache/{name}").is_file() for name in ("early-model-experiment.json", "race-model-experiment.json")):
                raise DataUnavailable("Fitted model artifacts have not been installed")
            history, _ = historical_dataset(root / "data_cache/http")
            known = {r["event"]["id"]: r for r in history}
            for round_no in range(1, event["round"]):
                endpoint = f"{event['season']}/{round_no}"
                results = races(provider.fetch(f"{endpoint}/results"), event["season"])
                if not results:
                    continue
                previous = race_event(results[0])
                if not previous["start_at"] or instant(previous["start_at"]) >= clock():
                    raise DataUnavailable("Historical response has not started")
                record = {"event": previous, "results": classification(results[0], "Results"), "qualifying": []}
                qualifying = races(provider.fetch(f"{endpoint}/qualifying"), event["season"])
                if qualifying:
                    if race_event(qualifying[0])["id"] != previous["id"]:
                        raise DataUnavailable("Historical qualifying identity mismatch")
                    record["qualifying"] = classification(qualifying[0], "QualifyingResults")
                known[previous["id"]] = record
            qualifying = races(provider.fetch(f"{event['season']}/{event['round']}/qualifying"), event["season"])
            if qualifying:
                if race_event(qualifying[0])["id"] != event["id"]:
                    raise DataUnavailable("Target qualifying identity mismatch")
                entrants = classification(qualifying[0], "QualifyingResults")
                stage, file = "post_qualifying", "race-model-experiment.json"
                field_source = {"event": event, "kind": "qualifying"}
            else:
                if not latest_result or latest_result["event"]["id"] == event["id"]:
                    raise DataUnavailable("No verified prior participant field for early forecast")
                entrants = [{key: r[key] for key in ("driver_id", "name", "team")} for r in latest_result["rows"]]
                stage, file = "pre_qualifying", "early-model-experiment.json"
                field_source = {"event": latest_result["event"], "kind": "previous_classification"}
            report = json.loads((root / f"data_cache/{file}").read_text())
            proposed = make_forecast(event, entrants, list(known.values()), report, list(provider.sources), clock(), stage, field_source)
            forecast = next((p for p in records if p["prediction_id"] == proposed["prediction_id"]), None)
            if forecast is None:
                forecast = capture(directory / "predictions", proposed)
                records.append(forecast)
        except (DataUnavailable, OSError, json.JSONDecodeError) as exc:
            warnings.append(f"Experimental forecast unavailable: {exc}")
    for prediction in records:
        if instant(prediction["event"]["start_at"]) >= clock():
            continue
        try:
            raw = races(provider.fetch(f"{prediction['season']}/{prediction['round']}/results"), prediction["season"])
            if raw:
                evaluation = compare(directory / "evaluations", prediction, race_event(raw[0]),
                                     classification(raw[0], "Results"), provider.sources[-1], clock())
                if not any(e["evaluation_id"] == evaluation["evaluation_id"] for e in evaluations):
                    evaluations.append(evaluation)
        except DataUnavailable as exc:
            warnings.append(f"Experimental evaluation pending for {prediction['race_id']}: {exc}")
    return {"experimental_prediction": forecast, "experimental_predictions": records,
            "experimental_evaluations": evaluations, "experimental_warnings": warnings}
