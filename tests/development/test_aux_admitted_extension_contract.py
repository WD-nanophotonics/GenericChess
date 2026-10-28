"""Real-source coherent consumer counterexamples; no synthetic game outcomes."""
import copy,gzip,json
from pathlib import Path
import pytest
from scripts import verify_aux_admitted_extension_packet as V

@pytest.fixture(scope='module')
def real():
    b=Path('tests/fixtures/aux_admitted_extension_contract_20261029.json.gz').read_bytes()
    assert V.digest(b)=='ef77d35378288c66d1c09c6dde0fe1aa7b709275f6d564ee52eada3e8dc20c0a'
    d=json.loads(gzip.decompress(b));r=d['root'];c=V.compile_legacy_ruleset_for_semantic_execution(V.ruleset_from_dict(r['RuleSet']))
    profile=V.record_value(V.build_ruleset_profile(c,V.EvaluationConfig()))
    return d,c,profile

def start(d,c):return V.GameSession.replay(c,V.deserialize_game_record(json.dumps(d['root']['record'])))
def q(d,i=0):return json.loads(d['qualification'][f'q{i:04d}']['original_utf8'])

def test_actual_source_qualifications_and_submit_accept(real):
    d,c,profile=real;V.qualification_schedule(d['qualification_schedule'],d['root_ids'])
    for i in (0,1):V.verify_return(q(d,i),start(d,c),c,bool(i),profile)
    raw=json.loads(d['first_game_raw']['original_utf8']);e=d['first_game_embedded'];s=start(d,c)
    action,n=V.verify_return(raw,s,c,True,profile);s.submit(action)
    V.check_submission(raw,e,V.record_hash(s))

def test_two_legal_off_qualifications_are_not_two_arm_coverage(real):
    d,c,profile=real
    off=q(d);off['query_id']='q0001'
    # This replacement is independently legal with coherent OFF tuning/counters.
    V.verify_return(off,start(d,c),c,False,profile)
    rows=copy.deepcopy(d['qualification_schedule']);rows[1]['on']=False
    with pytest.raises(AssertionError):V.qualification_schedule(rows,d['root_ids'])

def test_not_run_qualification_cannot_disappear_through_continue(real):
    d,_,_=real;rows=copy.deepcopy(d['qualification_schedule']);rows[1]['status']='NOT_RUN'
    with pytest.raises(AssertionError):V.qualification_schedule(rows,d['root_ids'])

def test_embedded_return_cannot_silently_change_original_score(real):
    d,_,_=real;raw=json.loads(d['first_game_raw']['original_utf8']);embedded=copy.deepcopy(d['first_game_embedded'])
    embedded['decision']['score']+=1
    with pytest.raises(AssertionError):V.check_submission(raw,embedded,embedded['record_after_sha256'])

def test_later_q_context_does_not_relabel_retained_first_iteration(real):
    d,_,profile=real;raw=q(d,1)
    assert raw['decision']['completed_depth']==1 and raw['decision']['termination_reason']=='cancelled'
    assert raw['decision']['main_check_extensions']>0
    V.validate_call(raw,True,profile)
    raw['decision']['result_ordinary_qdepth']=4
    with pytest.raises(AssertionError):V.validate_call(raw,True,profile)

def test_unexpected_completed_source_is_not_accepted_as_generic_legal_return(real):
    d,_,profile=real;raw=q(d);raw['decision']['result_source']='completed_root_win'
    with pytest.raises(AssertionError):V.validate_call(raw,False,profile)

def test_same_profile_in_every_return_can_still_be_the_wrong_profile(real):
    d,_,profile=real;raw=q(d);raw['evaluation_profile']['board_value_by_type']['A']+=1
    with pytest.raises(AssertionError):V.validate_call(raw,False,profile)

def test_request_15_and_frozen_165_eligibility_are_distinct(real):
    d,_,profile=real;raw=q(d);raw['service_wall_seconds']=1.60;raw['timing_eligible']=True
    V.validate_call(raw,False,profile)
    raw['service_wall_seconds']=1.66
    with pytest.raises(AssertionError):V.validate_call(raw,False,profile)

