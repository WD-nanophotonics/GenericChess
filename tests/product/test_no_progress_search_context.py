"""Actual no-progress histories must preserve terminals, keys and failed pushes."""
from copy import copy
from dataclasses import replace
import pytest
from generic_chess.core.actions import action_is_board, action_source_square, action_target_square
from generic_chess.core.coordinates import Square
from generic_chess.core.movement import LeapAtom
from generic_chess.core.pieces import Piece, PieceType
from generic_chess.core.search_runtime import SearchPathRuntime, RuntimeHistoryContext
from generic_chess.core.adjudication import IncompleteAdjudicationHistoryError
from generic_chess.core.identity import search_state_identity
from generic_chess.core.terminal import TerminalResult, TerminalStatus, _repeated_cycle_target_history_projection
from generic_chess.rules.schema import RuleSet, RuleNoProgressDraw, RuleSemanticAction, RuleGeometrySpec, RuleActionEffect, RuleSquareRef, RuleTypeRef, RuleInvariant
from generic_chess.rules.compiler import compile_ruleset, compile_legacy_ruleset_for_semantic_execution, compile_semantic_ruleset
from generic_chess.session.session import GameSession
from generic_chess.ai.alphabeta.player import AlphaBetaPlayer
from generic_chess.ai.alphabeta.tuning import SearchTuning
from generic_chess.ai.limits import SearchLimits


def rules(spawn=False):
    king = PieceType('K', 'anchor', tuple(LeapAtom((x,y)) for x in (-1,0,1) for y in (-1,0,1) if x or y), is_anchor=True)
    leaps = tuple(LeapAtom(x) for x in ((1,0),(-1,0),(0,1),(0,-1)))
    types = (king, PieceType('P','reset',leaps), PieceType('N','quiet',leaps), PieceType('R','creator',leaps))
    board = [[None]*8 for _ in range(8)]
    for o,t,x,y in ((0,'K',0,0),(1,'K',7,7),(0,'P',1,1),(0,'N',3,1)):
        board[y][x] = Piece(o,t,t)
    actions = ()
    if spawn:
        board[1][1] = Piece(0,'R','R')
        actions = (RuleSemanticAction(name='create_extra_actor',type_ids=('R',), geometry=RuleGeometrySpec(kind='leap',offset=(1,0)), target_relation='empty',composition='augment', effects=(RuleActionEffect('place',to_ref=RuleSquareRef(kind='target'),piece_type_ref=RuleTypeRef(kind='explicit',type_id='R'),piece_owner='self'),),invariants=(RuleInvariant('own_anchor_safe'),)),)
    return RuleSet(board_size=8,piece_types=types,initial_position=tuple(tuple(r) for r in board), drop_allowed={t:((False,)*64,(False,)*64) for t in ('P','N','R')}, no_progress_draw=RuleNoProgressDraw(4 if spawn else 6,True,() if spawn else ('P',)), semantic_actions=actions,max_ply=64,repetition_limit=4)


def action(s,source,target):
    return next(a for a in s.legal_actions() if action_is_board(a) and action_source_square(a)==Square(*source) and action_target_square(a)==Square(*target))


def pair(semantic=True):
    c = (replace(compile_legacy_ruleset_for_semantic_execution(rules()),_legacy_compiled=None) if semantic else compile_ruleset(rules()))
    a = (((1,1),(1,2)),((7,7),(7,6)),((1,2),(1,1)),((7,6),(7,7)))
    b = (((3,1),(3,2)),((7,7),(7,6)),((3,2),(3,1)),((7,6),(7,7)))
    sessions=[]
    for path in (a+b,b+a):
        s=GameSession(c)
        for src,dst in path:s.submit(action(s,src,dst))
        sessions.append(s)
    return c,sessions


def snapshot(rt):
    return rt.position,rt.ply_count,rt.terminal_status,rt.search_key(),tuple(rt.history),dict(rt.repetition_counts),rt.depth,rt._no_progress_context


@pytest.mark.parametrize('semantic',(False,True))
@pytest.mark.parametrize('supplied',(False,True))
@pytest.mark.parametrize('collision',(None,7))
def test_real_histories_keep_different_future_draws_and_restore_all_children(semantic,supplied,collision):
    c,sessions=pair(semantic);left,right=sessions
    assert left.state.position==right.state.position and left.state.repetition_counts==right.state.repetition_counts
    assert search_state_identity(left.state,c)!=search_state_identity(right.state,c)
    runtimes=[SearchPathRuntime(s.state,c,history_witnesses=s._search_witnesses if supplied else None,hash_override=collision) for s in sessions]
    assert runtimes[0].search_key()!=runtimes[1].search_key()
    statuses=[]
    for s,rt in zip(sessions,runtimes):
        before=snapshot(rt)
        for a in s.legal_actions():
            child=copy(s);child.submit(a)
            with rt.pushed(a):
                assert rt.position==child.state.position and rt.terminal_status==child.state.terminal_status
                counts,history=_repeated_cycle_target_history_projection(rt)
                assert counts==child.state.repetition_counts and history==child.state.history
            assert snapshot(rt)==before
        child=copy(s);child.submit(action(child,(0,0),(1,0)));statuses.append(child.state.terminal_status.status)
        rt.assert_balanced()
    assert statuses==[TerminalStatus.NO_PROGRESS_DRAW,TerminalStatus.ONGOING]


class Constant:
    def evaluate(self,state): return 77
    def type_value(self,t): return 0 if t=='K' else 1000
    def capture_order_value(self,moving,captured): return self.type_value(captured.current_type_id)


