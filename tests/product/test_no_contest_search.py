"""Neutral declarations are real defensive options, including inside qsearch."""
from dataclasses import replace
import pytest
from conftest import make_ruleset, king_type, T
from generic_chess.core.movement import RayAtom
from generic_chess.core.position import Hands, HistoryRecord
from generic_chess.core.identity import position_identity_key
from generic_chess.core.terminal import terminal_result
from generic_chess.core.declarations import available_declarations
from generic_chess.core.search_runtime import SearchPathRuntime
from generic_chess.rules.schema import (
    RuleDeclaration, RuleDeclarationOutcomeBand, RuleWeightedMaterialMetric,
)
from generic_chess.rules.compiler import compile_legacy_ruleset_for_semantic_execution
from generic_chess.session.session import GameSession
from generic_chess.ai.alphabeta import search
from generic_chess.ai.alphabeta.player import AlphaBetaPlayer
from generic_chess.ai.alphabeta.statistics import SearchStatistics
from generic_chess.ai.alphabeta.transposition import TranspositionTable
from generic_chess.ai.alphabeta.tuning import SearchTuning
from generic_chess.ai.evaluation.config import MATE_THRESHOLD
from generic_chess.ai.limits import SearchLimits
from scripts.full_q_refresh_comparison import SearchMetadataAdapter


def neutral(owner, outcome="NO_CONTEST", name="neutral"):
    return RuleDeclaration(declaration_id=name, owner=owner,
        require_not_in_check=False,
        weighted_metric=RuleWeightedMaterialMetric(weights={"K": 1}),
        outcome_bands=(RuleDeclarationOutcomeBand(1, outcome),))


def compile_session(rules):
    compiled = compile_legacy_ruleset_for_semantic_execution(rules)
    compiled = SearchMetadataAdapter(ir=compiled.ir,
        _legacy_compiled=compiled._legacy_compiled, support=compiled.support)
    return GameSession(compiled)


def defender_root():
    rules = make_ruleset(4, [king_type(), T("R", RayAtom((0, 1)),
        RayAtom((0, -1)), RayAtom((1, 0)), RayAtom((-1, 0)))],
        lines=["....", "...R", "....", ".k.K"])
    session = compile_session(replace(rules, declarations=(neutral(1),)))
    position = replace(session.state.position, hands=(Hands((("R", 1),)), Hands()))
    key = position_identity_key(position, session.compiled)
    state = replace(session.state, position=position,
        history=(HistoryRecord(key, -1, "", False),), repetition_counts=((key, 1),))
    session._state = replace(state, terminal_status=terminal_result(state, session.compiled))
    session._search_history_witnesses = (position,)
    return session


@pytest.mark.parametrize("qdepth", [0, 2])
@pytest.mark.parametrize("nodes", [99, 100000])
def test_opponent_no_contest_prevents_false_completed_root_win(qdepth, nodes):
    session = defender_root()
    before = session.state, session.to_record(), session._search_witnesses
    decision = AlphaBetaPlayer(session.compiled, use_disk_cache=False,
        use_native_semantic_legality=False).choose_action(session,
        SearchLimits(max_depth=2, max_nodes=nodes, max_time_seconds=5,
                     quiescence_max_depth=qdepth))
    assert before == (session.state, session.to_record(), session._search_witnesses)
    assert decision.runtime_depth_balanced
    assert decision.score < MATE_THRESHOLD
    assert decision.result_source != "completed_root_win"
    session.submit(decision.action)
    assert available_declarations(session.state, session.compiled)[0].outcome == "NO_CONTEST"
    result = session.declare("neutral")
    assert result.winner is None and result.declaration_outcome == "NO_CONTEST"


class Constant:
    def __init__(self, value):
        self.value = value

    def evaluate(self, state):
        return self.value


