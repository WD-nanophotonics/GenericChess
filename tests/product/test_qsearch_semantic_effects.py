"""Actual semantic outcomes, rather than redundant public promotion metadata."""
from dataclasses import replace
from types import SimpleNamespace

import pytest

from generic_chess.ai.alphabeta.quiescence import classify_noisy
from generic_chess.ai.alphabeta.search import (
    INF, _Budget, _Context, _runtime_noisy_actions, quiescence,
)
from generic_chess.ai.alphabeta.statistics import SearchStatistics
from generic_chess.ai.alphabeta.player import AlphaBetaPlayer
from generic_chess.ai.alphabeta.transposition import TranspositionTable
from generic_chess.ai.alphabeta.tuning import SearchTuning
from generic_chess.ai.evaluation.config import EvaluationConfig
from generic_chess.ai.evaluation.evaluator import Evaluator
from generic_chess.ai.evaluation.profile import build_ruleset_profile
from generic_chess.ai.limits import SearchLimits
from generic_chess.core.actions import action_is_drop, PassAction
from generic_chess.core.movement import LeapAtom, RayAtom
from generic_chess.core.pieces import Piece, PieceType
from generic_chess.core.search_runtime import SearchPathRuntime
from generic_chess.core.transition import legal_successors
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.schema import (
    RuleSemanticAction, RuleGeometrySpec, RuleActionEffect, RuleSquareRef,
    RuleTypeRef, RuleInvariant,
)
from generic_chess.session.session import GameSession
from rule_semantics_ir_fixtures import _semantic_ruleset, _king_type, cannon_ruleset


def transform_rules(kind="transform", *, encoding="combined", max_ply=None):
    a = PieceType("A", "A", (LeapAtom((0, 1)),),
                  is_promotable=kind == "nochange",
                  promotion_target_ids=("B",) if kind == "nochange" else ())
    b = PieceType("B", "B", tuple(RayAtom(d) for d in
                  ((1, 0), (-1, 0), (0, 1), (0, -1))))
    board = [None] * 16
    board[0], board[15] = Piece(0, "K", "K"), Piece(1, "K", "K")
    board[1] = (Piece(0, "A", "B", promoted=True) if kind == "nochange"
                else Piece(0, "A", "A"))
    effects = (
        RuleActionEffect("move", from_ref=RuleSquareRef("source"),
                         to_ref=RuleSquareRef("target")),
        RuleActionEffect("set_current_type", square_ref=RuleSquareRef("target"),
                         type_ref=RuleTypeRef("explicit", type_id="B")),
    )
    if kind == "balanced":
        board[2] = Piece(0, "B", "B")
        effects += (RuleActionEffect("set_current_type",
            square_ref=RuleSquareRef("fixed", square=(2, 0)),
            type_ref=RuleTypeRef("explicit", type_id="A")),)
    action = RuleSemanticAction(name="effect", type_ids=("B" if kind == "nochange" else "A",),
        geometry=RuleGeometrySpec(kind="leap", offset=(0, 1)),
        target_relation="empty", composition="augment", effects=effects,
        invariants=(RuleInvariant("own_anchor_safe"),))
    explicit = replace(action, name="explicit", promotion_mode="explicit",
                       explicit_promotion_type="B")
    actions = {"effect": (action,), "explicit": (explicit,),
               "combined": (action, explicit)}[encoding]
    rules = _semantic_ruleset((_king_type(), a, b), actions, n=4,
                             rows=tuple(tuple(board[i:i+4]) for i in range(0, 16, 4)))
    if kind == "nochange":
        rules = replace(rules, promotion_allowed={"A": (frozenset(),) * 2},
                        promotion_forced={"A": (frozenset(),) * 2})
    return rules if max_ply is None else replace(rules, max_ply=max_ply)


