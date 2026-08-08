"""Frozen independent-review regressions for Phase 1.9B-2 R2.

Authored against impl 3f3affd. Do not weaken or xfail these tests.
"""

from __future__ import annotations

from dataclasses import replace

import pytest

from generic_chess.core.coordinates import Square
from generic_chess.core.pieces import Piece, PieceType
from generic_chess.core.position import Hands, Position
from generic_chess.rules.schema import (
    RuleActionEffect,
    RuleAuxState,
    RuleGeometrySpec,
    RuleInvariant,
    RulePathConstraint,
    RuleReplaceSelector,
    RuleSemanticAction,
    RuleSlotGuard,
    RuleSpatialSelector,
    RuleSquareRef,
    RuleStateGuard,
    RuleTypeRef,
)

from rule_semantics_ir_fixtures import _king_type, _semantic_ruleset


def _idx(support, file, rank):
    return rank * support.board_size + file


def _rows(n, entries):
    rows = [[None for _ in range(n)] for _ in range(n)]
    for file, rank, piece in entries:
        rows[rank][file] = piece
    return tuple(tuple(row) for row in rows)


def _compile(ruleset):
    from generic_chess.rules.compiler import compile_semantic_ruleset
    return compile_semantic_ruleset(ruleset)


def _engine(ruleset):
    from generic_chess.core.semantic_executor import SemanticEngine
    return SemanticEngine(_compile(ruleset))


def _position(support, entries, side=0, hands=None, aux_state=()):
    board = [None] * (support.board_size * support.board_size)
    for file, rank, piece in entries:
        board[_idx(support, file, rank)] = piece
    if hands is None:
        hands = (Hands.empty(), Hands.empty())
    return Position(
        board=tuple(board),
        hands=hands,
        side_to_move=side,
        ruleset_fingerprint=support.ruleset_fingerprint,
        aux_state=aux_state,
    )


def test_public_semantic_actions_preserve_pattern_and_geometry_identity():
    from generic_chess.core.actions import action_from_dict, action_to_dict
    from generic_chess.core.keys import semantic_position_key
    from generic_chess.core.movegen import legal_actions
    from generic_chess.core.movement import LeapAtom
    from generic_chess.core.transition import apply_action, initial_state

    n = 5
    a = PieceType("A", "A", (LeapAtom((1, 0)),))
    flag = RuleAuxState("flag", "bool", "global", "persistent", 0)

    def semantic(name, value):
        return RuleSemanticAction(
            name=name,
            type_ids=("A",),
            geometry=RuleGeometrySpec(kind="leap", offset=(1, 0)),
            target_relation="empty",
            composition="augment",
            aux_state=(flag,),
            effects=(
                RuleActionEffect(
                    "move",
                    from_ref=RuleSquareRef("source"),
                    to_ref=RuleSquareRef("target"),
                ),
                RuleActionEffect("set_bool", slot_name="flag", value=value),
            ),
            invariants=(RuleInvariant("own_anchor_safe"),),
        )

    rows = _rows(
        n,
        [
            (0, 0, Piece(0, "K", "K")),
            (1, 1, Piece(0, "A", "A")),
            (4, 4, Piece(1, "K", "K")),
        ],
    )
    compiled = _compile(
        _semantic_ruleset(
            (_king_type(), a),
            (semantic("same_intent_zero", 0), semantic("same_intent_one", 1)),
            n=n,
            rows=rows,
        )
    )
    state = initial_state(compiled)
    public = legal_actions(state, compiled)

    semantic_actions = [
        action
        for action in public
        if getattr(action, "pattern_id", "").startswith("sem_")
        and getattr(action, "from_square", None) == Square(1, 1)
        and getattr(action, "to_square", None) == Square(2, 1)
    ]
    assert len(semantic_actions) == 2
    assert {a.pattern_id for a in semantic_actions} == {
        "sem_00_same_intent_zero",
        "sem_01_same_intent_one",
    }
    assert all(getattr(a, "geometry_id", None) for a in semantic_actions)
    assert len(set(semantic_actions)) == 2

    for action in semantic_actions:
        assert action_from_dict(action_to_dict(action)) == action

    children = [apply_action(state, action, compiled) for action in semantic_actions]
    keys = {
        semantic_position_key(child.position, compiled.support, compiled.ir.aux_slots)
        for child in children
    }
    assert len(keys) == 2


