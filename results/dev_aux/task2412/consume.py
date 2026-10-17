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
OUT=Path('results/dev_aux/task2412')
def run():
 tick=time.perf_counter();stop=SharedDeleteStopReader(Path.cwd());f=Path('results/dev_aux/task2411');result=json.loads((f/'result.json').read_text());certs=json.loads((f/'certificates.json').read_text());rows=[]
 for row in result['rows']:
  stop();c=compile_ruleset_for_execution(deserialize_ruleset(Path(row['rules']).read_text()));s=GameSession.replay(c,deserialize_game_record(json.dumps(row['record'])));board=sum(x is not None for x in s.state.position.board);hands=sum(h.total()for h in s.state.position.hands);assert board==row['board']==4 and hands==row['hands']==row['extra']+1 and row['gate_current']==(board<=4 and board+hands<=8)
  matches=[x for x in certs if x['extra']==row['extra']];assert bool(matches)==row['verified'];r=dict(extra=row['extra'],total=board+hands,gate=row['gate_current'],verified=False)
  if matches:
   cert=decode_graph(s,matches[0]['certificate']);v=verify_graph(s,cert,max_nodes=4096,seconds=5.,cancel=lambda:stop()or False);tree=verify_session_certificate(s,unroll(s,cert),max_nodes=4096,seconds=5.,cancel=lambda:stop()or False);assert v['verified']and tree['verified'];cur=GraphStrategyCursor(s,cert,max_nodes=4096,seconds=5.,cancel=lambda:stop()or False);final=deserialize_game_record(json.dumps(row['actual_record']))
   for a in final.actions[len(s.to_record().actions):]:
    stop();before=copy(s);from scripts.generic_session_win_proof import SessionChoice
    ch=SessionChoice('ACTION',action=a)
    if s.state.position.side_to_move==cert.target:assert cur.choose(s)==ch
    execute(s,ch);cur.observe(before,ch,s)
   assert s.result.status is not SessionStatus.ONGOING and s.result.winner==row['winner']==cert.target;r.update(verified=True,actual_winner=s.result.winner,actual_mate_moves=row['actual_mate_moves'],certificate_nodes=len(cert.nodes))
  rows.append(r)
 out=dict(status='PASS_REAL_HAND_RICH_GATE_WITNESSES',rows=rows,seconds=time.perf_counter()-tick,scope='Independentreconstruction/sameCore+publicfullhistoryverifier. Gatecounterexample only, not currentpolicychange/universalboard-onlypredicate orruntimebenchmark; unknownrowsretainednotdraw. ActualRstockfromtwoeffect-cardinality-compliant captures, no fabricatedPosition/prehistory.')
 (OUT/'result.json').write_text(json.dumps(out,indent=2));print(json.dumps(out))
if __name__=='__main__':run()
