"""Optional RelBench rel-f1 adapter.

RelBench is treated as an offline benchmark source. Normal PitWall prediction
runs should not import heavy graph-learning dependencies or download benchmark
data unless the operator explicitly enables it.
"""

from __future__ import annotations

import importlib.util
import os
from typing import Any

from .source_registry import SourceMetadata, unavailable_source

RELBENCH_SOURCE_URL = "https://relbench.stanford.edu/datasets/rel-f1/"
RELBENCH_GITHUB_URL = "https://github.com/snap-stanford/relbench"
RELBENCH_LICENSE = "CC-BY-4.0"
RELBENCH_TASKS = [
    "driver-dnf",
    "driver-top3",
    "driver-position",
    "results-position",
    "qualifying-position",
    "driver-circuit-compete",
]


def env_flag(name: str, default: str = "false") -> bool:
    return str(os.getenv(name, default)).strip().lower() in {"1", "true", "yes", "on"}


def relbench_metadata() -> dict[str, Any]:
    return {
        "source_name": "RelBench rel-f1",
        "source_type": "offline_relational_benchmark",
        "enabled": env_flag("RELBENCH_F1_ENABLED"),
        "source_url": RELBENCH_SOURCE_URL,
        "github_url": RELBENCH_GITHUB_URL,
        "license": RELBENCH_LICENSE,
        "tasks": RELBENCH_TASKS,
        "role": "offline benchmark and relational task validation, not live race prediction",
    }


def relbench_status(download: bool | None = None) -> dict[str, Any]:
    meta = relbench_metadata()
    enabled = bool(meta["enabled"])
    installed = importlib.util.find_spec("relbench") is not None
    if not enabled:
        return unavailable_source(
            "RelBench rel-f1",
            "offline_relational_benchmark",
            enabled=False,
            confidence=0.3,
            source_url=RELBENCH_SOURCE_URL,
            license_name=RELBENCH_LICENSE,
            warning="Set RELBENCH_F1_ENABLED=true and install relbench to run offline benchmarks.",
        ).to_dict()
    if not installed:
        return unavailable_source(
            "RelBench rel-f1",
            "offline_relational_benchmark",
            enabled=True,
            confidence=0.35,
            source_url=RELBENCH_SOURCE_URL,
            license_name=RELBENCH_LICENSE,
            warning="Python package 'relbench' is not installed; benchmark adapter is available but inactive.",
        ).to_dict()
    if download is None:
        download = env_flag("RELBENCH_F1_DOWNLOAD")
    try:
        from relbench.datasets import get_dataset  # type: ignore
        from relbench.tasks import get_task  # type: ignore

        dataset = get_dataset("rel-f1", download=bool(download))
        task_summaries = []
        for task_name in RELBENCH_TASKS:
            try:
                task = get_task("rel-f1", task_name, download=bool(download))
                task_summaries.append({"task": task_name, "available": True, "metric": getattr(task, "eval_metric", None)})
            except Exception as error:
                task_summaries.append({"task": task_name, "available": False, "error": str(error)})
        return SourceMetadata(
            source_name="RelBench rel-f1",
            source_type="offline_relational_benchmark",
            enabled=True,
            available=True,
            status="available",
            confidence=0.82,
            license=RELBENCH_LICENSE,
            source_url=RELBENCH_SOURCE_URL,
            supported_categories=RELBENCH_TASKS,
            notes={
                "download": bool(download),
                "dataset_class": dataset.__class__.__name__,
                "tasks": task_summaries,
            },
        ).to_dict()
    except Exception as error:
        return unavailable_source(
            "RelBench rel-f1",
            "offline_relational_benchmark",
            enabled=True,
            confidence=0.4,
            source_url=RELBENCH_SOURCE_URL,
            license_name=RELBENCH_LICENSE,
            warning=f"relbench_status_error:{error}",
        ).to_dict()
