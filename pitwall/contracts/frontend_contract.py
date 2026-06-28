"""Frontend contract file utilities."""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

from pitwall.io.atomic import atomic_write_json


def preserve_previous_valid_json(path: Path, previous_path: Path) -> bool:
    """Copy the current JSON artifact before overwrite when it is non-empty and valid."""

    if not path.exists() or path.stat().st_size <= 2:
        return False
    try:
        json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return False
    previous_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(path, previous_path)
    return True


def write_json_artifact(path: Path, payload: dict[str, Any], *, previous_path: Path | None = None) -> None:
    if previous_path is not None:
        preserve_previous_valid_json(path, previous_path)
    atomic_write_json(path, payload, indent=2, ensure_ascii=False)
