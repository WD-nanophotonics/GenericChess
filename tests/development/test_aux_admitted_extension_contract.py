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


def test_cumulative_extension_count_can_belong_only_to_abandoned_iteration(monkeypatch):
    """Actual return-state machine over a declared abstract tree, not a game.

    No Native push/cancellation campaign or real Player is executed. The Python
    abort occurs after a D2 extension, preserving the completed cold D1 result.
    """
    from contextlib import contextmanager
    from types import SimpleNamespace as N
    from generic_chess.ai.alphabeta import search as S
    from generic_chess.ai.alphabeta.statistics import SearchStatistics
    from generic_chess.ai.alphabeta.transposition import TranspositionTable
    from generic_chess.ai.limits import SearchLimits
    edges={'R':[('a','C')],'C':[('b','L')],'L':[('c','T')]}
    def node(name,ply=0):return N(name=name,ply_count=ply,position=N(side_to_move=ply%2),terminal_status=N(is_terminal=False))
    class Runtime:
        def __init__(self):self.state=node('R');self.depth=0
        @property
        def terminal_status(self):return self.state.terminal_status
        def attach_stats(self,stats):pass
        def legal_actions(self,checkpoint=None):return [a for a,_ in edges.get(self.state.name,[])]
        def in_check(self,side,checkpoint=None):return self.state.name=='C'
        @contextmanager
        def pushed(self,action,checkpoint=None):
            old=self.state;self.state=node(dict(edges[old.name])[action],old.ply_count+1);self.depth+=1
            try:yield self
            finally:self.state=old;self.depth-=1
    runtime=Runtime();stats=SearchStatistics();contexts=[];original_context=S._Context
    def context(*args,**kw):
        result=original_context(*args,**kw);contexts.append(result);return result
    monkeypatch.setattr(S.SearchPathRuntime,'from_state',lambda *a,**k:runtime)
    monkeypatch.setattr(S,'_Context',context)
    monkeypatch.setattr(S,'_declaration_options',lambda *a:[])
    monkeypatch.setattr(S,'semantic_engine_for',lambda c:None)
    def quiescence(state,alpha,beta,ply,qdepth,ctx):
        if ctx.first_main_iteration_complete is False:
            assert ctx.stats.main_check_extensions==0
            return 17
        assert ctx.first_main_iteration_complete is True
        assert ctx.stats.main_check_extensions==1
        raise S.SearchAborted('cancelled')
    monkeypatch.setattr(S,'quiescence',quiescence)
    got=S.run_root_search(runtime.state,N(),N(evaluate=lambda state:17),TranspositionTable(),SearchLimits(max_depth=2,max_nodes=10000,quiescence_max_depth=4,quiescence_hard_max_depth=8),None,stats,use_tt=False,use_ordering=False,tuning=S.SearchTuning(use_one_check_extension=True,use_root_tactical=False))
    assert got==('a',-17,('a',),'cancelled')
    assert stats.completed_depth==1 and stats.result_source=='main_iteration'
    assert stats.result_ordinary_qdepth==0 and stats.main_check_extensions==1
    assert contexts[0].first_main_iteration_complete is True
    assert runtime.depth==0 and runtime.state.name=='R'
