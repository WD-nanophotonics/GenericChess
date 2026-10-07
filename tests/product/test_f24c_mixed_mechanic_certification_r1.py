"""F24C corrective R1: lifecycle, serialization, rename and search evidence.

The first-pass F24C module is imported without modification.  This file adds
only evidence for the frozen mixed ruleset and its simultaneous root.
"""

from __future__ import annotations

import json
from dataclasses import replace
from types import SimpleNamespace

import pytest

from generic_chess.ai.alphabeta.native_legality import NativeSemanticLegalityProvider
from generic_chess.ai.alphabeta.player import AlphaBetaPlayer
from generic_chess.ai.limits import SearchLimits
from generic_chess.core.actions import action_from_dict, action_to_dict
from generic_chess.core.identity import repetition_identity_key
from generic_chess.core.position import GameState, Hands
from generic_chess.core.search_runtime import SearchPathRuntime
from generic_chess.core.semantic_executor import semantic_engine_for
from generic_chess.core.terminal import TerminalResult, TerminalStatus
from generic_chess.core.transition import apply_action, initial_state, legal_successors
from generic_chess.core.movegen import legal_actions
from generic_chess.rules.schema import ruleset_from_dict, ruleset_to_dict

from test_f24c_mixed_mechanic_certification import (
    A0, A1, B0, B1, C0, H0, N, Piece, _compiled, _mixed_ruleset,
    _position, _rename_ruleset,
)


def _simultaneous(compiled):
    return _position(
        compiled,
        [
            (1, 1, Piece(0, A0, A0)), (2, 1, Piece(1, A0, A0)),
            (1, 3, Piece(0, B0, B0)), (2, 3, Piece(1, B0, B0)),
            (1, 5, Piece(0, C0, C0)), (2, 5, Piece(0, A0, A0)), (4, 5, Piece(1, C0, C0)),
            (4, 4, Piece(0, A0, A0)), (4, 3, Piece(0, B0, B0)),
            (0, 0, Piece(0, H0, H0)), (6, 6, Piece(1, H0, H0)),
        ],
        hands=([(A0, 1)], ()),
    )


def _state(compiled, position, *, ply=0):
    key = repetition_identity_key(position, compiled)
    return GameState(position, ply, ((key, 1),), TerminalResult(TerminalStatus.ONGOING))


def _runtime_snapshot(runtime):
    return (
        runtime.position,
        runtime.ply_count,
        runtime.terminal_status,
        tuple(runtime.repetition_counts.items()),
        tuple(runtime.history),
        runtime.current_identity,
        runtime.search_key(),
        tuple(sorted(map(str, runtime.legal_actions()))),
        runtime.depth,
    )


def _find(actions, text, *, promotion=None):
    return next(
        a for a in actions
        if text in a.pattern_id
        and (promotion is None or a.promotion_target_id == promotion)
    )


def test_every_simultaneous_public_action_roundtrips_without_collision():
    compiled = _compiled()
    state = _state(compiled, _simultaneous(compiled))
    actions = tuple(action for action, _child in legal_successors(state, compiled))
    payloads = [json.dumps(action_to_dict(action), sort_keys=True, separators=(",", ":")) for action in actions]
    assert len(payloads) == len(set(payloads))
    for action in actions:
        rebuilt = action_from_dict(action_to_dict(action))
        assert rebuilt == action
        assert rebuilt.pattern_id == action.pattern_id
        assert rebuilt.geometry_id == action.geometry_id
        if hasattr(action, "actor_type_id"):
            assert rebuilt.actor_type_id == action.actor_type_id
            assert rebuilt.from_square == action.from_square
            assert rebuilt.to_square == action.to_square
        else:
            assert rebuilt.base_type_id == action.base_type_id
            assert rebuilt.to_square == action.to_square
        if hasattr(action, "promotion_target_id"):
            assert rebuilt.promotion_target_id == action.promotion_target_id


