"""F24C certification for victim-specific mixed mechanics.

The fixture deliberately uses opaque type IDs.  Every capture disposition is
selected by a target-local base-family guard; the capturing family is only an
actor selector.
"""

from __future__ import annotations

from dataclasses import replace

import pytest

from generic_chess.core.coordinates import Square
from generic_chess.core.keys import position_key
from generic_chess.core.movement import LeapAtom, RayAtom
from generic_chess.core.pieces import Piece, PieceType
from generic_chess.core.position import GameState, Hands, Position
from generic_chess.core.search_runtime import SearchPathRuntime
from generic_chess.core.semantic_executor import semantic_engine_for
from generic_chess.core.terminal import TerminalResult, TerminalStatus
from generic_chess.ai.alphabeta.ordering import MoveOrderer, StagedMovePicker
from generic_chess.ai.alphabeta.quiescence import classify_noisy
from generic_chess.ai.alphabeta.statistics import SearchStatistics
from generic_chess.ai.alphabeta.tuning import SearchTuning
from generic_chess.core.transition import legal_successors
from generic_chess.rules.compiler import compile_semantic_ruleset
from generic_chess.rules.schema import (
    RuleActionEffect,
    RuleGeometrySpec,
    RuleInvariant,
    RulePathConstraint,
    RuleReplaceSelector,
    RuleSemanticAction,
    RuleSet,
    RuleSpatialSelector,
    RuleSquareRef,
    RuleStateGuard,
    RuleTypeRef,
    compute_fingerprint,
    ruleset_from_dict,
    ruleset_to_dict,
)


N = 7
A0, A1, B0, B1, C0, H0 = "A0", "A1", "B0", "B1", "C0", "H0"
LEAP = (LeapAtom((1, 0)),)
RAY = (RayAtom((1, 0), max_steps=4),)


def _ref(kind: str, **kwargs):
    return RuleSquareRef(kind=kind, **kwargs)


def _selector(actor: str, relation: str, geometry: str):
    return RuleReplaceSelector(
        type_ids=(actor,),
        action_family="board",
        target_relation=relation,
        geometry_kind=geometry,
        replace_all_matching=True,
    )


def _victim_guard(victim_base: str):
    return RuleStateGuard(
        aggregation="exists",
        owner="opponent",
        type_ref=RuleTypeRef("explicit", victim_base),
        compare_field="base",
        promoted="any",
        location="board",
        spatial=RuleSpatialSelector(kind="exact", refs=(_ref("target"),)),
        comparison="eq",
        value=1,
    )


def _capture(actor: str, victim_base: str, geometry: RuleGeometrySpec, kind: str):
    disposition = "capture_to_hand" if victim_base == A0 else "remove_from_game"
    return RuleSemanticAction(
        name=f"capture_{actor}_{victim_base}_{kind}",
        type_ids=(actor,),
        geometry=geometry,
        target_relation="enemy",
        composition="replace_legacy",
        replace_selector=_selector(actor, "enemy", kind),
        state_guards=(_victim_guard(victim_base),),
        effects=(
            RuleActionEffect(
                "remove",
                square_ref=_ref("target"),
                piece_owner="opponent",
                piece_type_ref=RuleTypeRef("any"),
                disposition=disposition,
            ),
            RuleActionEffect("move", from_ref=_ref("source"), to_ref=_ref("target")),
        ),
        invariants=(RuleInvariant("own_anchor_safe"),),
    )


def _move(actor: str, *, promotion: bool = False):
    return RuleSemanticAction(
        name=f"advance_{actor}",
        type_ids=(actor,),
        geometry=RuleGeometrySpec(kind="legacy_atoms", atom_kind="leap"),
        target_relation="empty",
        composition="replace_legacy",
        replace_selector=_selector(actor, "empty", "leap"),
        promotion_mode="inherit_compiled_masks" if promotion else "none",
        effects=(RuleActionEffect("move", from_ref=_ref("source"), to_ref=_ref("target")),),
        invariants=(RuleInvariant("own_anchor_safe"),),
    )


