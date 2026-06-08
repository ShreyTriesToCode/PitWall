"""Feature-building wrappers and schema helpers for PitWall models."""

from __future__ import annotations

from typing import Iterable

import pandas as pd


def build_historical_features(raw_results: pd.DataFrame):
    import f1_briefing

    return f1_briefing.create_ml_features(raw_results)


def build_prediction_features(drivers, race, current_round_data, historical_df, feature_columns, *, stage: str = "pre_weekend"):
    import f1_briefing

    return f1_briefing.build_prediction_feature_rows(drivers, race, current_round_data, historical_df, feature_columns, stage=stage)


def feature_schema(columns: Iterable[str]) -> dict[str, object]:
    cols = list(columns)
    return {
        "feature_count": len(cols),
        "columns": cols,
        "categorical_columns": [],
        "numeric_columns": cols,
        "missingness_indicators": [col for col in cols if col.startswith("missing_") or col.startswith("insufficient_")],
    }


def missing_value_report(frame: pd.DataFrame, columns: Iterable[str]) -> dict[str, int]:
    return {col: int(frame[col].isna().sum()) for col in columns if col in frame}
