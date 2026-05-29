#!/usr/bin/env python
"""Query the optional local PitWall keyword index."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pitwall.ai.local_rag import DEFAULT_INDEX_PATH, query_keyword_index  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Query optional local PitWall RAG index.")
    parser.add_argument("query", nargs="?", default="")
    parser.add_argument("--base-dir", default=str(ROOT))
    parser.add_argument("--index", default=str(DEFAULT_INDEX_PATH))
    args = parser.parse_args()
    print(json.dumps(query_keyword_index(args.query, args.base_dir, args.index), indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