def assert_classification_parity(compiled, state, pairs, *, capture_only=False):
    expected = classify_noisy(state, pairs, compiled, capture_only=capture_only)
    runtime = SearchPathRuntime(state, compiled)
    root = runtime.position
    ctx = SimpleNamespace(runtime=runtime, compiled=compiled,
        stats=SearchStatistics(), checkpoint=lambda: None,
        tuning=SearchTuning(use_capture_only_qsearch=capture_only))
    actual = _runtime_noisy_actions(ctx, [a for a, _ in pairs])
    assert actual == expected
    assert all(any(a is original for original, _ in pairs) for a in actual)
    assert runtime.position is root
    runtime.assert_balanced()
    return expected, ctx.stats


@pytest.mark.parametrize("kind,noisy", [("transform", True), ("nochange", False),
                                      ("balanced", False)])
@pytest.mark.parametrize("capture_only", [False, True])
def test_same_physical_child_has_same_qsupport(kind, noisy, capture_only):
    c = compile_ruleset_for_execution(transform_rules(kind))
    state = GameSession(c).state
    pairs = [(a, x) for a, x in legal_successors(state, c)
             if getattr(a, "pattern_id", "").startswith("sem_")]
    assert len(pairs) == 2 and pairs[0][0] != pairs[1][0]
    assert pairs[0][1].position == pairs[1][1].position
    assert pairs[0][1].terminal_status == pairs[1][1].terminal_status
    support, stats = assert_classification_parity(c, state, pairs, capture_only=capture_only)
    assert support == ([a for a, _ in pairs] if noisy else [])
    assert stats.material_change_qactions == (2 if noisy else 0)
    assert stats.promotion_qactions == (1 if noisy else 0)


@pytest.mark.parametrize("mutable", [False, True])
@pytest.mark.parametrize("ordered", [False, True])
def test_transformation_qresult_does_not_depend_on_encoding(mutable, ordered):
    results = []
    for encoding in ("effect", "explicit"):
        c = compile_ruleset_for_execution(transform_rules(encoding=encoding))
        state = GameSession(c).state
        cfg = EvaluationConfig(dynamic_mobility_weight=0, anchor_escape_weight=0,
                               promotion_potential_weight=0)
        ev = Evaluator(c, build_ruleset_profile(c, cfg), cfg)
        limits = SearchLimits(max_nodes=4096, max_time_seconds=5,
                             quiescence_max_depth=1, quiescence_hard_max_depth=8)
        stats = SearchStatistics()
        ctx = _Context(c, ev, TranspositionTable(), stats, _Budget(limits, None),
            SearchTuning(use_ordered_qsearch=ordered), True, True, 1, 8, None,
            runtime=SearchPathRuntime(state, c) if mutable else None)
        result = quiescence(state, -INF, INF, 0, 0, ctx)
        if mutable:
            ctx.runtime.assert_balanced()
        results.append((result, stats.qnodes))
    assert results == [(1726, 2), (1726, 2)]


def test_runtime_qsearch_classifies_and_recurses_in_one_push_in_either_order():
    c = compile_ruleset_for_execution(transform_rules())
    state = GameSession(c).state
    legal_count = len(legal_successors(state, c))
    cfg = EvaluationConfig(dynamic_mobility_weight=0, anchor_escape_weight=0,
                           promotion_potential_weight=0)
    ev = Evaluator(c, build_ruleset_profile(c, cfg), cfg)
    observed = []
    for ordered in (False, True):
        stats = SearchStatistics()
        runtime = SearchPathRuntime(state, c)
        runtime.attach_stats(stats)
        ctx = _Context(c, ev, TranspositionTable(), stats,
            _Budget(SearchLimits(max_nodes=4096, max_time_seconds=5), None),
            SearchTuning(use_ordered_qsearch=ordered), False, False, 1, 8, None,
            runtime=runtime)
        score = quiescence(state, -INF, INF, 0, 0, ctx)
        runtime.assert_balanced()
        observed.append((score, stats.qnodes, stats.material_change_qactions,
                         stats.runtime_pushes, stats.runtime_pops))
    assert observed == [(1726, 3, 2, legal_count, legal_count),
                        (1726, 3, 2, legal_count, legal_count)]