def test_runtime_binding_keeps_exact_geometry_and_path():
    from generic_chess.core.movement import LeapAtom, RayAtom
    from generic_chess.core.semantic_executor import SemanticEngine

    n = 5
    a = PieceType(
        "A", "A", (LeapAtom((2, 0)), RayAtom((1, 0), max_steps=2))
    )
    token = RuleAuxState("token", "square_or_none", "global", "persistent", None)
    special = RuleSemanticAction(
        name="same_target_different_paths",
        type_ids=("A",),
        geometry=RuleGeometrySpec(kind="legacy_atoms"),
        target_relation="empty",
        composition="augment",
        aux_state=(token,),
        effects=(
            RuleActionEffect(
                "move",
                from_ref=RuleSquareRef("source"),
                to_ref=RuleSquareRef("target"),
            ),
            RuleActionEffect(
                "set_token",
                slot_name="token",
                square_ref=RuleSquareRef("path_step", step=0),
            ),
        ),
        invariants=(RuleInvariant("own_anchor_safe"),),
    )
    engine = SemanticEngine(_compile(_semantic_ruleset((_king_type(), a), (special,), n=n)))
    s = engine.support
    pos = _position(
        s,
        [
            (1, 1, Piece(0, "A", "A")),
            (0, 0, Piece(0, "K", "K")),
            (4, 4, Piece(1, "K", "K")),
        ],
    )
    bindings = [
        x
        for x in engine.legal_actions(pos)
        if x.pattern_id == "sem_00_same_target_different_paths"
        and x.source == _idx(s, 1, 1)
        and x.target == _idx(s, 3, 1)
    ]
    assert len(bindings) == 1
    binding = bindings[0]
    assert getattr(binding, "geometry_id", None)
    child = engine.apply(pos, binding)
    slot = next(x for x in engine.ir.aux_slots if x.value_kind == "square_or_none")
    assert dict(child.aux_state)[(slot.slot_id, -1)] == (2, 1)


def test_semantic_key_canonicalizes_absent_and_explicit_defaults():
    from generic_chess.core.keys import semantic_position_key
    from generic_chess.core.semantic_executor import SemanticEngine
    from rule_semantics_ir_fixtures import castling_ruleset

    compiled = _compile(castling_ruleset())
    engine = SemanticEngine(compiled)
    sparse = engine._initial_position()
    slot = next(s for s in compiled.ir.aux_slots if s.scope == "per_owner")
    explicit = replace(
        sparse,
        aux_state=(
            ((slot.slot_id, 0), slot.initial),
            ((slot.slot_id, 1), slot.initial),
        ),
    )
    assert semantic_position_key(
        sparse, compiled.support, compiled.ir.aux_slots
    ) == semantic_position_key(
        explicit, compiled.support, compiled.ir.aux_slots
    )


