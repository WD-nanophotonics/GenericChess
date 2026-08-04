"""The JSON-serializable RuleSet schema and fingerprint computation."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Any, Mapping

from ..core.coordinates import Square
from ..core.movement import LeapAtom, RayAtom, MovementAtom
from ..core.pieces import Piece, PieceType
from .validation import RuleValidationError, ValidationIssue


def atom_to_dict(atom: MovementAtom) -> dict[str, Any]:
    if isinstance(atom, LeapAtom):
        return {"kind": "leap", "offset": list(atom.offset)}
    return {"kind": "ray", "direction": list(atom.direction), "max_steps": atom.max_steps}


def _err(code: str, path: str, message: str) -> RuleValidationError:
    return RuleValidationError([ValidationIssue(code, path, message)])


def _require_mapping(data: Any, path: str) -> dict:
    if not isinstance(data, dict):
        raise _err("FIELD_NOT_OBJECT", path, f"expected a JSON object, got {data!r}")
    return data


def _require_field(data: dict, key: str, path: str) -> Any:
    if key not in data:
        raise _err("MISSING_FIELD", f"{path}.{key}", f"required field {key!r} is missing")
    return data[key]


def _require_int(value: Any, path: str, code: str = "FIELD_NOT_INT") -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise _err(code, path, f"expected an integer, got {value!r}")
    return value


def _require_bool(value: Any, path: str, code: str = "FIELD_NOT_BOOL") -> bool:
    if not isinstance(value, bool):
        raise _err(code, path, f"expected a boolean, got {value!r}")
    return value


def _require_str(value: Any, path: str, code: str = "FIELD_NOT_STRING") -> str:
    if not isinstance(value, str):
        raise _err(code, path, f"expected a string, got {value!r}")
    return value


def _require_int_pair(value: Any, path: str) -> tuple[int, int]:
    if (
        not isinstance(value, (list, tuple))
        or len(value) != 2
        or any(isinstance(x, bool) or not isinstance(x, int) for x in value)
    ):
        raise _err("FIELD_NOT_INT_PAIR", path, f"expected a pair of integers, got {value!r}")
    return (value[0], value[1])


def _require_int_quad(value: Any, path: str) -> tuple[int, int, int, int]:
    """A 4-int list: ``[from_file, from_rank, to_file, to_rank]``."""
    if (
        not isinstance(value, (list, tuple))
        or len(value) != 4
        or any(isinstance(x, bool) or not isinstance(x, int) for x in value)
    ):
        raise _err("FIELD_NOT_INT_QUAD", path, f"expected a 4-int list, got {value!r}")
    return (value[0], value[1], value[2], value[3])


def _require_str_list(value: Any, path: str) -> tuple[str, ...]:
    if not isinstance(value, (list, tuple)):
        raise _err("FIELD_NOT_LIST", path, f"expected a list, got {value!r}")
    return tuple(_require_str(v, f"{path}[{i}]") for i, v in enumerate(value))


def atom_from_dict(data: Mapping[str, Any], path: str = "movement_atoms[]") -> MovementAtom:
    data = _require_mapping(data, path)
    kind = _require_str(_require_field(data, "kind", path), f"{path}.kind")
    if kind == "leap":
        offset = _require_int_pair(_require_field(data, "offset", path), f"{path}.offset")
        return LeapAtom(offset)
    if kind == "ray":
        direction = _require_int_pair(
            _require_field(data, "direction", path), f"{path}.direction"
        )
        max_steps = data.get("max_steps")
        if max_steps is not None:
            max_steps = _require_int(max_steps, f"{path}.max_steps", "RAY_MAX_STEPS_INVALID")
            if max_steps < 1:
                raise _err(
                    "RAY_MAX_STEPS_INVALID",
                    f"{path}.max_steps",
                    f"max_steps must be a positive integer, got {max_steps}",
                )
        return RayAtom(direction, max_steps)
    raise _err("ATOM_KIND_INVALID", f"{path}.kind", f"unknown atom kind {kind!r}")


def piece_to_dict(piece: Piece) -> dict[str, Any]:
    return {
        "owner": piece.owner,
        "base_type_id": piece.base_type_id,
        "current_type_id": piece.current_type_id,
        "promoted": piece.promoted,
    }


def piece_from_dict(data: Mapping[str, Any], path: str = "initial_position[]") -> Piece:
    data = _require_mapping(data, path)
    owner = _require_int(_require_field(data, "owner", path), f"{path}.owner")
    if owner not in (0, 1):
        raise _err("ILLEGAL_OWNER", f"{path}.owner", f"owner must be 0 or 1, got {owner!r}")
    base = _require_str(_require_field(data, "base_type_id", path), f"{path}.base_type_id")
    current = data.get("current_type_id", base)
    current = _require_str(current, f"{path}.current_type_id")
    promoted = _require_bool(data.get("promoted", False), f"{path}.promoted")
    return Piece(
        owner=owner,
        base_type_id=base,
        current_type_id=current,
        promoted=promoted,
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
    """Strictly parse a RuleSet dict; malformed input raises RuleValidationError."""
    path = "ruleset"
    data = _require_mapping(data, path)
    schema_version = _require_int(data.get("schema_version", 1), f"{path}.schema_version")
    board_size = _require_int(_require_field(data, "board_size", path), f"{path}.board_size")
    if board_size < 3:
        raise _err(
            "BOARD_SIZE_TOO_SMALL", f"{path}.board_size", "board_size must be an integer >= 3"
        )

    piece_types_raw = _require_field(data, "piece_types", path)
    if not isinstance(piece_types_raw, list):
        raise _err("FIELD_NOT_LIST", f"{path}.piece_types", "piece_types must be a list")
    piece_types_list: list[PieceType] = []
    for i, raw in enumerate(piece_types_raw):
        p_path = f"{path}.piece_types[{i}]"
        raw = _require_mapping(raw, p_path)
        type_id = _require_str(_require_field(raw, "type_id", p_path), f"{p_path}.type_id")
        name = _require_str(raw.get("name", type_id), f"{p_path}.name")
        atoms_raw = _require_field(raw, "movement_atoms", p_path)
        if not isinstance(atoms_raw, list):
            raise _err("FIELD_NOT_LIST", f"{p_path}.movement_atoms", "movement_atoms must be a list")
        is_anchor = _require_bool(raw.get("is_anchor", False), f"{p_path}.is_anchor")
        is_promotable = _require_bool(
            raw.get("is_promotable", False), f"{p_path}.is_promotable"
        )
        targets = _require_str_list(
            raw.get("promotion_target_ids", ()), f"{p_path}.promotion_target_ids"
        )
        piece_types_list.append(
            PieceType(
                type_id=type_id,
                name=name,
                movement_atoms=tuple(atom_from_dict(a, f"{p_path}.movement_atoms[{j}]") for j, a in enumerate(atoms_raw)),
                is_anchor=is_anchor,
                is_promotable=is_promotable,
                promotion_target_ids=targets,
            )
        )
    piece_types = tuple(piece_types_list)

    initial_raw = _require_field(data, "initial_position", path)
    if not isinstance(initial_raw, list) or any(not isinstance(row, list) for row in initial_raw):
        raise _err(
            "FIELD_NOT_LIST",
            f"{path}.initial_position",
            "initial_position must be a list of rows",
        )
    initial_position = tuple(
        tuple(
            None
            if cell is None
            else piece_from_dict(cell, f"{path}.initial_position[{r}][{f}]")
            for f, cell in enumerate(row)
        )
        for r, row in enumerate(initial_raw)
    )

    drop_raw = _require_mapping(data.get("drop_allowed", {}), f"{path}.drop_allowed")
    drop_allowed: dict[str, tuple[tuple[bool, ...], ...]] = {}
    for tid, masks in drop_raw.items():
        d_path = f"{path}.drop_allowed[{tid}]"
        if not isinstance(masks, list) or len(masks) != 2:
            raise _err("DROP_MASK_BAD_SHAPE", d_path, "expected two player masks")
        players: list[tuple[bool, ...]] = []
        for player, mask in enumerate(masks):
            m_path = f"{d_path}[{player}]"
            if not isinstance(mask, list):
                raise _err("DROP_MASK_BAD_SHAPE", m_path, "mask must be a list of booleans")
            players.append(
                tuple(
                    _require_bool(b, f"{m_path}[{i}]", "DROP_MASK_BAD_TYPE")
                    for i, b in enumerate(mask)
                )
            )
        drop_allowed[tid] = tuple(players)

    promo_raw = _require_mapping(data.get("promotion_allowed", {}), f"{path}.promotion_allowed")
    promotion_allowed: dict[str, tuple[frozenset[tuple[Square, Square]], ...]] = {}
    for tid, masks in promo_raw.items():
        p_path = f"{path}.promotion_allowed[{tid}]"
        if not isinstance(masks, list) or len(masks) != 2:
            raise _err("PROMOTION_MASK_BAD_SHAPE", p_path, "expected two player masks")
        players: list[frozenset[tuple[Square, Square]]] = []
        for player, pairs in enumerate(masks):
            q_path = f"{p_path}[{player}]"
            if not isinstance(pairs, list):
                raise _err("PROMOTION_MASK_BAD_SHAPE", q_path, "pairs must be a list")
            squares: set[tuple[Square, Square]] = set()
            for i, a in enumerate(pairs):
                q = _require_int_quad(a, f"{q_path}[{i}]")
                squares.add((Square(q[0], q[1]), Square(q[2], q[3])))
            players.append(frozenset(squares))
        promotion_allowed[tid] = tuple(players)

    forced_raw = _require_mapping(data.get("promotion_forced", {}), f"{path}.promotion_forced")
    promotion_forced: dict[str, tuple[frozenset[Square], ...]] = {}
    for tid, masks in forced_raw.items():
        p_path = f"{path}.promotion_forced[{tid}]"
        if not isinstance(masks, list) or len(masks) != 2:
            raise _err("PROMOTION_MASK_BAD_SHAPE", p_path, "expected two player masks")
        players: list[frozenset[Square]] = []
        for player, squares in enumerate(masks):
            q_path = f"{p_path}[{player}]"
            if not isinstance(squares, list):
                raise _err("PROMOTION_MASK_BAD_SHAPE", q_path, "squares must be a list")
            fs: set[Square] = set()
            for i, s in enumerate(squares):
                q = _require_int_pair(s, f"{q_path}[{i}]")
                fs.add(Square(q[0], q[1]))
            players.append(frozenset(fs))
        promotion_forced[tid] = tuple(players)

    repetition_limit = _require_int(
        data.get("repetition_limit", 4), f"{path}.repetition_limit", "REPETITION_LIMIT_INVALID"
    )
    max_ply = _require_int(data.get("max_ply", 512), f"{path}.max_ply", "MAX_PLY_INVALID")
    stalemate_result = _require_str(
        data.get("stalemate_result", "draw"), f"{path}.stalemate_result"
    )
    metadata = _require_mapping(data.get("metadata", {}), f"{path}.metadata")

    return RuleSet(
        schema_version=schema_version,
        board_size=board_size,
        piece_types=piece_types,
        initial_position=initial_position,
        drop_allowed=drop_allowed,
        promotion_allowed=promotion_allowed,
        promotion_forced=promotion_forced,
        repetition_limit=repetition_limit,
        max_ply=max_ply,
        stalemate_result=stalemate_result,
        metadata=dict(metadata),
    )


def canonical_json(data: Any) -> str:
    """Deterministic JSON: sorted keys, compact separators, ASCII-safe."""
    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def compute_fingerprint(ruleset: RuleSet) -> str:
    """SHA-256 of the canonical JSON of all semantic fields (no metadata)."""
    payload = canonical_json(ruleset_to_dict(ruleset, include_metadata=False))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()