def test_hidden_choose_cap_does_not_match_source_exact_remaining_budget(real):
    d,_,profile=real;raw=q(d);raw['limits']['max_time_seconds']/=2
    with pytest.raises(AssertionError):V.validate_call(raw,False,profile)

def test_root_win_tag_requires_selected_action_to_be_actual_win(real):
    d,c,profile=real;raw=q(d);raw['decision'].update(result_source='root_immediate_win',completed_depth=0,score=V.MATE_SCORE-1)
    # Frozen admission already enumerated this same child's nonterminal result.
    with pytest.raises(AssertionError):V.verify_return(raw,start(d,c),c,False,profile)


@pytest.fixture
def abstract_return_runtime(monkeypatch):
    """Declared finite tree, no game rules or Native backend."""
    from contextlib import contextmanager
    from types import SimpleNamespace as N
    from generic_chess.ai.alphabeta import search as S
    edges={'R':[('a','C')],'C':[('b','L')],'L':[('c','T')]}
    def node(name,ply=0):return N(name=name,ply_count=ply,position=N(side_to_move=ply%2),terminal_status=N(is_terminal=False))
    class Runtime:
        def __init__(self):self.state=node('R');self.depth=0
        @property
        def terminal_status(self):return self.state.terminal_status
        def attach_stats(self,stats):pass
        def legal_actions(self,checkpoint=None):return [a for a,_ in edges.get(self.state.name,[])]
        def in_check(self,side,checkpoint=None):return self.state.name=='C'
        def search_key(self):return ('ABSTRACT_FULL_TREE_HISTORY',self.state.name,self.state.ply_count)
        @contextmanager
        def pushed(self,action,checkpoint=None):
            old=self.state;self.state=node(dict(edges[old.name])[action],old.ply_count+1);self.depth+=1
            try:yield self
            finally:self.state=old;self.depth-=1
    runtime=Runtime()
    monkeypatch.setattr(S.SearchPathRuntime,'from_state',lambda *a,**k:runtime)
    monkeypatch.setattr(S,'_declaration_options',lambda *a:[])
    monkeypatch.setattr(S,'semantic_engine_for',lambda c:None)
    return runtime,S,N


def test_cumulative_extension_count_can_belong_only_to_abandoned_iteration(abstract_return_runtime,monkeypatch):
    """Actual return state machine, abstract D2 abort; no Native failed push."""
    from generic_chess.ai.alphabeta.statistics import SearchStatistics
    from generic_chess.ai.alphabeta.transposition import TranspositionTable
    from generic_chess.ai.limits import SearchLimits
    runtime,S,N=abstract_return_runtime;stats=SearchStatistics();contexts=[];original_context=S._Context
    def context(*args,**kw):
        result=original_context(*args,**kw);contexts.append(result);return result
    monkeypatch.setattr(S,'_Context',context)
    def quiescence(state,alpha,beta,ply,qdepth,ctx):
        if ctx.first_main_iteration_complete is False:
            assert ctx.stats.main_check_extensions==0
            return 17
        assert ctx.first_main_iteration_complete is True and ctx.stats.main_check_extensions==1
        raise S.SearchAborted('cancelled')
    monkeypatch.setattr(S,'quiescence',quiescence)
    got=S.run_root_search(runtime.state,N(),N(evaluate=lambda state:17),TranspositionTable(),SearchLimits(max_depth=2,max_nodes=10000,quiescence_max_depth=4,quiescence_hard_max_depth=8),None,stats,use_tt=False,use_ordering=False,tuning=S.SearchTuning(use_one_check_extension=True,use_root_tactical=False))
    assert got==('a',-17,('a',),'cancelled')
    assert stats.completed_depth==1 and stats.result_source=='main_iteration'
    assert stats.result_ordinary_qdepth==0 and stats.main_check_extensions==1
    assert contexts[0].first_main_iteration_complete is True
    assert runtime.depth==0 and runtime.state.name=='R'