def test_mixed_global_and_per_owner_aux_uses_one_canonical_key_shape():
    from generic_chess.core.movement import LeapAtom

    n = 5
    a = PieceType("A", "A", (LeapAtom((1, 0)),))
    action = RuleSemanticAction(
        name="mixed_aux",
        type_ids=("A",),
        geometry=RuleGeometrySpec(kind="leap", offset=(1, 0)),
        target_relation="empty",
        aux_state=(
            RuleAuxState("right", "bool", "per_owner", "persistent", 0),
            RuleAuxState("token", "square_or_none", "global", "persistent", None),
        ),
        effects=(
            RuleActionEffect(
                "move",
                from_ref=RuleSquareRef("source"),
                to_ref=RuleSquareRef("target"),
            ),
            RuleActionEffect("set_bool", slot_name="right", value=1),
            RuleActionEffect(
                "set_token", slot_name="token", square_ref=RuleSquareRef("target")
            ),
        ),
        invariants=(RuleInvariant("own_anchor_safe"),),
    )
    engine = _engine(_semantic_ruleset((_king_type(), a), (action,), n=n))
    s = engine.support
    pos = _position(
        s,
        [
            (1, 1, Piece(0, "A", "A")),
            (0, 0, Piece(0, "K", "K")),
            (4, 4, Piece(1, "K", "K")),
        ],
    )
    binding = next(
        x for x in engine.legal_actions(pos) if x.pattern_id == "sem_00_mixed_aux"
    )
    child = engine.apply(pos, binding)
    keys = [key for key, _ in child.aux_state]
    assert keys == sorted(keys)
    assert keys
    assert all(isinstance(key, tuple) and len(key) == 2 for key in keys)
    assert all(key[1] in (-1, 0, 1) for key in keys)


def test_per_owner_expire_next_turn_expires_creator_instance():
    from generic_chess.core.keys import semantic_position_key
    from generic_chess.core.movement import LeapAtom

    n = 5
    a = PieceType("A", "A", (LeapAtom((1, 0)),))
    mark = RuleSemanticAction(
        name="mark_ephemeral",
        type_ids=("A",),
        geometry=RuleGeometrySpec(kind="leap", offset=(1, 0)),
        target_relation="empty",
        aux_state=(
            RuleAuxState("temp", "bool", "per_owner", "expire_next_turn", 0),
        ),
        effects=(
            RuleActionEffect(
                "move",
                from_ref=RuleSquareRef("source"),
                to_ref=RuleSquareRef("target"),
            ),
            RuleActionEffect("set_bool", slot_name="temp", value=1),
        ),
        invariants=(RuleInvariant("own_anchor_safe"),),
    )
    engine = _engine(_semantic_ruleset((_king_type(), a), (mark,), n=n))
    s = engine.support
    pos = _position(
        s,
        [
            (1, 1, Piece(0, "A", "A")),
            (0, 0, Piece(0, "K", "K")),
            (4, 4, Piece(1, "K", "K")),
        ],
        side=0,
    )
    first = next(
        x for x in engine.legal_actions(pos) if x.pattern_id == "sem_00_mark_ephemeral"
    )
    child = engine.apply(pos, first)
    reply = next(x for x in engine.legal_actions(child) if x.actor_type == "K")
    grandchild = engine.apply(child, reply)
    no_aux = replace(grandchild, aux_state=())
    assert semantic_position_key(
        grandchild, engine.support, engine.ir.aux_slots
    ) == semantic_position_key(
        no_aux, engine.support, engine.ir.aux_slots
    )


def test_aux_slot_square_resolves_scope_and_implicit_default():
    from generic_chess.core.movement import LeapAtom

    n = 5
    a = PieceType("A", "A", (LeapAtom((1, 0)),))
    b = PieceType("B", "B", (LeapAtom((1, 0)),))
    square_slot = RuleAuxState(
        "mark", "square_or_none", "per_owner", "persistent", (2, 2)
    )
    guard = RuleStateGuard(
        aggregation="count",
        owner="any",
        type_ref=RuleTypeRef("any"),
        compare_field="base",
        promoted="any",
        location="board",
        spatial=RuleSpatialSelector(
            kind="exact",
            refs=(RuleSquareRef("aux_slot_square", slot_name="mark"),),
        ),
        comparison="eq",
        value=1,
    )
    action = RuleSemanticAction(
        name="uses_aux_square",
        type_ids=("A",),
        geometry=RuleGeometrySpec(kind="leap", offset=(1, 0)),
        target_relation="empty",
        aux_state=(square_slot,),
        state_guards=(guard,),
        effects=(
            RuleActionEffect(
                "move",
                from_ref=RuleSquareRef("source"),
                to_ref=RuleSquareRef("target"),
            ),
        ),
        invariants=(RuleInvariant("own_anchor_safe"),),
    )
    engine = _engine(_semantic_ruleset((_king_type(), a, b), (action,), n=n))
    s = engine.support
    pos = _position(
        s,
        [
            (1, 1, Piece(0, "A", "A")),
            (2, 2, Piece(1, "B", "B")),
            (0, 0, Piece(0, "K", "K")),
            (4, 4, Piece(1, "K", "K")),
        ],
        side=0,
        aux_state=(),
    )
    assert [
        x
        for x in engine.legal_actions(pos)
        if x.pattern_id == "sem_00_uses_aux_square"
    ]


