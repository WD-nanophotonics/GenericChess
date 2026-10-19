"""Complete semantic qsearch and cache/control boundaries."""
from dataclasses import replace
import pytest
from generic_chess.native import SemanticSearchEngine, native_available, _module
from generic_chess.native.compiler import compile_native_semantic_rules
from generic_chess.ai.limits import SearchLimits
from generic_chess.ai.alphabeta.player import AlphaBetaPlayer
from generic_chess.ai.alphabeta.tuning import SearchTuning
from generic_chess.ai.cancellation import CancellationToken
from generic_chess.core.movegen import legal_actions
from generic_chess.core.transition import apply_action
from generic_chess.core.pieces import PieceType
from generic_chess.rules.compiler import (
    compile_legacy_ruleset_for_semantic_execution,
    compile_ruleset_for_execution,
    compile_semantic_ruleset,
)
from generic_chess.rules.schema import (
    RuleActionEffect,
    RuleGeometrySpec,
    RuleInvariant,
    RuleSemanticAction,
    RuleSet,
    RuleSquareRef,
)
from generic_chess.session.session import GameSession
from test_qsearch_semantic_effects import transform_rules

pytestmark = pytest.mark.skipif(
    not native_available() or getattr(_module(), "SEMANTIC_QSEARCH_VERSION", 0) < 1,
    reason="Native qsearch kernel unavailable; rebuild required")


class Material:
    values = {"K": 0, "A": 100, "B": 900}

    def evaluate(self, state):
        side = state.position.side_to_move
        return sum((1 if p.owner == side else -1) * self.values[p.current_type_id]
                   for p in state.position.board if p is not None) + sum(
            (1 if owner == side else -1) * self.values[tid] * count
            for owner, hand in enumerate(state.position.hands) for tid, count in hand.items())

    def type_value(self, tid):
        return self.values[tid]

    def capture_order_value(self, moving, captured):
        return 10 * self.values[captured.current_type_id] - self.values[moving.current_type_id]


def fixture(kind="transform"):
    return GameSession(compile_ruleset_for_execution(transform_rules(kind, encoding="effect")))


def engine(session, tt=0, values=None):
    values = Material.values if values is None else values
    return SemanticSearchEngine(session.compiled, compile_native_semantic_rules(session.compiled),
        board_values=values, hand_values=values,
        tt_megabytes=tt, ordering_cache_enabled=False)


def limits(q, hard=8, **kwargs):
    return SearchLimits(max_depth=2, max_time_seconds=5,
        quiescence_max_depth=q, quiescence_hard_max_depth=hard, **kwargs)


def normalize(score):
    return score if abs(score) < 50_000_000 else (
        (1 if score > 0 else -1) * (1_000_000_000 - (100_000_000 - abs(score))))


@pytest.mark.parametrize("kind", ["transform", "nochange", "balanced"])
@pytest.mark.parametrize("q", [1, 4])
def test_semantic_q_matches_independent_core_full_effect_policy(kind, q):
    session = fixture(kind)
    before = session.state, session.to_record(), session._search_witnesses
    core = AlphaBetaPlayer(session.compiled, evaluator_override=Material(), use_tt=False,
        use_disk_cache=False, use_ordering=False, use_native_semantic_legality=False,
        tuning=SearchTuning(use_root_tactical=False)).choose_action(session, limits(q))
    native = engine(session).search(session, limits(q), root_window_pruning=True)
    assert core.completed_depth == native.completed_depth == 2
    assert core.score == normalize(native.score)
    assert native.qnodes > 0
    assert before == (session.state, session.to_record(), session._search_witnesses)
    assert native.action in session.legal_actions()


