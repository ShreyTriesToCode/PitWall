#!/usr/bin/env python
"""Build an optional local keyword index for PitWall documents."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pitwall.ai.local_rag import DEFAULT_INDEX_PATH, build_keyword_index  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Build optional local PitWall RAG keyword index.")
    parser.add_argument("--base-dir", default=str(ROOT))
    parser.add_argument("--output", default=str(DEFAULT_INDEX_PATH))
    args = parser.parse_args()
    payload = build_keyword_index(args.base_dir, args.output)
    print(json.dumps({"ok": True, "document_count": payload["document_count"], "output": args.output}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
