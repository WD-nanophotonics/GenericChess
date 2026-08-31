"""Strict, deterministic GameRecord JSON serialization."""

from __future__ import annotations

import json
from typing import Any

from ..core.actions import (
    Action,
    BoardMove,
    DropMove,
    SemanticBoardMove,
    SemanticDropMove,
)
from ..core.coordinates import Square
from .record import DeclarationRecord, GameRecord
from .session import SessionRecordError


def _err(code: str, path: str, message: str) -> SessionRecordError:
    return SessionRecordError(f"[{code}] {path}: {message}")


def _require_mapping(value: Any, path: str) -> dict:
    if not isinstance(value, dict):
        raise _err("NOT_OBJECT", path, f"expected a JSON object, got {value!r}")
    return value


def _require_field(data: dict, key: str, path: str) -> Any:
    if key not in data:
        raise _err("MISSING_FIELD", f"{path}.{key}", f"required field {key!r} is missing")
    return data[key]


def _require_int(value: Any, path: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise _err("FIELD_NOT_INT", path, f"expected an integer, got {value!r}")
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


def _action_to_dict(action: Action) -> dict[str, Any]:
    if isinstance(action, SemanticBoardMove):
        return {
            "kind": "semantic_board",
            "pattern_id": action.pattern_id,
            "geometry_id": action.geometry_id,
            "actor_type_id": action.actor_type_id,
            "from": [action.from_square.file, action.from_square.rank],
            "to": [action.to_square.file, action.to_square.rank],
            "promotion_target_id": action.promotion_target_id,
        }
    if isinstance(action, SemanticDropMove):
        return {
            "kind": "semantic_drop",
            "pattern_id": action.pattern_id,
            "geometry_id": action.geometry_id,
            "base_type_id": action.base_type_id,
            "to": [action.to_square.file, action.to_square.rank],
        }
    if isinstance(action, BoardMove):
        return {
            "kind": "board",
            "from": [action.from_square.file, action.from_square.rank],
            "to": [action.to_square.file, action.to_square.rank],
            "promotion_target_id": action.promotion_target_id,
        }
    return {
        "kind": "drop",
        "base_type_id": action.base_type_id,
        "to": [action.to_square.file, action.to_square.rank],
    }


def _action_from_dict(data: dict, path: str) -> Action:
    """Strict action parser (does not trust :func:`action_from_dict`)."""
    kind = _require_str(_require_field(data, "kind", path), f"{path}.kind")
    if kind == "board":
        allowed = {"kind", "from", "to", "promotion_target_id"}
        unknown = set(data) - allowed
        if unknown:
            raise _err("UNKNOWN_FIELD", path, f"unknown field(s): {sorted(unknown)}")
        from_pair = _require_int_pair(_require_field(data, "from", path), f"{path}.from")
        to_pair = _require_int_pair(_require_field(data, "to", path), f"{path}.to")
        promotion = data.get("promotion_target_id")
        if promotion is not None:
            promotion = _require_str(promotion, f"{path}.promotion_target_id")
        return BoardMove(
            Square(from_pair[0], from_pair[1]),
            Square(to_pair[0], to_pair[1]),
            promotion,
        )
    if kind == "drop":
        allowed = {"kind", "base_type_id", "to"}
        unknown = set(data) - allowed
        if unknown:
            raise _err("UNKNOWN_FIELD", path, f"unknown field(s): {sorted(unknown)}")
        base = _require_str(_require_field(data, "base_type_id", path), f"{path}.base_type_id")
        to_pair = _require_int_pair(_require_field(data, "to", path), f"{path}.to")
        return DropMove(base, Square(to_pair[0], to_pair[1]))
    if kind == "semantic_board":
        allowed = {
            "kind", "pattern_id", "geometry_id", "actor_type_id", "from", "to",
            "promotion_target_id",
        }
        unknown = set(data) - allowed
        if unknown:
            raise _err("UNKNOWN_FIELD", path, f"unknown field(s): {sorted(unknown)}")
        from_pair = _require_int_pair(_require_field(data, "from", path), f"{path}.from")
        to_pair = _require_int_pair(_require_field(data, "to", path), f"{path}.to")
        promotion = data.get("promotion_target_id")
        if promotion is not None:
            promotion = _require_str(promotion, f"{path}.promotion_target_id")
        return SemanticBoardMove(
            pattern_id=_require_str(_require_field(data, "pattern_id", path), f"{path}.pattern_id"),
            geometry_id=_require_str(_require_field(data, "geometry_id", path), f"{path}.geometry_id"),
            actor_type_id=_require_str(_require_field(data, "actor_type_id", path), f"{path}.actor_type_id"),
            from_square=Square(from_pair[0], from_pair[1]),
            to_square=Square(to_pair[0], to_pair[1]),
            promotion_target_id=promotion,
        )
    if kind == "semantic_drop":
        allowed = {"kind", "pattern_id", "geometry_id", "base_type_id", "to"}
        unknown = set(data) - allowed
        if unknown:
            raise _err("UNKNOWN_FIELD", path, f"unknown field(s): {sorted(unknown)}")
        to_pair = _require_int_pair(_require_field(data, "to", path), f"{path}.to")
        return SemanticDropMove(
            pattern_id=_require_str(_require_field(data, "pattern_id", path), f"{path}.pattern_id"),
            geometry_id=_require_str(_require_field(data, "geometry_id", path), f"{path}.geometry_id"),
            base_type_id=_require_str(_require_field(data, "base_type_id", path), f"{path}.base_type_id"),
            to_square=Square(to_pair[0], to_pair[1]),
        )
    raise _err("UNKNOWN_KIND", f"{path}.kind", f"unknown action kind {kind!r}")


def serialize_game_record(record: GameRecord) -> str:
    """Canonical JSON: sorted keys, compact separators, ASCII-safe."""
    actions = [_action_to_dict(a) for a in record.actions]
    data = {
        "schema_version": record.schema_version,
        "ruleset_fingerprint": record.ruleset_fingerprint,
        "actions": actions,
        "resigned_by": record.resigned_by,
    }
    if record.schema_version == 2:
        if record.declaration is None or record.resigned_by is not None:
            raise SessionRecordError("schema v2 requires a declaration and forbids resignation")
        data["declaration"] = {
            "declaration_id": record.declaration.declaration_id,
            "declared_by": record.declaration.declared_by,
            "outcome": record.declaration.outcome,
            "weighted_score": record.declaration.weighted_score,
        }
    elif record.schema_version != 1 or record.declaration is not None:
        raise SessionRecordError("schema v1 cannot contain a declaration")
    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def deserialize_game_record(text: str) -> GameRecord:
    """Strictly parse a GameRecord; malformed input raises SessionRecordError."""
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        raise SessionRecordError(f"[INVALID_JSON] game_record: {exc}") from exc

    path = "game_record"
    payload = _require_mapping(payload, path)
    allowed_top = {"schema_version", "ruleset_fingerprint", "actions", "resigned_by", "declaration"}
    unknown = set(payload) - allowed_top
    if unknown:
        raise _err("UNKNOWN_FIELD", path, f"unknown field(s): {sorted(unknown)}")

    schema_version = _require_int(_require_field(payload, "schema_version", path), f"{path}.schema_version")
    if schema_version not in (1, 2):
        raise _err("UNSUPPORTED_SCHEMA", f"{path}.schema_version", "schema_version must be 1 or 2")

    fingerprint = _require_str(
        _require_field(payload, "ruleset_fingerprint", path), f"{path}.ruleset_fingerprint"
    )

    actions_raw = _require_field(payload, "actions", path)
    if not isinstance(actions_raw, list):
        raise _err("FIELD_NOT_LIST", f"{path}.actions", "actions must be a list")
    actions = tuple(
        _action_from_dict(_require_mapping(a, f"{path}.actions[{i}]"), f"{path}.actions[{i}]")
        for i, a in enumerate(actions_raw)
    )

    resigned = payload.get("resigned_by")
    if resigned is not None:
        resigned = _require_int(resigned, f"{path}.resigned_by")
        if resigned not in (0, 1):
            raise _err("INVALID_PLAYER", f"{path}.resigned_by", "resigned_by must be 0, 1 or null")

    declaration = None
    if schema_version == 1 and "declaration" in payload:
        raise _err("INVALID_SCHEMA", f"{path}.declaration", "declaration requires schema_version 2")
    if schema_version == 2:
        if "declaration" not in payload:
            raise _err("MISSING_FIELD", f"{path}.declaration", "schema v2 requires declaration")
        raw_declaration = _require_mapping(payload["declaration"], f"{path}.declaration")
        allowed = {"declaration_id", "declared_by", "outcome", "weighted_score"}
        unknown = set(raw_declaration) - allowed
        if unknown:
            raise _err("UNKNOWN_FIELD", f"{path}.declaration", f"unknown field(s): {sorted(unknown)}")
        declaration = DeclarationRecord(
            declaration_id=_require_str(_require_field(raw_declaration, "declaration_id", f"{path}.declaration"), f"{path}.declaration.declaration_id"),
            declared_by=_require_int(_require_field(raw_declaration, "declared_by", f"{path}.declaration"), f"{path}.declaration.declared_by"),
            outcome=_require_str(_require_field(raw_declaration, "outcome", f"{path}.declaration"), f"{path}.declaration.outcome"),
            weighted_score=(
                _require_int(raw_declaration["weighted_score"], f"{path}.declaration.weighted_score")
                if raw_declaration.get("weighted_score") is not None else None
            ),
        )
        if declaration.declared_by not in (0, 1):
            raise _err("INVALID_PLAYER", f"{path}.declaration.declared_by", "declared_by must be 0 or 1")
        if declaration.outcome not in ("WIN", "RESTART", "LOSS"):
            raise _err("INVALID_OUTCOME", f"{path}.declaration.outcome", "outcome must be WIN, RESTART or LOSS")
        if resigned is not None:
            raise _err("INVALID_SCHEMA", f"{path}.resigned_by", "resignation and declaration are mutually exclusive")

    return GameRecord(
        schema_version=schema_version,
        ruleset_fingerprint=fingerprint,
        actions=actions,
        resigned_by=resigned,
        declaration=declaration,
    )
