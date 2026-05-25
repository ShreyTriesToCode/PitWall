"""Shared PitWall runtime configuration helpers."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any


def env_bool(name: str, default: str = "false") -> bool:
    return str(os.getenv(name, default)).strip().lower() in {"1", "true", "yes", "on"}


def env_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except (TypeError, ValueError):
        return default


def env_float(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, str(default)))
    except (TypeError, ValueError):
        return default


def env_path(name: str, default: str | Path) -> Path:
    return Path(os.getenv(name, str(default))).expanduser()


def public_path(path: str | Path, base_dir: str | Path | None = None) -> str:
    path = Path(path)
    if base_dir is None:
        return str(path)
    try:
        return str(path.relative_to(Path(base_dir)))
    except ValueError:
        return str(path)


def fia_document_settings() -> dict[str, Any]:
    return {
        "user_agent": os.getenv(
            "FIA_DOCUMENT_USER_AGENT",
            "Mozilla/5.0 (compatible; PitWall/3.0; +https://github.com/ShreyTriesToCode/PitWall)",
        ),
        "referer": os.getenv(
            "FIA_DOCUMENT_REFERER",
            "https://www.fia.com/documents/championships/fia-formula-one-world-championship-14",
        ),
        "strict_downloads": env_bool("FIA_DOCUMENT_STRICT_DOWNLOADS", "false"),
    }