def _mixed_ruleset() -> RuleSet:
    anchor_atoms = tuple(
        LeapAtom((df, dr))
        for df in (-1, 0, 1)
        for dr in (-1, 0, 1)
        if (df, dr) != (0, 0)
    )
    types = (
        PieceType(A0, "family-a", LEAP, is_promotable=True, promotion_target_ids=(A1,)),
        PieceType(A1, "family-a-plus", LEAP),
        PieceType(B0, "family-b", LEAP, is_promotable=True, promotion_target_ids=(B1,)),
        PieceType(B1, "family-b-plus", LEAP),
        PieceType(C0, "family-c", LEAP + RAY),
        PieceType(H0, "anchor", anchor_atoms, is_anchor=True),
    )
    mask = (True,) * (N * N)
    promo_a = (Square(4, 4), Square(5, 4))
    promo_b = (Square(4, 3), Square(5, 3))
    actions = [
        *(_capture(actor, victim, RuleGeometrySpec(kind="legacy_atoms", atom_kind="leap"), "leap")
          for actor in (A0, B0, C0)
          for victim in (A0, B0, C0)),
        _move(A0, promotion=True),
        _move(B0, promotion=True),
        _move(C0),
        RuleSemanticAction(
            name="drop_A0",
            type_ids=(A0,),
            geometry=RuleGeometrySpec(kind="drop"),
            target_relation="empty",
            composition="replace_legacy",
            replace_selector=RuleReplaceSelector(
                type_ids=(A0,), action_family="drop", target_relation="empty"
            ),
            effects=(
                RuleActionEffect("remove_from_hand", piece_type_ref=RuleTypeRef("action_base")),
                RuleActionEffect("place", to_ref=_ref("target"), piece_type_ref=RuleTypeRef("action_base")),
            ),
            invariants=(RuleInvariant("own_anchor_safe"),),
        ),
        RuleSemanticAction(
            name="capture_C0_C0_path",
            type_ids=(C0,),
            geometry=RuleGeometrySpec(kind="ray", direction=(1, 0), min_steps=1, max_steps=4),
            target_relation="enemy",
            composition="replace_legacy",
            replace_selector=_selector(C0, "enemy", "ray"),
            state_guards=(_victim_guard(C0),),
            path_constraints=(RulePathConstraint("path_count_eq", count=1),),
            effects=(
                RuleActionEffect(
                    "remove", square_ref=_ref("target"), piece_owner="opponent",
                    piece_type_ref=RuleTypeRef("any"), disposition="remove_from_game",
                ),
                RuleActionEffect("move", from_ref=_ref("source"), to_ref=_ref("target")),
            ),
            invariants=(RuleInvariant("own_anchor_safe"),),
        ),
    ]
    rows = [[None for _ in range(N)] for _ in range(N)]
    rows[0][0] = Piece(0, H0, H0)
    rows[N - 1][N - 1] = Piece(1, H0, H0)
    return RuleSet(
        schema_version=1,
        board_size=N,
        piece_types=types,
        initial_position=tuple(tuple(row) for row in rows),
        drop_allowed={
            A0: (mask, mask),
            A1: ((False,) * (N * N),) * 2,
            B0: ((False,) * (N * N),) * 2,
            B1: ((False,) * (N * N),) * 2,
            C0: ((False,) * (N * N),) * 2,
        },
        promotion_allowed={A0: (frozenset((promo_a,)),) * 2, B0: (frozenset((promo_b,)),) * 2},
        promotion_forced={A0: (frozenset(),) * 2, B0: (frozenset(),) * 2},
        semantic_actions=tuple(actions),
        max_ply=128,
        repetition_limit=3,
        metadata={"display_label": "F24C opaque mixed certification"},
    )


def _compiled():
    return compile_semantic_ruleset(_mixed_ruleset())


