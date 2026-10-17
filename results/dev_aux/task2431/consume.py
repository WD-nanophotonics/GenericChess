from pathlib import Path
from copy import copy
import json,time
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.serialization import deserialize_ruleset
from generic_chess.session.session import GameSession
from generic_chess.session.serialization import deserialize_game_record,serialize_game_record
from generic_chess.session.result import SessionStatus
from scripts.generic_session_win_proof import verify_session_certificate,execute
from results.dev_aux.task2199.semantic_graph import verify_graph,GraphStrategyCursor
from results.dev_aux.task2200.controls import unroll
from results.dev_aux.task2205.consume import decode_graph
from results.dev_aux.task2392.reader import SharedDeleteStopReader
OUT=Path('results/dev_aux/task2431')
def run():
 tick=time.perf_counter();stop=SharedDeleteStopReader(Path.cwd());f=Path('results/dev_aux/task2429');result=json.loads((f/'result.json').read_text());certs=json.loads((f/'certificates.json').read_text());rows=[]
 for row in result['rows']:
  stop();c=compile_ruleset_for_execution(deserialize_ruleset(Path(row['rules']).read_text()));s=GameSession.replay(c,deserialize_game_record(json.dumps(row['record'])));assert all(not x for masks in deserialize_ruleset(Path(row['rules']).read_text()).drop_allowed.values()for mask in masks for x in mask)
  assert dict(s.state.position.hands[0].counts)==({'R':1}if row['setup']is None else{'P':1})
  assert dict(s.state.position.aux_state)[(0,-1)]==0
  promoted=s.state.position.board[8];assert promoted.base_type_id=='P'and promoted.current_type_id=='R'and promoted.promoted
  matches=[x for x in certs if x['setup']==row['setup']];assert bool(matches)==row['verified'];r=dict(setup=row['setup'],verified=False,unproved_is_UNKNOWN=not row['verified'])
  if matches:
   cert=decode_graph(s,matches[0]['certificate']);v=verify_graph(s,cert,max_nodes=4096,seconds=5.,cancel=lambda:stop()or False);tree=verify_session_certificate(s,unroll(s,cert),max_nodes=4096,seconds=5.,cancel=lambda:stop()or False);assert v['verified']and tree['verified'];cur=GraphStrategyCursor(s,cert,max_nodes=4096,seconds=5.,cancel=lambda:stop()or False);final=deserialize_game_record(json.dumps(row['actual_record']))
   for a in final.actions[len(s.to_record().actions):]:
    stop();before=copy(s);from scripts.generic_session_win_proof import SessionChoice
    ch=SessionChoice('ACTION',action=a)
    if s.state.position.side_to_move==cert.target:assert cur.choose(s)==ch
    execute(s,ch);cur.observe(before,ch,s)
   assert len(final.actions)==len(row['record']['actions'])+1;last=final.actions[-1];assert last.pattern_id.startswith('sem_01_hand_R_unlocks_rook_quiet')and not s.state.position.hands[0].counts;assert s.result.status is not SessionStatus.ONGOING and s.result.winner==row['winner']==cert.target;r.update(verified=True,actual_winner=s.result.winner,actual_mate_moves=row['actual_mate_moves'],certificate_nodes=len(cert.nodes))
  rows.append(r)
 out=dict(status='PASS_REAL_ORDINARY_HAND_CONSUMPTION_WIN',rows=rows,seconds=time.perf_counter()-tick,scope='Independentreconstruction/sameCore+publicfullhistoryverifier. No-drop ordinaryhandconsumingmatequalification only, not pricelearning or globalinertclassifier; unknownrowsretainednotdraw. ActualRstockfromonecompliantcapture/promote/expiry pluskingreply, no fabricatedPosition/prehistory.')
 (OUT/'result.json').write_text(json.dumps(out,indent=2));print(json.dumps(out))
if __name__=='__main__':run()
