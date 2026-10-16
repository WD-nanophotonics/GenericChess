from pathlib import Path
import json
import pytest
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.serialization import deserialize_ruleset
from generic_chess.session.session import GameSession
from scripts.generic_session_win_proof import SessionProofResult,verify_session_certificate
from results.dev_aux.task2068.teacher import CanonicalTeacher
from results.dev_aux.task2105.provider import TriggerProvider
@pytest.fixture(scope='module')
def teacher():return CanonicalTeacher('results/dev_aux/task2056','results/dev_aux/task2058','results/dev_aux/task2059')
def test_fivepiece_trigger_caps_genericPN_without_price_input(teacher):
 s=GameSession(compile_ruleset_for_execution(deserialize_ruleset(Path('results/dev_aux/task2100/rules-0.json').read_text(encoding='utf-8'))));calls=[]
 def stub(session,**kwargs):calls.append(kwargs);return SessionProofResult('UNKNOWN',None,'small_genericPN',0,0.,0)
 p=TriggerProvider(teacher,solver=stub)
 for target in(0,1):
  r=p(s,target=target,max_nodes=1024,seconds=.2,max_depth=64)
  assert p.last_route=='ABOVE4_SMALL_GENERIC_PN' and r.status=='UNKNOWN'and r.certificate is None
  assert calls[-1]['target']==target and calls[-1]['max_nodes']==32 and calls[-1]['seconds']==.02
 with pytest.raises(ValueError):p(s,target=True)

def test_endgame_true_certificate_or_negativeUNKNOWN(teacher):
 s=GameSession(compile_ruleset_for_execution(deserialize_ruleset(Path('results/dev_aux/task2087/rules-0.json').read_text(encoding='utf-8'))));p=TriggerProvider(teacher);seen=[]
 for target in(0,1):
  r=p(s,target=target);seen.append(r.status);assert p.last_route=='AT_MOST4_QUALIFIED_COMPOSITE'
  if r.status=='PROVEN_WIN':assert verify_session_certificate(s,r.certificate,max_nodes=16384,seconds=.5)['verified']
  else:assert r.status=='UNKNOWN'and r.certificate is None
 assert 'PROVEN_WIN'in seen and 'UNKNOWN'in seen
