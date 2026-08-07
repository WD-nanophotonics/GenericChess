"""Deterministic serialization helpers for the learning package."""

from __future__ import annotations

import hashlib
import json
from typing import Any


def canonical_json(data: Any) -> str:
    """Stable JSON with sorted keys (floats via repr for byte determinism)."""
    return json.dumps(data, sort_keys=True, separators=(",", ":"))


def stable_sha256(data: Any) -> str:
    return hashlib.sha256(canonical_json(data).encode("utf-8")).hexdigest()
