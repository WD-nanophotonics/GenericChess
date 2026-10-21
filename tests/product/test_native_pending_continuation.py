"""Observed Core/Native PENDING vs rule-ply limit disagreement."""
from dataclasses import replace

import pytest

from generic_chess import (RuleAutomaticAdjudication, build_builtin_ruleset,
                           compile_ruleset_for_execution)
from generic_chess.ai.limits import SearchLimits
from generic_chess.native import SemanticSearchEngine, native_available
from generic_chess.native.adapter import pack_semantic_search_position
from generic_chess.native.compiler import GC_SEM_MAX_PLY, compile_native_semantic_rules
from generic_chess.native.mirror import pack_semantic_action
from generic_chess.native import semantic as sem
from generic_chess.session.session import GameSession

pytestmark = pytest.mark.skipif(not native_available(), reason="Native unavailable")


def action(session, uci):
    def square(q):
        return chr(97 + q.file) + str(1 + q.rank)
    return next(a for a in session.legal_actions()
                if getattr(a, "from_square", None) is not None
                and square(a.from_square) + square(a.to_square) == uci)


def session_after(moves, *, limit=3, trigger=3):
    compiled = compile_ruleset_for_execution(replace(
        build_builtin_ruleset("western_chess"), max_ply=limit,
        automatic_adjudications=(() if trigger is None else
            (RuleAutomaticAdjudication("audit", trigger),)),
    ))
    session = GameSession(compiled)
    for move in moves:
        session.submit(action(session, move))
    return session


def assert_equal(session, nr, native):
    imported = pack_semantic_search_position(session.compiled, nr, session)
    assert sem.snapshot(nr, native) == sem.snapshot(nr, imported)
    assert sem.terminal_status(nr, native) == {
        "status": session.state.terminal_status.status.value,
        "winner": session.state.terminal_status.winner,
    }


def test_pending_crosses_rule_limit_and_preserves_exact_checked_state():
    session = session_after(("e2e4", "d7d5", "f1b5"))
    nr = compile_native_semantic_rules(session.compiled)
    native = pack_semantic_search_position(session.compiled, nr, session)
    assert session.result.status.value == "ongoing"
    assert_equal(session, nr, native)
    for move in ("c7c6", "b5a4"):
        expected_actions = set(session.legal_actions())
        assert {sem.public_action(nr, raw) for raw in sem.guarded_actions(nr, native)} == expected_actions
        selected = action(session, move)
        native = sem.make_checked(nr, native, pack_semantic_action(nr, session.state.position, selected))
        session.submit(selected)
        assert_equal(session, nr, native)
    assert session.result.status.value == "no_contest"


@pytest.mark.parametrize("root_window", (False, True))
def test_pending_search_returns_core_replayable_pv_cold_and_warm(root_window):
    session = session_after(("e2e4", "d7d5", "f1b5", "c7c6"))
    nr = compile_native_semantic_rules(session.compiled)
    engine = SemanticSearchEngine(session.compiled, nr, tt_megabytes=1)
    before = session.state, session._search_witnesses
    for _ in range(2):
        result = engine.search(session, SearchLimits(max_depth=2, max_nodes=256,
            quiescence_max_depth=0, quiescence_hard_max_depth=0), root_window_pruning=root_window)
        replay = session_after(("e2e4", "d7d5", "f1b5", "c7c6"))
        for decision in result.decision_line:
            if isinstance(decision, str):
                replay.declare(decision)
            else:
                replay.submit(decision)
        assert result.action in session.legal_actions()
        assert (session.state, session._search_witnesses) == before


@pytest.mark.parametrize("moves,limit,trigger,status", (
    (("e2e4", "d7d5", "f1b5"), 3, None, "max_ply"),
    (("e2e4",), 1, 1, "no_contest"),
    (("f2f3", "e7e5", "g2g4", "d8h4"), 4, 4, "checkmate"),
))
def test_terminal_precedence_unchanged(moves, limit, trigger, status):
    session = session_after(moves, limit=limit, trigger=trigger)
    nr = compile_native_semantic_rules(session.compiled)
    assert_equal(session, nr, pack_semantic_search_position(session.compiled, nr, session))
    assert session.result.status.value == status


