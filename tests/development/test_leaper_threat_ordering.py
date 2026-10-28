"""Contract controls for the threat-specific research orderer, not strength tests."""
import copy,gzip,json
from pathlib import Path
from types import SimpleNamespace
from collections import Counter
import pytest
from scripts.leaper_threat_ordering import ThreatOrderer
from generic_chess.ai.alphabeta.ordering import MoveOrderer
from generic_chess.ai.alphabeta.tuning import SearchTuning
from generic_chess.rules.compiler import compile_legacy_ruleset_for_semantic_execution
from generic_chess.rules.schema import ruleset_from_dict
from generic_chess.session.session import GameSession
from generic_chess.core.coordinates import square_to_index

E=SimpleNamespace(capture_order_value=lambda *_:100000)

def fixture(*,enemy=True,anchor=(4,0)):
    r=json.loads(gzip.decompress(Path('docs/research/data/leaper_root_order_quality_20261026/prepared-v2/inputs.json.gz').read_bytes()))['rows'][0]['RuleSet'];r=copy.deepcopy(r)
    king=[(x,y) for x in (-1,0,1) for y in (-1,0,1) if (x,y)!=(0,0)];w=[(-1,0),(1,0),(0,-1),(0,1)];knight=[(x,y) for x in (-2,-1,1,2) for y in (-2,-1,1,2) if abs(x)+abs(y)==3]
    r.update(board_size=8,max_ply=96,initial_position=[[None]*8 for _ in range(8)],metadata={});r.pop('initial_setup_options',None)
    r['piece_types']=[dict(type_id=t,name=t,is_anchor=t=='K',is_promotable=False,promotion_target_ids=[],movement_atoms=[dict(kind='leap',offset=list(o)) for o in offsets]) for t,offsets in [('K',king),('W',w),('N',knight)]];r['drop_allowed']={t:[[False]*64,[False]*64] for t in ('W','N')}
    for owner,typ,x,y in [(0,'K',*anchor),(0,'W',1,0),(1,'K',7,7)]+([(1,'N',1,3)] if enemy else []):r['initial_position'][y][x]=dict(owner=owner,base_type_id=typ,current_type_id=typ,promoted=False)
    c=compile_legacy_ruleset_for_semantic_execution(ruleset_from_dict(r));s=GameSession(c);assert not s.state.terminal_status.is_terminal;return c,s

def two_actions(s):
    a=s.legal_actions();return [next(x for x in a if getattr(x,'from_square',None) and x.from_square.file==1 and x.from_square.rank==0 and x.to_square.file==dst and x.to_square.rank==0) for dst in (0,2)]

def test_equal_total_coverage_but_specific_threat_and_negative_target_control():
    c,s=fixture();o=ThreatOrderer(c);a,b=two_actions(s);before=s.to_record();f=o.feature(s.state,[a,b]);assert f['target_mask']==(1<<(1*8+2))|(1<<(2*8+3));assert f['scores'][b]>f['scores'][a]
    # Both actions have equal global union delta; feature is not total coverage.
    allf=o.feature(s.state,[a,b],override_targets=(1<<64)-1);assert allf['scores'][a]==allf['scores'][b]
    negative=o.feature(s.state,[a,b],override_targets=(1<<(1*8+0))|(1<<(2*8+7)));assert negative['scores'][a]>negative['scores'][b]
    assert s.to_record()==before

def test_remove_enemy_or_change_parent_anchor_erases_original_feature():
    for kwargs in ({'enemy':False},{'anchor':(7,0)}):
        c,s=fixture(**kwargs);f=ThreatOrderer(c).feature(s.state,two_actions(s));assert f['target_mask']==0;assert set(f['scores'].values())=={0}

def test_permutation_duplicate_actions_protected_stages_stable_ties():
    c,s=fixture();actions=s.legal_actions();a,b=two_actions(s);o=ThreatOrderer(c);t=SearchTuning(use_countermove=True);previous=actions[-1];quiet=[x for x in actions if s.state.position.board[square_to_index(x.to_square,c.board_shape)] is None];tt=quiet[0];killer=quiet[1];counter=quiet[2];o.record_killer(2,killer);o.record_countermove(previous,counter)
    actions=list(actions)+[b];base=MoveOrderer();base._killers=o._killers;base._countermoves=o._countermoves
    old=base.order(s.state,actions,E,2,tt,previous,t);new=o.order(s.state,actions,E,2,tt,previous,t);assert Counter(old)==Counter(new)==Counter(actions)
    for i,x in enumerate(old):
        if x in (tt,killer,counter) or s.state.position.board[square_to_index(x.to_square,c.board_shape)] is not None:assert new[i] is x
    assert o.order(s.state,actions,E,0,tt,previous,t)==base.order(s.state,actions,E,0,tt,previous,t)

