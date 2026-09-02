from __future__ import annotations

import json
from pathlib import Path

import pytest

from generic_chess.native import _module
from generic_chess.native.compiler import compile_native_semantic_rules
from generic_chess.native.semantic import (
    assess_declaration,
    make_checked,
    make_unmake_roundtrip,
    pack_position,
    snapshot,
)
from generic_chess.rules.compiler import compile_semantic_ruleset
from generic_chess.rules.standard_shogi import build_standard_shogi_ruleset
from generic_chess.rules.western_chess import build_western_chess_ruleset


ROOT = Path(__file__).resolve().parents[1]
R1_FIXTURE = ROOT / "tests" / "fixtures" / "h50b1_r1_semantic_native_execution.json"


def test_r1_fixture_freezes_scope_and_next_boundary():
    fixture = json.loads(R1_FIXTURE.read_text(encoding="utf-8"))
    assert fixture["checkpoint"] == "H50B1-R1_F50_SEMANTIC_NATIVE_CANONICAL_EXECUTION"
    assert fixture["parent_sha"] == "66f1186908a48692b0e5b514b34dc77c78c7ec09"
    assert fixture["declarations"]["owner"] == "native_c_payload_and_c_runtime"
    assert fixture["history"]["fresh_entry"] == {"actor": 255, "gave_check": False}
    assert fixture["matrix"]["western"]["native_executable"] is True
    assert fixture["matrix"]["standard_shogi"]["native_executable"] is True
    assert fixture["historical_validation"]["historical_fixtures_rewritten"] is False
    assert fixture["F50B2_status"] == "NOT_STARTED"


def _initial(semantic, native):
    ids = {type_id: index for index, type_id in enumerate(native.type_ids)}
    board = [
        None if piece is None else [
            ids[piece.base_type_id], ids[piece.current_type_id],
            piece.owner, int(piece.promoted),
        ]
        for row in semantic.support.initial_position
        for piece in row
    ]
    return pack_position(native, {
        "side": 0,
        "ply": 0,
        "board": board,
        "hands": [[0] * len(ids), [0] * len(ids)],
        "aux_state": (),
    })


@pytest.mark.parametrize("builder", [build_western_chess_ruleset, build_standard_shogi_ruleset])
def test_r1_fresh_history_and_native_roundtrip_are_event_exact(builder):
    semantic = compile_semantic_ruleset(builder())
    native = compile_native_semantic_rules(semantic)
    position = _initial(semantic, native)
    before = snapshot(native, position)
    assert before["history"] and len(before["history"]) == 1
    assert before["history_events"] == ((255, False),)
    assert before["history_exact"] is True
    assert before["history_events_exact"] is True

    action = _module().semantic_candidate_actions(native.capsule, position)[0]
    child = make_checked(native, position, int(action))
    after = snapshot(native, child)
    assert len(after["history"]) == 2
    assert after["history_events"][0] == (255, False)
    assert after["history_events"][1][0] == 0
    assert after["history_events_exact"] is True
    assert make_unmake_roundtrip(native, position, int(action))["restored"] == 1


def test_r1_incomplete_or_non_sentinel_events_fail_closed():
    semantic = compile_semantic_ruleset(build_standard_shogi_ruleset())
    native = compile_native_semantic_rules(semantic)
    position = _initial(semantic, native)
    key = tuple(int(_module().semantic_position_key(native.capsule, position)[i:i + 16], 16)
                for i in range(0, 64, 16))
    imported = pack_position(native, {
        "side": 0,
        "ply": 0,
        "board": [
            None if cell is None else list(cell)
            for cell in snapshot(native, position)["board"]
        ],
        "hands": snapshot(native, position)["hands"],
        "history": [key] * 4,
        "history_events": [(0, 1), (1, 0), (0, 1), (1, 0)],
        "aux_state": (),
    })
    observed = snapshot(native, imported)
    assert observed["history_exact"] is True
    assert observed["history_events_exact"] is False


def test_r1_declaration_and_automatic_contracts_are_reconstructed_by_c():
    semantic = compile_semantic_ruleset(build_standard_shogi_ruleset())
    native = compile_native_semantic_rules(semantic)
    info = dict(_module().semantic_rules_info(native.capsule))
    assert [item["declaration_id"] for item in info["declarations"]] == [
        "claim_owner_0", "claim_owner_1"
    ]
    assert info["declarations"][0]["weighted_metric"]["weights"]
    assert info["automatic_adjudications"] == [{
        "adjudication_id": "standard_shogi_500_move_no_contest",
        "trigger_ply": 500,
        "outcome": 3,
        "continuation_policy": 0,
    }]
    position = _initial(semantic, native)
    import generic_chess.core.declarations as core_declarations

    original = core_declarations._assess_declaration_position
    core_declarations._assess_declaration_position = lambda *args, **kwargs: (_ for _ in ()).throw(
        AssertionError("Native declaration path called the Python private oracle")
    )
    try:
        result = assess_declaration(native, position, "claim_owner_0")
    finally:
        core_declarations._assess_declaration_position = original
    assert result.declaration_id == "claim_owner_0"
    assert result.outcome == "LOSS"