@pytest.mark.parametrize("ordered", [False, True])
def test_runtime_q_cutoff_skips_unused_classification_and_matches_immutable(ordered):
    c = compile_ruleset_for_execution(transform_rules())
    state = GameSession(c).state
    cfg = EvaluationConfig(dynamic_mobility_weight=0, anchor_escape_weight=0,
                           promotion_potential_weight=0)
    ev = Evaluator(c, build_ruleset_profile(c, cfg), cfg)
    assert ev.evaluate(state) < 300
    observations = []
    for mutable in (False, True):
        stats = SearchStatistics()
        runtime = SearchPathRuntime(state, c) if mutable else None
        if runtime is not None:
            runtime.attach_stats(stats)
        ctx = _Context(c, ev, TranspositionTable(), stats,
            _Budget(SearchLimits(max_nodes=4096, max_time_seconds=5), None),
            SearchTuning(use_ordered_qsearch=ordered), False, False, 1, 8, None,
            runtime=runtime)
        score = quiescence(state, -INF, 300, 0, 0, ctx)
        observations.append((score, stats.qnodes, stats.material_change_qactions))
        if runtime is not None:
            runtime.assert_balanced()
            assert runtime.position == state.position
            assert 0 < stats.runtime_pushes < len(legal_successors(state, c))
    # Both complete the same first transformation; the unused equivalent
    # transformation is neither classified nor searched after the cutoff.
    # At this narrow window the child returns the bound, not the full-window
    # value1726. Neither implementation promises an exact cutoff score.
    assert observations == [(300, 2, 1), (300, 2, 1)]


def test_terminal_nochange_action_stays_noisy_in_capture_only_mode():
    c = compile_ruleset_for_execution(transform_rules("nochange", max_ply=1))
    state = GameSession(c).state
    pairs = [(a, x) for a, x in legal_successors(state, c)
             if getattr(a, "pattern_id", "").startswith("sem_")]
    assert pairs and all(x.terminal_status.is_terminal for _, x in pairs)
    support, _ = assert_classification_parity(c, state, pairs, capture_only=True)
    assert support == [a for a, _ in pairs]


def test_public_decision_exports_material_counter_without_inventing_promotions():
    c = compile_ruleset_for_execution(transform_rules())
    game = GameSession(c)
    before = game.state
    decision = AlphaBetaPlayer(c, use_disk_cache=False,
        tuning=SearchTuning(use_root_tactical=False)).choose_action(game,
        SearchLimits(max_depth=2, max_nodes=4096, max_time_seconds=5,
                     quiescence_max_depth=1, quiescence_hard_max_depth=8))
    assert decision.completed_depth == 2
    assert decision.material_change_qactions > decision.promotion_qactions > 0
    assert game.state == before


def test_nonactor_type_change_is_noisy_without_promotion_metadata():
    rules = transform_rules(encoding="effect")
    action = rules.semantic_actions[0]
    # A moves without transforming; an off-target friendly B changes
    # current type. An actor-local promotion detector would miss the effect.
    rows = [list(row) for row in rules.initial_position]
    rows[0][2] = Piece(0, "B", "B")
    effects = (action.effects[0], replace(action.effects[1],
        square_ref=RuleSquareRef("fixed", square=(2, 0)),
        type_ref=RuleTypeRef("explicit", type_id="A")))
    c = compile_ruleset_for_execution(replace(rules,
        initial_position=tuple(tuple(row) for row in rows),
        semantic_actions=(replace(action, effects=effects),)))
    state = GameSession(c).state
    pairs = [(a, x) for a, x in legal_successors(state, c)
             if getattr(a, "pattern_id", "").startswith("sem_")]
    assert len(pairs) == 1
    action, child = pairs[0]
    assert action.promotion_target_id is None
    assert child.position.board[5].current_type_id == "A"
    assert child.position.board[2].current_type_id == "A"
    assert not child.terminal_status.is_terminal
    support, stats = assert_classification_parity(c, state, pairs, capture_only=True)
    assert support == [action]
    assert stats.material_change_qactions == 1
    assert stats.promotion_qactions == 0


