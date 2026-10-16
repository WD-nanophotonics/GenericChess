from pathlib import Path
from copy import copy
import json,time,hashlib
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.serialization import deserialize_ruleset
from generic_chess.session.session import GameSession
from generic_chess.session.serialization import deserialize_game_record,serialize_game_record
from scripts.generic_session_win_proof import SessionChoice,execute
from generic_chess.session.result import SessionStatus
from results.dev_aux.task2199.semantic_graph import verify_graph,GraphStrategyCursor
from results.dev_aux.task2205.consume import decode_graph
from results.dev_aux.task2153.stop_evidence import EvidenceStopReader
OUT=Path('results/dev_aux/task2383')
def inventory(s):
 b=sum(x is not None for x in s.state.position.board);h=sum(hand.total()for hand in s.state.position.hands);return dict(board=b,hands=h,total=b+h,old_TOTAL4=b+h<=4,new_BOARD4_TOTAL8=b<=4 and b+h<=8)
def run():
 t=time.perf_counter();stop=EvidenceStopReader(Path.cwd());stop();folder=Path('results/dev_aux/task2315');data=json.loads((folder/'result.json').read_text());c=compile_ruleset_for_execution(deserialize_ruleset((folder/'rules.json').read_text()));states=[];edges=0;nonconserved=[];witnesses=[];certs=json.loads((folder/'certificates.json').read_text())
 for row in data['rows']:
  initial=GameSession(c,**({}if row['setup']is None else dict(initial_setup_key=row['setup'])));records=[('initial',json.loads(serialize_game_record(initial.to_record())))]+[(f'prefix{i+1}',p['record'])for i,p in enumerate(row['prefixes'])]
  if 'actual_record'in row:records.append(('actual_terminal',row['actual_record']))
  for name,record in records:
   stop();s=GameSession.replay(c,deserialize_game_record(json.dumps(record)));before=inventory(s);legal=s.legal_actions()if s.result.status is SessionStatus.ONGOING else();childrows=[]
   for action in legal:
    stop();child=copy(s);child.submit(action);after=inventory(child);edges+=1
    if before['total']!=after['total']:nonconserved.append(dict(setup=row['setup'],phase=name,action=repr(action),before=before,after=after))
    childrows.append(dict(action=repr(action),inventory=after,actual_status=child.result.status.value))
   states.append(dict(setup=row['setup'],phase=name,record=record,inventory=before,legal_choices=len(legal),children=childrows,actual_status=s.result.status.value))
  if row.get('verified'):
   s=GameSession.replay(c,deserialize_game_record(json.dumps(row['root_record'])));cert=decode_graph(s,next(x['certificate']for x in certs if x['setup']==row['setup']));v=verify_graph(s,cert,max_nodes=4096,seconds=5.,cancel=lambda:stop()or False)
   with(OUT/'verification-attempts.jsonl').open('a')as fp:fp.write(json.dumps(v)+'\n')
   assert v['verified'];cur=GraphStrategyCursor(s,cert,max_nodes=4096,seconds=5.,cancel=lambda:stop()or False);count=0;startinv=inventory(s)
   while s.result.status is SessionStatus.ONGOING:
    stop();node=cert.nodes[cur.index];ch=cur.choose(s)if s.state.position.side_to_move==cert.target else max(node.edges,key=lambda e:cert.nodes[e[1]].rank)[0];cur.commit(s,ch);count+=1
   assert s.result.winner==cert.target and not startinv['old_TOTAL4']and startinv['new_BOARD4_TOTAL8'];witnesses.append(dict(setup=row['setup'],root_inventory=startinv,verification=v,actual_mate_moves=count,actual_record=json.loads(serialize_game_record(s.to_record())),winner=s.result.winner))
 result=dict(status='PASS_ACTUAL_COMPOSITE_GATE_COUNTEREXAMPLE',states=states,actual_legal_children=edges,nonconserved_edges=nonconserved,witnesses=witnesses,seconds=time.perf_counter()-t,scope='Existing5actor actualcapture/promotion/hand/drop/expiringauxhistories; oldTOTAL4nevereligible alongtheseconservingedges despiteindependentlyverifiedexecutableWIN. NOnewproofquery/noheldoutlearninglabel. NewBOARD4TOTAL8eligibilityisheuristic/finitebudget, notproof/cost/completeness. CapturedpromotedtypeBASE semantics andallfullPosition/history retained. Notuniversalactorconservationunderarbitraryspawn/delete/royalremoval. Unknownswappedbase remainsUNKNOWN.')
 (OUT/'result.json').write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps({k:v for k,v in result.items()if k not in('states','witnesses')}))
if __name__=='__main__':run()