def test_semantic_public_core_rejects_ruleset_mismatch():
    from generic_chess.core.errors import RuleSetMismatchError
    from generic_chess.core.movegen import legal_actions
    from generic_chess.core.transition import initial_state
    from rule_semantics_ir_fixtures import cannon_ruleset, castling_ruleset

    a = _compile(cannon_ruleset())
    b = _compile(castling_ruleset())
    state = initial_state(a)
    with pytest.raises(RuleSetMismatchError):
        legal_actions(state, b)


def test_semantic_legal_successors_matches_public_apply():
    from generic_chess.core.movegen import legal_actions
    from generic_chess.core.transition import apply_action, initial_state, legal_successors
    from rule_semantics_ir_fixtures import castling_ruleset

    compiled = _compile(castling_ruleset())
    state = initial_state(compiled)
    actions = legal_actions(state, compiled)
    successors = legal_successors(state, compiled)
    assert [action for action, _ in successors] == actions
    assert [child for _, child in successors] == [
        apply_action(state, action, compiled) for action in actions
    ]


def test_pseudo_attack_respects_type_geometry_binding():
    from generic_chess.core.movement import LeapAtom

    n = 5
    a = PieceType("A", "A", (LeapAtom((1, 0)),))
    b = PieceType("B", "B", (LeapAtom((0, 1)),))
    capture = RuleSemanticAction(
        name="multi_capture",
        type_ids=("A", "B"),
        geometry=RuleGeometrySpec(kind="legacy_atoms", atom_kind="leap"),
        target_relation="enemy",
        composition="augment",
        effects=(
            RuleActionEffect(
                "remove",
                square_ref=RuleSquareRef("target"),
                piece_owner="opponent",
                piece_type_ref=RuleTypeRef("any"),
                disposition="capture_to_hand",
            ),
            RuleActionEffect(
                "move",
                from_ref=RuleSquareRef("source"),
                to_ref=RuleSquareRef("target"),
            ),
        ),
        invariants=(RuleInvariant("own_anchor_safe"),),
    )
    engine = _engine(_semantic_ruleset((_king_type(), a, b), (capture,), n=n))
    s = engine.support
    pos = _position(
        s,
        [
            (2, 2, Piece(0, "A", "A")),
            (2, 3, Piece(1, "K", "K")),
            (0, 0, Piece(0, "K", "K")),
        ],
        side=1,
    )
    assert engine.is_square_attacked(pos, _idx(s, 2, 3), 0) is False


