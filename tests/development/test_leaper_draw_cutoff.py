from dataclasses import replace
from pathlib import Path
import pytest
from scripts import leaper_design as L
from scripts.leaper_delayed_capture_witness import replay
from scripts.pure_leaper_search_study import rule
from scripts.leaper_draw_cutoff import ProvenDrawCutoff
from generic_chess.ai.alphabeta import search as S
from generic_chess.ai.alphabeta.player import AlphaBetaPlayer
from generic_chess.ai.alphabeta.tuning import SearchTuning
from generic_chess.ai.limits import SearchLimits

def test_paid_twoK_history_true_draw_and_actual_work_reduction():
    import gzip,json
    data=json.loads(gzip.decompress(Path('docs/research/data/leaper_draw_consumer_20261025/inputs.json.gz').read_bytes()))
    case=next(x for x in data['cases']if x['kind']=='paid_twoK_root')
    r=L.ruleset_from_dict(case['rule']);c=L.compile_rule(r);s=replay(c,case['record']);before=L.record_value(s.to_record())
    baseline=AlphaBetaPlayer(c,use_disk_cache=False,tuning=SearchTuning(use_pvs=True)).choose_action(s,SearchLimits(max_depth=6,max_nodes=10000))
    with ProvenDrawCutoff(r,c)as p:
        d=AlphaBetaPlayer(c,use_disk_cache=False,tuning=SearchTuning(use_pvs=True)).choose_action(s,SearchLimits(max_depth=6,max_nodes=10000))
    assert p.counts['cutoffs']>0 and d.score==0 and d.completed_depth==6
    assert d.action in s.legal_actions() and d.nodes+d.qnodes<baseline.nodes+baseline.qnodes
    assert L.record_value(s.to_record())==before
    assert d.runtime_pushes==d.runtime_pops
    assert not hasattr(S,'_draw_cutoff')

def test_unsupported_rule_has_no_policy_change():
    r=replace(rule(4,1,8),stalemate_result='loss');c=L.compile_rule(r);s=L.GameSession(c)
    def play():return AlphaBetaPlayer(c,use_disk_cache=False,tuning=SearchTuning(use_pvs=True)).choose_action(s,SearchLimits(max_depth=3,max_nodes=10000))
    a=play()
    with ProvenDrawCutoff(r,c) as p:b=play()
    assert p.anchor is None and p.counts['cutoffs']==0
    for k in ('action','score','completed_depth','nodes','qnodes','principal_variation','tt_hits','tt_cutoffs'):
        assert getattr(a,k)==getattr(b,k)

def test_clock_scope_geometry_loss_and_unsupported_clocks():
    base=rule(4,1,8)
    for h in (64,96,128):
        r=replace(base,max_ply=h);c=L.compile_rule(r);assert ProvenDrawCutoff(r,c).anchor is not None
    for h in (63,129):
        r=replace(base,max_ply=h);c=L.compile_rule(r);assert ProvenDrawCutoff(r,c).anchor is None
    r=replace(base,repetition_limit=3);c=L.compile_rule(r);assert ProvenDrawCutoff(r,c).anchor is None

def test_live_cancel_preserves_record_and_patch_restore():
    r=rule(4,1,8);c=L.compile_rule(r);s=L.GameSession(c);before=L.record_value(s.to_record());original=S.negamax
    with ProvenDrawCutoff(r,c) as p:
        class Cancel:
            def is_cancelled(self):return p.counts['checks']>=10
        d=AlphaBetaPlayer(c,use_disk_cache=False,tuning=SearchTuning(use_pvs=True)).choose_action(s,SearchLimits(max_depth=10,max_nodes=10000),cancel_token=Cancel())
    assert d.termination_reason=='cancelled' and L.record_value(s.to_record())==before
    assert d.runtime_pushes==d.runtime_pops and S.negamax is original