@pytest.mark.parametrize("root_window", [False, True])
def test_warm_tt_separates_reserve_qdepth_and_hard_depth(root_window):
    import json
    from pathlib import Path
    from generic_chess.rules.serialization import deserialize_ruleset
    from generic_chess.rules.compiler import compile_legacy_ruleset_for_semantic_execution
    from scripts.full_q_refresh_comparison import SearchMetadataAdapter
    from scripts.research_record import record_value
    data = json.loads((Path(__file__).parent / "data/native_q_tt_objective_2401.json").read_text())
    raw = compile_legacy_ruleset_for_semantic_execution(deserialize_ruleset(json.dumps(data["ruleset"])))
    c = SearchMetadataAdapter(ir=raw.ir, _legacy_compiled=raw._legacy_compiled, support=raw.support)
    session = GameSession(c)
    for av in data["walk"]:
        action, = [a for a in session.legal_actions() if record_value(a) == av]
        session.submit(action)
    values = {tid: 0 if m.is_anchor else 100 for tid, m in c.support.type_metadata.items()}
    def make(tt):
        return SemanticSearchEngine(c, compile_native_semantic_rules(c),
            board_values=values, hand_values=values, tt_megabytes=tt, ordering_cache_enabled=False)
    shared = make(1)
    scores = {}
    for q, hard in [(0, 8), (1, 4), (4, 8), (0, 8), (1, 4), (4, 8)]:
        lim = limits(q, hard)
        fresh = make(0).search(session, lim, root_window_pruning=root_window)
        warm = shared.search(session, lim, root_window_pruning=root_window)
        assert warm.completed_depth == fresh.completed_depth == 2
        assert (warm.score, warm.action, warm.declaration_id, warm.principal_variation) == (
            fresh.score, fresh.action, fresh.declaration_id, fresh.principal_variation)
        scores[q] = warm.score
    assert scores[0] != scores[4]  # This fixture actually distinguishes cache objectives.


def test_native_q_stop_preserves_root_and_reports_real_budget():
    session = fixture()
    before = session.state, session.to_record(), session._search_witnesses
    for lim in [limits(4, max_nodes=1), limits(4, quiescence_max_nodes=1), limits(1, 1)]:
        result = engine(session, 1).search(session, lim, root_window_pruning=True)
        assert result.termination_reason in ("node_budget", "qsearch_budget", "qsearch_check_hard_limit")
        assert result.completed_depth < 2
        assert result.action in session.legal_actions()
        assert before == (session.state, session.to_record(), session._search_witnesses)
    token = CancellationToken()
    token.cancel()
    result = engine(session).search(session, limits(4), token)
    assert result.termination_reason == "cancelled" and result.completed_depth == 0
    assert result.qnodes == 0
    assert before == (session.state, session.to_record(), session._search_witnesses)


def test_unsupported_q_capability_requires_rebuild_without_silent_downgrade(monkeypatch):
    session = fixture()
    e = engine(session)
    monkeypatch.setattr(_module(), "SEMANTIC_QSEARCH_VERSION", 0)
    with pytest.raises(ValueError, match="rebuilt Native kernel"):
        e.search(session, limits(1))
    assert e.search(session, limits(0)).qnodes == 0


@pytest.mark.parametrize("depth,ordinary", [(1, 0), (2, 4)])
def test_retained_iteration_reports_actual_q_policy(depth, ordinary):
    session = fixture()
    result = engine(session).search(session, SearchLimits(max_depth=depth,
        max_time_seconds=5, quiescence_max_depth=4, quiescence_hard_max_depth=8))
    assert result.completed_depth == depth
    assert result.result_ordinary_qdepth == ordinary
    assert result.result_check_hard_qdepth == 8

def test_q_node_limit_is_expansion_check_not_quiet_reserve_visit_cap():
    from generic_chess import build_builtin_ruleset
    session = GameSession(compile_ruleset_for_execution(build_builtin_ruleset("western_chess")))
    values = {tid: 0 if m.is_anchor else 100
              for tid, m in session.compiled.support.type_metadata.items()}
    e = SemanticSearchEngine(session.compiled, compile_native_semantic_rules(session.compiled),
        board_values=values, hand_values=values, tt_megabytes=0)
    before = session.state, session.to_record(), session._search_witnesses
    result = e.search(session, SearchLimits(max_depth=1, max_time_seconds=5,
        quiescence_max_depth=4, quiescence_hard_max_depth=8, quiescence_max_nodes=1))
    assert result.completed_depth == 1 and result.result_ordinary_qdepth == 0
    assert result.qnodes > 1
    assert result.termination_reason == "completed"
    assert before == (session.state, session.to_record(), session._search_witnesses)


