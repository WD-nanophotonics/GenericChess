"""Persistence helper for already-evaluated F91 compact candidates."""

from __future__ import annotations

import json
from pathlib import Path


def persist_compact_payload(output_dir: Path, alpha: float, payload: dict) -> Path:
    """Persist the native compact-checkpoint payload without changing it."""
    path = Path(output_dir) / "candidates" / f"alpha-{alpha:g}" / "compact_model.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_text(json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n", encoding="utf-8")
    temporary.replace(path)
    return path