@pytest.mark.parametrize("outcomes", [("NO_CONTEST",), ("NO_CONTEST", "RESTART")])
@pytest.mark.parametrize("use_tt", [False, True])
def test_root_neutral_floor_and_real_warm_tt_preserve_declaration_identity(outcomes, use_tt):
    rules = make_ruleset(4, [king_type()], lines=["...k", "....", "....", "K..."])
    declarations = tuple(neutral(0, outcome, f"claim{i}") for i, outcome in enumerate(outcomes))
    session = compile_session(replace(rules, declarations=declarations))
    before = session.state, session.to_record(), session._search_witnesses
    player = AlphaBetaPlayer(session.compiled, evaluator_override=Constant(1),
        use_tt=use_tt, use_ordering=False, use_native_semantic_legality=False,
        tuning=SearchTuning(use_root_tactical=False))
    for _ in range(2):
        decision = player.choose_action(session, SearchLimits(
            max_depth=1, quiescence_max_depth=0, max_time_seconds=5))
        assert decision.score == 0 and decision.action is None
        assert decision.choice_kind == "DECLARATION"
        # Preserve the old RESTART preference when both value-zero options exist.
        assert decision.declaration.outcome == ("RESTART" if "RESTART" in outcomes else "NO_CONTEST")
        assert decision.declaration.declaration_id == ("claim1" if len(outcomes) == 2 else "claim0")
        assert decision.runtime_depth_balanced
    assert before == (session.state, session.to_record(), session._search_witnesses)


@pytest.mark.parametrize("mutable", [False, True])
@pytest.mark.parametrize("in_check", [False, True])
def test_qsearch_neutral_floor_includes_no_contest(mutable, in_check):
    rules = make_ruleset(4, [king_type(), T("R", RayAtom((0, 1)),
        RayAtom((0, -1)), RayAtom((1, 0)), RayAtom((-1, 0)))],
        lines=[".r.k", "....", "....", "K..."] if in_check
        else ["...k", "....", "....", "K..."])
    session = compile_session(replace(rules, declarations=(neutral(0),)))
    if in_check:
        # Initial setups disallow attacked anchors; this is a declared checked
        # analysis root with a complete fresh identity witness.
        board = list(session.state.position.board)
        board[12], board[13] = board[13], None
        position = replace(session.state.position, board=tuple(board))
        key = position_identity_key(position, session.compiled)
        state = replace(session.state, position=position,
            history=(HistoryRecord(key, -1, "", False),), repetition_counts=((key, 1),))
        session._state = replace(state, terminal_status=terminal_result(state, session.compiled))
        session._search_history_witnesses = (position,)
    class Losing:
        def evaluate(self, state):
            return -31 if state.position.side_to_move == 0 else 31

    runtime = SearchPathRuntime.from_state(session.state, session.compiled,
        history_witnesses=session._search_witnesses) if mutable else None
    ctx = search._Context(session.compiled, Losing(), TranspositionTable(),
        SearchStatistics(), search._Budget(SearchLimits(max_time_seconds=5), None),
        SearchTuning(), False, False, 0, 8, None, runtime=runtime)
    score = search.quiescence(session.state, -search.INF, search.INF, 0, 0, ctx)
    assert score == 0
    if runtime is not None:
        runtime.assert_balanced()


def test_reference_minimax_has_same_no_contest_option():
    rules = make_ruleset(4, [king_type()], lines=["...k", "....", "....", "K..."])
    session = compile_session(replace(rules, declarations=(neutral(0),)))
    assert search.reference_minimax(session.state, 1, Constant(1), session.compiled) == (0, None)


def test_winning_declaration_has_priority_over_neutral_options():
    rules = make_ruleset(4, [king_type()], lines=["...k", "....", "....", "K..."])
    session = compile_session(replace(rules, declarations=(
        neutral(0), neutral(0, "WIN", "win"))))
    decision = AlphaBetaPlayer(session.compiled, evaluator_override=Constant(1),
        use_native_semantic_legality=False).choose_action(session, SearchLimits(max_depth=1))
    assert decision.choice_kind == "DECLARATION" and decision.declaration.outcome == "WIN"
    assert decision.result_source == "root_declaration"



