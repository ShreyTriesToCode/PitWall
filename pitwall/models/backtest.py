"""Chronological reconstruction from original Jolpica qualifying/results caches.

These are retrospective experiments, not forecasts captured before those races.
No target grid, lap, pit, weather, result or DNF fields enter the predictor.
The fixed candidate averages qualifying rank and prior-five-result rank. It is
compared on the same eligible races; no weights are fitted on the test period.
"""

from datetime import datetime, timezone
import json
from pathlib import Path
from statistics import mean

from pitwall.data.jolpica import DataUnavailable, classification, digest, race_event, races, instant
from pitwall.models.ranking import CANDIDATE_VERSION, MODEL_VERSION, evaluate, predict


def historical_dataset(cache: Path, end_season=2025) -> tuple[list[dict], list[dict]]:
    collected = {}
    rejected = []
    for file in sorted(cache.glob("https-api-jolpi-ca-ergast-f1-*-json.json")):
        if not (file.name.endswith("-results-json.json") or file.name.endswith("-qualifying-json.json")):
            continue
        try:
            payload = json.loads(file.read_text())
            meta = payload["MRData"]
            if int(meta["offset"]) != 0 or int(meta["total"]) > int(meta["limit"]):
                raise DataUnavailable("Incomplete cache page")
            for raw in races(payload):
                event = race_event(raw)
                if event["season"] > end_season:
                    continue
                field = "Results" if "Results" in raw else "QualifyingResults"
                rows = classification(raw, field)
                value = collected.setdefault(event["id"], {"event": event, "sources": []})
                value["results" if field == "Results" else "qualifying"] = rows
                value["sources"].append({"url": meta.get("url"), "sha256": digest(payload)})
        except (ValueError, KeyError, OSError, TypeError) as exc:
            rejected.append({"file": file.name, "reason": str(exc)})
    return sorted(collected.values(), key=lambda r: (r["event"]["season"], r["event"]["round"])), rejected


def aggregate(rows, key):
    values = [r[key] for r in rows if r.get(key)]
    if not values:
        return {"races": 0, "mae": None, "rmse": None, "spearman": None, "winner_hit": None, "winner_top3": None}
    return {"races": len(values), **{k: mean(v[k] for v in values) for k in ["mae", "rmse", "spearman", "winner_hit", "winner_top3"]}}


def run_backtest(dataset, rejected=None):
    history, rows, skipped = [], [], list(rejected or [])
    ids = [race["event"]["id"] for race in dataset]
    if len(ids) != len(set(ids)):
        raise DataUnavailable("Duplicate race groups would leak target results into history")
    eligible = [race for race in dataset if race["event"].get("start_at")]
    skipped.extend({"race_id": race["event"]["id"], "reason": "Race start time missing"} for race in dataset if not race["event"].get("start_at"))
    for race in sorted(eligible, key=lambda race: instant(race["event"]["start_at"])):
        event = race["event"]
        prior = [record for record in history if instant(record["start_at"]) < instant(event["start_at"])]
        if "results" not in race:
            skipped.append({"race_id": event["id"], "reason": "Results missing"})
            continue
        if event["season"] >= 2019:
            try:
                baseline = predict(race.get("qualifying") or [])
                candidate = predict(race.get("qualifying") or [], prior, candidate=True)
                rows.append({"race_id": event["id"], "name": event["name"], "season": event["season"],
                             "round": event["round"], "start_at": event["start_at"],
                             "split": "test" if event["season"] >= 2024 else "development",
                             "baseline": evaluate(baseline, race["results"]),
                             "candidate": evaluate(candidate, race["results"]),
                             "input_hash": digest({"qualifying": race["qualifying"], "history": prior}),
                             "sources": race["sources"]})
            except DataUnavailable as exc:
                skipped.append({"race_id": event["id"], "reason": str(exc)})
        history.append({"race_id": event["id"], "start_at": event["start_at"], "results": race["results"]})
    test = [r for r in rows if r["split"] == "test"]
    development = [r for r in rows if r["split"] == "development"]
    baseline, candidate = aggregate(test, "baseline"), aggregate(test, "candidate")
    seasons = sorted({r["season"] for r in test})
    blocks = [{"season": season, "baseline": aggregate([r for r in test if r["season"] == season], "baseline"),
               "candidate": aggregate([r for r in test if r["season"] == season], "candidate")} for season in seasons]
    # Improvement must persist across seasons, not just one unusual race. A release
    # review remains required; this experiment never mutates production weights.
    checks = {"at_least_30_test_races": len(test) >= 30,
              "at_least_two_test_seasons": len(seasons) >= 2,
              "mae_improves_by_5_percent": bool(test) and candidate["mae"] <= baseline["mae"] * 0.95,
              "no_season_mae_regression": bool(blocks) and all(b["candidate"]["mae"] <= b["baseline"]["mae"] for b in blocks),
              "no_rank_correlation_regression": bool(test) and candidate["spearman"] >= baseline["spearman"]}
    return {"status": "AVAILABLE" if test else "UNAVAILABLE", "kind": "retrospective_reconstruction",
            "created_at": datetime.now(timezone.utc).isoformat(), "model_version": MODEL_VERSION,
            "candidate_version": CANDIDATE_VERSION, "training_data_cutoff": None,
            "test_period": "2024–2025", "development_period": "2019–2023", "history_start": "2018",
            "baseline": baseline, "candidate": candidate, "by_season": blocks,
            "development": {"baseline": aggregate(development, "baseline"), "candidate": aggregate(development, "candidate")},
            "promotion": {"eligible_for_review": all(checks.values()), "promoted": False, "checks": checks,
                          "reason": "Production remains the qualifying-order baseline. Promotion requires an independently reviewed version change and untouched future validation."},
            "limitations": ["Historical provider revisions may differ from what was published at the time; publication timestamps were not retained.",
                            "Complete qualifying/result fields with prior history for every entrant are required; excluded races are listed.",
                            "Qualifying rank is not the starting grid: penalties, pit-lane starts, substitutions and weather are not modeled.",
                            "Metrics use final classified order including DNFs, DNS and DSQ; this is not a pace model.",
                            "No probability calibration, confidence interval or statistical significance claim is made."],
            "races": rows, "excluded": skipped, "dataset_hash": digest(dataset)}