def _rename_ruleset(ruleset, mapping):
    def ref(value):
        if value is None or value.kind != "explicit":
            return value
        return replace(value, type_id=mapping[value.type_id])

    def piece(value):
        if value is None:
            return None
        return replace(
            value,
            base_type_id=mapping[value.base_type_id],
            current_type_id=mapping[value.current_type_id],
        )

    renamed_types = tuple(
        replace(
            value,
            type_id=mapping[value.type_id],
            promotion_target_ids=tuple(mapping.get(tid, tid) for tid in value.promotion_target_ids),
        )
        for value in ruleset.piece_types
    )
    renamed_actions = []
    for action in ruleset.semantic_actions:
        selector = action.replace_selector
        if selector is not None:
            selector = replace(selector, type_ids=tuple(mapping[tid] for tid in selector.type_ids))
        guards = tuple(replace(g, type_ref=ref(g.type_ref)) for g in action.state_guards)
        effects = tuple(replace(e, piece_type_ref=ref(e.piece_type_ref), type_ref=ref(e.type_ref)) for e in action.effects)
        renamed_actions.append(
            replace(
                action,
                type_ids=tuple(mapping[tid] for tid in action.type_ids),
                replace_selector=selector,
                state_guards=guards,
                effects=effects,
                explicit_promotion_type=mapping.get(action.explicit_promotion_type, action.explicit_promotion_type),
            )
        )
    return replace(
        ruleset,
        piece_types=renamed_types,
        initial_position=tuple(tuple(piece(cell) for cell in row) for row in ruleset.initial_position),
        drop_allowed={mapping[tid]: value for tid, value in ruleset.drop_allowed.items()},
        promotion_allowed={mapping[tid]: value for tid, value in ruleset.promotion_allowed.items()},
        promotion_forced={mapping[tid]: value for tid, value in ruleset.promotion_forced.items()},
        semantic_actions=tuple(renamed_actions),
    )


def _position(compiled, entries, *, side=0, hands=((), ())):
    board = [None] * (N * N)
    for file, rank, piece in entries:
        board[rank * N + file] = piece
    return Position(
        board=tuple(board),
        hands=(Hands(tuple(hands[0])), Hands(tuple(hands[1]))),
        side_to_move=side,
        ruleset_fingerprint=compiled.ruleset_fingerprint,
    )


def _actions(engine, position, *, contains: str | None = None):
    actions = engine.legal_actions(position)
    if contains is not None:
        actions = tuple(a for a in actions if contains in a.pattern_id)
    return actions


def test_victim_disposition_is_target_family_sensitive_across_capturers():
    compiled = _compiled()
    engine = semantic_engine_for(compiled)
    anchors = [(0, 0, Piece(0, H0, H0)), (6, 6, Piece(1, H0, H0))]
    for actor in (A0, B0, C0):
        for victim, current, promoted in ((A0, A0, False), (A0, A1, True), (B0, B0, False), (B0, B1, True), (C0, C0, False)):
            actor_piece = Piece(0, actor, actor)
            victim_piece = Piece(1, victim, current, promoted=promoted)
            pos = _position(compiled, [(1, 1, actor_piece), (2, 1, victim_piece), *anchors])
            candidates = tuple(a for a in engine.legal_actions(pos) if a.source == 8 and a.target == 9 and "capture" in a.pattern_id)
            assert len(candidates) == 1, (actor, victim, current, candidates)
            child = engine.apply(pos, candidates[0])
            assert child.board[9].base_type_id == actor
            if victim == A0:
                assert child.hands[0].count(A0) == 1
            else:
                assert child.hands[0].total() == 0


