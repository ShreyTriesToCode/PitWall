"""Atomic text and JSON writes for generated PitWall artifacts."""

from __future__ import annotations

import json
import os
import secrets
import time
from pathlib import Path
from typing import Any


def _temporary_path(path: Path) -> Path:
    suffix = f".tmp-{os.getpid()}-{time.time_ns()}-{secrets.token_hex(4)}"
    return path.with_name(path.name + suffix)


def atomic_write_text(path: str | Path, text: str, encoding: str = "utf-8") -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp = _temporary_path(target)
    try:
        tmp.write_text(text, encoding=encoding)
        tmp.replace(target)
    except Exception:
        tmp.unlink(missing_ok=True)
        raise
    return target


def atomic_write_json(
    path: str | Path,
    payload: Any,
    *,
    indent: int | None = 2,
    sort_keys: bool = False,
    ensure_ascii: bool = False,
    encoding: str = "utf-8",
) -> Path:
    text = json.dumps(payload, indent=indent, sort_keys=sort_keys, ensure_ascii=ensure_ascii, default=str)
    tmp_target = Path(path)
    target = atomic_write_text(tmp_target, text, encoding=encoding)
    json.loads(target.read_text(encoding=encoding))
    return target
