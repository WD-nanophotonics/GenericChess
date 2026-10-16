"""All three old canonical-LOSS contexts; explicit paid reference-rank construction."""
from pathlib import Path
from copy import copy
import json,time,datetime,hashlib,sys
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.serialization import deserialize_ruleset
from generic_chess.session.session import GameSession
from generic_chess.session.serialization import deserialize_game_record,serialize_game_record
from generic_chess.session.result import SessionStatus
from scripts.generic_session_win_proof import SessionChoice,execute
from scripts.generic_win_proof import _ordered
from scripts.generic_proof_rnb_bridge import actor_state
from results.dev_aux.task2251.study import Guide
from results.dev_aux.task2335.rank_build import discover,encode
from results.dev_aux.task2320.refutation import verify_no_forced_win,RefutationCursor
from results.dev_aux.task2199.semantic_graph import canonical,verify_graph,GraphStrategyCursor
from results.dev_aux.task2179.graph import GraphNode,GraphCertificate
from results.dev_aux.task2181.run import encode as positive_encode
from results.dev_aux.task2153.stop_evidence import EvidenceStopReader
OUT=Path('results/dev_aux/task2335')
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def key(raw):return ''.join(raw[:-1])+str(raw[-1])
def freeze():
 contexts=json.loads(Path('results/dev_aux/task2311/inputs.json').read_text())['contexts'];labels=json.loads(Path('results/dev_aux/task2312/result.json').read_text())['rows'];selected=[contexts[r['context']] for r in labels if r['canonical_mover_label']=='LOSS'];assert [r['context']for r in selected]==[0,10,12]
 with(OUT/'inputs.json').open('x')as f:json.dump(selected,f,indent=2)
 p=dict(question='Can opponent WIN-rank defense compact ALLthree previous referenceLOSS negative candidates enough for12s admission; do separate actual-history positive-opponent certificates prove LOSS?',caller_seconds=12.,proof_seconds=8.4,shared_verification_seconds=3.,cap_seconds=120,estimated_seconds=45,expected=3,qualification_seconds=5.,inputs_sha=sha(OUT/'inputs.json'),pins={n:sha(n)for n in('results/dev_aux/task2335/study.py','results/dev_aux/task2335/rank_build.py','results/dev_aux/task2320/refutation.py','results/dev_aux/task2199/semantic_graph.py','results/dev_aux/task2251/study.py')},scope='ALL3oldcanonicalLOSScontexts selectedaslabel-tier/costqualification, NOTnewW-Lpopulation orfreegenericdiscovery. Explicitprepaid2248/2249/2250teacher. NewWINrankdefense changesoldsafehashwhichcanchooseDRAW; old60cap/UNKNOWN untouched. Caller12/proof8.4/shared3negativechecks; positiveopponentverification+actualrolloutseparatequalificationpaid. No player/filter/reward/default/PRIMARYadoption.')
 with(OUT/'plan.json').open('x')as f:json.dump(p,f,indent=2)
def run():
 assert not(OUT/'started.json').exists();p=json.loads((OUT/'plan.json').read_text());assert sha(OUT/'inputs.json')==p['inputs_sha']
 for n,h in p['pins'].items():assert sha(n)==h
 stop=EvidenceStopReader(Path.cwd());start=time.perf_counter()
 def cancel():stop();return time.perf_counter()-start>=p['cap_seconds']
 with(OUT/'started.json').open('x')as f:json.dump(dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),plan_sha=sha(OUT/'plan.json')),f)
 tick=time.perf_counter();guide=Guide();teacher_load=time.perf_counter()-tick;rows=[];certs=[];records=[]
 for r in json.loads((OUT/'inputs.json').read_text()):
  if cancel():break
  c=compile_ruleset_for_execution(deserialize_ruleset(Path(r['rules']).read_text()));s=GameSession.replay(c,deserialize_game_record(json.dumps(r['root_record'])));tick=time.perf_counter();result=discover(s,seconds=p['proof_seconds'],cancel=cancel,guide=guide);cert=result.pop('certificate');q=dict(context=r['context'],discovery=result,negative=None,current=None,claim='UNKNOWN',positive_opponent=None,actual=None)
  if cert is not None:
   certs.append(dict(context=r['context'],negative=encode(cert)));deadline=min(tick+p['caller_seconds'],time.perf_counter()+p['shared_verification_seconds']);v=verify_no_forced_win(s,cert,seconds=max(0.,deadline-time.perf_counter()),cancel=cancel,return_positions=True)
   if isinstance(v,tuple):
    q['negative'],positions=v
    try:
     cur=RefutationCursor(s,cert,seconds=max(0.,deadline-time.perf_counter()),cancel=cancel);q['current']=cur.receipt;q['claim']='NO_FORCED_WIN'
    except ValueError as error:q['cursor_failure']=str(error)
   else:q['negative']=v
  q['query_seconds']=time.perf_counter()-tick
  if q['claim']=='NO_FORCED_WIN':
   qualify_start=time.perf_counter();nodes=[]
   for i,node in enumerate(cert.nodes):
    state=canonical(positions[i],c);terminal=state.result.status is not SessionStatus.ONGOING;rank=0 if terminal else guide.rows[key(actor_state(state.state))]['rank'];assert rank is not None
    nodes.append(GraphNode(rank=rank,edges=node.edges,terminal=state.result if terminal else None))
   opposite=GraphCertificate(c.ruleset_fingerprint,s.to_record(),s.state,1-cert.target,tuple(nodes));v=verify_graph(s,opposite,seconds=p['qualification_seconds'],cancel=cancel);q['positive_opponent']=v;certs[-1]['positive_opponent']=positive_encode(opposite)
   if v['verified']:
    pos=GraphStrategyCursor(s,opposite,seconds=p['qualification_seconds'],cancel=cancel);steps=0
    while s.result.status is SessionStatus.ONGOING:
     if cancel()or time.perf_counter()-qualify_start>=p['qualification_seconds']:raise TimeoutError('qualification_cap')
     before=copy(s);choice=cur.choose(s)if s.state.position.side_to_move!=cert.target else SessionChoice('ACTION',action=_ordered(s.legal_actions())[0]);execute(s,choice);cur.observe(before,choice,s);pos.observe(before,choice,s);steps+=1
    assert s.result.winner==opposite.target;q['actual']=dict(plies=steps,winner=s.result.winner,status=s.result.status.value);records.append(dict(context=r['context'],record=json.loads(serialize_game_record(s.to_record())),plies=steps));q['actual_history_claim']='MOVER_FORCED_LOSS_CERTIFIED_BY_OPPONENT_WIN'
   q['qualification_seconds']=time.perf_counter()-qualify_start
  rows.append(q);print(json.dumps(dict(context=r['context'],negative=q['claim'],nodes=result['positions'],query_seconds=q['query_seconds'],positive_opponent=bool(q['positive_opponent']and q['positive_opponent']['verified']))),flush=True)
 for name,value in(('certificates.json',certs),('actual_records.json',records),('result.json',dict(status='COMPLETE'if len(rows)==3 else'PARTIAL_GLOBAL_CAP',rows=rows,expected=3,missing=3-len(rows),teacher_load_seconds=teacher_load,seconds=time.perf_counter()-start,scope=p['scope']))):
  with(OUT/name).open('x')as f:json.dump(value,f,indent=2)
if __name__=='__main__':{'freeze':freeze,'run':run}[sys.argv[1]]()