def noop_target_rules():
    a = PieceType("A", "A", (LeapAtom((0, 1)),))
    board = [None] * 16
    board[0], board[15] = Piece(0, "K", "K"), Piece(1, "K", "K")
    board[1], board[5] = Piece(0, "A", "A"), Piece(1, "A", "A")
    occupied = RuleSemanticAction(name="occupied_noop", type_ids=("A",),
        geometry=RuleGeometrySpec(kind="leap", offset=(0, 1)),
        target_relation="enemy", composition="augment",
        effects=(RuleActionEffect("set_current_type", square_ref=RuleSquareRef("source"),
                                 type_ref=RuleTypeRef("explicit", type_id="A")),),
        invariants=(RuleInvariant("own_anchor_safe"),))
    empty = replace(occupied, name="empty_noop", target_relation="empty",
                    geometry=RuleGeometrySpec(kind="leap", offset=(1, 0)))
    return _semantic_ruleset((_king_type(), a), (occupied, empty), n=4,
        rows=tuple(tuple(board[i:i+4]) for i in range(0, 16, 4)))


@pytest.mark.parametrize("capture_only", [False, True])
def test_enemy_target_does_not_claim_capture_without_actual_removal(capture_only):
    c = compile_ruleset_for_execution(noop_target_rules())
    state = GameSession(c).state
    pairs = [(a, x) for a, x in legal_successors(state, c)
             if getattr(a, "pattern_id", "").startswith("sem_")]
    assert len(pairs) == 2
    assert pairs[0][1].position == pairs[1][1].position
    support, stats = assert_classification_parity(c, state, pairs, capture_only=capture_only)
    assert support == []
    assert stats.capture_qactions == stats.material_change_qactions == 0


@pytest.mark.parametrize("capture_only", [False, True])
def test_semantic_drop_pass_terminal_and_check_controls(capture_only):
    from generic_chess.core.semantic_executor import semantic_engine_for
    from conftest import make_state
    from test_generic_pass_action import _compiled

    # A normal drop transfers the same base type from hand to board. The
    # checking subset and terminal subset retain their independent precedence.
    rules = cannon_ruleset()
    n = rules.board_size
    rules = replace(rules, drop_allowed={"C": ((True,) * (n*n),) * 2})
    c = compile_ruleset_for_execution(rules)
    lines = ["." * n for _ in range(n)]
    lines[0], lines[-1] = "." * (n-1) + "k", "K" + "." * (n-1)
    state = make_state(c, lines, hands=([("C", 1)], ()))
    pairs = [(a, x) for a, x in legal_successors(state, c) if action_is_drop(a)]
    engine = semantic_engine_for(c)
    support, stats = assert_classification_parity(c, state, pairs, capture_only=capture_only)
    expected = [a for a, x in pairs if x.terminal_status.is_terminal
                or (not capture_only and engine.in_check(x.position, 1))]
    assert support == expected
    assert stats.material_change_qactions == 0
    assert any(a not in support for a, _ in pairs)
    for semantic in (False, True):
        _, c = _compiled(semantic, True)
        state = GameSession(c).state
        pairs = [(a, x) for a, x in legal_successors(state, c) if isinstance(a, PassAction)]
        assert len(pairs) == 1 and not pairs[0][1].terminal_status.is_terminal
        support, stats = assert_classification_parity(c, state, pairs, capture_only=capture_only)
        assert support == []
        assert stats.material_change_qactions == 0
