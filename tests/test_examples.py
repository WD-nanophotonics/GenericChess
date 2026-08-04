"""The shipped example ruleset must deserialize and compile."""

import json
from pathlib import Path

from generic_chess.rules.compiler import compile_ruleset
from generic_chess.rules.schema import compute_fingerprint
from generic_chess.rules.serialization import deserialize_ruleset, serialize_ruleset


def _example_path() -> Path:
    return Path(__file__).resolve().parent.parent / "examples" / "minimal_ruleset.json"


def test_example_ruleset_is_valid_json():
    data = json.loads(_example_path().read_text(encoding="utf-8"))
    assert data["schema_version"] == 1
    assert data["board_size"] == 4


def test_example_ruleset_compiles_and_round_trips():
    ruleset = deserialize_ruleset(_example_path().read_text(encoding="utf-8"))
    compiled = compile_ruleset(ruleset)
    assert compiled.board_size == 4
    assert compiled.initial_entity_count == 3  # P0 K + P0 P + P1 K

    text = serialize_ruleset(ruleset)
    back = deserialize_ruleset(text)
    assert compute_fingerprint(back) == compute_fingerprint(ruleset)
