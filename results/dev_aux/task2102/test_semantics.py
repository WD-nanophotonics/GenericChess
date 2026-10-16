from pathlib import Path
from copy import copy
import json
import pytest
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.serialization import deserialize_ruleset
from generic_chess.session.session import GameSession
from generic_chess.session.serialization import deserialize_game_record
from generic_chess.session.result import SessionStatus
from scripts.generic_proof_rnb_bridge import uci,actor_state
from scripts.generic_session_win_proof_batch_pn import prove_session_win_batch_pn
from scripts.generic_session_win_proof import verify_session_certificate
from results.dev_aux.task2068.teacher import CanonicalTeacher
from results.dev_aux.task2088.provider import CompositeProvider
from results.dev_aux.task2091.history_rank import HistoryCheckedRankProvider
@pytest.fixture(scope='module')
def teacher():return CanonicalTeacher('results/dev_aux/task2056','results/dev_aux/task2073','results/dev_aux/task2074')

def test_genuine_history_draw_is_not_positional_win(teacher):
 row=json.loads(Path('results/dev_aux/task2101/result.json').read_text(encoding='utf-8'));c=compile_ruleset_for_execution(deserialize_ruleset(Path('results/dev_aux/task2101/rules.json').read_text(encoding='utf-8')));s=GameSession.replay(c,deserialize_game_record(json.dumps(row['root_record'])));before=s.to_record()
 assert s.result.status is SessionStatus.ONGOING and teacher.rows[teacher.key(actor_state(s.state))]['label']=='WIN'
 assert max(n for _,n in s.state.repetition_counts)==2
 r=HistoryCheckedRankProvider(teacher)(s,target=row['target'])
 assert r.status=='UNKNOWN'and r.certificate is None and r.reason=='unsupported_or_actual_strategy_invalid'
 child=copy(s);child.submit({uci(a):a for a in child.legal_actions()}[row['canonical_winning_action']]);assert child.result.status is SessionStatus.REPETITION and child.result.winner is None
 assert s.to_record()==before

def test_real_foreign_rule_fallback_same_PN_work(teacher):
 c=compile_ruleset_for_execution(deserialize_ruleset(Path('results/dev_aux/task2064/rules.json').read_text(encoding='utf-8')));s=GameSession(c);calls=[]
 def fallback(session,**kwargs):
  calls.append(kwargs);return prove_session_win_batch_pn(session,**kwargs)
 p=CompositeProvider(teacher,fallback=fallback)
 for target in(0,1):
  reference=prove_session_win_batch_pn(s,target=target,max_nodes=32,seconds=1.,max_depth=4)
  actual=p(s,target=target,max_nodes=32,seconds=1.,max_depth=4)
  assert actual.status==reference.status and actual.nodes==reference.nodes and actual.reason==reference.reason
  assert calls[-1]['target']==target and calls[-1]['max_nodes']==32 and 0<calls[-1]['seconds']<=1.
  assert p.trace[0]['reason']=='foreign_execution'and p.trace[-1]['phase']=='fallback'
  if actual.certificate:assert verify_session_certificate(s,actual.certificate,max_nodes=16384,seconds=.5)['verified']
