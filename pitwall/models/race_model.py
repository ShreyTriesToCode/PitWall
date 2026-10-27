"""Research-only fitted race ranking with chronological feature construction.

See docs/RACE_MODEL_EXPERIMENT.md for the predeclared experiment protocol.
This module never changes the production model or prediction ledger.
"""
from datetime import datetime, timezone
from statistics import mean

import numpy as np
from sklearn.impute import SimpleImputer
from sklearn.linear_model import Ridge
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from pitwall.data.jolpica import DataUnavailable, digest, instant
from pitwall.models.backtest import aggregate
from pitwall.models.ranking import evaluate, predict

VERSION = "prior-form-ridge-v1"
FEATURE_VERSION = "prior-five-normalized-v1"
FEATURES = ["qualifying_percentile", "driver_finish", "driver_qualifying",
            "constructor_finish", "driver_nonfinish", "driver_samples", "constructor_samples"]
ALPHAS = (0.1, 1.0, 10.0, 100.0)


def features(event, qualifying, history):
    """Target results are not an argument. Reject any future/duplicate history."""
    predict(qualifying)  # Complete field and uniqueness validation.
    start = instant(event["start_at"])
    ids = [r["event"]["id"] for r in history]
    if len(ids) != len(set(ids)):
        raise DataUnavailable("Duplicate historical race")
    for race in history:
        if race["event"]["id"] == event["id"] or instant(race["event"]["start_at"]) >= start:
            raise DataUnavailable("Target or future race in feature history")
    ordered = sorted(history, key=lambda r: instant(r["event"]["start_at"]))
    result = []
    for driver in qualifying:
        finishes, quals, teams, failures = [], [], [], []
        for race in ordered:
            actual = race.get("results", [])
            q = race.get("qualifying", [])
            own = next((r for r in actual if r["driver_id"] == driver["driver_id"]), None)
            if own and len(actual) > 1:
                finishes.append((own["position"] - 1) / (len(actual) - 1))
                status = own.get("status")
                if status:
                    failures.append(float(status not in ("Finished", "Lapped") and not status.startswith("+")))
            old_q = next((r for r in q if r["driver_id"] == driver["driver_id"]), None)
            if old_q and len(q) > 1:
                quals.append((old_q["position"] - 1) / (len(q) - 1))
            members = [(r["position"] - 1) / (len(actual) - 1) for r in actual
                       if r["team"] == driver["team"] and len(actual) > 1]
            if members:
                teams.append(mean(members))
        recent = lambda xs: mean(xs[-5:]) if xs else np.nan
        result.append([(driver["position"] - 1) / (len(qualifying) - 1), recent(finishes),
                       recent(quals), recent(teams), recent(failures), min(len(finishes), 5), min(len(teams), 5)])
    return np.asarray(result, dtype=float)


def prepare(dataset):
    ids = [r["event"]["id"] for r in dataset]
    if len(ids) != len(set(ids)):
        raise DataUnavailable("Duplicate race groups")
    history, samples, excluded = [], [], []
    for race in sorted(dataset, key=lambda r: instant(r["event"]["start_at"])):
        event = race["event"]
        try:
            if event["season"] >= 2019:
                qualifying = race.get("qualifying") or []
                baseline = predict(qualifying)
                evaluate(baseline, race.get("results") or [])
                prior = [r for r in history if instant(r["event"]["start_at"]) < instant(event["start_at"])]
                x = features(event, qualifying, prior)
                actual = {r["driver_id"]: r["position"] for r in race["results"]}
                y = [(actual[q["driver_id"]] - 1) / (len(qualifying) - 1) for q in qualifying]
                samples.append({"race": race, "x": x, "y": y, "baseline": baseline})
        except DataUnavailable as exc:
            excluded.append({"race_id": event["id"], "reason": str(exc)})
        if race.get("results"):
            history.append(race)
    return samples, excluded


def fit(samples, alpha):
    if not samples:
        raise DataUnavailable("No training races")
    model = make_pipeline(SimpleImputer(strategy="median", add_indicator=True, keep_empty_features=True),
                          StandardScaler(), Ridge(alpha=alpha))
    # Every race contributes equal total weight, independent of field size.
    model.fit(np.vstack([s["x"] for s in samples]), np.concatenate([s["y"] for s in samples]),
              ridge__sample_weight=np.concatenate([np.full(len(s["y"]), 20 / len(s["y"])) for s in samples]))
    return model


