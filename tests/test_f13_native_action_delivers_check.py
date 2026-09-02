from __future__ import annotations

from copy import deepcopy

import pytest

from scripts.audit_f13_native_action_delivers_check import certified_semantic_shogi
from generic_chess.core.semantic_executor import semantic_engine_for
from generic_chess.learning.shogi_rules import sfen_to_gc_state
from generic_chess.native import _module, native_available
from generic_chess.native.compiler import (
    NativeUnsupportedRuleError,
    build_semantic_compile_payload,
    compile_native_semantic_rules,
)
from generic_chess.native.semantic import guarded_actions, pack_position


SHOGI_CHECK_DROP_SFEN = (
    "ln4rnl/1gk1gs3/3ps1p1b/p1p2p1pp/1P1P5/"
    "PpR1p1PPP/4PP1S1/4G3L/LNSKG2NB b P 59"
)


def _native_position(semantic, native_rules, state):
    ids = {type_id: index for index, type_id in enumerate(native_rules.type_ids)}
    board = [
        None
        if piece is None
        else [
            ids[piece.base_type_id],
            ids[piece.current_type_id],
            piece.owner,
            int(piece.promoted),
        ]
        for piece in state.position.board
    ]
    hands = []
    for owner in (0, 1):
        counts = [0] * len(ids)
        for type_id, count in state.position.hands[owner].counts:
            counts[ids[type_id]] = count
        hands.append(counts)
    return pack_position(
        native_rules,
        {
            "side": state.position.side_to_move,
            "ply": state.ply_count,
            "root_hash_count": 1,
            "board": board,
            "hands": hands,
            "aux_state": (),
        },
    )


def _raw_action(native_rules, action):
    ids = {type_id: index for index, type_id in enumerate(native_rules.type_ids)}
    patterns = {pattern_id: index for index, pattern_id in enumerate(native_rules.pattern_ids)}
    geometries = {geometry_id: index for index, geometry_id in enumerate(native_rules.geometry_ids)}
    assert action.source is None
    actor = ids[action.actor_type]
    return (
        action.target
        | (0xFF << 8)
        | (0xFF << 16)
        | (actor << 24)
        | (3 << 32)
        | (patterns[action.pattern_id] << 36)
        | (geometries[action.geometry_id] << 44)
        | (actor << 56)
    )


@pytest.mark.skipif(not native_available(), reason="native extension unavailable")
def test_f13_standard_shogi_checking_drop_witness_matches_python():
    semantic = certified_semantic_shogi()
    native_rules = compile_native_semantic_rules(semantic)
    state = sfen_to_gc_state(semantic, SHOGI_CHECK_DROP_SFEN)
    engine = semantic_engine_for(semantic)
    native_position = _native_position(semantic, native_rules, state)

    checking = next(
        action
        for action in engine.legal_actions(state.position)
        if action.source is None and action.target == 60
    )
    child = engine.apply(state.position, checking)
    assert engine._action_delivers_check(state.position, child, checking) is True
    raw = _raw_action(native_rules, checking)
    assert _module()._semantic_action_delivers_check_debug(
        native_rules.capsule, native_position, raw
    ) is True
    assert raw in guarded_actions(native_rules, native_position)


@pytest.mark.skipif(not native_available(), reason="native extension unavailable")
def test_f13_nonchecking_drop_does_not_collapse_to_opponent_checked():
    semantic = certified_semantic_shogi()
    native_rules = compile_native_semantic_rules(semantic)
    state = sfen_to_gc_state(semantic, SHOGI_CHECK_DROP_SFEN)
    engine = semantic_engine_for(semantic)
    native_position = _native_position(semantic, native_rules, state)

    nonchecking = next(
        action
        for action in engine.legal_actions(state.position)
        if action.source is None and action.target == 15
    )
    child = engine.apply(state.position, nonchecking)
    assert engine._action_delivers_check(state.position, child, nonchecking) is False
    raw = _raw_action(native_rules, nonchecking)
    assert _module()._semantic_action_delivers_check_debug(
        native_rules.capsule, native_position, raw
    ) is False
    assert raw in guarded_actions(native_rules, native_position)


@pytest.mark.skipif(not native_available(), reason="native extension unavailable")
def test_f13_compile_gate_and_frozen_postcondition_code_contract():
    semantic = certified_semantic_shogi()
    payload, report = build_semantic_compile_payload(semantic)
    native_rules = compile_native_semantic_rules(semantic)
    assert report.native_executable is True
    assert native_rules.native_executable is True
    assert report.ruleset_fingerprint == semantic.ruleset_fingerprint
    assert report.ir_version == 2
    assert report.semantic_payload_version == 3
    assert report.native_schema_version == "native-0.5.0"
    assert 2 in {
        post["kind"]
        for pattern in payload["patterns"]
        for post in pattern["postconditions"]
    }

    malformed = deepcopy(payload)
    pattern = next(item for item in malformed["patterns"] if item["postconditions"])
    pattern["postconditions"][0]["kind"] = 3
    with pytest.raises(ValueError):
        _module().compile_semantic_rules(malformed)


@pytest.mark.skipif(not native_available(), reason="native extension unavailable")
def test_f13_standard_shogi_four_prefix_native_candidate_and_guarded_order():
    from scripts.audit_f4_runtime_cost import corpus_specs, make_session

    semantic = certified_semantic_shogi()
    native_rules = compile_native_semantic_rules(semantic)
    engine = semantic_engine_for(semantic)
    for prefix_id in (
        "semantic_prefix_0",
        "semantic_prefix_1",
        "semantic_prefix_2",
        "semantic_prefix_3",
    ):
        session = make_session(next(spec for spec in corpus_specs() if spec["id"] == prefix_id))
        state = session.state
        position = _native_position(semantic, native_rules, state)
        python_actions = tuple(
            (a.pattern_id, a.geometry_id, a.actor_type, a.source, a.target)
            for a in engine.legal_actions(state.position)
        )
        native_actions = guarded_actions(native_rules, position)
        assert len(native_actions) == len(python_actions), prefix_id

