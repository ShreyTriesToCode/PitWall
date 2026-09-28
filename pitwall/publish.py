"""Production publication entrypoint; independent of legacy numerical enrichments."""

from datetime import datetime, timezone
import json
import logging
import os
from pathlib import Path

from pitwall.data.jolpica import DataUnavailable, Jolpica, classification, instant, race_event, races, select_event
from pitwall.io.atomic import atomic_write_json
from pitwall.models.backtest import historical_dataset, run_backtest
from pitwall.models.ledger import capture, compare, evaluated_dataset, read_records
from pitwall.models.ranking import FEATURE_VERSION, MODEL_VERSION, make_prediction

ROOT = Path(__file__).resolve().parents[1]
LOG = logging.getLogger(__name__)


def safe_history(root):
    """Expose the original ranking only; legacy provenance cannot be repaired."""
    try:
        index = json.loads((root / "briefings/index.json").read_text())
        entries = index.get("briefings", []) if isinstance(index, dict) else index
        return [{"title": e.get("title"), "generated_at": e.get("generated_iso"), "start_at": e.get("start_iso"),
                 "status": "UNVERIFIED_LEGACY", "model_version": e.get("model_version"),
                 "reason": "Original data cutoff and immutable model provenance are absent. Excluded from measured forecast performance.",
                 "rows": [{"rank": i + 1, "driver_id": r.get("driver_id"), "name": r.get("name"), "team": r.get("team")}
                          for i, r in enumerate(e.get("full_grid") or e.get("top10") or [])]}
                for e in entries if isinstance(e, dict)]
    except (OSError, ValueError, TypeError) as exc:
        LOG.warning("Legacy archive unavailable: %s", type(exc).__name__)
        return []


def fia_archive(root, season):
    """Preserve saved source metadata without claiming a fresh verification."""
    path = root / f"data_cache/fia-documents/{season}/season_index.json"
    try:
        saved = json.loads(path.read_text())
        keys = ("document_id", "title", "source_url", "download_url", "source_authority",
                "source_status", "published_at", "fetched_at", "verification_status",
                "is_official", "is_verified", "is_stale", "error_summary", "parse_error")
        return {"status": "HISTORICAL", "checked_at": saved.get("checked_at"),
                "source_authority": saved.get("source_authority"), "source_status": saved.get("source_status"),
                "errors": saved.get("errors", []),
                "documents": [{k: row.get(k) for k in keys} for row in saved.get("documents", [])]}
    except (OSError, ValueError, TypeError) as exc:
        LOG.warning("FIA metadata archive unavailable: %s", type(exc).__name__)
        return {"status": "UNAVAILABLE", "documents": [], "errors": ["Saved FIA metadata is unavailable."]}


def publish(root=ROOT, *, provider=None, now=None):
    clock = (lambda: now) if now is not None else (lambda: datetime.now(timezone.utc))
    now = clock()
    ledger = root / "data_cache/ledger"
    provider = provider or Jolpica(root / "data_cache/provider")
    warnings, events, latest_result, current, forecast = [], [], None, None, None
    records = read_records(ledger / "predictions")
    evaluations = read_records(ledger / "evaluations")
    try:
        events = [race_event(r) for r in races(provider.fetch(f"{now.year}/races"), now.year)]
        if not events:
            raise DataUnavailable("Season calendar is empty")
        completed = set()
        try:
            last = races(provider.fetch(f"{now.year}/last/results"), now.year)
            if last:
                result_event = race_event(last[0])
                if result_event.get("start_at") and instant(result_event["start_at"]) < now:
                    latest_result = {"event": result_event, "rows": classification(last[0], "Results"), "source": provider.sources[-1]}
                    completed.add(result_event["id"])
        except DataUnavailable as exc:
            warnings.append(f"Latest results unavailable: {exc}")
        current = select_event(events, completed, now)
        # Across the winter break, ask for the published next season; never invent it.
        if not current["event"] and all(e.get("start_at") and instant(e["start_at"]) < now for e in events):
            following = [race_event(r) for r in races(provider.fetch(f"{now.year + 1}/races"), now.year + 1)]
            if following:
                events += following
                current = select_event(events, completed, now)
        event = current.get("event")
        if current["state"] == "UPCOMING":
            qualifying_races = races(provider.fetch(f"{event['season']}/{event['round']}/qualifying"), event["season"])
            if qualifying_races:
                if race_event(qualifying_races[0])["id"] != event["id"]:
                    raise DataUnavailable("Qualifying response belongs to another event")
                qualifying = classification(qualifying_races[0], "QualifyingResults")
                stamp = clock()
                proposed = make_prediction(event, qualifying, [source for source in provider.sources if source.get("retrieved_at")], stamp)
                # Same inputs reuse the first capture timestamp; never rewrite history.
                forecast = next((p for p in records if p["prediction_id"] == proposed["prediction_id"]), None)
                if forecast is None:
                    forecast = capture(ledger / "predictions", proposed)
                    records.append(forecast)
            else:
                warnings.append("Prediction unavailable: qualifying classification has not been published.")
    except DataUnavailable as exc:
        LOG.warning("Forecast publication unavailable: %s", exc)
        warnings.append(str(exc))
    for prediction in records:
        if instant(prediction["event"]["start_at"]) >= now:
            continue
        try:
            raw = races(provider.fetch(f"{prediction['season']}/{prediction['round']}/results"), prediction["season"])
            if raw:
                evaluation = compare(ledger / "evaluations", prediction, race_event(raw[0]), classification(raw[0], "Results"), provider.sources[-1], clock())
                if not any(e["evaluation_id"] == evaluation["evaluation_id"] for e in evaluations):
                    evaluations.append(evaluation)
        except DataUnavailable as exc:
            warnings.append(f"Evaluation pending for {prediction['race_id']}: {exc}")
    report_path = root / "data_cache/ranking-backtest.json"
    dataset = evaluated_dataset(records, evaluations)
    atomic_write_json(root / "data_cache/evaluated-dataset.json", {"schema_version": 1, "races": dataset})
    try:
        report = json.loads(report_path.read_text())
    except (OSError, ValueError):
        report = {"status": "UNAVAILABLE", "reason": "No chronological backtest has been run."}
    payload = {"schema_version": 3, "generated_at": clock().isoformat(),
               "calendar": events, "current": current or {"state": "UNAVAILABLE", "event": None},
               "prediction": forecast, "latest_result": latest_result, "predictions": records,
               "evaluations": evaluations, "legacy_archive": safe_history(root), "sources": provider.sources,
               "evaluated_races": len(dataset),
               "fia_archive": fia_archive(root, now.year),
               "warnings": warnings, "model": {"version": MODEL_VERSION, "feature_version": FEATURE_VERSION,
               "objective": "Final classification ranking after qualifying", "probabilities": False,
               "training": "No fitted parameters. Qualifying order is the production baseline."},
               "backtest": report}
    atomic_write_json(root / "data_cache/product.json", payload, indent=2)
    return payload


def main():
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--backtest", action="store_true", help="Reconstruct historical rankings before publishing")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO)
    root = Path(os.getenv("PITWALL_PROJECT_ROOT") or ROOT)
    if args.backtest:
        dataset, rejected = historical_dataset(root / "data_cache/http")
        atomic_write_json(root / "data_cache/ranking-backtest.json", run_backtest(dataset, rejected))
    result = publish(root)
    print(json.dumps({"state": result["current"]["state"], "event": result["current"].get("event"),
                      "warnings": result["warnings"], "predictions": len(result["predictions"])}))


if __name__ == "__main__":
    main()
