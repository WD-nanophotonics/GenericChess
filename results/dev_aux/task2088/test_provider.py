from pathlib import Path
import json
import pytest
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.serialization import deserialize_ruleset
from generic_chess.session.session import GameSession
from results.dev_aux.task2068.teacher import CanonicalTeacher
from results.dev_aux.task2088.provider import CompositeProvider
from scripts.generic_session_win_proof import SessionProofResult

@pytest.fixture(scope='module')
def teacher():
    return CanonicalTeacher('results/dev_aux/task2056','results/dev_aux/task2073','results/dev_aux/task2074')
def session(i=0):
    return GameSession(compile_ruleset_for_execution(deserialize_ruleset(Path(f'results/dev_aux/task2087/rules-{i}.json').read_text(encoding='utf-8'))))
def result(nodes=0,reason='unsupported'):
    return SessionProofResult('UNKNOWN',None,reason,nodes,0.,0)

def test_shared_node_time_and_depth_budget(teacher):
    now=[10.];seen=[]
    def rank(s,**k):
        seen.append(('rank',k));now[0]+=.3;return result(7)
    def fallback(s,**k):
        seen.append(('fallback',k));now[0]+=.2;return result(4)
    p=CompositeProvider(teacher,rank=rank,fallback=fallback)
    # Foreign execution must really reach fallback, not graph-negative skip.
    c=compile_ruleset_for_execution(deserialize_ruleset(Path('results/dev_aux/task2064/rules.json').read_text(encoding='utf-8')))
    r=p(GameSession(c),max_nodes=20,seconds=1.,max_depth=9,_clock=lambda:now[0])
    assert r.nodes==11 and r.seconds==pytest.approx(.5)
    assert [x[0] for x in seen]==['rank','fallback']
    assert seen[1][1]['max_nodes']==13 and seen[1][1]['seconds']==pytest.approx(.7)
    assert seen[1][1]['max_depth']==9

def test_exhaustion_cancel_never_restarts_fallback(teacher):
    s=session();calls=[];now=[0.]
    def fallback(*a,**k):calls.append(k);return result()
    def rank(*a,**k):now[0]+=2.;return result(5)
    p=CompositeProvider(teacher,rank=rank,fallback=fallback)
    r=p._positive(s,target=0,max_nodes=20,seconds=1.,max_depth=64,_clock=lambda:now[0])
    assert r.status=='UNKNOWN' and r.reason=='time_budget' and r.nodes==5 and not calls
    p.rank=lambda *a,**k:result(20)
    r=p._positive(s,target=0,max_nodes=20,seconds=1.,max_depth=64)
    assert r.reason=='node_budget' and not calls
    r=p(s,cancel=lambda:True)
    assert r.reason=='cancelled' and not calls
    with pytest.raises(ValueError):p(s,target=True)

def test_target_sign_and_actual_session_unchanged(teacher):
    seen=[]
    def rank(s,**k):seen.append(k['target']);return result()
    def fallback(s,**k):return result()
    p=CompositeProvider(teacher,rank=rank,fallback=fallback);covered=set()
    for i in range(24):
        s=session(i);value=teacher.label(s).value;before=s.to_record()
        for target in (0,1):
            n=len(seen);r=p(s,target=target)
            v=value if target==s.state.position.side_to_move else -value
            if v<=0:assert r.reason=='certified_complete_graph_no_win' and r.nodes==0 and len(seen)==n;covered.add('negative')
            else:assert len(seen)==n+1 and seen[-1]==target;covered.add('positive')
        assert s.to_record()==before
    assert covered=={'negative','positive'}
