#!/usr/bin/env python
"""Validate generated PitWall frontend/model contracts."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pitwall.validation.contracts import ContractValidationError, validate_contract_files  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate PitWall generated JSON contracts.")
    parser.add_argument("--base-dir", default=str(ROOT), help="Repository root containing data_cache/ and briefings/.")
    args = parser.parse_args()
    try:
        result = validate_contract_files(Path(args.base_dir))
    except ContractValidationError as error:
        print(f"CONTRACT_VALIDATION_FAILED: {error}", file=sys.stderr)
        return 1
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
