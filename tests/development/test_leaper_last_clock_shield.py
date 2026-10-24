"""Real Core last-clock frontier, budgets and restoration; no Player calls."""
from dataclasses import replace
import pytest
from scripts import leaper_design as L
from scripts.leaper_last_clock_shield import LastClockShield
from generic_chess.ai.alphabeta import search as S
from generic_chess.ai.alphabeta.statistics import SearchStatistics
from generic_chess.ai.alphabeta.transposition import TranspositionTable
from generic_chess.ai.alphabeta.tuning import SearchTuning
from generic_chess.ai.limits import SearchLimits
from generic_chess.core.search_runtime import SearchPathRuntime

class Fixed:
    def evaluate(self,state):return 4242

def context(rule,*,hard=8,qcap=None,cancel=None):
    c=L.compile_rule(rule);sess=L.GameSession(c);limits=SearchLimits(max_nodes=10000,quiescence_max_depth=0,quiescence_hard_max_depth=hard)
    rt=SearchPathRuntime.from_state(sess.state,c)
    ctx=S._Context(c,Fixed(),TranspositionTable(),SearchStatistics(),S._Budget(limits,cancel),SearchTuning(),True,True,0,hard,qcap,runtime=rt)
    return sess,ctx

def q(ctx):return S.quiescence(ctx.runtime.state,-S.INF,S.INF,0,0,ctx)

def test_last_clock_quiet_standpat_replaced_by_actual_mandatory_move_draw():
    r=replace(L.definition(5,7),max_ply=1);sess,ctx=context(r)
    for a in sess.legal_actions():
        child=L.GameSession(ctx.compiled);child.submit(a)
        assert child.state.terminal_status.is_terminal and child.result.winner is None
    assert q(ctx)==4242
    with LastClockShield()as shield:
        assert q(ctx)==0 and shield.counts['entered']==1 and shield.counts['children']==len(sess.legal_actions())
    ctx.runtime.assert_balanced()

def test_checkmate_precedes_draw_clock():
    # Legal initial position. A has finite (1,0)/(2,0) leaps, not a Rider.
    types=(L.PieceType('K','K',tuple(L.LeapAtom(v)for v in L.offsets(3)),is_anchor=True),L.PieceType('A','A',tuple(L.LeapAtom(v)for v in L.offsets(5))))
    r=L.RuleSet(board_size=3,piece_types=types,initial_position=((L.Piece(0,'A','A'),None,None),(L.Piece(0,'K','K'),None,None),(None,None,L.Piece(1,'K','K'))),drop_allowed={'A':((False,)*9,)*2},capture_disposition='remove_from_game',max_ply=1,repetition_limit=4)
    sess,ctx=context(r);wins=[]
    for a in sess.legal_actions():
        child=L.GameSession(ctx.compiled);child.submit(a)
        if child.result.winner==0:
            assert child.result.status.value=='checkmate';wins.append(a)
    assert wins,'fixture must have actual Core checkmate at the clock boundary'
    with LastClockShield():assert q(ctx)==S.MATE_SCORE-1
    ctx.runtime.assert_balanced()

def test_other_clocks_keep_original_value_and_no_activation():
    _,ctx=context(L.definition(5,7))
    with LastClockShield()as shield:assert q(ctx)==4242 and not shield.counts
    ctx.runtime.assert_balanced()

def test_hard_limit_aborts_and_restores_original_function():
    _,ctx=context(replace(L.definition(5,7),max_ply=1),hard=0);original=S._quiescence_runtime
    with pytest.raises(S.SearchAborted,match='clock_shield_hard_limit'):
        with LastClockShield():q(ctx)
    assert S._quiescence_runtime is original and not hasattr(S,'_last_clock_ply');ctx.runtime.assert_balanced()

def test_q_expansion_cap_remains_observed():
    _,ctx=context(replace(L.definition(5,7),max_ply=1),qcap=1)
    with pytest.raises(S.SearchAborted,match='qsearch_budget'):
        with LastClockShield():q(ctx)
    ctx.runtime.assert_balanced()

def test_cancellation_remains_authoritative_before_new_expansion():
    class Cancel:
        def is_cancelled(self):return True
    _,ctx=context(replace(L.definition(5,7),max_ply=1),cancel=Cancel())
    with pytest.raises(S.SearchAborted,match='cancelled'):
        with LastClockShield()as shield:q(ctx)
    assert not shield.counts;ctx.runtime.assert_balanced()


def test_neutral_declaration_keeps_original_path(monkeypatch):
    from generic_chess.core.declarations import DeclarationAssessment
    _,ctx=context(replace(L.definition(5,7),max_ply=1))
    monkeypatch.setattr(S,'_declaration_options',lambda *args:(DeclarationAssessment('restart',0,'RESTART'),))
    with LastClockShield()as shield:
        assert q(ctx)==4242 and not shield.counts
    ctx.runtime.assert_balanced()


def test_in_check_last_clock_evasions_keep_original_code():
    r=replace(L.definition(31,31),max_ply=2);base=L.GameSession(L.compile_rule(r));selected=None
    for action in base.legal_actions():
        child=L.GameSession(base.compiled);child.submit(action)
        rt=SearchPathRuntime.from_state(child.state,base.compiled)
        if not child.state.terminal_status.is_terminal and rt.in_check(child.state.position.side_to_move):selected=child;break
    assert selected is not None,'must supply an actual checked, nonterminal history'
    _,ctx=context(r);ctx.runtime=SearchPathRuntime.from_state(selected.state,ctx.compiled)
    old=q(ctx)
    with LastClockShield()as shield:assert q(ctx)==old and not shield.counts
    ctx.runtime.assert_balanced()