def test_native_semantic_qsearch_includes_full_history_repetition_child():
    """A legacy-derived semantic action reaching repetition is tactical at qsearch."""
    from test_native_history import _cycle_ruleset
    from generic_chess.core.terminal import TerminalStatus
    from generic_chess.core.transition import apply_action

    legacy = _cycle_ruleset()
    size = legacy.board_size
    rows = tuple(
        tuple(legacy.initial_position.board[rank * size + file] for file in range(size))
        for rank in range(size)
    )
    rules = RuleSet(
        board_size=size,
        piece_types=legacy.piece_types,
        initial_position=rows,
        drop_allowed=legacy.drop_allowed,
        promotion_allowed=legacy.promotion_allowed,
        promotion_forced=legacy.promotion_forced,
        repetition_limit=legacy.repetition_limit,
        max_ply=legacy.max_ply,
        stalemate_result=legacy.stalemate_result,
    )
    compiled = compile_legacy_ruleset_for_semantic_execution(rules)
    session = GameSession(compiled)
    for _ in range(8):
        actions = session.legal_actions()
        assert len(actions) == 1
        session.submit(actions[0])

    # The fixed four-position cycle leaves the root ongoing at ply 8. Three
    # forced moves reach the qsearch node; its only semantic action is a
    # fourth occurrence under the complete played history.
    node = session.state
    for _ in range(3):
        action, = legal_actions(node, compiled)
        node = apply_action(node, action, compiled)
    assert node.terminal_status.status is TerminalStatus.ONGOING
    terminal_action, = legal_actions(node, compiled)
    assert (
        apply_action(node, terminal_action, compiled).terminal_status.status
        is TerminalStatus.REPETITION
    )

    values = {"K": 0, "F": 500, "G": 100, "Z": 0}
    evaluator = Material()
    evaluator.values = values

    def search(qdepth):
        limits = SearchLimits(
            max_depth=3,
            max_nodes=500,
            max_time_seconds=5,
            quiescence_max_depth=qdepth,
            quiescence_hard_max_depth=2,
        )
        core = AlphaBetaPlayer(
            compiled,
            evaluator_override=evaluator,
            use_tt=False,
            use_disk_cache=False,
            use_ordering=False,
            use_native_semantic_legality=False,
            tuning=SearchTuning(use_root_tactical=False),
        ).choose_action(session, limits)
        native = engine(session, values=values).search(
            session, limits, root_window_pruning=False
        )
        return core, native

    core_without, native_without = search(0)
    core_with, native_with = search(1)
    assert core_without.completed_depth == native_without.completed_depth == 3
    assert core_with.completed_depth == native_with.completed_depth == 3
    assert core_without.score == normalize(native_without.score) == 400
    assert core_with.score == normalize(native_with.score) == 0
    assert native_without.qnodes == 0
    assert native_with.qnodes > 0
    assert core_with.action == native_with.action
    assert core_with.principal_variation == native_with.principal_variation
    assert session.state.ply_count == 8
    assert len(session.state.history) == 9


