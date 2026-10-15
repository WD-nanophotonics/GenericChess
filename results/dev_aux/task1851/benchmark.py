"""Frozen paired proof-bank cost feasibility on chronological paid queries."""
from pathlib import Path
from dataclasses import replace
import hashlib,json,time
from generic_chess.rules.serialization import deserialize_ruleset
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.session.serialization import deserialize_game_record
from generic_chess.session.session import GameSession
from scripts.generic_session_proof_bank import SessionLogicalProofBank
OUT=Path('results/dev_aux/task1851')
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def write(n,d):
 with (OUT/n).open('x',encoding='utf-8') as f:json.dump(d,f,indent=2)
def freeze():
 files=[str(Path(__file__).relative_to(Path.cwd())),'scripts/generic_session_proof_bank.py','scripts/generic_session_win_proof_pn.py','scripts/generic_session_win_proof.py','results/dev_aux/task1825/games.jsonl','results/dev_aux/task1825/moves.jsonl','results/dev_aux/task1822/rules.json']
 write('plan.json',dict(question='Can conservative completed-result reuse reduce physical proof cost for the first768chronological oldqueries, without confusing logical counts, timeouts or actual verified wins?',source_sha={f:sha(f) for f in files},queries=768,proof_seconds=.0625,proof_depth=64,verification_seconds=.5,verification_nodes=65536,capacity=256,whole_seconds=180,scope='Exposed input replay, no new gameplay/price/labels. Both tracks charge actual replay admission and independent verifier on misses; bank hits retain logical source counts but physical proof0. First query order fixed, per-query method order counterbalanced. Timing/noise may change timeout outcomes: no unchanged-policy or general speedup claim, cache not integrated into chooser.'))
def run():
 p=json.loads((OUT/'plan.json').read_text());assert all(sha(f)==h for f,h in p['source_sha'].items())
 c=compile_ruleset_for_execution(deserialize_ruleset(Path('results/dev_aux/task1822/rules.json').read_text()))
 games={x['slot']:x for x in (json.loads(s) for s in Path('results/dev_aux/task1825/games.jsonl').read_text().splitlines())};queries=[]
 for line in Path('results/dev_aux/task1825/moves.jsonl').read_text().splitlines():
  row=json.loads(line)
  if row['proof_reason'] not in ('disabled','verified_strategy','new_proof_disabled'):queries.append(row)
 queries=queries[:p['queries']];assert len(queries)==p['queries']
 bank=SessionLogicalProofBank(capacity=p['capacity']);rows=[];start=time.perf_counter();error=None
 def cancelled():return time.perf_counter()-start>=p['whole_seconds']
 with (OUT/'calls.jsonl').open('x',encoding='utf-8') as log:
  try:
   for qi,m in enumerate(queries):
    record=dict(games[m['slot']]['record']);record['actions']=record['actions'][:m['ply']]
    session=GameSession.replay(c,deserialize_game_record(json.dumps(record)))
    assert hashlib.sha256(repr(session.state).encode()).hexdigest()==m['before_state_sha']
    methods=['COLD','BANK']
    if qi%2:methods.reverse()
    for method in methods:
     if cancelled():raise TimeoutError('bank feasibility frozen whole cap')
     engine=SessionLogicalProofBank(capacity=1) if method=='COLD' else bank
     q=engine.query(session,target=m['side'],max_nodes=m['budget']//4,seconds=p['proof_seconds'],max_depth=p['proof_depth'],verification_max_nodes=p['verification_nodes'],verification_seconds=p['verification_seconds'],cancel=cancelled)
     r=q.logical_result
     if q.stored and r.status=='PROVEN_WIN':assert q.verification['verified']
     row=dict(query=qi,slot=m['slot'],ply=m['ply'],method=method,target=m['side'],proof_nodes_cap=m['budget']//4,status=r.status,reason=r.reason,logical_nodes=r.nodes,actual_proof_nodes=q.actual_proof_nodes,actual_verification_nodes=q.actual_verification_nodes,seconds=q.seconds,proof_seconds=q.proof_seconds,verification_seconds=q.verification_seconds,origin_reference_seconds=q.origin_reference_seconds,hit=q.hit,stored=q.stored,verified=None if q.verification is None else q.verification['verified'],key_sha=hashlib.sha256(repr(q.key).encode()).hexdigest())
     rows.append(row);log.write(json.dumps(row)+'\n');log.flush()
    if (qi+1)%128==0:print(json.dumps(dict(queries=qi+1,seconds=round(time.perf_counter()-start,3))),flush=True)
  except BaseException as ex:error=type(ex).__name__+':'+str(ex)
 write('result.json',dict(status='COMPLETE' if error is None else 'PARTIAL_PRESERVED',error=error,calls=len(rows),expected=2*p['queries'],seconds=time.perf_counter()-start,tracks=[dict(method=m,queries=sum(x['method']==m for x in rows),hits=sum(x['method']==m and x['hit'] for x in rows),actual_proof_nodes=sum(x['actual_proof_nodes'] for x in rows if x['method']==m),logical_nodes=sum(x['logical_nodes'] for x in rows if x['method']==m),actual_verification_nodes=sum(x['actual_verification_nodes'] for x in rows if x['method']==m),seconds=sum(x['seconds'] for x in rows if x['method']==m),wins=sum(x['method']==m and x['status']=='PROVEN_WIN' for x in rows),time_budget=sum(x['method']==m and x['reason']=='time_budget' for x in rows)) for m in ('COLD','BANK')],current_player_or_old_games_changed=False))
if __name__=='__main__':
 import sys
 {'freeze':freeze,'run':run}[sys.argv[1]]()
