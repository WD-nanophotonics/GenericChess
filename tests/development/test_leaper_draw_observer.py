import pytest
from dataclasses import replace
from scripts import leaper_design as L
from scripts.pure_leaper_search_study import rule
from scripts.leaper_draw_observer import DrawObserver, rule_gate, inventory
from generic_chess.ai.alphabeta import search as S
from generic_chess.ai.alphabeta.player import AlphaBetaPlayer
from generic_chess.ai.alphabeta.tuning import SearchTuning
from generic_chess.ai.limits import SearchLimits

def run(r,s,limits,cancel=None):
    c=L.compile_rule(r)
    return AlphaBetaPlayer(c,use_disk_cache=False,tuning=SearchTuning(use_pvs=True)).choose_action(s,limits,cancel_token=cancel)

def test_real_core_observer_preserves_complete_value_action_work_and_history():
    r=rule(4,1,8); c=L.compile_rule(r);s=L.GameSession(c); before=L.record_value(s.to_record())
    limits=SearchLimits(max_depth=4,max_nodes=30000)
    a=run(r,s,limits)
    with DrawObserver(r) as o: b=run(r,s,limits)
    for k in ('action','score','principal_variation','completed_depth','nodes','qnodes','tt_hits','tt_cutoffs','termination_reason','runtime_pushes','runtime_pops'):
        assert getattr(a,k)==getattr(b,k), k
    # root_tactical_scan (search.py) separately increments nodes and root_scan_nodes.
    # The observer intentionally covers recursive negamax, not that paid scan.
    summary=o.summary(); assert summary['counts']['main_calls']==b.nodes-b.root_scan_nodes
    assert summary['counts']['q_calls']==b.qnodes
    assert L.record_value(s.to_record())==before
    assert not hasattr(S,'_draw_observer')

def test_gate_rejects_rule_semantic_changes_and_inventory_uses_geometry_not_name():
    r=rule(4,1,8);k=next(p for p in r.piece_types if p.is_anchor)
    assert rule_gate(r)==k.type_id
    assert rule_gate(replace(r,stalemate_result='loss')) is None
    assert rule_gate(replace(r,max_ply=95)) is None
    assert rule_gate(replace(r,piece_types=tuple(replace(p,movement_atoms=p.movement_atoms[:-1]) if p.is_anchor else p for p in r.piece_types))) is None
    pos=L.GameSession(L.compile_rule(r)).state.position
    board=tuple(p if p is None or p.current_type_id==k.type_id else None for p in pos.board)
    two=replace(pos,board=board)
    assert inventory(two,k.type_id)
    assert not inventory(pos,k.type_id)
    p=next(p for p in board if p is not None)
    wrong=replace(two,board=tuple(replace(x,promoted=True) if x is p else x for x in board))
    assert not inventory(wrong,k.type_id)

def test_budget_and_cancellation_unwind_tokens_restore_and_keep_history():
    r=rule(4,1,8);s=L.GameSession(L.compile_rule(r));before=L.record_value(s.to_record());original=S.negamax
    with DrawObserver(r) as o:
        class Cancel:
            def is_cancelled(self): return o.counts['main_calls']>=10
        d=run(r,s,SearchLimits(max_depth=8,max_nodes=30000),Cancel())
    assert d.termination_reason=='cancelled'
    assert o.summary()['counts']['main_calls']>=10
    assert d.runtime_pushes==d.runtime_pops
    assert L.record_value(s.to_record())==before
    assert S.negamax is original


def test_context_restores_on_observer_exception():
    r=rule(4,1,8); original=S.negamax; qoriginal=S._quiescence_runtime
    with pytest.raises(RuntimeError,match='injected'):
        with DrawObserver(r): raise RuntimeError('injected')
    assert S.negamax is original and S._quiescence_runtime is qoriginal
    assert not hasattr(S,'_draw_observer')