def test_ruleset_roundtrip_has_behavioral_equivalence_at_simultaneous_root():
    source = _mixed_ruleset()
    rebuilt = ruleset_from_dict(ruleset_to_dict(source))
    left = _compiled()
    from generic_chess.rules.compiler import compile_semantic_ruleset
    right = compile_semantic_ruleset(rebuilt)
    left_actions = semantic_engine_for(left).legal_actions(_simultaneous(left))
    right_actions = semantic_engine_for(right).legal_actions(_simultaneous(right))
    shape = lambda actions: {(a.pattern_id, a.source, a.target, a.promotion_target_id, a.actor_type) for a in actions}
    assert shape(left_actions) == shape(right_actions)
    for needle in ("capture_A0_A0", "capture_B0_B0", "capture_C0_C0_path"):
        a = _find(left_actions, needle)
        b = _find(right_actions, needle)
        assert semantic_engine_for(left).apply(_simultaneous(left), a).hands == semantic_engine_for(right).apply(_simultaneous(right), b).hands


def test_full_type_rename_preserves_simultaneous_shapes_and_children():
    mapping = {A0: "RA0", A1: "RA1", B0: "RB0", B1: "RB1", C0: "RC0", H0: "RH0"}
    inverse = {value: key for key, value in mapping.items()}
    from generic_chess.rules.compiler import compile_semantic_ruleset
    original = _compiled()
    renamed = compile_semantic_ruleset(_rename_ruleset(_mixed_ruleset(), mapping))
    original_pos = _simultaneous(original)
    renamed_pos = _position(
        renamed,
        [
            (1, 1, Piece(0, mapping[A0], mapping[A0])), (2, 1, Piece(1, mapping[A0], mapping[A0])),
            (1, 3, Piece(0, mapping[B0], mapping[B0])), (2, 3, Piece(1, mapping[B0], mapping[B0])),
            (1, 5, Piece(0, mapping[C0], mapping[C0])), (2, 5, Piece(0, mapping[A0], mapping[A0])), (4, 5, Piece(1, mapping[C0], mapping[C0])),
            (4, 4, Piece(0, mapping[A0], mapping[A0])), (4, 3, Piece(0, mapping[B0], mapping[B0])),
            (0, 0, Piece(0, mapping[H0], mapping[H0])), (6, 6, Piece(1, mapping[H0], mapping[H0])),
        ],
        hands=([(mapping[A0], 1)], ()),
    )
    original_actions = semantic_engine_for(original).legal_actions(original_pos)
    renamed_actions = semantic_engine_for(renamed).legal_actions(renamed_pos)
    normalize = lambda actions: {(a.pattern_id, a.source, a.target, inverse.get(a.promotion_target_id, a.promotion_target_id), inverse.get(a.actor_type, a.actor_type)) for a in actions}
    assert normalize(original_actions) == normalize(renamed_actions)
    for needle in ("capture_A0_A0", "capture_B0_B0", "capture_C0_C0_path"):
        left = _find(original_actions, needle)
        right = _find(renamed_actions, needle)
        left_child = semantic_engine_for(original).apply(original_pos, left)
        right_child = semantic_engine_for(renamed).apply(renamed_pos, right)
        assert sum(p is not None for p in left_child.board) == sum(p is not None for p in right_child.board)
        assert left_child.hands[0].total() == right_child.hands[0].total()
    for actor in (A0, B0, C0):
        for victim, current, promoted in ((A0, A0, False), (A0, A1, True), (B0, B0, False), (B0, B1, True), (C0, C0, False)):
            left_pos = _position(original, [(1, 1, Piece(0, actor, actor)), (2, 1, Piece(1, victim, current, promoted=promoted)), (0, 0, Piece(0, H0, H0)), (6, 6, Piece(1, H0, H0))])
            right_pos = _position(renamed, [(1, 1, Piece(0, mapping[actor], mapping[actor])), (2, 1, Piece(1, mapping[victim], mapping[current], promoted=promoted)), (0, 0, Piece(0, mapping[H0], mapping[H0])), (6, 6, Piece(1, mapping[H0], mapping[H0]))])
            left = next(a for a in semantic_engine_for(original).legal_actions(left_pos) if "capture_" in a.pattern_id and a.source == 8 and a.target == 9)
            right = next(a for a in semantic_engine_for(renamed).legal_actions(right_pos) if "capture_" in a.pattern_id and a.source == 8 and a.target == 9)
            left_child = semantic_engine_for(original).apply(left_pos, left)
            right_child = semantic_engine_for(renamed).apply(right_pos, right)
            normalize_piece = lambda p: None if p is None else (p.owner, inverse.get(p.base_type_id, p.base_type_id), inverse.get(p.current_type_id, p.current_type_id), p.promoted)
            assert tuple(map(normalize_piece, left_child.board)) == tuple(map(normalize_piece, right_child.board))
            assert left_child.hands[0].total() == right_child.hands[0].total()
    for base, target_id, square in ((A0, A1, (4, 4)), (B0, B1, (4, 3))):
        left_pos = _position(original, [(square[0], square[1], Piece(0, base, base)), (0, 0, Piece(0, H0, H0)), (6, 6, Piece(1, H0, H0))])
        right_pos = _position(renamed, [(square[0], square[1], Piece(0, mapping[base], mapping[base])), (0, 0, Piece(0, mapping[H0], mapping[H0])), (6, 6, Piece(1, mapping[H0], mapping[H0]))])
        assert any(a.promotion_target_id == target_id for a in semantic_engine_for(original).legal_actions(left_pos))
        assert any(a.promotion_target_id == mapping[target_id] for a in semantic_engine_for(renamed).legal_actions(right_pos))
    drop_left = _position(original, [(0, 0, Piece(0, H0, H0)), (6, 6, Piece(1, H0, H0))], hands=([(A0, 1)], ()))
    drop_right = _position(renamed, [(0, 0, Piece(0, mapping[H0], mapping[H0])), (6, 6, Piece(1, mapping[H0], mapping[H0]))], hands=([(mapping[A0], 1)], ()))
    assert any(a.actor_type == A0 and a.source is None for a in semantic_engine_for(original).legal_actions(drop_left))
    assert any(a.actor_type == mapping[A0] and a.source is None for a in semantic_engine_for(renamed).legal_actions(drop_right))


