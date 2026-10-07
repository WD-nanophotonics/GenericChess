"""GameRecord JSON determinism and strict validation."""

import json

import pytest

from generic_chess.core.actions import BoardMove, DropMove
from generic_chess.core.coordinates import Square
from generic_chess.generation.config import GeneratorConfig
from generic_chess.generation.generator import generate_game
from generic_chess.session.record import GameRecord
from generic_chess.session.session import GameSession, SessionRecordError
from generic_chess.session.serialization import (
    deserialize_game_record,
    serialize_game_record,
)


def _record() -> GameRecord:
    game = generate_game(GeneratorConfig(seed=42))
    session = GameSession(game.compiled_ruleset)
    session.submit(session.legal_actions()[0])
    session.submit(session.legal_actions()[0])
    return session.to_record()


def test_serialization_is_canonical_and_deterministic():
    record = _record()
    assert serialize_game_record(record) == serialize_game_record(record)


def test_round_trip_equality():
    record = _record()
    back = deserialize_game_record(serialize_game_record(record))
    assert back == record
    assert back.actions == record.actions


def test_serialization_contains_all_action_kinds():
    record = GameRecord(
        schema_version=1,
        ruleset_fingerprint="fp",
        actions=(
            BoardMove(Square(1, 0), Square(1, 2), "G"),
            DropMove("P", Square(3, 3)),
        ),
        resigned_by=1,
    )
    data = json.loads(serialize_game_record(record))
    assert [a["kind"] for a in data["actions"]] == ["board", "drop"]
    assert data["resigned_by"] == 1


def test_unknown_top_level_field_rejected():
    data = json.loads(serialize_game_record(_record()))
    data["extra"] = 1
    with pytest.raises(SessionRecordError):
        deserialize_game_record(json.dumps(data))


def test_unknown_action_field_rejected():
    data = json.loads(serialize_game_record(_record()))
    data["actions"][0]["color"] = "red"
    with pytest.raises(SessionRecordError):
        deserialize_game_record(json.dumps(data))


def test_board_action_rejects_drop_field():
    data = {
        "schema_version": 1,
        "ruleset_fingerprint": "fp",
        "actions": [
            {"kind": "board", "from": [0, 0], "to": [1, 1], "base_type_id": "P"}
        ],
        "resigned_by": None,
    }
    with pytest.raises(SessionRecordError):
        deserialize_game_record(json.dumps(data))


def test_drop_action_rejects_board_fields():
    data = {
        "schema_version": 1,
        "ruleset_fingerprint": "fp",
        "actions": [
            {
                "kind": "drop",
                "base_type_id": "P",
                "to": [2, 2],
                "from": [7, 7],
                "promotion_target_id": "G",
            }
        ],
        "resigned_by": None,
    }
    with pytest.raises(SessionRecordError):
        deserialize_game_record(json.dumps(data))


def test_unsupported_schema_rejected():
    data = json.loads(serialize_game_record(_record()))
    data["schema_version"] = 2
    with pytest.raises(SessionRecordError):
        deserialize_game_record(json.dumps(data))


def test_bad_coordinate_types_rejected():
    data = json.loads(serialize_game_record(_record()))
    data["actions"][0]["from"] = ["a", 1]
    with pytest.raises(SessionRecordError):
        deserialize_game_record(json.dumps(data))


def test_bad_promotion_type_rejected():
    data = json.loads(serialize_game_record(_record()))
    data["actions"][0]["promotion_target_id"] = 42
    with pytest.raises(SessionRecordError):
        deserialize_game_record(json.dumps(data))


def test_bad_resigned_by_rejected():
    data = json.loads(serialize_game_record(_record()))
    data["resigned_by"] = 7
    with pytest.raises(SessionRecordError):
        deserialize_game_record(json.dumps(data))


def test_no_bare_parse_exceptions_leak():
    bad_inputs = [
        "{not json",
        "[]",
        '"just a string"',
        '{"schema_version": 1}',
        '{"schema_version": 1, "ruleset_fingerprint": "x", "actions": [{"kind": "board"}], "resigned_by": null}',
        '{"schema_version": 1, "ruleset_fingerprint": "x", "actions": "nope", "resigned_by": null}',
    ]
    for text in bad_inputs:
        with pytest.raises(SessionRecordError):
            deserialize_game_record(text)