def test_simultaneous_root_has_active_capture_drop_promotion_and_path():
    compiled = _compiled()
    engine = semantic_engine_for(compiled)
    pos = _position(
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
    actions = engine.legal_actions(pos)
    assert any("capture_A0_A0" in a.pattern_id for a in actions)
    assert any("capture_B0_B0" in a.pattern_id for a in actions)
    assert any("capture_C0_C0_path" in a.pattern_id for a in actions)
    assert any(a.pattern_id.endswith("drop_A0") for a in actions)
    assert any(a.promotion_target_id == A1 for a in actions)
    assert any(a.promotion_target_id == B1 for a in actions)
    assert len({(a.pattern_id, a.source, a.target, a.promotion_target_id) for a in actions}) == len(actions)
    assert not any("capture" in a.pattern_id and not a.pattern_id.startswith("sem_") for a in actions)
    promotion = next(a for a in actions if a.promotion_target_id == A1)
    promoted = engine.apply(pos, promotion).board[promotion.target]
    assert promoted is not None and promoted.base_type_id == A0 and promoted.current_type_id == A1 and promoted.promoted
    promotion_b = next(a for a in actions if a.promotion_target_id == B1)
    promoted_b = engine.apply(pos, promotion_b).board[promotion_b.target]
    assert promoted_b is not None and promoted_b.base_type_id == B0 and promoted_b.current_type_id == B1 and promoted_b.promoted
    assert not any(a.actor_type == C0 and a.promotion_target_id is not None for a in actions)
    drop = next(a for a in actions if a.pattern_id.endswith("drop_A0"))
    dropped = engine.apply(pos, drop)
    assert dropped.board[drop.target].base_type_id == A0
    assert dropped.hands[0].count(A0) == 0
    imported_non_droppable = _position(compiled, [(0, 0, Piece(0, H0, H0)), (6, 6, Piece(1, H0, H0))], hands=([(B0, 1), (C0, 1)], ()))
    assert not any(a.pattern_id.endswith("drop_A0") for a in engine.legal_actions(imported_non_droppable))


@pytest.mark.parametrize("blockers, expected", [(0, False), (1, True), (2, False)])
def test_family_c_path_predicate_is_exact(blockers, expected):
    compiled = _compiled()
    engine = semantic_engine_for(compiled)
    entries = [(1, 1, Piece(0, C0, C0)), (4, 1, Piece(1, C0, C0)), (0, 0, Piece(0, H0, H0)), (6, 6, Piece(1, H0, H0))]
    entries += [(2, 1, Piece(0, A0, A0)), (3, 1, Piece(0, B0, B0))][:blockers]
    pos = _position(compiled, entries)
    path_actions = tuple(a for a in engine.legal_actions(pos) if a.pattern_id.endswith("capture_C0_C0_path") and a.source == 8 and a.target == 11)
    assert bool(path_actions) is expected


def test_roundtrip_fingerprint_and_runtime_push_pop_are_stable():
    ruleset = _mixed_ruleset()
    payload = ruleset_to_dict(ruleset)
    rebuilt = ruleset_from_dict(payload)
    assert compute_fingerprint(rebuilt) == compute_fingerprint(ruleset)
    assert compute_fingerprint(replace(ruleset, metadata={"different": True})) == compute_fingerprint(ruleset)
    compiled = compile_semantic_ruleset(rebuilt)
    engine = semantic_engine_for(compiled)
    pos = _position(compiled, [(1, 1, Piece(0, A0, A0)), (2, 1, Piece(1, A0, A0)), (0, 0, Piece(0, H0, H0)), (6, 6, Piece(1, H0, H0))])
    key = position_key(pos, compiled)
    state = GameState(pos, 0, ((key, 1),), TerminalResult(TerminalStatus.ONGOING))
    runtime = SearchPathRuntime(state, compiled)
    capture = next(a for a in runtime.legal_actions() if "capture_A0_A0" in a.pattern_id)
    before = runtime.position
    runtime.push(capture)
    assert runtime.position.hands[0].count(A0) == 1
    runtime.pop()
    assert runtime.position == before
    runtime.assert_balanced()
    with pytest.raises(Exception):
        runtime.push(replace(capture, target=0))
    assert runtime.position == before
    runtime.assert_balanced()


def test_type_id_renaming_preserves_action_shapes_and_disposition():
    mapping = {A0: "RA0", A1: "RA1", B0: "RB0", B1: "RB1", C0: "RC0", H0: "RH0"}
    original = _compiled()
    renamed = compile_semantic_ruleset(_rename_ruleset(_mixed_ruleset(), mapping))
    original_engine = semantic_engine_for(original)
    renamed_engine = semantic_engine_for(renamed)
    original_pos = _position(original, [(1, 1, Piece(0, A0, A0)), (2, 1, Piece(1, A0, A0)), (0, 0, Piece(0, H0, H0)), (6, 6, Piece(1, H0, H0))])
    renamed_pos = _position(renamed, [(1, 1, Piece(0, mapping[A0], mapping[A0])), (2, 1, Piece(1, mapping[A0], mapping[A0])), (0, 0, Piece(0, mapping[H0], mapping[H0])), (6, 6, Piece(1, mapping[H0], mapping[H0]))])
    original_capture = next(a for a in original_engine.legal_actions(original_pos) if "capture_A0_A0" in a.pattern_id)
    renamed_capture = next(a for a in renamed_engine.legal_actions(renamed_pos) if "capture_A0_A0" in a.pattern_id)
    assert (original_capture.source, original_capture.target, original_capture.promotion_target_id) == (renamed_capture.source, renamed_capture.target, renamed_capture.promotion_target_id)
    child = renamed_engine.apply(renamed_pos, renamed_capture)
    assert child.hands[0].count(mapping[A0]) == 1


def test_native_mode_is_recorded_without_changing_python_authority():
    from generic_chess.ai.alphabeta.native_legality import NativeSemanticLegalityProvider

    assert NativeSemanticLegalityProvider.try_create(_compiled()) is not None


def test_mixed_semantic_capture_promotion_and_drop_keep_f24b_tactical_parity():
    compiled = _compiled()
    engine = semantic_engine_for(compiled)
    pos = _position(
        compiled,
        [(1, 1, Piece(0, A0, A0)), (2, 1, Piece(1, A0, A0)),
         (4, 4, Piece(0, A0, A0)), (4, 3, Piece(0, B0, B0)),
         (0, 0, Piece(0, H0, H0)), (6, 6, Piece(1, H0, H0))],
        hands=([(A0, 1)], ()),
    )
    key = position_key(pos, compiled)
    state = GameState(pos, 0, ((key, 1),), TerminalResult(TerminalStatus.ONGOING))
    successors = legal_successors(state, compiled)
    capture, capture_child = next((a, child) for a, child in successors if "capture_A0_A0" in a.pattern_id)
    promotion, promotion_child = next((a, child) for a, child in successors if a.promotion_target_id == A1)
    drop, drop_child = next((a, child) for a, child in successors if a.pattern_id.endswith("drop_A0"))
    stats = SearchStatistics()
    assert classify_noisy(state, [(capture, capture_child)], compiled, stats) == [capture]
    assert stats.capture_qactions == 1
    stats = SearchStatistics()
    assert classify_noisy(state, [(promotion, promotion_child)], compiled, stats) == [promotion]
    assert stats.promotion_qactions == 1
    stats = SearchStatistics()
    assert classify_noisy(state, [(drop, drop_child)], compiled, stats) == []
    assert stats.nonchecking_drop_excluded == 1

    class _OrderingEvaluator:
        def capture_order_value(self, _mover, _victim):
            return 1

        def type_value(self, _type_id):
            return 1

    orderer = MoveOrderer()
    ordered = orderer.order(state, [promotion, capture], _OrderingEvaluator(), 1, None, None, SearchTuning())
    assert ordered[0] is capture and ordered[1] is promotion
    picker_stats = SearchStatistics()
    staged = list(StagedMovePicker(state, [promotion, capture], _OrderingEvaluator(), 1, None, None, orderer, SearchTuning(), picker_stats))
    assert staged == [capture, promotion]
    assert picker_stats.move_picker_yielded_by_stage == {"good_capture": 1, "promotion": 1}