def ranked(model, sample):
    scores = model.predict(sample["x"])
    rows = [{"driver_id": q["driver_id"], "name": q["name"], "team": q["team"],
             "qualifying_position": q["position"], "ranking_score": float(score)}
            for q, score in zip(sample["race"]["qualifying"], scores, strict=True)]
    rows.sort(key=lambda r: (r["ranking_score"], r["qualifying_position"], r["driver_id"]))
    return [{**r, "rank": i + 1} for i, r in enumerate(rows)]


def assess(model, samples):
    return [{"race_id": s["race"]["event"]["id"], "season": s["race"]["event"]["season"],
             "baseline": evaluate(s["baseline"], s["race"]["results"]),
             "candidate": evaluate(ranked(model, s), s["race"]["results"]),
             "positions_changed": sum(a["driver_id"] != b["driver_id"] for a, b in zip(s["baseline"], ranked(model, s), strict=True))}
            for s in samples]


def experiment(dataset):
    samples, excluded = prepare(dataset)
    subset = lambda lo, hi: [s for s in samples if lo <= s["race"]["event"]["season"] <= hi]
    train, selection, development, validation = subset(2019, 2021), subset(2022, 2023), subset(2019, 2023), subset(2024, 2025)
    if not all([train, selection, validation]):
        raise DataUnavailable("Missing chronological experiment blocks")
    tuning = [{"alpha": alpha, "metrics": aggregate(assess(fit(train, alpha), selection), "candidate")} for alpha in ALPHAS]
    alpha = min(tuning, key=lambda r: (r["metrics"]["mae"], -r["alpha"]))["alpha"]
    model = fit(development, alpha)
    rows = assess(model, validation)
    baseline, candidate = aggregate(rows, "baseline"), aggregate(rows, "candidate")
    seasons = [{"season": y, "baseline": aggregate([r for r in rows if r["season"] == y], "baseline"),
                "candidate": aggregate([r for r in rows if r["season"] == y], "candidate")} for y in (2024, 2025)]
    differences = np.array([r["candidate"]["mae"] - r["baseline"]["mae"] for r in rows])
    rng = np.random.default_rng(20261027)
    interval = np.quantile(rng.choice(differences, (10000, len(rows)), replace=True).mean(axis=1), [0.025, 0.975]).tolist()
    checks = {"at_least_30_races": len(rows) >= 30, "two_seasons": all(b["baseline"]["races"] for b in seasons),
              "mae_improves_5_percent": candidate["mae"] <= baseline["mae"] * .95,
              "no_season_mae_regression": all(b["candidate"]["mae"] <= b["baseline"]["mae"] for b in seasons),
              "no_rank_regression": candidate["spearman"] >= baseline["spearman"]}
    imputer, scaler, ridge = model.steps[0][1], model.steps[1][1], model.steps[2][1]
    artifact = {"model_version": VERSION, "feature_version": FEATURE_VERSION, "features": FEATURES,
                "alpha": alpha, "training_data_cutoff": max(s["race"]["event"]["start_at"] for s in development),
                "training_race_ids": [s["race"]["event"]["id"] for s in development],
                "imputation_medians": imputer.statistics_.tolist(), "missing_indicators": imputer.indicator_.features_.tolist(),
                "scaler_mean": scaler.mean_.tolist(), "scaler_scale": scaler.scale_.tolist(),
                "coefficients": ridge.coef_.tolist(), "intercept": float(ridge.intercept_)}
    return {"status": "RESEARCH_ONLY", "model_version": VERSION, "feature_version": FEATURE_VERSION,
            "created_at": datetime.now(timezone.utc).isoformat(), "dataset_hash": digest(dataset),
            "objective": "Final classification rank; no probabilities",
            "selection_period": "2022–2023", "training_period": "2019–2023", "validation_period": "2024–2025",
            "selection": tuning, "baseline": baseline, "candidate": candidate, "by_season": seasons,
            "mae_difference_95_percent_interval": interval, "races": rows, "excluded": excluded,
            "promotion": {"promoted": False, "retrospective_checks_pass": all(checks.values()), "checks": checks,
                          "reason": "Research only. Retrospective validation is not untouched; 2026 and prospective review are required."},
            "artifact": artifact, "artifact_hash": digest(artifact)}


def main():
    from pathlib import Path
    from pitwall.io.atomic import atomic_write_json
    from pitwall.models.backtest import historical_dataset
    root = Path(__file__).resolve().parents[2]
    dataset, rejected = historical_dataset(root / "data_cache/http")
    report = experiment(dataset)
    report["excluded_sources"] = rejected
    atomic_write_json(root / "data_cache/race-model-experiment.json", report, indent=2)
    print({key: report[key] for key in ("baseline", "candidate", "by_season", "promotion")})


if __name__ == "__main__":
    main()