@pytest.mark.parametrize('collision',(False,True))
def test_warm_caller_keeps_exact_history_even_when_history_digests_collide(monkeypatch,collision):
    if collision:monkeypatch.setattr(RuntimeHistoryContext,'_record_digest',staticmethod(lambda *_:bytes(16)))
    c,sessions=pair()
    def player():return AlphaBetaPlayer(c,evaluator_override=Constant(),use_disk_cache=False,use_native_semantic_legality=False,tuning=SearchTuning(use_root_tactical=False,require_full_pv=True))
    shared=player();limits=SearchLimits(max_depth=1,quiescence_max_depth=0,quiescence_hard_max_depth=0)
    for s in sessions+sessions[::-1]:
        before=s.state;a=shared.choose_action(s,limits);b=player().choose_action(s,limits)
        assert (a.action,a.score,a.principal_variation)==(b.action,b.score,b.principal_variation)
        expected_status = (
            TerminalStatus.NO_PROGRESS_DRAW
            if s is sessions[0]
            else TerminalStatus.ONGOING
        )
        expected_score = 0 if expected_status is TerminalStatus.NO_PROGRESS_DRAW else -77
        child = copy(s)
        child.submit(a.action)
        assert child.state.terminal_status.status is expected_status
        assert a.score == expected_score
        assert s.state is before


def spawn_prefix():
    c=replace(compile_semantic_ruleset(rules(True)),_legacy_compiled=None);s=GameSession(c)
    a=next(a for a in s.legal_actions() if getattr(a,'pattern_id','').startswith('sem_'));s.submit(a)
    s.submit(action(s,(7,7),(6,7)));s.submit(action(s,(0,0),(1,0)))
    return c,s


def test_ambiguity_is_deferred_to_original_threshold_and_failure_restores_parent():
    c,s=spawn_prefix();rt=SearchPathRuntime(s.state,c,history_witnesses=s._search_witnesses);before=snapshot(rt);a=action(s,(6,7),(7,7))
    for perform in (lambda:copy(s).submit(a),lambda:rt.push(a)):
        with pytest.raises(IncompleteAdjudicationHistoryError,match='capture fact is ambiguous at action 1'):perform()
    assert snapshot(rt)==before
    rt.assert_balanced()


def test_root_replay_rejects_permuted_witnesses_with_unchanged_counts():
    c,(s,_)=pair();w=list(s._search_witnesses);w[1],w[2]=w[2],w[1]
    with pytest.raises(IncompleteAdjudicationHistoryError,match='witness differs.*action 1'):SearchPathRuntime(s.state,c,history_witnesses=w)


@pytest.mark.parametrize("supplied", (False, True))
def test_imported_terminal_cannot_be_changed_to_ongoing(supplied):
    c,(s,_)=pair();s.submit(action(s,(0,0),(1,0)));assert s.state.terminal_status.status is TerminalStatus.NO_PROGRESS_DRAW
    witnesses=s._search_witnesses if supplied else None
    valid=SearchPathRuntime(s.state,c,history_witnesses=witnesses)
    assert valid.terminal_status==s.state.terminal_status
    bad=replace(s.state,terminal_status=TerminalResult(TerminalStatus.ONGOING))
    with pytest.raises(IncompleteAdjudicationHistoryError,match='imported terminal'):SearchPathRuntime(bad,c,history_witnesses=witnesses)


def test_exception_after_context_update_rolls_back_context_and_full_key(monkeypatch):
    from generic_chess.core import search_runtime
    c,(s,_)=pair();rt=SearchPathRuntime(s.state,c,history_witnesses=s._search_witnesses);before=snapshot(rt)
    class Cancelled(BaseException):pass
    def fail(*_):raise Cancelled()
    monkeypatch.setattr(search_runtime,'terminal_from_search_runtime',fail)
    with pytest.raises(Cancelled):rt.push(s.legal_actions()[0])
    assert snapshot(rt)==before
    rt.assert_balanced()


@pytest.mark.parametrize('explicit_cache',(False,True))
def test_semantic_only_default_profile_error_is_actionable_before_cache(explicit_cache):
    c,_=pair()
    class CacheMustNotRun:
        def get_or_build(self,*_):
            raise AssertionError('metadata validation must precede cached profiles')
    with pytest.raises(ValueError,match='supply evaluator_override'):
        AlphaBetaPlayer(c,use_disk_cache=False,profile_cache=CacheMustNotRun() if explicit_cache else None)


def test_semantic_only_explicit_evaluator_uses_actual_core_with_default_legality_preference():
    c,(s,_)=pair();before=s.state
    player=AlphaBetaPlayer(c,evaluator_override=Constant(),use_disk_cache=False)
    assert player.native_legality_provider is None
    result=player.choose_action(s,SearchLimits(max_depth=1,quiescence_max_depth=0,quiescence_hard_max_depth=0))
    assert result.completed_depth==1 and result.action in s.legal_actions()
    assert s.state is before and player.evaluation_profile is None


def test_optional_witness_import_does_not_readjudicate_each_no_progress_prefix(monkeypatch):
    from generic_chess.core import adjudication
    c,(s,_)=pair()
    original=adjudication.no_progress_draw_status
    def checked(policy,*args,**kwargs):
        if policy is not None:
            raise AssertionError('optional witness import must not re-adjudicate every prefix')
        return original(policy,*args,**kwargs)
    monkeypatch.setattr(adjudication,'no_progress_draw_status',checked)
    runtime=SearchPathRuntime(s.state,c)
    assert tuple(runtime.history) and runtime.terminal_status==s.state.terminal_status
    assert runtime._no_progress_context.quiet_plies==5