def test_native_qsearch_full_history_on_declared_semantic_actions():
    """Complete-history qsearch parity also holds for declared semantic actions."""
    from test_native_history import _cycle_ruleset
    from generic_chess.core.terminal import TerminalStatus

    legacy = _cycle_ruleset()
    size = legacy.board_size
    rows = tuple(
        tuple(legacy.initial_position.board[rank * size + file] for file in range(size))
        for rank in range(size)
    )
    types = tuple(
        PieceType(
            piece.type_id,
            piece.name,
            (),
            is_anchor=piece.is_anchor,
            is_promotable=piece.is_promotable,
            promotion_target_ids=piece.promotion_target_ids,
        )
        for piece in legacy.piece_types
    )
    rules = RuleSet(
        board_size=size,
        piece_types=types,
        initial_position=rows,
        drop_allowed=legacy.drop_allowed,
        promotion_allowed=legacy.promotion_allowed,
        promotion_forced=legacy.promotion_forced,
        repetition_limit=legacy.repetition_limit,
        max_ply=legacy.max_ply,
        stalemate_result=legacy.stalemate_result,
    )
    move_effect = RuleActionEffect(
        "move",
        from_ref=RuleSquareRef("source"),
        to_ref=RuleSquareRef("target"),
    )
    declared_actions = tuple(
        RuleSemanticAction(
            name=f"{type_id}_{direction}",
            type_ids=(type_id,),
            geometry=RuleGeometrySpec(kind="leap", offset=(0, direction)),
            target_relation="empty",
            effects=(move_effect,),
            invariants=(RuleInvariant("own_anchor_safe"),),
        )
        for type_id in ("F", "G")
        for direction in (-1, 1)
    )
    compiled = compile_semantic_ruleset(replace(rules, semantic_actions=declared_actions))
    native_rules = compile_native_semantic_rules(compiled)
    assert native_rules.native_executable

    short_session = GameSession(compiled)
    session = GameSession(compiled)
    for _ in range(8):
        actions = session.legal_actions()
        assert len(actions) == 1
        assert getattr(actions[0], "pattern_id", "").startswith("sem_")
        session.submit(actions[0])
    node = session.state
    for _ in range(3):
        action, = legal_actions(node, compiled)
        node = apply_action(node, action, compiled)
    terminal_action, = legal_actions(node, compiled)
    assert node.terminal_status.status is TerminalStatus.ONGOING
    assert apply_action(node, terminal_action, compiled).terminal_status.status is TerminalStatus.REPETITION

    values = {"K": 0, "F": 500, "G": 100, "Z": 0}
    evaluator = Material()
    evaluator.values = values

    def compare(search_session, qdepth):
        limits = SearchLimits(
            max_depth=3,
            max_nodes=500,
            max_time_seconds=5,
            quiescence_max_depth=qdepth,
            quiescence_hard_max_depth=2,
        )
        core = AlphaBetaPlayer(
            compiled,
            evaluator_override=evaluator,
            use_tt=False,
            use_disk_cache=False,
            use_ordering=False,
            use_native_semantic_legality=False,
            tuning=SearchTuning(use_root_tactical=False),
        ).choose_action(search_session, limits)
        native = engine(search_session, values=values).search(
            search_session, limits, root_window_pruning=False
        )
        return core, native

    core_without, native_without = compare(session, 0)
    core_with, native_with = compare(session, 1)
    core_short, native_short = compare(short_session, 1)
    assert core_without.completed_depth == native_without.completed_depth == 3
    assert core_with.completed_depth == native_with.completed_depth == 3
    assert core_without.score == normalize(native_without.score) == 400
    assert core_with.score == normalize(native_with.score) == 0
    assert native_without.qnodes == 0
    assert native_with.qnodes == 4
    assert core_with.action == native_with.action
    assert core_with.principal_variation == native_with.principal_variation
    assert short_session.state.position == session.state.position
    assert len(short_session.state.history) == 1
    assert core_short.score == normalize(native_short.score) == 400
    assert session.state.ply_count == 8
    assert len(session.state.history) == 9