def test_conditional_capture_guard_controls_pseudo_attack():
    from generic_chess.core.movement import LeapAtom

    n = 5
    a = PieceType("A", "A", (LeapAtom((1, 0)),))
    permit = RuleAuxState("permit", "bool", "global", "persistent", 0)
    capture = RuleSemanticAction(
        name="conditional_capture",
        type_ids=("A",),
        geometry=RuleGeometrySpec(kind="legacy_atoms", atom_kind="leap"),
        target_relation="enemy",
        composition="replace_legacy",
        replace_selector=RuleReplaceSelector(
            type_ids=("A",),
            action_family="board",
            target_relation="enemy",
            geometry_kind="leap",
            replace_all_matching=True,
        ),
        aux_state=(permit,),
        slot_guards=(RuleSlotGuard("permit", comparison="eq", value=1),),
        effects=(
            RuleActionEffect(
                "remove",
                square_ref=RuleSquareRef("target"),
                piece_owner="opponent",
                piece_type_ref=RuleTypeRef("any"),
                disposition="capture_to_hand",
            ),
            RuleActionEffect(
                "move",
                from_ref=RuleSquareRef("source"),
                to_ref=RuleSquareRef("target"),
            ),
        ),
        invariants=(RuleInvariant("own_anchor_safe"),),
    )
    engine = _engine(_semantic_ruleset((_king_type(), a), (capture,), n=n))
    s = engine.support
    base = _position(
        s,
        [
            (1, 1, Piece(0, "A", "A")),
            (2, 1, Piece(1, "K", "K")),
            (0, 0, Piece(0, "K", "K")),
        ],
        side=1,
    )
    slot = next(x for x in engine.ir.aux_slots if x.value_kind == "bool")
    assert engine.is_square_attacked(base, _idx(s, 2, 1), 0) is False
    allowed = replace(base, aux_state=(((slot.slot_id, -1), 1),))
    assert engine.is_square_attacked(allowed, _idx(s, 2, 1), 0) is True


def test_blocker_owner_filter_uses_attacker_perspective():
    from generic_chess.core.movement import RayAtom

    n = 5
    a = PieceType("A", "A", (RayAtom((1, 0)),))
    capture = RuleSemanticAction(
        name="screen_is_self",
        type_ids=("A",),
        geometry=RuleGeometrySpec(kind="legacy_atoms", atom_kind="ray"),
        target_relation="enemy",
        composition="replace_legacy",
        replace_selector=RuleReplaceSelector(
            type_ids=("A",),
            action_family="board",
            target_relation="enemy",
            geometry_kind="ray",
            replace_all_matching=True,
        ),
        path_constraints=(
            RulePathConstraint("path_count_eq", count=1),
            RulePathConstraint("path_first_blocker_owner", owner_filter="self"),
        ),
        effects=(
            RuleActionEffect(
                "remove",
                square_ref=RuleSquareRef("target"),
                piece_owner="opponent",
                piece_type_ref=RuleTypeRef("any"),
                disposition="capture_to_hand",
            ),
            RuleActionEffect(
                "move",
                from_ref=RuleSquareRef("source"),
                to_ref=RuleSquareRef("target"),
            ),
        ),
        invariants=(RuleInvariant("own_anchor_safe"),),
    )
    engine = _engine(_semantic_ruleset((_king_type(), a), (capture,), n=n))
    s = engine.support
    pos = _position(
        s,
        [
            (0, 1, Piece(0, "A", "A")),
            (1, 1, Piece(0, "A", "A")),
            (2, 1, Piece(1, "K", "K")),
            (0, 0, Piece(0, "K", "K")),
        ],
        side=1,
    )
    assert engine.is_square_attacked(pos, _idx(s, 2, 1), 0) is True


def test_action_relative_typeref_is_actor_bound_inside_effects():
    from generic_chess.core.movement import LeapAtom

    n = 5
    a = PieceType("A", "A", (LeapAtom((1, 0)),))
    action = RuleSemanticAction(
        name="reassert_actor_current",
        type_ids=("A",),
        geometry=RuleGeometrySpec(kind="leap", offset=(1, 0)),
        target_relation="empty",
        effects=(
            RuleActionEffect(
                "move",
                from_ref=RuleSquareRef("source"),
                to_ref=RuleSquareRef("target"),
            ),
            RuleActionEffect(
                "set_current_type",
                square_ref=RuleSquareRef("target"),
                type_ref=RuleTypeRef("action_current"),
            ),
        ),
        invariants=(RuleInvariant("own_anchor_safe"),),
    )
    engine = _engine(_semantic_ruleset((_king_type(), a), (action,), n=n))
    s = engine.support
    pos = _position(
        s,
        [
            (1, 1, Piece(0, "A", "A")),
            (0, 0, Piece(0, "K", "K")),
            (4, 4, Piece(1, "K", "K")),
        ],
    )
    binding = next(
        x
        for x in engine.legal_actions(pos)
        if x.pattern_id == "sem_00_reassert_actor_current"
    )
    child = engine.apply(pos, binding)
    moved = child.board[_idx(s, 2, 1)]
    assert moved is not None and moved.current_type_id == "A"


