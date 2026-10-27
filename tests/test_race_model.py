"""Synthetic fixtures for leakage boundaries; not production F1 records."""
from copy import deepcopy

import numpy as np
import pytest

from pitwall.data.jolpica import DataUnavailable
from pitwall.models.race_model import features, fit, prepare, ranked


def race(year, round_no=1):
    event = {"id": f"{year}:{round_no}:race", "season": year, "start_at": f"{year}-03-{round_no:02}T14:00:00Z"}
    rows = [{"driver_id": str(i), "name": f"Fixture {i}", "team": f"Team {i // 2}",
             "position": i + 1, "status": "Finished"} for i in range(4)]
    return {"event": event, "qualifying": rows, "results": deepcopy(rows), "sources": []}


def test_features_reject_future_target_and_duplicate_races():
    target = race(2025)
    for history in [[target], [race(2026)], [race(2024), race(2024)]]:
        with pytest.raises(DataUnavailable):
            features(target["event"], target["qualifying"], history)


def test_target_results_cannot_change_features_or_prediction():
    data = [race(2018), race(2019), race(2020)]
    samples, _ = prepare(data)
    model = fit(samples[:1], 1)
    before = ranked(model, samples[-1])
    data[-1]["results"].reverse()
    for i, row in enumerate(data[-1]["results"]):
        row["position"] = i + 1
    after, _ = prepare(data)
    np.testing.assert_equal(samples[-1]["x"], after[-1]["x"])
    assert ranked(model, after[-1]) == before


def test_history_is_ordered_and_missing_rookie_history_is_explicit():
    target = race(2025)
    a = features(target["event"], target["qualifying"], [race(2024), race(2023)])
    b = features(target["event"], target["qualifying"], [race(2023), race(2024)])
    np.testing.assert_equal(a, b)
    missing = features(target["event"], target["qualifying"], [])
    assert np.isnan(missing[:, 1:5]).all()
    assert (missing[:, 5:] == 0).all()


def test_duplicate_dataset_rejected_and_fitting_is_deterministic():
    with pytest.raises(DataUnavailable):
        prepare([race(2019), race(2019)])
    samples, _ = prepare([race(2018), race(2019), race(2020)])
    assert ranked(fit(samples, 10), samples[-1]) == ranked(fit(samples, 10), samples[-1])


def test_future_results_do_not_change_prior_samples():
    original, _ = prepare([race(2018), race(2019), race(2020)])
    with_future, _ = prepare([race(2018), race(2019), race(2020), race(2025)])
    for a, b in zip(original, with_future, strict=False):
        np.testing.assert_equal(a["x"], b["x"])
        assert a["y"] == b["y"]


def test_validation_results_never_select_parameters_or_fit_coefficients():
    from pitwall.models.race_model import experiment
    data = [race(year) for year in range(2018, 2026)]
    before = experiment(data)
    changed = deepcopy(data)
    for row in changed[-1]["results"]:
        row["position"] = 5 - row["position"]
    after = experiment(changed)
    assert before["artifact"] == after["artifact"]
    assert before["selection"] == after["selection"]
    assert before["candidate"] != after["candidate"]
