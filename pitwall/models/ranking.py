"""Deterministic post-qualifying rankings, shared by publication and backtests.

Ranks estimate final classification order (including DNFs/DNS/DSQ), not win
probabilities. No target-race result fields are accepted by predict().
"""

from __future__ import annotations

from statistics import mean

from pitwall.data.jolpica import DataUnavailable, digest

MODEL_VERSION = "qualifying-order-v1"
FEATURE_VERSION = "qualifying-position-v1"
CANDIDATE_VERSION = "qualifying-recent5-equal-rank-v1"


def predict(qualifying: list[dict], history: list[dict] | None = None, *, candidate=False) -> list[dict]:
    ids = [row["driver_id"] for row in qualifying]
    if len(ids) < 2 or len(ids) != len(set(ids)):
        raise DataUnavailable("A unique qualifying field is required")
    positions = [row["position"] for row in qualifying]
    if sorted(positions) != list(range(1, len(ids) + 1)):
        raise DataUnavailable("Qualifying classification is incomplete")
    recent = {}
    for event in history or []:
        for row in event["results"]:
            recent.setdefault(row["driver_id"], []).append(row["position"])
    form = {driver: mean(recent[driver][-5:]) for driver in ids if driver in recent}
    # Missing driver history means the candidate is unavailable, not a fabricated prior.
    if candidate and len(form) != len(ids):
        raise DataUnavailable("Candidate requires prior classifications for every entrant")
    form_order = sorted(ids, key=lambda driver: (form[driver], driver)) if candidate else []
    form_rank = {driver: i + 1 for i, driver in enumerate(form_order)}
    rows = [{"driver_id": q["driver_id"], "name": q["name"], "team": q["team"],
             "qualifying_position": q["position"],
             "ranking_score": (q["position"] + form_rank[q["driver_id"]]) / 2 if candidate else q["position"]}
            for q in qualifying]
    rows.sort(key=lambda row: (row["ranking_score"], row["qualifying_position"], row["driver_id"]))
    return [{**row, "rank": i + 1} for i, row in enumerate(rows)]


def evaluate(predictions: list[dict], actual: list[dict]) -> dict:
    predicted_ids = [r["driver_id"] for r in predictions]
    actual_ids = [r["driver_id"] for r in actual]
    if len(set(predicted_ids)) != len(predicted_ids) or len(set(actual_ids)) != len(actual_ids):
        raise DataUnavailable("Duplicate drivers cannot be evaluated")
    if set(predicted_ids) != set(actual_ids) or len(actual) < 2:
        raise DataUnavailable("Evaluation requires the same complete field (substitutions need review)")
    n = len(actual)
    if sorted(r["rank"] for r in predictions) != list(range(1, n + 1)) or sorted(r["position"] for r in actual) != list(range(1, n + 1)):
        raise DataUnavailable("Evaluation requires complete ordinal positions")
    lookup = {r["driver_id"]: r["position"] for r in actual}
    errors = [r["rank"] - lookup[r["driver_id"]] for r in predictions]
    ordered = sorted(predictions, key=lambda r: r["rank"])
    winner = next(r["driver_id"] for r in actual if r["position"] == 1)
    return {"mae": mean(abs(e) for e in errors), "rmse": mean(e * e for e in errors) ** 0.5,
            "spearman": 1 - 6 * sum(e * e for e in errors) / (n * (n * n - 1)),
            "winner_hit": int(ordered[0]["driver_id"] == winner),
            "winner_top3": int(winner in [r["driver_id"] for r in ordered[:3]]), "drivers": n}


def make_prediction(event, qualifying, sources, now):
    from pitwall.data.jolpica import instant

    start = instant(event["start_at"])
    if now >= start:
        raise DataUnavailable("Cannot capture a forecast after the scheduled race start")
    if not sources or any(not s.get("retrieved_at") or instant(s["retrieved_at"]) > now for s in sources):
        raise DataUnavailable("Prediction inputs require retrieval provenance before capture")
    for session in event.get("sessions", []):
        if session["name"] == "Qualifying" and session.get("start_at") and instant(session["start_at"]) > now:
            raise DataUnavailable("Qualifying is scheduled in the future")
    grid = predict(qualifying)
    input_hash = digest({"event": event, "qualifying": qualifying})
    return {"prediction_id": digest([event["id"], MODEL_VERSION, input_hash]), "race_id": event["id"],
            "event": event, "season": event["season"], "round": event["round"], "target_type": "race",
            "model_version": MODEL_VERSION, "feature_version": FEATURE_VERSION,
            "generated_at": now.isoformat(), "data_cutoff": max((s["retrieved_at"] for s in sources), key=instant),
            "training_data_cutoff": None, "input_hash": input_hash, "sources": sources,
            "inputs": {"qualifying": qualifying},
            "objective": "final_classification_rank", "stage": "post_qualifying", "full_grid": grid, "top10": grid[:10]}


def validate_prediction(prediction: dict) -> dict:
    """Recompute the published baseline and identity before persisting or serving it."""
    from pitwall.data.jolpica import instant

    try:
        event = prediction["event"]
        qualifying = prediction["inputs"]["qualifying"]
        expected = make_prediction(event, qualifying, prediction["sources"], instant(prediction["generated_at"]))
        for key in ("prediction_id", "race_id", "model_version", "feature_version", "input_hash",
                    "full_grid", "top10", "data_cutoff", "objective", "stage", "target_type", "season", "round"):
            if prediction.get(key) != expected[key]:
                raise DataUnavailable(f"Prediction integrity mismatch: {key}")
    except (KeyError, TypeError, ValueError) as exc:
        raise DataUnavailable("Malformed prediction record") from exc
    return prediction
