"""Isolated synthetic race fixtures for fitted forecast lifecycle safeguards."""
from copy import deepcopy
from datetime import datetime, timezone
import json
from pathlib import Path

import pytest

from pitwall.data.jolpica import DataUnavailable
from pitwall.models.experimental import capture, compare, make_forecast, validate_forecast

ROOT = Path(__file__).resolve().parents[1]


def fixture(stage="pre_qualifying"):
    event = {"id": "2030:2:race", "season": 2030, "round": 2, "name": "Fixture GP",
             "start_at": "2030-03-10T14:00:00Z", "sessions": []}
    previous = {**event, "id": "2030:1:race", "round": 1, "start_at": "2030-03-01T14:00:00Z"}
    rows = [{"driver_id": str(i), "name": f"Fixture {i}", "team": f"Fixture team {i//2}",
             "position": i + 1, "status": "Finished"} for i in range(4)]
    history = [{"event": previous, "results": rows, "qualifying": rows}]
    entrants = rows if stage == "post_qualifying" else [{k: r[k] for k in ("driver_id", "name", "team")} for r in rows]
    report = json.loads((ROOT / f"data_cache/{'race' if stage == 'post_qualifying' else 'early'}-model-experiment.json").read_text())
    field = {"kind": "qualifying" if stage == "post_qualifying" else "previous_classification",
             "event": event if stage == "post_qualifying" else previous}
    now = datetime(2030, 3, 9, tzinfo=timezone.utc)
    return make_forecast(event, entrants, history, report, [{"url": "fixture", "retrieved_at": now.isoformat()}], now, stage, field)


def test_early_and_qualifying_forecasts_have_distinct_models_and_derived_top10():
    early, later = fixture(), fixture("post_qualifying")
    for p in (early, later):
        assert validate_forecast(p) is p
        assert p["top10"] == p["full_grid"][:10]
        assert p["status"] == "EXPERIMENTAL"
    assert early["model_version"] != later["model_version"]
    assert all(r["qualifying_position"] is None for r in early["full_grid"])


def test_forecast_corruption_future_history_and_field_invention_fail_closed():
    p = fixture()
    for edit in ("score", "history", "field", "model", "capture"):
        broken = deepcopy(p)
        if edit == "score":
            broken["full_grid"][0]["ranking_score"] += 1
        elif edit == "history":
            broken["inputs"]["history"][0]["event"] = broken["event"]
        elif edit == "field":
            broken["inputs"]["entrants"][0]["team"] = "Invented team"
        elif edit == "model":
            broken["inputs"]["model_hash"] = "wrong"
        else:
            broken["generated_at"] = broken["event"]["start_at"]
        with pytest.raises(DataUnavailable):
            validate_forecast(broken)


def test_capture_is_immutable_and_evaluation_keeps_original_prediction(tmp_path):
    p = fixture()
    capture(tmp_path / "predictions", p)
    assert capture(tmp_path / "predictions", p) == p
    actual = [{"driver_id": r["driver_id"], "position": r["rank"]} for r in p["full_grid"]]
    evaluation = compare(tmp_path / "evaluations", p, p["event"], actual, {"url": "fixture"},
                         datetime(2030, 3, 11, tzinfo=timezone.utc))
    assert evaluation["metrics"]["mae"] == 0
    assert json.loads(next((tmp_path / "predictions").glob("*.json")).read_text()) == p
    assert len(list((tmp_path / "evaluations").glob("*.json"))) == 1