@pytest.mark.parametrize("outcome", ["NO_CONTEST", "RESTART"])
@pytest.mark.parametrize("stop", ["nodes", "cancelled", "root_generation", "root_scan"])
def test_incomplete_root_keeps_executable_neutral_floor(outcome, stop, monkeypatch):
    from generic_chess.ai.cancellation import CancellationToken
    rules = make_ruleset(4, [king_type()], lines=["...k", "....", "....", "K..."])
    session = compile_session(replace(rules, declarations=(neutral(0, outcome),)))
    before = session.state, session.to_record(), session._search_witnesses
    if stop == "root_generation":
        def interrupted(ctx, checkpoint):
            if checkpoint is not None:
                raise search.SearchAborted("time_limit")
            raise AssertionError("known neutral needs no uncancelled fallback generation")
        monkeypatch.setattr(search, "_runtime_legal_actions", interrupted)
    if stop == "root_scan":
        def interrupted(*args, **kwargs):
            raise search.SearchAborted("time_limit")
        monkeypatch.setattr(search, "root_tactical_scan", interrupted)
    token = CancellationToken()
    if stop == "cancelled":
        token.cancel()
    decision = AlphaBetaPlayer(session.compiled, evaluator_override=Constant(1),
        use_native_semantic_legality=False,
        tuning=SearchTuning(use_root_tactical=stop == "root_scan")).choose_action(
            session, SearchLimits(max_depth=1, max_nodes=1 if stop == "nodes" else None,
                                  quiescence_max_depth=0), cancel_token=token)
    assert before == (session.state, session.to_record(), session._search_witnesses)
    assert decision.action is None and decision.score == 0
    assert decision.choice_kind == "DECLARATION"
    assert decision.declaration.outcome == outcome
    assert decision.result_source == "root_declaration"
    assert decision.completed_depth == 0 and decision.runtime_depth_balanced
    assert decision.termination_reason == ({"nodes": "node_limit", "cancelled": "cancelled"}.get(stop, "time_limit"))
    actual = session.declare(decision.declaration.declaration_id)
    assert actual.declaration_outcome == outcome and actual.winner is None


@pytest.mark.parametrize("decl", [neutral(1), neutral(0, "LOSS"), replace(neutral(0), outcome_bands=(RuleDeclarationOutcomeBand(2, "NO_CONTEST"),))])
def test_incomplete_root_does_not_invent_a_neutral_option(decl):
    rules=make_ruleset(4,[king_type()],lines=["...k","....","....","K..."])
    session=compile_session(replace(rules,declarations=(decl,)))
    d=AlphaBetaPlayer(session.compiled,evaluator_override=Constant(1),
        use_native_semantic_legality=False,tuning=SearchTuning(use_root_tactical=False)).choose_action(
            session,SearchLimits(max_depth=1,max_nodes=1,quiescence_max_depth=0))
    assert d.choice_kind=="ACTION" and d.declaration is None and d.action in session.legal_actions()
    assert d.termination_reason=="node_limit" and d.result_source=="legal_fallback"


def test_neutral_fallback_keeps_restart_preference_but_completed_action_wins_tie():
    rules=make_ruleset(4,[king_type()],lines=["...k","....","....","K..."])
    session=compile_session(replace(rules,declarations=(neutral(0),neutral(0,"RESTART","restart"))))
    p=AlphaBetaPlayer(session.compiled,evaluator_override=Constant(0),
        use_native_semantic_legality=False,tuning=SearchTuning(use_root_tactical=False))
    short=p.choose_action(session,SearchLimits(max_depth=1,max_nodes=1,quiescence_max_depth=0))
    assert short.choice_kind=="DECLARATION" and short.declaration.outcome=="RESTART"
    complete=p.choose_action(session,SearchLimits(max_depth=1,quiescence_max_depth=0))
    assert complete.choice_kind=="ACTION" and complete.score==0 and complete.result_source=="main_iteration"


def test_root_immediate_board_win_remains_ahead_of_neutral_floor():
    # Rd4 mates the a4 king: the b2 king covers a3/b3 and the rook b4.
    from generic_chess.core.transition import apply_action
    rules=make_ruleset(4,[king_type(),T("R",RayAtom((0,1)),RayAtom((0,-1)),RayAtom((1,0)),RayAtom((-1,0)))],
        lines=["k...","....",".K..","...R"])
    session=compile_session(replace(rules,declarations=(neutral(0),)))
    d=AlphaBetaPlayer(session.compiled,use_disk_cache=False,use_native_semantic_legality=False).choose_action(
        session,SearchLimits(max_depth=2,max_nodes=10000,quiescence_max_depth=0))
    assert d.choice_kind=="ACTION" and d.score>=MATE_THRESHOLD
    assert d.result_source in ("root_immediate_win","main_iteration","completed_root_win")
    assert apply_action(session.state,d.action,session.compiled).terminal_status.winner==0