@pytest.mark.parametrize(
    "label, entries, hands, matcher, expected",
    [
        ("hand_capture", [(1, 1, Piece(0, A0, A0)), (2, 1, Piece(1, A0, A0)), (0, 0, Piece(0, H0, H0)), (6, 6, Piece(1, H0, H0))], ((), ()), "capture_A0_A0", "hand"),
        ("remove_capture", [(1, 1, Piece(0, A0, A0)), (2, 1, Piece(1, B0, B0)), (0, 0, Piece(0, H0, H0)), (6, 6, Piece(1, H0, H0))], ((), ()), "capture_A0_B0", "remove"),
        ("promoted_A_victim", [(1, 1, Piece(0, B0, B0)), (2, 1, Piece(1, A0, A1, promoted=True)), (0, 0, Piece(0, H0, H0)), (6, 6, Piece(1, H0, H0))], ((), ()), "capture_B0_A0", "hand"),
        ("promoted_B_victim", [(1, 1, Piece(0, A0, A0)), (2, 1, Piece(1, B0, B1, promoted=True)), (0, 0, Piece(0, H0, H0)), (6, 6, Piece(1, H0, H0))], ((), ()), "capture_A0_B0", "remove"),
        ("drop", [(0, 0, Piece(0, H0, H0)), (6, 6, Piece(1, H0, H0))], (((A0, 1),), ()), "drop_A0", "drop"),
        ("promote_A", [(4, 4, Piece(0, A0, A0)), (0, 0, Piece(0, H0, H0)), (6, 6, Piece(1, H0, H0))], ((), ()), "advance_A0", "promote_a"),
        ("promote_B", [(4, 3, Piece(0, B0, B0)), (0, 0, Piece(0, H0, H0)), (6, 6, Piece(1, H0, H0))], ((), ()), "advance_B0", "promote_b"),
        ("path", [(1, 1, Piece(0, C0, C0)), (2, 1, Piece(0, A0, A0)), (4, 1, Piece(1, C0, C0)), (0, 0, Piece(0, H0, H0)), (6, 6, Piece(1, H0, H0))], ((), ()), "capture_C0_C0_path", "remove"),
        ("quiet", [(4, 4, Piece(0, A0, A0)), (0, 0, Piece(0, H0, H0)), (6, 6, Piece(1, H0, H0))], ((), ()), "advance_A0", "quiet"),
    ],
)
def test_representative_mechanic_runtime_push_pop(label, entries, hands, matcher, expected):
    compiled = _compiled()
    position = _position(compiled, entries, hands=hands)
    runtime = SearchPathRuntime(_state(compiled, position), compiled)
    before = _runtime_snapshot(runtime)
    actions = runtime.legal_actions()
    target_index = lambda action: action.target if hasattr(action, "target") else action.to_square.rank * N + action.to_square.file
    if expected == "promote_a":
        action = next(a for a in actions if matcher in a.pattern_id and a.promotion_target_id == A1)
    elif expected == "promote_b":
        action = next(a for a in actions if matcher in a.pattern_id and a.promotion_target_id == B1)
    elif expected == "quiet":
        action = next(a for a in actions if matcher in a.pattern_id and a.promotion_target_id is None)
    else:
        action = _find(actions, matcher)
    runtime.push(action)
    assert runtime.position.side_to_move == 1
    assert runtime.ply_count == 1
    assert len(runtime.history) == 2
    if expected == "hand":
        assert runtime.position.hands[0].count(A0) == 1
    elif expected == "drop":
        assert runtime.position.hands[0].count(A0) == 0
        assert runtime.position.board[target_index(action)].base_type_id == A0
    elif expected == "promote_a":
        piece = runtime.position.board[target_index(action)]
        assert (piece.base_type_id, piece.current_type_id, piece.promoted) == (A0, A1, True)
    elif expected == "promote_b":
        piece = runtime.position.board[target_index(action)]
        assert (piece.base_type_id, piece.current_type_id, piece.promoted) == (B0, B1, True)
    runtime.pop()
    assert _runtime_snapshot(runtime) == before
    runtime.assert_balanced()


