"""Release gate for the small production contract (legacy exports are excluded)."""

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from pitwall.data.jolpica import digest, instant  # noqa: E402
from pitwall.models.ranking import MODEL_VERSION, evaluate, validate_prediction  # noqa: E402


def validate(product):
    assert product["schema_version"] == 3, "Unsupported product schema"
    instant(product["generated_at"])
    assert product["model"]["version"] == MODEL_VERSION
    assert product["model"]["probabilities"] is False
    seen = set()
    for prediction in product["predictions"]:
        validate_prediction(prediction)
        key = prediction["prediction_id"]
        assert key not in seen, "Duplicate prediction IDs"
        seen.add(key)
        assert prediction["model_version"] == MODEL_VERSION
        assert prediction["feature_version"] and prediction["input_hash"] and prediction["sources"]
        assert prediction["input_hash"] == digest({"event": prediction["event"], "qualifying": prediction["inputs"]["qualifying"]})
        assert instant(prediction["data_cutoff"]) <= instant(prediction["generated_at"]) < instant(prediction["event"]["start_at"])
        assert prediction["race_id"] == prediction["event"]["id"]
        assert prediction["top10"] == prediction["full_grid"][:10]
        evaluate(prediction["full_grid"], [{"driver_id": r["driver_id"], "position": r["rank"]} for r in prediction["full_grid"]])
        for row in prediction["full_grid"]:
            assert not any("probability" in k or "confidence" in k for k in row)
    for record in product["evaluations"]:
        prediction = next(p for p in product["predictions"] if p["prediction_id"] == record["prediction_id"])
        assert record["metrics"] == evaluate(prediction["full_grid"], record["actual"])
    for old in product["legacy_archive"]:
        assert old["status"] == "UNVERIFIED_LEGACY"
    if product["backtest"]["status"] == "AVAILABLE":
        assert product["backtest"]["kind"] == "retrospective_reconstruction"
        assert product["backtest"]["promotion"]["promoted"] is False
    return {"ok": True, "forecasts": len(seen), "evaluations": len(product["evaluations"])}


if __name__ == "__main__":
    file = ROOT / "data_cache/product.json"
    assert file.stat().st_size < 5_000_000, "Published contract exceeds 5 MB"
    print(json.dumps(validate(json.loads(file.read_text()))))