def test_native_shogi_check_history_search_result_matches_core():
    """A bounded Shogi check-history q search agrees with Core on full history."""
    from generic_chess import build_builtin_ruleset, compile_ruleset_for_execution
    from generic_chess.core.terminal import TerminalStatus
    from generic_chess.native import semantic as sem
    from generic_chess.native.adapter import pack_semantic_search_position
    from scripts.search_backend_comparison import CoreBoard

    class Zero:
        def evaluate(self, state):
            return 0

        def type_value(self, type_id):
            return 0

        def capture_order_value(self, moving, captured):
            return 0

    compiled = compile_ruleset_for_execution(replace(
        build_builtin_ruleset("standard_shogi"), stalemate_result="draw"))
    setup = "4k4/3R5/9/9/9/9/9/9/8K b - 1"
    cycle = "6b5b 5a6a 5b6b 6a5a".split()
    # This is the position immediately before the final checking/escape pair.
    board = CoreBoard(dict(game="shogi", setup=setup,
        moves=" ".join((cycle * 3)[:10])), compiled)
    session = GameSession(compiled)
    session._state = board.initial
    session._search_history_witnesses = board.witnesses
    before = session.state, session.to_record(), session._search_witnesses

    # Independently certify that the retained full event history makes the
    # final quiet king reply a continuous-check loss for the checker.
    full = CoreBoard(dict(game="shogi", setup=setup, moves=" ".join(cycle * 3)), compiled)
    assert full.initial.terminal_status.status is TerminalStatus.PERPETUAL_CHECK
    assert full.initial.terminal_status.winner == 1
    checking_move = next(action for action in session.legal_actions()
        if (action.from_square.file, action.from_square.rank,
            action.to_square.file, action.to_square.rank) == (4, 7, 5, 7)
        and action.promotion_target_id is None)
    checked = apply_action(session.state, checking_move, compiled)
    assert checked.terminal_status.status is TerminalStatus.ONGOING
    assert checked.history[-1].gave_check
    final_reply = next(action for action in legal_actions(checked, compiled)
        if (action.from_square.file, action.from_square.rank,
            action.to_square.file, action.to_square.rank) == (5, 8, 4, 8))
    assert apply_action(checked, final_reply, compiled).terminal_status.status is TerminalStatus.PERPETUAL_CHECK

    values = {type_id: 0 for type_id in compiled.support.type_metadata}
    native_rules = compile_native_semantic_rules(compiled)
    native_position = pack_semantic_search_position(compiled, native_rules, session)
    native_snapshot = sem.snapshot(native_rules, native_position)
    assert native_snapshot["history_exact"] and native_snapshot["history_events_exact"]
    assert native_snapshot["history_events"] == tuple(
        (255 if event.actor < 0 else event.actor, bool(event.gave_check))
        for event in session.state.history)

    limits = SearchLimits(max_depth=1, max_nodes=10_000, max_time_seconds=5,
        quiescence_max_depth=1, quiescence_hard_max_depth=12)
    core = AlphaBetaPlayer(compiled, evaluator_override=Zero(), use_tt=False,
        use_disk_cache=False, use_ordering=False, use_native_semantic_legality=False,
        tuning=SearchTuning(use_root_tactical=False)).choose_action(session, limits)
    native = SemanticSearchEngine(compiled, native_rules, board_values=values,
        hand_values=values, tt_megabytes=0, ordering_cache_enabled=False).search(
            session, limits, root_window_pruning=False)
    assert core.completed_depth == native.completed_depth == 1
    assert core.score == normalize(native.score)
    assert core.action == native.action
    assert core.principal_variation == native.principal_variation
    assert native.qnodes > 0 and native.result_check_hard_qdepth == 12
    assert before == (session.state, session.to_record(), session._search_witnesses)

def test_raw_q_call_rejects_combined_stack_overflow_and_releases_engine():
    from generic_chess.native.compiler import GC_SEM_MAX_PLY
    from generic_chess.native.adapter import pack_semantic_search_position
    session = fixture()
    e = engine(session)
    position = pack_semantic_search_position(session.compiled, e._native_rules, session)
    with pytest.raises(ValueError, match="bounded search stack"):
        _module().semantic_engine_search(e._capsule, position, GC_SEM_MAX_PLY,
            None, 0.0, None, None, False, False, 1, 8, None)
    assert e.search(session, limits(0)).completed_depth == 2
