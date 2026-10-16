"""Independent generic verification of explicit teacher-rank candidates and real rollouts."""
from pathlib import Path
from copy import copy
import json,time,hashlib
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.serialization import deserialize_ruleset
from generic_chess.session.session import GameSession
from generic_chess.session.serialization import deserialize_game_record
from generic_chess.session.result import SessionStatus
from scripts.generic_session_win_proof import SessionChoice,execute
from results.dev_aux.task2320.build import decode
from results.dev_aux.task2320.refutation import verify_no_forced_win,RefutationCursor
from results.dev_aux.task2205.consume import decode_graph
from results.dev_aux.task2199.semantic_graph import verify_graph,GraphStrategyCursor
from results.dev_aux.task2153.stop_evidence import EvidenceStopReader
OUT=Path('results/dev_aux/task2350')
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def run():
 stop=EvidenceStopReader(Path.cwd());t=time.perf_counter();read=lambda p:json.loads(Path(p).read_text());f=Path('results/dev_aux/task2335');p=read(f/'plan.json');inputs=read(f/'inputs.json');r=read(f/'result.json');assert [x['context']for x in inputs]==[0,10,12]and sha(f/'inputs.json')==p['inputs_sha'];assert len(r['rows'])+r['missing']==3
 for n,h in p['pins'].items():assert sha(n)==h
 contexts={x['context']:x for x in inputs};certs={x['context']:x for x in read(f/'certificates.json')};records={x['context']:x for x in read(f/'actual_records.json')};checked=[]
 for q in r['rows']:
  stop();row=contexts[q['context']];c=compile_ruleset_for_execution(deserialize_ruleset(Path(row['rules']).read_text()));s=GameSession.replay(c,deserialize_game_record(json.dumps(row['root_record'])));item=dict(context=q['context'],original_claim=q['claim'],negative=None,positive_opponent=None,actual_plies=0)
  if q['context']not in certs:assert q['claim']=='UNKNOWN';checked.append(item);continue
  raw=certs[q['context']];cert=decode(s,raw['negative']);v=verify_no_forced_win(s,cert,seconds=12.,cancel=stop)
  with(OUT/'verification-attempts.jsonl').open('a')as log:log.write(json.dumps(dict(context=q['context'],kind='NEGATIVE_OFFLINE',result=v))+'\n')
  item['negative']=v
  if not v['verified']:
   assert q['claim']=='UNKNOWN'and v['reason']in('time_budget','node_budget','cancelled'),v;checked.append(item);continue
  if q['claim']=='NO_FORCED_WIN':
   assert q['negative']['verified']and q['current']['verified']and q['negative']['seconds']+q['current']['seconds']<=3.1;cur=RefutationCursor(s,cert,seconds=12.,cancel=stop)
   if raw.get('positive_opponent')is not None:
    positive=decode_graph(s,raw['positive_opponent']);pv=verify_graph(s,positive,seconds=12.,cancel=stop);item['positive_opponent']=pv
    with(OUT/'verification-attempts.jsonl').open('a')as log:log.write(json.dumps(dict(context=q['context'],kind='POSITIVE_OFFLINE',result=pv))+'\n')
    if q['positive_opponent']['verified']:assert pv['verified'],pv
    if q['actual']is not None:
     assert q['positive_opponent']['verified'];pos=GraphStrategyCursor(s,positive,seconds=12.,cancel=stop);record=deserialize_game_record(json.dumps(records[q['context']]['record']));actions=record.actions[len(s.to_record().actions):]
     for a in actions:
      stop();before=copy(s);choice=SessionChoice('ACTION',action=a)
      if s.state.position.side_to_move!=cert.target:assert cur.choose(s)==choice and pos.choose(s)==choice
      execute(s,choice);cur.observe(before,choice,s);pos.observe(before,choice,s)
     assert s.result.status is not SessionStatus.ONGOING and s.result.winner==positive.target==1-cert.target;item['actual_plies']=len(actions)
  else:assert q['claim']=='UNKNOWN'
  checked.append(item)
 result=dict(status='PASS_SELECTED_CONTEXTS_AND_ADMITTED_CERTIFICATES_BOUNDED_UNKNOWN_RETAINED',contexts=len(checked),original_admissions=sum(q['claim']=='NO_FORCED_WIN'for q in r['rows']),independent_candidates=len(certs),offline_verified_negatives=sum(bool(x['negative']and x['negative']['verified'])for x in checked),offline_UNKNOWN_negatives=sum(bool(x['negative']and not x['negative']['verified'])for x in checked),actual_opponent_win_paths=sum(x['actual_plies']>0 for x in checked),actual_qualification_plies=sum(x['actual_plies']for x in checked),rows=checked,seconds=time.perf_counter()-t,scope='GenericindependentCorecheckers/cursors; NOGuideorlabeltableloadedbyconsumer. Explicitteacher-assistedconstructioncostretained; offline12schecksdoNOTupgradeoriginaltimedUNKNOWN orclaimgenericdiscovery/actualDRAW. OpponentWINclaimonlywhenoriginalpositivecheck+realactualcursorpathqualified; no newrewardgames/pricefit.')
 with(OUT/'result.json').open('x')as f:json.dump(result,f,indent=2)
 print(json.dumps({k:v for k,v in result.items()if k!='rows'}))
if __name__=='__main__':run()