def test_en_passant_requires_real_matching_opponent_victim():
    from rule_semantics_ir_fixtures import en_passant_ruleset

    engine = _engine(en_passant_ruleset())
    s = engine.support
    pattern = next(
        p
        for p in engine.ir.patterns
        if p.pattern_id == "sem_01_token_adjacent_capture_removes_off_target"
    )
    remove = next(e for e in pattern.effects if e.kind == "remove")
    assert remove.piece_owner == "opponent"
    assert remove.piece_type_ref is not None
    assert remove.piece_type_ref.kind == "action_base"

    pos = _position(
        s,
        [
            (4, 1, Piece(0, "P", "P")),
            (3, 3, Piece(1, "P", "P")),
            (4, 0, Piece(0, "K", "K")),
            (3, 7, Piece(1, "K", "K")),
        ],
        side=0,
    )
    double = next(
        a
        for a in engine.legal_actions(pos)
        if a.pattern_id == "sem_00_double_step_creates_token"
    )
    child = engine.apply(pos, double)

    board = list(child.board)
    board[_idx(s, 4, 3)] = None
    missing = replace(child, board=tuple(board))
    assert not [
        a
        for a in engine.legal_actions(missing)
        if a.pattern_id.startswith("sem_")
        and "capture" in a.pattern_id
        and a.target == _idx(s, 4, 2)
    ]

    board[_idx(s, 4, 3)] = Piece(1, "P", "P")
    friendly = replace(child, board=tuple(board))
    assert not [
        a
        for a in engine.legal_actions(friendly)
        if a.pattern_id.startswith("sem_")
        and "capture" in a.pattern_id
        and a.target == _idx(s, 4, 2)
    ]


def test_compound_effect_cannot_overwrite_unremoved_destination_piece():
    from generic_chess.core.movement import LeapAtom

    n = 5
    atom = (LeapAtom((1, 0)),)
    a = PieceType("A", "A", atom)
    b = PieceType("B", "B", atom)
    c = PieceType("C", "C", atom)
    action = RuleSemanticAction(
        name="compound_no_overwrite",
        type_ids=("A",),
        geometry=RuleGeometrySpec(kind="leap", offset=(1, 0)),
        target_relation="empty",
        effects=(
            RuleActionEffect(
                "move",
                from_ref=RuleSquareRef("source"),
                to_ref=RuleSquareRef("target"),
            ),
            RuleActionEffect(
                "shift",
                from_ref=RuleSquareRef(
                    "offset_from_source", offset=(2, 0), owner_relative=True
                ),
                to_ref=RuleSquareRef(
                    "offset_from_source", offset=(2, 1), owner_relative=True
                ),
                piece_owner="self",
                piece_type_ref=RuleTypeRef("explicit", "B"),
            ),
        ),
        invariants=(RuleInvariant("own_anchor_safe"),),
    )
    engine = _engine(_semantic_ruleset((_king_type(), a, b, c), (action,), n=n))
    s = engine.support
    pos = _position(
        s,
        [
            (1, 1, Piece(0, "A", "A")),
            (3, 1, Piece(0, "B", "B")),
            (3, 2, Piece(0, "C", "C")),
            (0, 0, Piece(0, "K", "K")),
            (4, 4, Piece(1, "K", "K")),
        ],
    )
    assert not [
        x
        for x in engine.legal_actions(pos)
        if x.pattern_id == "sem_00_compound_no_overwrite"
    ]
