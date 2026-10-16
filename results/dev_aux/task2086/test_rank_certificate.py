from pathlib import Path
from dataclasses import replace
import json
import pytest
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.serialization import deserialize_ruleset
from generic_chess.session.session import GameSession
from generic_chess.session.serialization import deserialize_game_record
from generic_chess.session.result import SessionStatus
from scripts.generic_session_win_proof import SessionWinCertificate,verify_session_certificate
from scripts.generic_proof_rnb_bridge import actor_state,uci
from scripts.generic_royal_actor import RoyalActor
from results.dev_aux.task2048.portable_certificate import decode
from results.dev_aux.task2068.teacher import CanonicalTeacher
from results.dev_aux.task2086.rank_certificate import RankCertificateProvider
@pytest.fixture(scope='module')
def objects():
 t=CanonicalTeacher('results/dev_aux/task2056','results/dev_aux/task2058','results/dev_aux/task2059');return t,RankCertificateProvider(t)
def first():
 row=json.loads(Path('results/dev_aux/task2086/certificates.json').read_text())[0];c=compile_ruleset_for_execution(deserialize_ruleset(Path(row['rules']).read_text()));return row,GameSession.replay(c,deserialize_game_record(json.dumps(row['root_record'])))
def test_budget_cancel_and_foreign_rules_unknown(objects):
 t,p=objects;row,s=first();before=s.to_record()
 for kwargs in(dict(max_nodes=0),dict(cancel=lambda:True)):
  r=p(s,target=row['target'],**kwargs);assert r.status=='UNKNOWN'and r.certificate is None
 assert s.to_record()==before
 c=compile_ruleset_for_execution(deserialize_ruleset(Path('results/dev_aux/task2064/rules.json').read_text()));r=p(GameSession(c));assert r.status=='UNKNOWN'and r.reason=='foreign_execution'
def test_real_repeated_history_is_not_table_win(objects):
 t,p=objects;actor=RoyalActor(4);hit=False
 for i in range(16):
  c=compile_ruleset_for_execution(deserialize_ruleset(Path(f'results/dev_aux/task2063/rules-{i}.json').read_text()));s=GameSession(c);root=actor_state(s.state);l=t.rows[t.key(root)]
  if l['label']=='DRAW':continue
  target=root[-1]if l['label']=='WIN'else 1-root[-1]
  def cycle(raw,path):
   if len(path)==4:return path if raw==root else None
   for name,child in actor.moves(raw):
    found=cycle(child,path+[name])
    if found:return found
  path=cycle(root,[])
  if not path:continue
  for name in path:s.submit({uci(a):a for a in s.legal_actions()}[name])
  assert actor_state(s.state)==root and s.result.status is SessionStatus.ONGOING and max(n for _,n in s.state.repetition_counts)==2
  r=p(s,target=target);assert r.status=='UNKNOWN'and r.reason=='history_repeats_outside_positive_guard'and r.certificate is None;hit=True;break
 assert hit

def test_omitted_actual_defense_rejected():
 row,s=first();cert=SessionWinCertificate(s.compiled.ruleset_fingerprint,s.to_record(),s.state,row['target'],decode(row['tree'],s.compiled.ruleset_fingerprint))
 def omit(node,side):
  if side!=cert.target and node.edges:return replace(node,edges=node.edges[:-1]),True
  if not node.edges:return node,False
  choice,child=node.edges[0];new,hit=omit(child,1-side);return replace(node,edges=((choice,new),)+node.edges[1:]),hit
 bad,hit=omit(cert.tree,s.state.position.side_to_move);assert hit
 receipt=verify_session_certificate(s,replace(cert,tree=bad),max_nodes=16384,seconds=.5);assert not receipt['verified']