def test_nested_sibling_isolation_and_stale_action_rollback():
    compiled = _compiled()
    runtime = SearchPathRuntime(_state(compiled, _simultaneous(compiled)), compiled)
    root = _runtime_snapshot(runtime)
    capture = _find(runtime.legal_actions(), "capture_A0_A0")
    drop = _find(runtime.legal_actions(), "drop_A0")
    runtime.push(capture)
    child = _runtime_snapshot(runtime)
    reply = runtime.legal_actions()[0]
    runtime.push(reply)
    runtime.pop()
    assert _runtime_snapshot(runtime) == child
    runtime.pop()
    assert _runtime_snapshot(runtime) == root
    runtime.push(drop)
    assert runtime.position.hands[0].count(A0) == 0
    runtime.pop()
    assert _runtime_snapshot(runtime) == root
    with pytest.raises(Exception):
        runtime.push(replace(capture, target=0))
    assert _runtime_snapshot(runtime) == root
    runtime.assert_balanced()


def test_repetition_cycle_reaches_authoritative_limit_and_pops():
    compiled = _compiled()
    position = _position(compiled, [(0, 0, Piece(0, H0, H0)), (6, 6, Piece(1, H0, H0))])
    public = _state(compiled, position)
    runtime = SearchPathRuntime(public, compiled)
    cycle = ((0, 0, 1, 0), (6, 6, 5, 6), (1, 0, 0, 0), (5, 6, 6, 6))
    actions = []
    for _ in range(2):
        for f0, r0, f1, r1 in cycle:
            action = next(a for a in runtime.legal_actions() if a.from_square.file == f0 and a.from_square.rank == r0 and a.to_square.file == f1 and a.to_square.rank == r1)
            actions.append(action)
            runtime.push(action)
            public = apply_action(public, action, compiled)
    assert runtime.terminal_status.status is TerminalStatus.REPETITION
    assert public.terminal_status.status is TerminalStatus.REPETITION
    assert runtime.occurrence_count() == 3
    for _ in actions:
        runtime.pop()
    assert runtime.position == position
    assert runtime.ply_count == 0
    runtime.assert_balanced()


