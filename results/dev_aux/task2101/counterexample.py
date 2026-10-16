from pathlib import Path
from dataclasses import replace
from copy import copy
import json,time
from generic_chess.rules.serialization import deserialize_ruleset,serialize_ruleset
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.core.pieces import Piece
from generic_chess.session.session import GameSession
from generic_chess.session.serialization import serialize_game_record
from generic_chess.session.result import SessionStatus
from scripts.generic_royal_actor import RoyalActor
from scripts.generic_proof_rnb_bridge import actor_state,uci
from results.dev_aux.task2068.teacher import CanonicalTeacher
from results.dev_aux.task2091.history_rank import HistoryCheckedRankProvider
OUT=Path('results/dev_aux/task2101')
def run():
 if (OUT/'result.json').exists():raise RuntimeError('no rerun')
 start=time.perf_counter();teacher=CanonicalTeacher('results/dev_aux/task2056','results/dev_aux/task2073','results/dev_aux/task2074');actor=RoyalActor(4);base=deserialize_ruleset(Path('results/dev_aux/task2087/rules-0.json').read_text(encoding='utf-8'));checked=0
 for row in teacher.rows.values():
  if time.perf_counter()-start>=120:break
  raw=tuple(row['board'])
  if row['label']!='WIN'or row['status']!='ongoing'or raw[-1]!=1 or any(actor.attacked(raw,actor.king(raw,side),1-side)for side in(0,1)):continue
  a=row['winning_action'];child=dict(actor.moves(raw))[a]
  if any(actor.attacked(child,actor.king(child,side),1-side)for side in(0,1)):continue
  def path3(current,path):
   if len(path)==3:return path if current==raw else None
   for name,nxt in actor.moves(current):
    found=path3(nxt,path+[name])
    if found:return found
  path=path3(child,[]);checked+=1
  if not path:continue
  board=[None if ch=='.'else Piece(int(ch.islower()),ch.upper(),ch.upper())for ch in child[:-1]];rule=replace(base,initial_position=tuple(tuple(board[i:i+4])for i in range(0,16,4)),initial_setup_options=());c=compile_ruleset_for_execution(rule);s=GameSession(c);assert actor_state(s.state)==child
  for name in path+[a]+path:s.submit({uci(x):x for x in s.legal_actions()}[name])
  assert actor_state(s.state)==raw and s.result.status is SessionStatus.ONGOING
  test=copy(s);test.submit({uci(x):x for x in test.legal_actions()}[a]);assert test.result.winner is None and test.result.status is not SessionStatus.ONGOING
  r=HistoryCheckedRankProvider(teacher)(s,target=1,max_nodes=1024,seconds=1.5,max_depth=64)
  assert r.status=='UNKNOWN'and r.certificate is None
  (OUT/'rules.json').write_text(serialize_ruleset(rule),encoding='utf-8');data=dict(status='FOUND_GENUINE_OLD_HISTORY_SPOILS_STORED_POSITIONAL_WIN',candidates_checked=checked,seconds=time.perf_counter()-start,root_record=json.loads(serialize_game_record(s.to_record())),current_board=list(raw),graph_label=row['label'],target=1,canonical_winning_action=a,after_action_actual_status=test.result.status.value,history_checked_provider=dict(status=r.status,reason=r.reason,nodes=r.nodes,seconds=r.seconds),scope='ActualongoinghistorywithtableWIN butstoredpositionalstrategyhitsDRAW; doesNOTproveallactualstrategiesdraw. UNKNOWNnotDRAW, nooldartifact/policychange.')
  (OUT/'result.json').write_text(json.dumps(data,indent=2),encoding='utf-8');print(json.dumps(data));return
 (OUT/'result.json').write_text(json.dumps(dict(status='NO_WITNESS_WITHIN_PREDECLARED_SEARCH',candidates_checked=checked,seconds=time.perf_counter()-start)),encoding='utf-8');print('NO_WITNESS')
if __name__=='__main__':run()
