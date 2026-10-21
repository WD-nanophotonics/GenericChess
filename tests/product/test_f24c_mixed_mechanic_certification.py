"""F24C certification for victim-specific mixed mechanics.

The fixture deliberately uses opaque type IDs.  Every capture disposition is
selected by a target-local base-family guard; the capturing family is only an
actor selector.
"""

from __future__ import annotations

from dataclasses import replace

import pytest

from generic_chess.core.actions import SemanticBoardMove, SemanticDropMove
from generic_chess.core.coordinates import Square
from generic_chess.core.keys import position_key
from generic_chess.core.movement import LeapAtom, RayAtom
from generic_chess.core.pieces import Piece, PieceType
from generic_chess.core.position import GameState, Hands, Position
from generic_chess.core.movegen import legal_actions
from generic_chess.core.search_runtime import SearchPathRuntime
from generic_chess.core.semantic_executor import semantic_engine_for
from generic_chess.core.terminal import TerminalResult, TerminalStatus
from generic_chess.ai.alphabeta.ordering import MoveOrderer, StagedMovePicker
from generic_chess.ai.alphabeta.quiescence import classify_noisy
from generic_chess.ai.alphabeta.statistics import SearchStatistics
from generic_chess.ai.alphabeta.tuning import SearchTuning
from generic_chess.core.transition import legal_successors
from generic_chess.core.transition import apply_action
from generic_chess.ai.alphabeta.player import AlphaBetaPlayer
from generic_chess.ai.limits import SearchLimits
from generic_chess.session.session import GameSession
from generic_chess.session.serialization import deserialize_game_record, serialize_game_record
from generic_chess.rules.compiler import compile_ruleset_for_execution, compile_semantic_ruleset
from generic_chess.rules.serialization import deserialize_ruleset, serialize_ruleset
from generic_chess.rules.schema import (
    RuleActionEffect,
    RuleAuxState,
    RuleGeometrySpec,
    RuleInvariant,
    RulePathConstraint,
    RuleReplaceSelector,
    RuleSemanticAction,
    RuleSlotGuard,
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


def test_public_search_preserves_promotion_capture_to_hand_then_drop():
    rules = _mixed_ruleset()
    rows = [[None for _ in range(N)] for _ in range(N)]
    for file, rank, piece in (
        (0, 0, Piece(0, H0, H0)),
        (6, 6, Piece(1, H0, H0)),
        (4, 4, Piece(0, A0, A0)),
        (6, 4, Piece(1, B0, B0)),
        (0, 2, Piece(0, C0, C0)),
    ):
        rows[rank][file] = piece
    compiled = compile_semantic_ruleset(
        replace(rules, initial_position=tuple(tuple(row) for row in rows))
    )
    session = GameSession(compiled)

    def target_index(action):
        if hasattr(action, "target"):
            return action.target
        return action.to_square.rank * N + action.to_square.file

    def submit_one(predicate):
        candidates = tuple(action for action in session.legal_actions() if predicate(action))
        assert len(candidates) == 1, candidates
        session.submit(candidates[0])
        return candidates[0]

    class PreferPromotedA1:
        def evaluate(self, state):
            promoted = any(
                piece is not None and piece.owner == 0
                and piece.current_type_id == A1 and piece.promoted
                for piece in state.position.board
            )
            return -10_000 if promoted else 10_000

    promotion_decision = AlphaBetaPlayer(
        compiled, evaluator_override=PreferPromotedA1(), use_disk_cache=False
    ).choose_action(
        session,
        SearchLimits(
            max_depth=1, max_nodes=4096,
            quiescence_max_depth=0, quiescence_hard_max_depth=0,
        ),
    )
    assert isinstance(promotion_decision.action, SemanticBoardMove)
    assert promotion_decision.action.promotion_target_id == A1
    assert promotion_decision.principal_variation[0] == promotion_decision.action
    promotion = promotion_decision.action
    expected_promotion = apply_action(session.state, promotion, compiled)
    session.submit(promotion)
    assert session.state == expected_promotion
    promoted = session.state.position.board[target_index(promotion)]
    assert (promoted.base_type_id, promoted.current_type_id, promoted.promoted) == (
        A0, A1, True
    )

    before_capture = session.state
    class PreferCapturedA0:
        def evaluate(self, state):
            captured = state.position.hands[1].count(A0) > 0
            return -10_000 if captured else 10_000

        def capture_order_value(self, _mover, _victim):
            return 0

    capture_player = AlphaBetaPlayer(
        compiled, evaluator_override=PreferCapturedA0(), use_disk_cache=False
    )
    assert capture_player.native_legality_provider is not None
    capture_limits = SearchLimits(
        max_depth=1, max_nodes=4096,
        quiescence_max_depth=0, quiescence_hard_max_depth=0,
    )
    capture_decision = capture_player.choose_action(session, capture_limits)
    core_capture_decision = AlphaBetaPlayer(
        compiled,
        evaluator_override=PreferCapturedA0(),
        use_native_semantic_legality=False,
        use_disk_cache=False,
    ).choose_action(session, capture_limits)
    assert session.state is before_capture
    assert (
        capture_decision.action,
        capture_decision.score,
        capture_decision.completed_depth,
        capture_decision.principal_variation,
        capture_decision.nodes,
    ) == (
        core_capture_decision.action,
        core_capture_decision.score,
        core_capture_decision.completed_depth,
        core_capture_decision.principal_variation,
        core_capture_decision.nodes,
    )
    assert capture_decision.native_legality_calls > 0
    assert capture_decision.native_legality_fallbacks == 0
    assert capture_decision.native_legality_operational_failures == 0
    assert core_capture_decision.native_legality_calls == 0
    assert isinstance(capture_decision.action, SemanticBoardMove)
    assert capture_decision.action.pattern_id.endswith("_capture_B0_A0_leap")
    assert capture_decision.action.actor_type_id == B0
    assert target_index(capture_decision.action) == target_index(promotion)
    assert capture_decision.principal_variation[0] == capture_decision.action
    expected_capture = apply_action(before_capture, capture_decision.action, compiled)
    assert expected_capture.position.hands[1].count(A0) == 1
    session.submit(capture_decision.action)
    assert session.state == expected_capture
    assert session.state.position.hands[1].count(A0) == 1

    submit_one(lambda action: "advance_C0" in getattr(action, "pattern_id", ""))
    before_drop = session.state
    class PreferDroppedA0:
        def evaluate(self, state):
            dropped = any(
                piece is not None and piece.owner == 1
                and piece.base_type_id == A0 and piece.current_type_id == A0
                for piece in state.position.board
            )
            return -10_000 if dropped else 10_000

    drop_player = AlphaBetaPlayer(
        compiled, evaluator_override=PreferDroppedA0(), use_disk_cache=False
    )
    assert drop_player.native_legality_provider is not None
    drop_decision = drop_player.choose_action(
        session,
        SearchLimits(
            max_depth=1, max_nodes=4096,
            quiescence_max_depth=0, quiescence_hard_max_depth=0,
        ),
    )
    core_drop_decision = AlphaBetaPlayer(
        compiled,
        evaluator_override=PreferDroppedA0(),
        use_native_semantic_legality=False,
        use_disk_cache=False,
    ).choose_action(
        session,
        SearchLimits(
            max_depth=1, max_nodes=4096,
            quiescence_max_depth=0, quiescence_hard_max_depth=0,
        ),
    )
    assert session.state is before_drop
    assert (
        drop_decision.action,
        drop_decision.score,
        drop_decision.completed_depth,
        drop_decision.principal_variation,
        drop_decision.nodes,
    ) == (
        core_drop_decision.action,
        core_drop_decision.score,
        core_drop_decision.completed_depth,
        core_drop_decision.principal_variation,
        core_drop_decision.nodes,
    )
    assert drop_decision.native_legality_calls > 0
    assert drop_decision.native_legality_fallbacks == 0
    assert drop_decision.native_legality_operational_failures == 0
    assert core_drop_decision.native_legality_calls == 0
    assert isinstance(drop_decision.action, SemanticDropMove)
    assert drop_decision.action.base_type_id == A0
    assert drop_decision.action.pattern_id.endswith("_drop_A0")
    assert drop_decision.principal_variation[0] == drop_decision.action
    expected_drop = apply_action(before_drop, drop_decision.action, compiled)
    assert expected_drop.position.hands[1].count(A0) == 0
    assert expected_drop.position.board[target_index(drop_decision.action)].base_type_id == A0
    session.submit(drop_decision.action)
    replayed = GameSession.replay(
        compiled,
        deserialize_game_record(serialize_game_record(session.to_record())),
    )
    assert replayed.state == session.state == expected_drop
    assert replayed.result == session.result

    assert session.state.position.hands[1].count(A0) == 0
    assert session.state.ply_count == 4
    assert len(session._search_witnesses) == 5

    class FlatEvaluator:
        def evaluate(self, _state):
            return 0

        def capture_order_value(self, _mover, _victim):
            return 0

        def type_value(self, _type_id):
            return 0

    limits = SearchLimits(
        max_depth=2,
        max_nodes=4096,
        quiescence_max_depth=0,
        quiescence_hard_max_depth=0,
    )
    native_requested = AlphaBetaPlayer(
        compiled, evaluator_override=FlatEvaluator(), use_disk_cache=False
    )
    core_only = AlphaBetaPlayer(
        compiled,
        evaluator_override=FlatEvaluator(),
        use_native_semantic_legality=False,
        use_disk_cache=False,
    )
    assert native_requested.native_legality_provider is not None
    native_decision = native_requested.choose_action(session, limits)
    core_decision = core_only.choose_action(session, limits)
    assert (
        native_decision.action,
        native_decision.score,
        native_decision.completed_depth,
        native_decision.principal_variation,
        native_decision.nodes,
    ) == (
        core_decision.action,
        core_decision.score,
        core_decision.completed_depth,
        core_decision.principal_variation,
        core_decision.nodes,
    )
    assert native_decision.completed_depth == 2
    assert native_decision.principal_variation[0] == native_decision.action


@pytest.mark.parametrize(
    "lifetime, expected_after_reply",
    (("persistent", 1), ("expire_next_turn", 0)),
)
def test_public_search_preserves_semantic_drop_with_aux_write_and_replay(
    lifetime, expected_after_reply,
):
    """Public search composes drop, aux lifetime, slot guard and path state."""
    rules = _mixed_ruleset()
    rows = [[None for _ in range(N)] for _ in range(N)]
    for file, rank, piece in (
        (0, 0, Piece(0, H0, H0)),
        (6, 6, Piece(1, H0, H0)),
        (4, 4, Piece(0, A0, A0)),
        (6, 4, Piece(1, B0, B0)),
        (0, 2, Piece(0, C0, C0)),
    ):
        rows[rank][file] = piece

    semantic_actions = []
    for action in rules.semantic_actions:
        if action.name == "drop_A0":
            action = replace(
                action,
                aux_state=(
                    RuleAuxState("drop_mark", "bool", "global", lifetime, 0),
                ),
                effects=action.effects + (
                    RuleActionEffect("set_bool", slot_name="drop_mark", value=1),
                ),
            )
        semantic_actions.append(action)
    semantic_actions.append(RuleSemanticAction(
        name="after_drop_C0",
        type_ids=(C0,),
        geometry=RuleGeometrySpec(kind="leap", offset=(-1, 0)),
        target_relation="empty",
        slot_guards=(RuleSlotGuard("drop_mark", comparison="eq", value=1),),
        aux_state=(RuleAuxState("reply_mark", "bool", "global", "persistent", 0),),
        effects=(RuleActionEffect(
            "move", from_ref=_ref("source"), to_ref=_ref("target")
        ), RuleActionEffect("set_bool", slot_name="reply_mark", value=1)),
        invariants=(RuleInvariant("own_anchor_safe"),),
    ))
    authored_rules = replace(
        rules,
        initial_position=tuple(tuple(row) for row in rows),
        semantic_actions=tuple(semantic_actions),
    )
    serialized = serialize_ruleset(authored_rules)
    restored_rules = deserialize_ruleset(serialized)
    assert restored_rules == authored_rules
    assert compute_fingerprint(restored_rules) == compute_fingerprint(authored_rules)
    # Match benchmark_alphabeta --ruleset's deserialize/compile route.
    compiled = compile_ruleset_for_execution(restored_rules)
    engine = semantic_engine_for(compiled)
    drop_slot = next(
        item for item in engine.ir.aux_slots if item.slot_id == 0
    )
    reply_slot = next(
        item for item in engine.ir.aux_slots if item.slot_id == 1
    )
    session = GameSession(compiled)

    def submit_one(predicate):
        matches = [action for action in session.legal_actions() if predicate(action)]
        assert len(matches) == 1, matches
        session.submit(matches[0])
        return matches[0]

    promotion = submit_one(
        lambda action: isinstance(action, SemanticBoardMove)
        and action.promotion_target_id == A1
    )
    capture = submit_one(
        lambda action: isinstance(action, SemanticBoardMove)
        and "capture_B0_A0_leap" in action.pattern_id
    )
    assert session.state.position.hands[1].count(A0) == 1
    advance = submit_one(
        lambda action: isinstance(action, SemanticBoardMove)
        and "advance_C0" in action.pattern_id
    )
    before_drop = session.state

    class PreferMarkedDrop:
        def evaluate(self, state):
            marked = dict(state.position.aux_state).get(
                (drop_slot.slot_id, -1), 0
            ) == 1
            placed = any(
                piece is not None and piece.owner == 1
                and piece.base_type_id == A0
                for piece in state.position.board
            )
            return -10_000 if marked and placed else 10_000

        def type_value(self, _piece_type):
            return 0

        def capture_order_value(self, _mover, _victim):
            return 0

    limits = SearchLimits(
        max_depth=1,
        max_nodes=4096,
        quiescence_max_depth=0,
        quiescence_hard_max_depth=0,
    )
    native_player = AlphaBetaPlayer(
        compiled, evaluator_override=PreferMarkedDrop(), use_disk_cache=False
    )
    core_player = AlphaBetaPlayer(
        compiled,
        evaluator_override=PreferMarkedDrop(),
        use_native_semantic_legality=False,
        use_disk_cache=False,
    )
    assert native_player.native_legality_provider is not None
    native = native_player.choose_action(session, limits)
    core = core_player.choose_action(session, limits)
    assert session.state is before_drop
    assert isinstance(native.action, SemanticDropMove)
    assert native.action.pattern_id.endswith("_drop_A0")
    assert (
        native.action,
        native.score,
        native.completed_depth,
        native.principal_variation,
        native.nodes,
    ) == (
        core.action,
        core.score,
        core.completed_depth,
        core.principal_variation,
        core.nodes,
    )
    assert native.native_legality_calls > 0
    assert native.native_legality_fallbacks == 0
    assert native.native_legality_operational_failures == 0

    expected = apply_action(before_drop, native.action, compiled)
    assert expected.position.hands[1].count(A0) == 0
    assert dict(expected.position.aux_state)[(drop_slot.slot_id, -1)] == 1
    square = native.action.to_square
    assert expected.position.board[square.rank * N + square.file].base_type_id == A0
    after_drop_actions = legal_actions(expected, compiled)
    without_flag_state = replace(
        expected, position=replace(expected.position, aux_state=())
    )
    without_flag_actions = legal_actions(without_flag_state, compiled)
    assert any(
        isinstance(action, SemanticBoardMove)
        and "after_drop_C0" in action.pattern_id
        for action in after_drop_actions
    )
    assert not any(
        isinstance(action, SemanticBoardMove)
        and "after_drop_C0" in action.pattern_id
        for action in without_flag_actions
    )
    session.submit(native.action)
    replayed = GameSession.replay(
        compiled,
        deserialize_game_record(serialize_game_record(session.to_record())),
    )
    assert session.state == replayed.state == expected
    assert session.state.ply_count == 4
    assert len(session._search_witnesses) == 5

    # Exercise the real product evaluator on the imported post-drop state as
    # well as the decision-forcing evaluators below. This is a legal-search
    # integration check only, not evidence about default price utility.
    default_post_drop = AlphaBetaPlayer(
        compiled, use_disk_cache=False
    ).choose_action(replayed, limits)
    assert default_post_drop.action in replayed.legal_actions()
    assert default_post_drop.completed_depth == 1
    assert default_post_drop.native_legality_calls > 0
    assert default_post_drop.native_legality_fallbacks == 0
    assert default_post_drop.native_legality_operational_failures == 0

    class PreferGuardedReply:
        def evaluate(self, state):
            marked = dict(state.position.aux_state).get(
                (reply_slot.slot_id, -1), 0
            ) == 1
            return -10_000 if marked else 10_000

        def type_value(self, _piece_type):
            return 0

        def capture_order_value(self, _mover, _victim):
            return 0

    native_reply_player = AlphaBetaPlayer(
        compiled, evaluator_override=PreferGuardedReply(), use_disk_cache=False
    )
    core_reply_player = AlphaBetaPlayer(
        compiled,
        evaluator_override=PreferGuardedReply(),
        use_native_semantic_legality=False,
        use_disk_cache=False,
    )
    native_reply = native_reply_player.choose_action(replayed, limits)
    core_reply = core_reply_player.choose_action(replayed, limits)
    assert isinstance(native_reply.action, SemanticBoardMove)
    assert "after_drop_C0" in native_reply.action.pattern_id
    assert (
        native_reply.action,
        native_reply.score,
        native_reply.completed_depth,
        native_reply.principal_variation,
        native_reply.nodes,
    ) == (
        core_reply.action,
        core_reply.score,
        core_reply.completed_depth,
        core_reply.principal_variation,
        core_reply.nodes,
    )
    assert native_reply.principal_variation[0] == native_reply.action
    assert native_reply.native_legality_calls > 0
    assert native_reply.native_legality_fallbacks == 0
    assert native_reply.native_legality_operational_failures == 0

    # The direct Native engine below also exercises this cap, but the public
    # AlphaBeta caller has two legality backends sharing Python search. Check
    # that the separate q-node expansion boundary reports the same abort and
    # leaves the imported session untouched through both public modes.
    for qnode_cap in (0, 1):
        public_q_limits = SearchLimits(
            max_depth=2,
            max_nodes=10_000,
            quiescence_max_depth=1,
            quiescence_hard_max_depth=2,
            quiescence_max_nodes=qnode_cap,
        )
        public_q_decisions = (
            native_reply_player.choose_action(replayed, public_q_limits),
            core_reply_player.choose_action(replayed, public_q_limits),
        )
        for decision in public_q_decisions:
            assert decision.action in replayed.legal_actions()
            assert decision.nodes + decision.qnodes <= 10_000
            assert decision.qsearch_budget_aborts > 0
            assert decision.termination_reason == "qsearch_budget"
            assert decision.completed_depth < public_q_limits.max_depth
            if decision.completed_depth == 0:
                assert decision.root_scan_used_fallback
                assert decision.principal_variation == ()
            else:
                assert not decision.root_scan_used_fallback
                assert decision.result_source == "main_iteration"
                # Default TT policy promises score/action, not a full PV.
                if decision.principal_variation:
                    assert decision.principal_variation[0] == decision.action
            assert replayed.state == expected

    # A zero deadline is a valid exhausted budget at the public API too. Both
    # legality backends must return the same kind of legal root fallback rather
    # than treating deadline exhaustion as terminal or leaking partial state.
    public_zero_time = SearchLimits(
        max_depth=2,
        max_nodes=10_000,
        max_time_seconds=0.0,
        quiescence_max_depth=1,
        quiescence_hard_max_depth=2,
    )
    public_time_decisions = (
        native_reply_player.choose_action(replayed, public_zero_time),
        core_reply_player.choose_action(replayed, public_zero_time),
    )
    for decision in public_time_decisions:
        assert decision.action in replayed.legal_actions()
        assert decision.nodes + decision.qnodes <= 10_000
        assert decision.completed_depth == 0
        assert decision.termination_reason == "time_limit"
        assert decision.root_scan_used_fallback
        assert decision.time_to_first_legal_action is not None
        assert 0 <= decision.time_to_first_legal_action <= decision.elapsed_seconds
        assert decision.time_to_first_completed_iteration is None
        assert replayed.state == expected

    # Distinguish the Core AlphaBeta caller above from the separate full Native
    # semantic-search API: this imported post-drop root carries the complete
    # action/aux/history state into the latter as well.
    from generic_chess.learning.arena import _engine_for
    from generic_chess.core.identity import position_identity_key
    from generic_chess.native.adapter import pack_semantic_search_position
    from generic_chess.native.mirror import snapshot_matches
    from generic_chess.native.semantic import snapshot as native_semantic_snapshot
    from generic_chess.native.semantic_engine import SemanticSearchEngine

    native_rules = native_player.native_legality_provider.native_rules
    assert native_rules.native_executable
    packed_root = pack_semantic_search_position(compiled, native_rules, replayed)
    native_root = native_semantic_snapshot(native_rules, packed_root)
    expected_history = tuple(
        tuple(
            int(position_identity_key(witness, compiled)[offset:offset + 16], 16)
            for offset in range(0, 64, 16)
        )
        for witness in replayed._search_witnesses
    )
    expected_events = tuple(
        (255 if record.actor < 0 else record.actor, int(bool(record.gave_check)))
        for record in replayed.state.history
    )
    assert native_root["history"] == expected_history
    assert native_root["history_events"] == expected_events
    assert native_root["history_exact"]
    assert native_root["history_events_exact"]
    assert snapshot_matches(
        native_root, replayed.state.position, native_rules, compiled
    )
    native_engine = _engine_for(compiled, native_rules, None, 0)
    assert isinstance(native_engine, SemanticSearchEngine)
    native_search = native_engine.search(replayed, limits)
    assert native_search.action in replayed.legal_actions()
    assert native_search.completed_depth == 1
    assert native_search.termination_reason == "completed"
    assert not native_search.used_fallback

    native_input = replayed.state
    native_qsearch = native_engine.search(
        replayed,
        SearchLimits(
            max_depth=2,
            max_nodes=10_000,
            max_time_seconds=5.0,
            quiescence_max_depth=1,
            quiescence_hard_max_depth=2,
        ),
    )
    assert native_qsearch.action in replayed.legal_actions()
    assert native_qsearch.nodes + native_qsearch.qnodes <= 10_000
    assert native_qsearch.completed_depth == 2
    assert native_qsearch.result_ordinary_qdepth == 1
    assert native_qsearch.result_check_hard_qdepth == 2
    assert native_qsearch.qnodes > 0
    assert native_qsearch.principal_variation
    assert native_qsearch.principal_variation[0] == native_qsearch.action
    q_pv_state = replayed.state
    for pv_action in native_qsearch.principal_variation:
        assert pv_action in legal_actions(q_pv_state, compiled)
        q_pv_state = apply_action(q_pv_state, pv_action, compiled)
    assert replayed.state == native_input

    # Confirm a retained Native TT can search this exact aux/history root
    # twice without changing the selected line or mutating its source session.
    native_tt_engine = _engine_for(compiled, native_rules, None, 1)
    cold_tt_search = native_tt_engine.search(
        replayed,
        SearchLimits(
            max_depth=2,
            max_nodes=10_000,
            max_time_seconds=5.0,
            quiescence_max_depth=1,
            quiescence_hard_max_depth=2,
        ),
    )
    warm_tt_search = native_tt_engine.search(
        replayed,
        SearchLimits(
            max_depth=2,
            max_nodes=10_000,
            max_time_seconds=5.0,
            quiescence_max_depth=1,
            quiescence_hard_max_depth=2,
        ),
    )
    assert cold_tt_search.tt_status == warm_tt_search.tt_status == "ENABLED"
    assert warm_tt_search.tt_probes > 0
    assert warm_tt_search.tt_hits > 0
    assert (warm_tt_search.score, warm_tt_search.action,
            warm_tt_search.principal_variation) == (
        cold_tt_search.score, cold_tt_search.action,
        cold_tt_search.principal_variation,
    )
    assert replayed.state == native_input

    # Exercise the same low combined-node caps through both public
    # AlphaBeta callers with qsearch enabled: Core legality and Native-backed
    # legality remain distinct from the full semantic Native engine above.
    for total_cap in (0, 1):
        public_limits = SearchLimits(
            max_depth=2,
            max_nodes=total_cap,
            quiescence_max_depth=1,
            quiescence_hard_max_depth=2,
        )
        native_public = native_player.choose_action(replayed, public_limits)
        core_public = core_player.choose_action(replayed, public_limits)
        for decision in (native_public, core_public):
            assert decision.action in replayed.legal_actions()
            assert decision.nodes + decision.qnodes <= total_cap
            assert decision.termination_reason == "node_limit"
        assert replayed.state == native_input

    # The separate q-node policy is checked at expansion boundaries rather
    # than treated as a hard visit ceiling; the total-node cap remains the
    # hard bound. Exercise that control path on the same imported mixed root.
    for qnode_cap in (0, 1):
        qnode_limited = native_engine.search(
            replayed,
            SearchLimits(
                max_depth=2,
                max_nodes=10_000,
                max_time_seconds=5.0,
                quiescence_max_depth=1,
                quiescence_hard_max_depth=2,
                quiescence_max_nodes=qnode_cap,
            ),
        )
        assert qnode_limited.action in replayed.legal_actions()
        assert qnode_limited.nodes + qnode_limited.qnodes <= 10_000
        assert qnode_limited.termination_reason == "qsearch_budget"
        assert replayed.state == native_input

    for total_cap in (0, 1):
        qsearch_node_limited = native_engine.search(
            replayed,
            SearchLimits(
                max_depth=2,
                max_nodes=total_cap,
                quiescence_max_depth=1,
                quiescence_hard_max_depth=2,
            ),
        )
        assert qsearch_node_limited.action in replayed.legal_actions()
        assert qsearch_node_limited.nodes + qsearch_node_limited.qnodes <= total_cap
        assert qsearch_node_limited.termination_reason == "node_budget"
        assert qsearch_node_limited.used_fallback
        assert replayed.state == native_input

    for node_cap in (0, 1):
        bounded_native = native_engine.search(
            replayed,
            SearchLimits(
                max_depth=1,
                max_nodes=node_cap,
                quiescence_max_depth=0,
                quiescence_hard_max_depth=0,
            ),
        )
        assert bounded_native.action in replayed.legal_actions()
        assert bounded_native.nodes <= node_cap
        assert bounded_native.qnodes == 0
        assert bounded_native.completed_depth == 0
        assert bounded_native.termination_reason == "node_budget"
        assert bounded_native.used_fallback
        assert replayed.state == native_input
    zero_time_native = native_engine.search(
        replayed,
        SearchLimits(
            max_depth=1,
            max_nodes=4096,
            max_time_seconds=0.0,
            quiescence_max_depth=0,
            quiescence_hard_max_depth=0,
        ),
    )
    assert zero_time_native.action in replayed.legal_actions()
    assert zero_time_native.nodes <= 4096
    assert zero_time_native.completed_depth == 0
    assert zero_time_native.termination_reason == "time_budget"
    assert zero_time_native.used_fallback
    assert replayed.state == native_input

    from generic_chess.ai.cancellation import CancellationToken

    cancelled_token = CancellationToken()
    cancelled_token.cancel()
    cancelled_native = native_engine.search(
        replayed,
        SearchLimits(max_depth=1, max_nodes=4096, quiescence_max_depth=0),
        cancel_token=cancelled_token,
    )
    assert cancelled_native.action in replayed.legal_actions()
    assert cancelled_native.completed_depth == 0
    assert cancelled_native.termination_reason == "cancelled"
    assert cancelled_native.used_fallback
    assert replayed.state == native_input

    # The serialized post-drop state must still yield a legal root fallback
    # when the public caller supplies an exhausted fixed-node budget. This is
    # a separate contract from selecting the guarded reply with a completed
    # search above.
    zero_node_limits = SearchLimits(
        max_depth=1,
        max_nodes=0,
        quiescence_max_depth=0,
        quiescence_hard_max_depth=0,
    )
    native_zero = AlphaBetaPlayer(
        compiled, evaluator_override=PreferGuardedReply(), use_disk_cache=False
    ).choose_action(replayed, zero_node_limits)
    core_zero = AlphaBetaPlayer(
        compiled,
        evaluator_override=PreferGuardedReply(),
        use_native_semantic_legality=False,
        use_disk_cache=False,
    ).choose_action(replayed, zero_node_limits)
    legal_post_drop = set(replayed.legal_actions())
    assert native_zero.action in legal_post_drop
    assert core_zero.action in legal_post_drop
    assert (
        native_zero.action,
        native_zero.score,
        native_zero.completed_depth,
        native_zero.principal_variation,
        native_zero.nodes,
        native_zero.termination_reason,
    ) == (
        core_zero.action,
        core_zero.score,
        core_zero.completed_depth,
        core_zero.principal_variation,
        core_zero.nodes,
        core_zero.termination_reason,
    )
    assert native_zero.nodes == native_zero.qnodes == 0
    assert native_zero.termination_reason == "node_limit"
    assert native_zero.native_legality_calls > 0
    assert native_zero.native_legality_fallbacks == 0
    assert native_zero.native_legality_operational_failures == 0

    runtime = SearchPathRuntime.from_state(
        session.state,
        compiled,
        history_witnesses=session._search_witnesses,
    )
    runtime_replies = runtime.legal_actions()
    guarded_reply = next(
        action for action in runtime_replies
        if isinstance(action, SemanticBoardMove)
        and "after_drop_C0" in action.pattern_id
    )
    with runtime.pushed(guarded_reply):
        assert runtime.ply_count == 5
        assert dict(runtime.position.aux_state).get((drop_slot.slot_id, -1), 0) == expected_after_reply
        assert runtime.position.board[2 * N].base_type_id == C0
    runtime.assert_balanced()

    before_reply = session.state
    expected_reply = apply_action(before_reply, guarded_reply, compiled)
    session.submit(guarded_reply)
    assert session.state == expected_reply
    assert dict(session.state.position.aux_state).get(
        (drop_slot.slot_id, -1), 0
    ) == expected_after_reply
    replayed_reply = GameSession.replay(
        compiled,
        deserialize_game_record(serialize_game_record(session.to_record())),
    )
    assert replayed_reply.state == session.state
    assert session.state.ply_count == 5
    assert len(session._search_witnesses) == 6