def test_max_ply_boundary_is_authoritative_and_reversible():
    from generic_chess.rules.compiler import compile_semantic_ruleset
    compiled = compile_semantic_ruleset(replace(_mixed_ruleset(), max_ply=1))
    position = _position(compiled, [(0, 0, Piece(0, H0, H0)), (6, 6, Piece(1, H0, H0))])
    state = _state(compiled, position)
    runtime = SearchPathRuntime(state, compiled)
    action = runtime.legal_actions()[0]
    runtime.push(action)
    assert runtime.ply_count == 1
    assert runtime.terminal_status.status is TerminalStatus.MAX_PLY
    assert runtime.terminal_status == apply_action(state, action, compiled).terminal_status
    runtime.pop()
    assert runtime.position == position and runtime.ply_count == 0
    runtime.assert_balanced()


def test_eight_state_mixed_search_smoke_is_deterministic_at_128_and_512():
    from generic_chess.learning.round5_benchmark import SearchSemanticCompiled
    semantic = _compiled()
    compiled = SearchSemanticCompiled(ir=semantic.ir, _legacy_compiled=semantic._legacy_compiled, support=semantic.support)
    assert NativeSemanticLegalityProvider.try_create(compiled) is not None
    positions = [
        _simultaneous(compiled),
        _position(compiled, [(1, 1, Piece(0, A0, A0)), (2, 1, Piece(1, A0, A0)), (0, 0, Piece(0, H0, H0)), (6, 6, Piece(1, H0, H0))]),
        _position(compiled, [(1, 1, Piece(0, A0, A0)), (2, 1, Piece(1, B0, B0)), (0, 0, Piece(0, H0, H0)), (6, 6, Piece(1, H0, H0))]),
        _position(compiled, [(0, 0, Piece(0, H0, H0)), (6, 6, Piece(1, H0, H0))], hands=([(A0, 1)], ())),
        _position(compiled, [(4, 4, Piece(0, A0, A0)), (4, 3, Piece(0, B0, B0)), (0, 0, Piece(0, H0, H0)), (6, 6, Piece(1, H0, H0))]),
        _position(compiled, [(1, 1, Piece(0, C0, C0)), (2, 1, Piece(0, A0, A0)), (4, 1, Piece(1, C0, C0)), (0, 0, Piece(0, H0, H0)), (6, 6, Piece(1, H0, H0))]),
        _position(compiled, [(1, 1, Piece(0, B0, B0)), (2, 1, Piece(1, A0, A1, promoted=True)), (0, 0, Piece(0, H0, H0)), (6, 6, Piece(1, H0, H0))]),
        _position(compiled, [(0, 0, Piece(0, H0, H0)), (6, 6, Piece(1, H0, H0))]),
    ]
    descriptors = [json.dumps({"board": [None if p is None else (p.owner, p.base_type_id, p.current_type_id, p.promoted) for p in pos.board], "hands": [h.counts for h in pos.hands], "side": pos.side_to_move}, sort_keys=True, default=str, separators=(",", ":")) for pos in positions]
    assert len(descriptors) == 8 and len(set(descriptors)) == 8
    for pos in positions:
        state = _state(compiled, pos)
        for budget in (128, 512):
            decisions = []
            for _ in range(2):
                session = SimpleNamespace(state=state, _search_witnesses=(pos,))
                decision = AlphaBetaPlayer(compiled, use_disk_cache=False, use_tt=False, use_native_semantic_legality=True).choose_action(
                    session, SearchLimits(max_depth=4, max_nodes=budget, quiescence_max_depth=0, quiescence_hard_max_depth=0)
                )
                decisions.append(decision)
                assert decision.action in legal_actions(state, compiled)
                assert decision.nodes + decision.qnodes <= budget
                assert decision.termination_reason in {"node_limit", "completed_depth", "terminal_position"}
            assert (decisions[0].action, decisions[0].score, decisions[0].principal_variation[:1]) == (decisions[1].action, decisions[1].score, decisions[1].principal_variation[:1])
