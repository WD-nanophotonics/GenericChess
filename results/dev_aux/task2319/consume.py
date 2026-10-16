"""Independent consumer for the saved composite-semantic WIN witness."""
from pathlib import Path
from copy import copy
from dataclasses import replace
import json,time
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.serialization import deserialize_ruleset
from generic_chess.session.session import GameSession
from generic_chess.session.serialization import deserialize_game_record,serialize_game_record
from generic_chess.session.result import SessionStatus
from scripts.generic_session_win_proof import SessionChoice,execute,verify_session_certificate
from results.dev_aux.task2205.consume import decode_graph
from results.dev_aux.task2199.semantic_graph import verify_graph,GraphStrategyCursor,canonical
from results.dev_aux.task2200.controls import unroll
from results.dev_aux.task2153.stop_evidence import EvidenceStopReader
OUT=Path('results/dev_aux/task2319')
def run():
 t=time.perf_counter();stop=EvidenceStopReader(Path.cwd());f=Path('results/dev_aux/task2315');c=compile_ruleset_for_execution(deserialize_ruleset((f/'rules.json').read_text()));result=json.loads((f/'result.json').read_text());raw=json.loads((f/'certificates.json').read_text());assert len(raw)==1;rows=[]
 for row in result['rows']:
  stop();s=GameSession.replay(c,deserialize_game_record(json.dumps(row['root_record'])));assert len(s.to_record().actions)==2 and s.result.status is SessionStatus.ONGOING
  actual_first=GameSession.replay(c,deserialize_game_record(json.dumps(row['prefixes'][0]['record'])));p=actual_first.state.position.board[8];assert(p.owner,p.base_type_id,p.current_type_id,p.promoted)==(0,'P','R',True);assert dict(actual_first.state.position.aux_state)[(0,-1)]==1 and dict(s.state.position.aux_state)[(0,-1)]==0
  expected='R'if row['setup']is None else'P';assert s.state.position.hands[0].count(expected)==1
  canonical_root=canonical(s.state.position,c);assert canonical_root.state.position==s.state.position and canonical_root.legal_actions()==s.legal_actions()
  saved=next((x for x in raw if x['setup']==row['setup']),None)
  if saved is None:assert not row['verified'];rows.append(dict(setup=row['setup'],proof='UNKNOWN,no falseLOSS'));continue
  cert=decode_graph(s,saved['certificate']);v=verify_graph(s,cert,max_nodes=4096,seconds=5.);tree=verify_session_certificate(s,unroll(s,cert),max_nodes=4096,seconds=5.);assert v['verified']and tree['verified'];cur=GraphStrategyCursor(s,cert,seconds=5.);a=cur.choose(s);assert a.action.base_type_id=='R'and a.action.pattern_id.startswith('sem_');before=copy(s);execute(s,a);cur.observe(before,a,s);assert s.result.status is not SessionStatus.ONGOING and s.result.winner==0 and json.loads(serialize_game_record(s.to_record()))==row['actual_record']
  other=GameSession.replay(c,deserialize_game_record(json.dumps(next(r for r in result['rows']if r['setup']=='swapped_bases')['root_record'])));stale=replace(cert,root_record=other.to_record(),root_state=other.state);bad=verify_graph(other,stale,seconds=5.);assert not bad['verified'];assert GameSession.replay(c,s.to_record()).state==s.state
  rows.append(dict(setup=row['setup'],graph=v,fullhistory_tree=tree,actual_semantic_drop_mate=True,wrongbase_rebound_rejected=bad))
 out=dict(status='PASS_SAVED_COMPOSITE_SEMANTIC_FULLHISTORY_GRAPH_TREE_CURSOR',contexts=2,positive_certificates=1,actual_checkmates=1,UNKNOWN=1,rows=rows,seconds=time.perf_counter()-t,scope='NEWfullhistorycapture/basecurrentchange/realauxexpiry+guardeddrop execution. Savednewcertificate, notunsaved2196originalrecovery. ActualfullSessiontreechecker crosscheck; no arbitrarygenerateddomain/WDLpopulation/materialpriceclaim. OtherhandP isUNKNOWN, notLOSS; staleRdrop independentlyrejected.')
 with(OUT/'result.json').open('x')as f:json.dump(out,f,indent=2)
 print(json.dumps({k:v for k,v in out.items()if k!='rows'}))
if __name__=='__main__':run()