def test_allzero_fallback_is_exact_baseline_and_missing_compiled_falls_back():
    c,s=fixture(enemy=False);a=s.legal_actions();t=SearchTuning();base=MoveOrderer().order(s.state,a,E,2,None,None,t);assert ThreatOrderer(c).order(s.state,a,E,2,None,None,t)==base;assert ThreatOrderer().order(s.state,a,E,2,None,None,t)==base

def test_preprocessing_cancel_does_not_publish_partial_cache_or_change_record():
    c,s=fixture();o=ThreatOrderer(c);before=s.to_record();count=0
    def stop():
        nonlocal count
        count+=1
        if count==8:raise RuntimeError('synthetic cancellation')
    with pytest.raises(RuntimeError,match='synthetic'):o.feature(s.state,two_actions(s),stop)
    assert o.tables is None and not o.attempted and s.to_record()==before
    assert o.feature(s.state,two_actions(s)) is not None

def test_actorwise_intersection_forbids_cross_type_spurious_targets():
    c,s=fixture();o=ThreatOrderer(c);o._tables();f,r=o.tables
    # Actual enemy N=b4. Another enemy K=h8 is the only actor given target0 reach;
    # only N has reverse attack from0. Combining unions would invent target0.
    o.tables=({(1,'N',25):0,(1,'K',63):1}, {(1,'N',4):1,(1,'K',4):0});x=o.feature(s.state,two_actions(s));assert x['target_mask']==0

def test_actual_player_policy_context_restores_hook_and_preserves_finite_value_record():
    from scripts.leaper_threat_policy import threat_policy
    from generic_chess.ai.alphabeta.player import AlphaBetaPlayer
    from generic_chess.ai.limits import SearchLimits
    import generic_chess.ai.alphabeta.search as search
    c,s=fixture();before=s.to_record();original=search._Context.__init__;players=[];decisions=[]
    for enabled in (False,True):
        p=AlphaBetaPlayer(c,use_disk_cache=False,tuning=SearchTuning());players.append(p)
        with threat_policy(enabled) as orderers:d=p.choose_action(s,SearchLimits(max_depth=2,max_nodes=50000,quiescence_max_depth=0,quiescence_hard_max_depth=8));decisions.append(d)
        assert s.to_record()==before and d.runtime_depth_balanced and d.completed_depth==2 and d.action in s.legal_actions();assert search._Context.__init__ is original
        if enabled:assert len(orderers)==1 and orderers[0].metrics['calls']>0
    assert decisions[0].score==decisions[1].score;assert players[0]._tt is not players[1]._tt

def test_actual_player_cancel_during_feature_recovers_original_record_and_context(monkeypatch):
    from scripts.leaper_threat_policy import threat_policy
    from generic_chess.ai.alphabeta.player import AlphaBetaPlayer
    from generic_chess.ai.limits import SearchLimits
    import generic_chess.ai.alphabeta.search as search
    c,s=fixture();before=s.to_record();original=search._Context.__init__;old=ThreatOrderer.feature;control={'cancelled':False,'entered':False}
    def feature(self,*a,**kw):
        control.update(cancelled=True,entered=True);return old(self,*a,**kw)
    monkeypatch.setattr(ThreatOrderer,'feature',feature)
    with threat_policy(True):d=AlphaBetaPlayer(c,use_disk_cache=False).choose_action(s,SearchLimits(max_depth=4,max_nodes=50000),cancel_token=SimpleNamespace(is_cancelled=lambda:control['cancelled']))
    assert control['entered'] and d.termination_reason=='cancelled' and s.to_record()==before and d.runtime_depth_balanced;assert search._Context.__init__ is original

def test_changed_iterator_yield_can_precede_cancel_without_child_entry(monkeypatch):
    from scripts.leaper_threat_ordering import _ObservedActions
    from scripts.leaper_threat_policy import threat_policy
    from generic_chess.ai.alphabeta.player import AlphaBetaPlayer
    from generic_chess.ai.limits import SearchLimits
    import generic_chess.ai.alphabeta.search as search
    c,s=fixture();control={'cancelled':False,'children':0,'at_yield':None};old_init=_ObservedActions.__init__;old_negamax=search.negamax
    def initialize(self,values,callback,changed):
        def observed():
            callback();control['at_yield']=control['children'];control['cancelled']=True
        old_init(self,values,observed,changed)
    def negamax(*args,**kwargs):
        if args[4]>0:control['children']+=1
        return old_negamax(*args,**kwargs)
    monkeypatch.setattr(_ObservedActions,'__init__',initialize);monkeypatch.setattr(search,'negamax',negamax)
    with threat_policy(True) as obs:d=AlphaBetaPlayer(c,use_disk_cache=False).choose_action(s,SearchLimits(max_depth=2,max_nodes=50000),cancel_token=SimpleNamespace(is_cancelled=lambda:control['cancelled']))
    assert d.termination_reason=='cancelled' and d.runtime_depth_balanced
    assert control['at_yield'] is not None and control['children']==control['at_yield']
    assert sum(obs[0].yield_counts.values())>0
