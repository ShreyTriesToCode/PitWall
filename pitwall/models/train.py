"""Training entrypoints exposed outside the monolithic briefing script."""

from __future__ import annotations

from typing import Any


def train_or_load_champion(*, force: bool = False) -> dict[str, Any] | None:
    """Run the existing PitWall training entrypoint lazily.

    The import stays inside the function so notebooks/tests can import this
    module without immediately executing the large briefing module import path.
    """

    import f1_briefing

    return f1_briefing.train_ml_model(force=force)


def training_status(*, force: bool = False) -> dict[str, Any]:
    import f1_briefing

    return f1_briefing.model_retrain_status(force=force)


def chronological_split(feature_df):
    import f1_briefing

    return f1_briefing.chronological_group_split(feature_df)
