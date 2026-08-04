"""The JSON-serializable RuleSet schema and fingerprint computation."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Any, Mapping

from ..core.coordinates import Square
from ..core.movement import LeapAtom, RayAtom, MovementAtom
from ..core.pieces import Piece, PieceType


def atom_to_dict(atom: MovementAtom) -> dict[str, Any]:
    if isinstance(atom, LeapAtom):
        return {"kind": "leap", "offset": list(atom.offset)}
    return {"kind": "ray", "direction": list(atom.direction), "max_steps": atom.max_steps}


def atom_from_dict(data: Mapping[str, Any]) -> MovementAtom:
    kind = data["kind"]
    if kind == "leap":
        return LeapAtom(tuple(data["offset"]))
    if kind == "ray":
        return RayAtom(tuple(data["direction"]), data.get("max_steps"))
    raise ValueError(f"unknown atom kind {kind!r}")


def piece_to_dict(piece: Piece) -> dict[str, Any]:
    return {
        "owner": piece.owner,
        "base_type_id": piece.base_type_id,
        "current_type_id": piece.current_type_id,
        "promoted": piece.promoted,
    }


def piece_from_dict(data: Mapping[str, Any]) -> Piece:
    base = data["base_type_id"]
    return Piece(
        owner=data["owner"],
        base_type_id=base,
        current_type_id=data.get("current_type_id", base),
        promoted=bool(data.get("promoted", False)),
    )


@dataclass(frozen=True, slots=True)
class RuleSet:
    """A declarative, JSON-serializable game definition.

    ``initial_position`` is stored as rows of ``Piece | None`` ordered from
    rank 0 (bottom) to rank n-1 (top).  Drop and promotion policies are
    stored as explicit per-square masks so the compiler never has to guess
    them.  ``metadata`` must never influence game results; it is excluded
    from the fingerprint.
    """

    schema_version: int = 1
    board_size: int = 8
    piece_types: tuple[PieceType, ...] = ()
    initial_position: tuple[tuple[Piece | None, ...], ...] = ()
    drop_allowed: Mapping[str, tuple[tuple[bool, ...], ...]] = field(default_factory=dict)
    promotion_allowed: Mapping[str, tuple[frozenset[tuple[Square, Square]], ...]] = field(
        default_factory=dict
    )
    promotion_forced: Mapping[str, tuple[frozenset[Square], ...]] = field(default_factory=dict)
    repetition_limit: int = 4
    max_ply: int = 512
    stalemate_result: str = "draw"
    metadata: Mapping[str, Any] = field(default_factory=dict)


def ruleset_to_dict(ruleset: RuleSet, include_metadata: bool = True) -> dict[str, Any]:
    """Convert a RuleSet to a JSON-friendly dict with canonical ordering."""
    piece_types = []
    for pt in ruleset.piece_types:
        piece_types.append(
            {
                "type_id": pt.type_id,
                "name": pt.name,
                "movement_atoms": [atom_to_dict(a) for a in pt.movement_atoms],
                "is_anchor": pt.is_anchor,
                "is_promotable": pt.is_promotable,
                "promotion_target_ids": list(pt.promotion_target_ids),
            }
        )
    initial_position = [
        [None if cell is None else piece_to_dict(cell) for cell in row]
        for row in ruleset.initial_position
    ]
    drop_allowed = {
        tid: [[bool(b) for b in mask] for mask in masks] for tid, masks in ruleset.drop_allowed.items()
    }
    promotion_allowed = {
        tid: [
            sorted(([a.file, a.rank, b.file, b.rank] for a, b in pairs))
            for pairs in masks
        ]
        for tid, masks in ruleset.promotion_allowed.items()
    }
    promotion_forced = {
        tid: [sorted([s.file, s.rank] for s in squares) for squares in masks]
        for tid, masks in ruleset.promotion_forced.items()
    }
    data: dict[str, Any] = {
        "schema_version": ruleset.schema_version,
        "board_size": ruleset.board_size,
        "piece_types": piece_types,
        "initial_position": initial_position,
        "drop_allowed": drop_allowed,
        "promotion_allowed": promotion_allowed,
        "promotion_forced": promotion_forced,
        "repetition_limit": ruleset.repetition_limit,
        "max_ply": ruleset.max_ply,
        "stalemate_result": ruleset.stalemate_result,
    }
    if include_metadata:
        data["metadata"] = dict(ruleset.metadata)
    return data


def ruleset_from_dict(data: Mapping[str, Any]) -> RuleSet:
    piece_types = tuple(
        PieceType(
            type_id=pt["type_id"],
            name=pt.get("name", pt["type_id"]),
            movement_atoms=tuple(atom_from_dict(a) for a in pt["movement_atoms"]),
            is_anchor=bool(pt.get("is_anchor", False)),
            is_promotable=bool(pt.get("is_promotable", False)),
            promotion_target_ids=tuple(pt.get("promotion_target_ids", ())),
        )
        for pt in data["piece_types"]
    )
    initial_position = tuple(
        tuple(None if cell is None else piece_from_dict(cell) for cell in row)
        for row in data["initial_position"]
    )
    drop_allowed = {
        tid: tuple(tuple(bool(b) for b in player_mask) for player_mask in masks)
        for tid, masks in data.get("drop_allowed", {}).items()
    }
    promotion_allowed = {
        tid: tuple(
            frozenset((Square(a[0], a[1]), Square(a[2], a[3])) for a in pairs)
            for pairs in masks
        )
        for tid, masks in data.get("promotion_allowed", {}).items()
    }
    promotion_forced = {
        tid: tuple(frozenset(Square(s[0], s[1]) for s in squares) for squares in masks)
        for tid, masks in data.get("promotion_forced", {}).items()
    }
    return RuleSet(
        schema_version=data.get("schema_version", 1),
        board_size=data["board_size"],
        piece_types=piece_types,
        initial_position=initial_position,
        drop_allowed=drop_allowed,
        promotion_allowed=promotion_allowed,
        promotion_forced=promotion_forced,
        repetition_limit=data.get("repetition_limit", 4),
        max_ply=data.get("max_ply", 512),
        stalemate_result=data.get("stalemate_result", "draw"),
        metadata=dict(data.get("metadata", {})),
    )


def canonical_json(data: Any) -> str:
    """Deterministic JSON: sorted keys, compact separators, ASCII-safe."""
    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def compute_fingerprint(ruleset: RuleSet) -> str:
    """SHA-256 of the canonical JSON of all semantic fields (no metadata)."""
    payload = canonical_json(ruleset_to_dict(ruleset, include_metadata=False))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()
