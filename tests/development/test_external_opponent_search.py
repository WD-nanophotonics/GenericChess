"""Real opponent search work is charged; external values never become TD targets."""
from dataclasses import replace
import math
import pytest
from generic_chess.learning.incremental import (
    BudgetEnd,FixedScaleSessionEnv,Model,Receipt,SessionChoice,TDLeafEpisode,play_episode)
from generic_chess.learning.mainline_search import search
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.session.session import GameSession
from scripts.generic_proof_fixtures import krk_ruleset
def env():
    return FixedScaleSessionEnv(GameSession(compile_ruleset_for_execution(krk_ruleset(4))),unit_type='R')
@pytest.mark.parametrize('color',[0,1])
def test_actual_external_search_charged_without_importing_its_values(color):
    e=env();model=Model([1.,.73]);foe=Model([1.,2.3]);calls=[];logged=[]
    def external(state,current,**kw):
        assert current is foe
        r=search(state,current,**kw);calls.append(r)
        # No valid TD value/phi is exported by the policy-only provider.
        return replace(r,value=None,pv_phi=None,pv_terminal=False)
    result=play_episode(e,model,opponent=foe,learner=TDLeafEpisode(),
        learner_color=color,horizon=2,depth=1,query_nodes=2048,max_nodes=4096,
        opponent_search=external,on_query=lambda ply,actor,r:logged.append((actor,r)))
    assert len(calls)==1 and len(logged)==result.queries==result.plies==2
    assert result.nodes==sum(r.nodes for _,r in logged)
    assert result.update['observed_searches']==1
    assert all(r.value is None and r.pv_phi is None for actor,r in logged if actor!=color)
    assert model.fixed==0 and model.weights[0]==1
    e.replay()
def test_external_partial_work_stays_unknown_and_unplayed():
    e=env();before=e.record();seen=[]
    def limited(state,current,**kw):
        r=search(state,current,depth=5,nodes=1,seconds=kw['seconds'],cancel=kw['cancel'])
        seen.append(r);return r
    result=play_episode(e,Model([1.,.73]),opponent=Model([1.,2.3]),
        learner=TDLeafEpisode(),learner_color=1,horizon=2,
        opponent_search=limited,query_nodes=64,max_nodes=64)
    assert not seen[0].complete and result.queries==1 and result.nodes==1
    assert result.outcome is None and result.plies==0 and e.record()==before
    assert result.update['observed_searches']==0
def test_stop_after_external_return_charges_work_but_withholds_move():
    e=env();before=e.record();stop=[False]
    def external(state,current,**kw):return search(state,current,**kw)
    def observed(*args):stop[0]=True
    def cancel():
        if stop[0]:raise BudgetEnd('TEST_USER_STOP')
    result=play_episode(e,Model([1.,.73]),opponent=Model([1.,2.3]),
        learner=TDLeafEpisode(),learner_color=1,horizon=2,depth=1,
        opponent_search=external,on_query=observed,cancel=cancel)
    assert result.queries==1 and result.nodes>0 and result.plies==0
    assert result.ending=='TEST_USER_STOP' and result.outcome is None and e.record()==before
    assert result.update['observed_searches']==0
def test_external_overrun_retains_paid_cost_not_a_draw_or_action():
    e=env();before=e.record()
    def overrun(state,current,**kw):
        r=search(state,current,depth=1,nodes=2048,seconds=2)
        return replace(r,nodes=kw['nodes']+1)
    result=play_episode(e,Model([1.,.73]),opponent=Model([1.,2.3]),
        learner=TDLeafEpisode(),learner_color=1,horizon=1,query_nodes=10,max_nodes=10,
        opponent_search=overrun)
    assert result.nodes==11 and result.queries==1 and result.plies==0
    assert result.ending=='SEARCH_NODE_OVERRUN_UNKNOWN' and result.outcome is None and e.record()==before
def test_ambiguous_policy_and_search_rejected_before_either_callback():
    def forbidden(*a,**k):raise AssertionError('not called')
    with pytest.raises(ValueError,match='choose opponent_policy'):
        play_episode(env(),Model([1.,1.]),opponent=Model([1.,1.]),
            opponent_policy=forbidden,opponent_search=forbidden)
def test_actual_default_public_player_can_supply_policy_only_work_receipt():
    from generic_chess.ai.alphabeta.player import AlphaBetaPlayer
    from generic_chess.ai.alphabeta.tuning import SearchTuning
    from generic_chess.ai.limits import SearchLimits
    from time import perf_counter
    e=env();raw=[]
    def external(state,current,*,depth,nodes,seconds,seed,cancel):
        began=perf_counter();cancel()
        player=AlphaBetaPlayer(state.session.compiled,use_disk_cache=False,
            tuning=SearchTuning(use_capture_only_qsearch=True))
        d=player.choose_action(state.session,SearchLimits(max_depth=depth,
            max_nodes=nodes,max_time_seconds=max(1e-9,seconds-(perf_counter()-began)),
            quiescence_max_depth=4,quiescence_hard_max_depth=8))
        raw.append(d)
        # Action-only policy: no DEFAULT score or q leaf gradient enters TD.
        choice=SessionChoice('ACTION',action=d.action) if d.action is not None else None
        return Receipt(choice,None,None,False,(),d.nodes+d.qnodes,choice is not None,
            0,perf_counter()-began,d.termination_reason)
    model=Model([1.,.73]);result=play_episode(e,model,opponent=Model([1.,2.3]),
        learner=TDLeafEpisode(),learner_color=1,horizon=1,depth=1,
        query_nodes=1024,max_nodes=1024,opponent_search=external)
    assert len(raw)==1 and result.queries==1
    assert result.nodes==raw[0].nodes+raw[0].qnodes and result.nodes>0
    assert result.plies==1 and result.update['observed_searches']==0
    assert model.weights==[1.,.73]
    e.replay()
