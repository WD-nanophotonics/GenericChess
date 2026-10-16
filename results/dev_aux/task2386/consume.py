from pathlib import Path
from collections import defaultdict
from copy import copy
import json,time,hashlib,statistics
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.serialization import deserialize_ruleset
from generic_chess.session.session import GameSession
from generic_chess.session.serialization import deserialize_game_record,serialize_game_record
from generic_chess.session.result import SessionStatus
from results.dev_aux.task2205.consume import decode_graph
from results.dev_aux.task2199.semantic_graph import verify_graph,GraphStrategyCursor
from results.dev_aux.task2153.stop_evidence import EvidenceStopReader
OUT=Path('results/dev_aux/task2386')
def run():
 t=time.perf_counter();stop=EvidenceStopReader(Path.cwd());stop();f=Path('results/dev_aux/task2381');p=json.loads((f/'plan.json').read_text());cs=json.loads((f/'contexts.json').read_text());done=json.loads((f/'completion.json').read_text());rs=list(map(json.loads,(f/'queries.jsonl').read_text().splitlines()));certs=list(map(json.loads,(f/'certificates.jsonl').read_text().splitlines()));assert done['status']=='COMPLETE'and len(rs)==done['queries']==114 and not done['missing']
 for name,h in p['pins'].items():assert hashlib.sha256(Path(name).read_bytes()).hexdigest()==h
 assert hashlib.sha256((f/'contexts.json').read_bytes()).hexdigest()==p['contexts_sha'];assert len({(r['context'],r['mode'],r['arm'])for r in rs})==114;keys=['status','reason','positions','expanded','transitions','rank','visits','fallbacks','cycles','updates','certificate_sha'];equal=[]
 for ctx in cs:
  group=[r for r in rs if r['context']==ctx['context']and r['mode']=='FIXED_POSITIONS512'];assert len(group)==3 and all(r['reason']not in('time_budget','cancelled')for r in group);assert len({json.dumps({k:r[k]for k in keys},sort_keys=True)for r in group})==1;equal.append(ctx['context'])
 verified=[];moves=0
 for certrow in certs:
  stop();r=rs[certrow['query']];ctx=cs[r['context']];s=GameSession.replay(compile_ruleset_for_execution(deserialize_ruleset(Path(ctx['rules']).read_text())),deserialize_game_record(json.dumps(ctx['record'])));cert=decode_graph(s,certrow['certificate']);v=verify_graph(s,cert,max_nodes=131072,seconds=5.,cancel=lambda:stop()or False)
  with(OUT/'verification-attempts.jsonl').open('a')as out:out.write(json.dumps(dict(query=r['query'],receipt=v))+'\n')
  assert v['verified']and r['verification']['verified'];assert hashlib.sha256(json.dumps(certrow['certificate'],sort_keys=True).encode()).hexdigest()==r['certificate_sha'];cur=GraphStrategyCursor(s,cert,max_nodes=131072,seconds=5.,cancel=lambda:stop()or False);count=0
  while s.result.status is SessionStatus.ONGOING:
   stop();node=cert.nodes[cur.index];ch=cur.choose(s)if s.state.position.side_to_move==ctx['target']else max(node.edges,key=lambda e:cert.nodes[e[1]].rank)[0];cur.commit(s,ch);count+=1
  assert s.result.winner==ctx['target']and count==r['actual_mate']['moves']and json.loads(serialize_game_record(s.to_record()))==r['actual_mate']['record'];moves+=count;verified.append(dict(query=r['query'],context=r['context'],mode=r['mode'],arm=r['arm'],verification=v,actual_moves=count))
 summary=[]
 for mode in p['modes']:
  for arm in p['arms']:
   rows=[r for r in rs if r['mode']==mode and r['arm']==arm];summary.append(dict(mode=mode,arm=arm,queries=len(rows),measured_seconds=sum(r['measured_seconds']for r in rows),expanded=sum(r['expanded']for r in rows),transitions=sum(r['transitions']for r in rows),reader_reads=sum(r['reader_reads']for r in rows),reader_bytes=sum(r['reader_bytes']for r in rows),verified=sum(bool(r['verification']and r['verification']['verified'])for r in rows),converted=sum(r['actual_mate']is not None for r in rows),max_observed_cancel_start_gap=max(r['max_cancel_start_gap_seconds']for r in rows)))
 wall={a:{r['context']for r in rs if r['mode']=='FIXED_WALL8.4'and r['arm']==a and r['verification']and r['verification']['verified']}for a in p['arms']};result=dict(status='PASS_COMPLETE_RUNTIME_RESULT_CERTIFICATE_AND_ACTUAL_MATE_REPLAY',queries=114,distinct_complete_histories=19,original_selected_calls=58,fixed_work_identical_contexts=equal,certificates=len(verified),actual_conversion_moves=moves,summary=summary,wall_verified_contexts={a:sorted(x)for a,x in wall.items()},helper_only_contexts=sorted(wall['SELECTOR16']-wall['BASE']),seconds=time.perf_counter()-t,scope='Original2382helperqualification panel, NOT2384correctedsourceexecutionclaim. Fixedpositionsresult/certificate equality separatelyfromwallcoverage. Persistentstop/exceptionexitcontrolscorrected2384afterthispanel; oldsource/data retained. Bothsamenumericalbudget whiledifferentcompletedwork, nosemanticuniversality/speedguarantee/externalengine. ObservedgapnotstoplatencySLA. 19contextsfrom58calls/8TRAINfamilies/exposed, not19independentsamples; fullorderalternated(BASEfirstvsSELECTORfirst),FILEIOalwaysmiddle. No newprover/game/capreset.')
 (OUT/'result.json').write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps({k:v for k,v in result.items()if k not in('fixed_work_identical_contexts','summary')}));print(json.dumps(summary))
if __name__=='__main__':run()