def test_fixed_capacity_is_explicit_not_a_rule_terminal_or_empty_frontier():
    session = session_after(("e2e4", "d7d5", "f1b5", "c7c6"))
    nr = compile_native_semantic_rules(session.compiled)
    native = pack_semantic_search_position(session.compiled, nr, session)
    snap = sem.snapshot(nr, native)
    # Transport-boundary fixture, NOT a claimed reachable 1024-ply game.
    history = [(i + 1, 0, 0, 0, 255 if i == 0 else (i - 1) % 2,
                int(i > 0 and i % 2 == 1)) for i in range(GC_SEM_MAX_PLY + 1)]
    history[-1] = (*snap["history"][-1], 1, 0)
    payload = dict(side=snap["side"], ply=GC_SEM_MAX_PLY,
        board=[None if p is None else list(p) for p in snap["board"]],
        hands=[list(x) for x in snap["hands"]], history=history,
        aux_state=snap["aux_state"])
    full = sem.pack_position(nr, payload)
    assert sem.terminal_status(nr, full)["status"] == "ongoing"
    for operation in (
        lambda: sem.guarded_actions(nr, full),
        lambda: sem.dynamic_features(nr, full),
        lambda: sem.spatial_features(nr, full),
        lambda: sem.evaluate(nr, full, dynamic_values=(1, 0, 0)),
        lambda: sem.evaluate(nr, full, localized_control_values=(1, -1, 0, 0, 0, 0, 0, 0, 0)),
        lambda: sem.make_checked(nr, full, pack_semantic_action(nr, session.state.position, action(session, "b5a4"))),
        lambda: sem.fixed_depth_search(nr, full, 1),
        lambda: sem.semantic_iterative_search(nr, full, 1),
    ):
        with pytest.raises(NotImplementedError, match="history capacity.*Core"):
            operation()
    with pytest.raises(NotImplementedError, match="history capacity"):
        sem.pack_position(nr, dict(payload, ply=GC_SEM_MAX_PLY + 1))


def test_old_kernel_declines_pending_authority_but_core_path_remains_available():
    from generic_chess.native.compiler import NativeUnsupportedRuleError
    from generic_chess.ai.alphabeta.player import AlphaBetaPlayer

    session = session_after(("e2e4", "d7d5", "f1b5", "c7c6"))
    nr = compile_native_semantic_rules(session.compiled)
    actual = nr.backend_module
    class OldKernel:
        def __getattr__(self, name):
            return getattr(actual, name)
        def native_capabilities(self):
            caps = dict(actual.native_capabilities())
            caps.pop("semantic_pending_continuation", None)
            return caps
    nr._backend_module = OldKernel()
    with pytest.raises(NativeUnsupportedRuleError, match="PENDING.*rebuilt"):
        SemanticSearchEngine(session.compiled, nr, tt_megabytes=0)
    class Flat:
        def evaluate(self, state):
            return 0
        def capture_order_value(self, mover, occupant):
            return 0
    player = AlphaBetaPlayer(session.compiled, evaluator_override=Flat(),
                            use_native_semantic_legality=False, use_tt=False)
    decision = player.choose_action(session, SearchLimits(max_depth=1, max_nodes=128,
        quiescence_max_depth=0, quiescence_hard_max_depth=0))
    assert decision.action in session.legal_actions()


@pytest.mark.parametrize("path", (
    "guarded", "guarded_audit", "transient", "transient_audit", "subset", "checked",
))
def test_missing_pending_history_is_failure_not_empty_legality(path):
    session = session_after(("e2e4", "d7d5", "f1b5"))
    rules = compile_native_semantic_rules(session.compiled)
    full = pack_semantic_search_position(session.compiled, rules, session)
    # Explicit state-only import: no claim that this contains the played history.
    short = sem.pack_current_position(rules, session.state.position,
                                      ply_count=session.state.ply_count)
    before = sem.snapshot(rules, short)
    candidates = sem.candidate_actions(rules, short)
    selected = pack_semantic_action(rules, session.state.position,
                                    session.legal_actions()[0])
    operations = {
        "guarded": lambda: sem.guarded_actions(rules, short),
        "guarded_audit": lambda: sem.guarded_actions_audit(rules, short),
        "transient": lambda: sem.transient_legal_actions(rules, short),
        "transient_audit": lambda: sem.transient_legal_actions_audit(rules, short),
        "subset": lambda: sem.transient_legal_subset(rules, short, candidates),
        "checked": lambda: sem.make_checked(rules, short, selected),
    }
    with pytest.raises(RuntimeError, match="required checked transition"):
        operations[path]()
    assert sem.snapshot(rules, short) == before
    # The valid complete import remains usable after every error/mode cleanup.
    assert {sem.public_action(rules, a) for a in sem.guarded_actions(rules, full)} == set(session.legal_actions())
