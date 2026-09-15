"""Small shared serialization for related evaluator checkpoints."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

from .material import LearnableMaterialCheckpoint
from .serialization import stable_sha256


SCHEMA = "generic-chess-compact-checkpoint-v1"
_VARIANT_FIELDS = ("generation", "parent_checkpoint_id", "training_config_hash", "training_updates", "training_seed", "games_seen", "positions_seen")


def _variant(checkpoint: LearnableMaterialCheckpoint) -> dict[str, Any]:
    return {
        "checkpoint_id": checkpoint.checkpoint_id,
        **{field: getattr(checkpoint, field) for field in _VARIANT_FIELDS},
        "compact_nonlinear": checkpoint.compact_nonlinear,
    }


def _payload(checkpoints: Mapping[str, LearnableMaterialCheckpoint], provenance: dict[str, Any] | None = None) -> dict[str, Any]:
    if not checkpoints:
        raise ValueError("compact checkpoint requires at least one variant")
    first = next(iter(checkpoints.values())).to_dict()
    base = {key: value for key, value in first.items() if key not in set(_VARIANT_FIELDS) | {"compact_nonlinear"}}
    slots = {
        "parent": checkpoints.get("parent") or checkpoints.get("f86_parent"),
        "candidate": checkpoints.get("candidate") or checkpoints.get("f86_candidate") or checkpoints.get("f87_candidate"),
    }
    if slots["parent"] is None or slots["candidate"] is None:
        raise ValueError("compact checkpoint requires parent and candidate slots")
    return {"schema": SCHEMA, "base": base, "parent": _variant(slots["parent"]), "candidate": _variant(slots["candidate"]), "provenance": provenance or {}}


def write_compact_checkpoint(path: Path, checkpoints: Mapping[str, LearnableMaterialCheckpoint], provenance: dict[str, Any] | None = None) -> str:
    payload = _payload(checkpoints, provenance)
    payload["payload_sha256"] = stable_sha256(payload)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, separators=(",", ":"), sort_keys=True) + "\n", encoding="utf-8")
    return payload["payload_sha256"]


def upsert_compact_checkpoint(path: Path, name: str, checkpoint: LearnableMaterialCheckpoint, provenance: dict[str, Any] | None = None) -> str:
    if path.is_file():
        payload = json.loads(path.read_text(encoding="utf-8"))
        if payload.get("schema") != SCHEMA:
            raise ValueError("invalid compact checkpoint schema")
        existing = {"parent": load_compact_checkpoint(path, "parent"), "candidate": load_compact_checkpoint(path, "candidate")}
        existing["parent" if "parent" in name else "candidate"] = checkpoint
        return write_compact_checkpoint(path, existing, provenance or payload.get("provenance", {}))
    return write_compact_checkpoint(path, {name: checkpoint}, provenance)


def load_compact_checkpoint(path: Path, name: str) -> LearnableMaterialCheckpoint:
    payload = json.loads(path.read_text(encoding="utf-8"))
    slot = "parent" if "parent" in name else "candidate"
    if payload.get("schema") != SCHEMA or slot not in payload:
        raise ValueError(f"compact checkpoint variant is unavailable: {name}")
    variant = payload[slot]
    data = dict(payload["base"])
    data.update({field: variant[field] for field in _VARIANT_FIELDS})
    data["compact_nonlinear"] = variant["compact_nonlinear"]
    checkpoint = LearnableMaterialCheckpoint.from_dict(data)
    if checkpoint.checkpoint_id != variant["checkpoint_id"]:
        raise ValueError(f"compact checkpoint identity mismatch: {name}")
    return checkpoint