@pytest.mark.parametrize("full_pv",[False,True])
def test_warm_deeper_q4_target_can_return_with_first_q0_metadata(abstract_return_runtime,monkeypatch,full_pv):
    from generic_chess.ai.alphabeta.statistics import SearchStatistics
    from generic_chess.ai.alphabeta.transposition import TranspositionTable,BoundType
    from generic_chess.ai.limits import SearchLimits
    runtime,S,N=abstract_return_runtime;events=[];table=TranspositionTable()
    tuning=S.SearchTuning(use_one_check_extension=True,use_root_tactical=False,require_full_pv=full_pv)
    def quiescence(state,alpha,beta,ply,qdepth,ctx):
        phase=S._ordinary_qdepth_limit(ctx);events.append((state.name,phase))
        return 17 if phase==0 else 11
    monkeypatch.setattr(S,'quiescence',quiescence)
    limits=SearchLimits(max_depth=2,max_nodes=10000,quiescence_max_depth=4,quiescence_hard_max_depth=8)
    warmstats=SearchStatistics()
    ctx=S._Context(N(),N(evaluate=lambda state:17),table,warmstats,S._Budget(limits,None),tuning,True,False,4,8,None,runtime=runtime,first_main_iteration_complete=True)
    prior=S.negamax(runtime.state,2,-S.INF,S.INF,0,ctx)
    assert prior.score==-11 and events==[('T',4)] and warmstats.main_check_extensions==1
    rootentry=table.probe(S._policy_tt_key(runtime.search_key(),ctx,1))
    assert rootentry.depth==2 and rootentry.bound is BoundType.EXACT
    def run(tt):
        stats=SearchStatistics();result=S.run_root_search(runtime.state,N(),N(evaluate=lambda state:17),tt,SearchLimits(max_depth=1,max_nodes=10000,quiescence_max_depth=4,quiescence_hard_max_depth=8),None,stats,use_tt=True,use_ordering=False,tuning=tuning)
        return result,stats
    events.clear();cold,coldstats=run(TranspositionTable())
    assert cold==('a',-17,('a',),'completed_depth') and events==[('C',0)]
    events.clear();hot,hotstats=run(table)
    assert hot==('a',-11,('a',) if full_pv else (),'completed_depth') and events==[]
    if full_pv:
        assert hot[2]==cold[2] and hot[1]!=cold[1] # same literal short leaf, deeper cached score
    assert hotstats.completed_depth==coldstats.completed_depth==1
    assert hotstats.result_ordinary_qdepth==coldstats.result_ordinary_qdepth==0
    assert hotstats.result_source==coldstats.result_source=='main_iteration'
    assert hotstats.tt_hits==1 and hotstats.main_check_extensions==0
    assert runtime.depth==0 and runtime.state.name=='R'


def test_player_q_guard_tracks_configuration_not_internal_first_iteration_phase(monkeypatch):
    """Exercise public caller guard with an abstract return stub, no game."""
    from types import SimpleNamespace as N
    from generic_chess.ai.alphabeta import player as P
    from generic_chess.ai.alphabeta.transposition import BoundType
    from generic_chess.ai.limits import SearchLimits
    player=P.AlphaBetaPlayer(N(),evaluator_override=N(evaluate=lambda s:0))
    marker=('SENTINEL',);player._tt_q_depths=(4,8);player._tt.store(marker,2,7,BoundType.EXACT,'a')
    observed=[]
    def root(state,compiled,evaluator,tt,limits,token,stats,**kwargs):
        observed.append((limits.quiescence_max_depth,tt.probe(marker) is not None))
        return 'a',0,(),'completed_depth'
    monkeypatch.setattr(P,'run_root_search',root)
    session=N(state=N(position=N(side_to_move=0)),result=None,_search_witnesses=None)
    for qdepth in (4,0):player.choose_action(session,SearchLimits(max_depth=1,quiescence_max_depth=qdepth,quiescence_hard_max_depth=8))
    assert observed==[(4,True),(0,False)]
