"""Optional data-source adapters used by PitWall.

Adapters in this package are intentionally dependency-light. They expose
metadata, health/status checks, and typed row helpers without forcing network
downloads during normal prediction runs.
"""

from .f1db import f1db_metadata, f1db_status
from .relbench_f1 import relbench_metadata, relbench_status

__all__ = [
    "f1db_metadata",
    "f1db_status",
    "relbench_metadata",
    "relbench_status",
]
