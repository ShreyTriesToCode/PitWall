#!/usr/bin/env python3
"""Print PitWall optional dataset bootstrap instructions."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from pitwall.data.bootstrap import dataset_bootstrap_plan


def main() -> int:
    parser = argparse.ArgumentParser(description="Plan optional F1DB/RelBench dataset setup for PitWall.")
    parser.add_argument("source", choices=["f1db", "relbench"], help="Dataset source to plan.")
    parser.add_argument("--base-dir", default="data_cache/external", help="Local artifact base directory.")
    parser.add_argument("--execute", action="store_true", help="Reserved for future explicit download/import execution.")
    args = parser.parse_args()
    plan = dataset_bootstrap_plan(args.source, base_dir=Path(args.base_dir), dry_run=not args.execute)
    print(json.dumps(plan, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
