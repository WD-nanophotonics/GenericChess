"""Newphase paid-prefix proof+real consumer cost, no new policy/game outcome."""
from pathlib import Path
import hashlib,json,time
from generic_chess.rules.serialization import deserialize_ruleset
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.session.serialization import deserialize_game_record
from generic_chess.session.session import GameSession
from scripts.generic_session_proof_bank import SessionLogicalProofBank
from scripts.generic_session_win_proof_batch_pn import prove_session_win_batch_pn
from scripts.generic_session_win_proof import SessionStrategyCursor
from scripts.generic_win_proof import CertificateVerificationError
OUT=Path('results/dev_aux/task1856')
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def write(n,d):
 with (OUT/n).open('x',encoding='utf-8') as f:json.dump(d,f,indent=2)
def freeze():
 files=[str(Path(__file__).relative_to(Path.cwd())),'scripts/generic_session_proof_bank.py','scripts/generic_session_win_proof_batch_pn.py','scripts/generic_session_win_proof.py','results/dev_aux/task1848/games.jsonl','results/dev_aux/task1848/moves.jsonl','results/dev_aux/task1846/rules.json']
 write('plan.json',dict(question='Does conservative bank reuse save physical cost on the changed node-completed phase workload AFTER actual adopting-cursor verification, unlike old1851query-onlycost?',source_sha={f:sha(f) for f in files},queries=192,capacity=256,whole_seconds=180,pipeline_seconds=2.25,expected_seconds=85,cost_evidence='First192chronological NEWphase queries already paid42.165699proofseconds/594823nodes. Paired cold+bank at most~85s plus qualification, so180sfuse. Input prefix selected by chronology only, not labels or timings. No cohort rerun or cap reset.',scope='Proof+actualSessionCursor qualification only, no normal search/game/WDL. Cold has direct batchproof+oneconsumerverify; bank counts miss fill verify PLUS consumerverify and all hit/admission/key costs. Same2.25pipeline ceiling, independent phase caps, no oldwall-policy identity. Fresh bank, deterministic chronological order, alternate track order.'))
def run():
 p=json.loads((OUT/'plan.json').read_text());assert all(sha(f)==h for f,h in p['source_sha'].items())
 c=compile_ruleset_for_execution(deserialize_ruleset(Path('results/dev_aux/task1846/rules.json').read_text()))
 games={g['slot']:g for g in (json.loads(x) for x in Path('results/dev_aux/task1848/games.jsonl').read_text().splitlines())}
 queries=[json.loads(x) for x in Path('results/dev_aux/task1848/moves.jsonl').read_text().splitlines() if json.loads(x)['proof_reason'] not in ('disabled','verified_strategy','new_proof_disabled')][:p['queries']]
 assert len(queries)==p['queries'];bank=SessionLogicalProofBank(prove_session_win_batch_pn,capacity=p['capacity']);rows=[];start=time.perf_counter();error=None
 with (OUT/'calls.jsonl').open('x',encoding='utf-8') as log:
  try:
   for qi,m in enumerate(queries):
    raw=dict(games[m['slot']]['record']);raw['actions']=raw['actions'][:m['ply']];session=GameSession.replay(c,deserialize_game_record(json.dumps(raw)));assert hashlib.sha256(repr(session.state).encode()).hexdigest()==m['before_state_sha'];caps=m['phase_limits'];methods=['COLD','BANK']
    if qi%2:methods.reverse()
    for method in methods:
     if time.perf_counter()-start>=p['whole_seconds']:raise TimeoutError('frozen whole cap')
     begun=time.perf_counter();hit=False;fill_verified=None;actual_nodes=fill_nodes=consumer_nodes=0;consumer_seconds=0.;adopted=False;consumer_reason=None
     def cancel():return time.perf_counter()-start>=p['whole_seconds'] or time.perf_counter()-begun>=p['pipeline_seconds']
     kwargs=dict(target=m['side'],max_nodes=caps['proof_nodes'],seconds=caps['proof_seconds'],max_depth=64,cancel=cancel)
     if method=='COLD':
      result=prove_session_win_batch_pn(session,**kwargs);actual_nodes=result.nodes
     else:
      receipt=bank.query(session,**kwargs,verification_max_nodes=caps['verification_nodes'],verification_seconds=caps['verification_seconds']);result=receipt.logical_result;hit=receipt.hit;actual_nodes=receipt.actual_proof_nodes;fill_nodes=receipt.actual_verification_nodes;fill_verified=None if receipt.verification is None else receipt.verification['verified']
     if result.status=='PROVEN_WIN' and not cancel():
      try:
       cursor=SessionStrategyCursor(session,result.certificate,max_nodes=caps['verification_nodes'],seconds=min(caps['verification_seconds'],max(0.,p['pipeline_seconds']-(time.perf_counter()-begun))),cancel=cancel)
       consumer_nodes=cursor.receipt['nodes'];consumer_seconds=cursor.receipt['seconds'];consumer_reason=cursor.receipt['reason'];adopted=cursor.choose(session) is not None
      except CertificateVerificationError as ex:
       consumer_nodes=ex.receipt['nodes'];consumer_seconds=ex.receipt['seconds'];consumer_reason=ex.receipt['reason']
     row=dict(query=qi,slot=m['slot'],ply=m['ply'],method=method,status=result.status,reason=result.reason,logical_nodes=result.nodes,actual_proof_nodes=actual_nodes,fill_verification_nodes=fill_nodes,consumer_verification_nodes=consumer_nodes,consumer_verification_seconds=consumer_seconds,consumer_reason=consumer_reason,adoptable_win=adopted,hit=hit,fill_or_historical_verified=fill_verified,seconds=time.perf_counter()-begun,pipeline_expired=time.perf_counter()-begun>=p['pipeline_seconds'])
     rows.append(row);log.write(json.dumps(row)+'\n');log.flush()
    if (qi+1)%32==0:print(json.dumps(dict(queries=qi+1,seconds=round(time.perf_counter()-start,3))),flush=True)
  except BaseException as ex:error=type(ex).__name__+':'+str(ex)
 write('result.json',dict(status='COMPLETE' if error is None else 'PARTIAL_PRESERVED',error=error,calls=len(rows),expected=2*p['queries'],seconds=time.perf_counter()-start,tracks=[dict(method=m,queries=sum(x['method']==m for x in rows),hits=sum(x['method']==m and x['hit'] for x in rows),actual_proof_nodes=sum(x['actual_proof_nodes'] for x in rows if x['method']==m),fill_verification_nodes=sum(x['fill_verification_nodes'] for x in rows if x['method']==m),consumer_verification_nodes=sum(x['consumer_verification_nodes'] for x in rows if x['method']==m),seconds=sum(x['seconds'] for x in rows if x['method']==m),adoptable_wins=sum(x['method']==m and x['adoptable_win'] for x in rows),pipeline_expired=sum(x['method']==m and x['pipeline_expired'] for x in rows)) for m in ('COLD','BANK')],new_native_or_games=0,current_cohort_cache_enabled=False))
if __name__=='__main__':
 import sys
 {'freeze':freeze,'run':run}[sys.argv[1]]()
