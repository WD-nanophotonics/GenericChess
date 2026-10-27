"""Relative history counts actual main action opportunities, not generated/Q moves."""
from dataclasses import replace
from types import SimpleNamespace
from collections import Counter
import pytest
from scripts import leaper_design as L
from generic_chess.ai.alphabeta.ordering import MoveOrderer
from generic_chess.ai.alphabeta.tuning import SearchTuning
from generic_chess.ai.alphabeta.statistics import SearchStatistics
from generic_chess.ai.alphabeta.player import AlphaBetaPlayer
from generic_chess.ai.limits import SearchLimits
from generic_chess.session.session import GameSession
from generic_chess.core.movement import RayAtom


def fixture():
    c=L.compile_rule(L.definition(1,2));s=GameSession(c)
    return c,s,list(s.legal_actions())


def test_normalization_can_prefer_rare_success_over_frequent_low_yield():
    c,s,actions=fixture();o=MoveOrderer(c);on=SearchTuning(use_relative_history=True)
    ev=SimpleNamespace(capture_order_value=lambda *_:0)
    a,b=actions[:2];o.order(s.state,[a,b],ev,3,None,None,on)
    for i in range(100):
        o.record_attempt(0,a)
        if i<4:o.record_history(0,a,on)
    for i in range(2):o.record_attempt(0,b);o.record_history(0,b,on)
    assert o.relative_history_value(0,a)==5/102
    assert o.relative_history_value(0,b)==3/4
    off=replace(on,use_relative_history=False)
    assert o.order(s.state,[a,b],ev,3,None,None,off)==[a,b]
    assert o.order(s.state,[a,b],ev,3,None,None,on)==[b,a]
    assert o.relative_history_value(1,a)==.5
    assert o.order(s.state,[a,b],ev,-1,None,None,on)==[a,b]
    o.clear();assert not o._relative_attempts and not o._relative_cutoffs


def test_protected_slots_duplicates_and_default_off_stay_exact():
    c,s,actions=fixture();stats=SearchStatistics();o=MoveOrderer(c,stats)
    on=SearchTuning(use_relative_history=True,use_countermove=True);ev=SimpleNamespace(capture_order_value=lambda *_:10**12)
    tt,killer,counter=actions[:3];previous=actions[-1]
    o.record_killer(3,killer);o.record_countermove(previous,counter)
    values=actions+[actions[-1]]
    baseline=o.order(s.state,values,ev,3,tt,previous,replace(on,use_relative_history=False))
    result=o.order(s.state,values,ev,3,tt,previous,on)
    assert Counter(result)==Counter(baseline)
    assert all(result[i] is a for i,a in enumerate(baseline) if a in (tt,killer,counter))
    assert stats.relative_history_attempts==stats.relative_history_cutoffs==0


@pytest.mark.parametrize('enabled',[False,True])
def test_real_search_credits_parent_side_once_before_every_counted_cutoff(monkeypatch,enabled):
    c,s,_=fixture();before=s.to_record();original=MoveOrderer.record_history
    def cutoff(self,player,action,tuning):
        if tuning.use_relative_history and self._relative_allowed:
            assert self._relative_attempts.get((player,action),0)>self._relative_cutoffs.get((player,action),0)
        return original(self,player,action,tuning)
    monkeypatch.setattr(MoveOrderer,'record_history',cutoff)
    p=AlphaBetaPlayer(c,use_disk_cache=False,use_native_semantic_legality=False,
                     tuning=SearchTuning(use_pvs=True,use_relative_history=enabled))
    d=p.choose_action(s,SearchLimits(max_depth=3,max_nodes=100000,max_time_seconds=3,quiescence_max_depth=0))
    assert d.completed_depth==3 and d.runtime_depth_balanced and s.to_record()==before
    if enabled:
        assert d.relative_history_attempts>0 and d.relative_history_cutoffs>0
        assert d.relative_history_attempts<=d.successors_searched
    else:assert d.relative_history_attempts==d.relative_history_cutoffs==0


def test_pvs_research_does_not_duplicate_opportunity_for_same_parent_action(monkeypatch):
    import generic_chess.ai.alphabeta.search as search
    original_search=search.negamax;original_attempt=MoveOrderer.record_attempt
    stack=[];serial=0;child_entries={};attempts={}
    def wrapped(*args,**kwargs):
        nonlocal serial
        previous=kwargs.get('prev_action')
        if stack and previous is not None:
            key=stack[-1],previous
            child_entries[key]=child_entries.get(key,0)+1
        serial+=1;stack.append(serial)
        try:return original_search(*args,**kwargs)
        finally:stack.pop()
    def attempt(self,player,action):
        if self._relative_allowed:
            key=stack[-1],action
            attempts[key]=attempts.get(key,0)+1
        return original_attempt(self,player,action)
    monkeypatch.setattr(search,'negamax',wrapped)
    monkeypatch.setattr(MoveOrderer,'record_attempt',attempt)
    c,s,_=fixture()
    p=AlphaBetaPlayer(c,use_disk_cache=False,use_native_semantic_legality=False,
                     tuning=SearchTuning(use_pvs=True,use_relative_history=True))
    d=p.choose_action(s,SearchLimits(max_depth=4,max_nodes=100000,max_time_seconds=3,quiescence_max_depth=0))
    assert d.completed_depth==4 and d.pvs_researches>0
    assert set(attempts)==set(child_entries)
    assert all(n==1 for n in attempts.values())
    assert any(n>1 for n in child_entries.values())
    assert d.relative_history_attempts==len(attempts)


def test_ray_rule_declines_relative_ranking_and_counters():
    rule=L.definition(1,2);rule=replace(rule,piece_types=rule.piece_types[:2]+(replace(rule.piece_types[2],movement_atoms=(RayAtom((1,0)),)),))
    c=L.compile_rule(rule);s=GameSession(c);o=MoveOrderer(c);ev=SimpleNamespace(capture_order_value=lambda *_:0)
    on=SearchTuning(use_relative_history=True)
    assert o.order(s.state,s.legal_actions(),ev,2,None,None,on)==o.order(s.state,s.legal_actions(),ev,2,None,None,SearchTuning())
    assert o._relative_allowed is False
