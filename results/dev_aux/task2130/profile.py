from pathlib import Path
from collections import Counter
import json,time,hashlib
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.serialization import deserialize_ruleset
from generic_chess.session.session import GameSession
from generic_chess.session.serialization import deserialize_game_record
from scripts.generic_session_native_material import _load_transport
from scripts.generic_proof_player import ProofMaterialPlayer
from scripts.generic_session_win_proof_batch_pn import prove_session_win_batch_pn
from results.dev_aux.task2100.campaign import evaluate
OUT=Path('results/dev_aux/task2130')
def run():
 if(OUT/'started.json').exists():raise RuntimeError('one60cap')
 start=time.perf_counter();deadline=start+60;p=json.loads((OUT/'plan.json').read_text());(OUT/'started.json').write_text(json.dumps(dict(source_sha=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())),encoding='utf-8');stop=_load_transport().stop_check;root=Path.cwd();rows=[];count=0;cost=0.
 def cancelled():
  nonlocal count,cost
  began=time.perf_counter();stop(root);count+=1;cost+=time.perf_counter()-began;return time.perf_counter()>=deadline
 began=time.perf_counter()
 for _ in range(512):
  if cancelled():raise TimeoutError('one60cap')
 micro=dict(calls=count,callback_seconds=cost,loop_seconds=time.perf_counter()-began);files=[]
 for owner,folder in [('DEV_AUX',root),('PRIMARY_SANDBOX',root.parent/'GenericChess 2')]:
  for name in('rollout.json','advisor.json','slack.json'):files.append(dict(owner=owner,file=name,bytes=(folder/'.local_agent'/name).stat().st_size))
 g=json.loads(Path('results/dev_aux/task2100/games.jsonl').read_text().splitlines()[0]);inputs=json.loads(Path('results/dev_aux/task2100/inputs.json').read_text())['roots'];c=compile_ruleset_for_execution(deserialize_ruleset(Path(inputs[g['family']]['rules']).read_text(encoding='utf-8')));s=GameSession(c);record=deserialize_game_record(json.dumps(g['record']))
 for ply in range(8):
  for name in('NORMAL','PN')if ply%2==0 else('PN','NORMAL'):
   count=0;cost=0.;began=time.perf_counter()
   r=ProofMaterialPlayer(c,evaluate(g['ratio']if s.state.position.side_to_move==g['candidate_side']else 1.),proof_enabled=False,max_depth=3).choose(s.state,max_nodes=4096,seconds=.1,cancel=cancelled)if name=='NORMAL'else prove_session_win_batch_pn(s,max_nodes=1024,seconds=.2,max_depth=64,cancel=cancelled)
   elapsed=time.perf_counter()-began;rows.append(dict(ply=ply,kind=name,callback_calls=count,callback_seconds=cost,seconds=elapsed,callback_fraction=cost/elapsed,nodes=r.nodes,reason=r.exit_cause if name=='NORMAL'else r.reason,completed_depth=r.completed_depth if name=='NORMAL'else None))
  s.submit(record.actions[ply])
 result=dict(status='COMPLETE_UNCHANGED_STOP_SEMANTICS_COST_ATTRIBUTION',micro=micro,flag_metadata_only=files,by_kind={k:dict(queries=sum(r['kind']==k for r in rows),callback_calls=sum(r['callback_calls']for r in rows if r['kind']==k),callback_seconds=sum(r['callback_seconds']for r in rows if r['kind']==k),seconds=sum(r['seconds']for r in rows if r['kind']==k))for k in('NORMAL','PN')},seconds=time.perf_counter()-start,scope='Allsixactualflagreadsremainoneveryoriginalcallback. No stopdelay/cache/skip, exclusivity, noisetimingspeedup, orproductionchange. Actualsame-machineconcurrencyisinterpretationlimit; callbackinstrumentationpaidinsidecaps. No rawflagcontentpublished.')
 (OUT/'queries.json').write_text(json.dumps(rows,indent=2),encoding='utf-8');(OUT/'result.json').write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps(result))
if __name__=='__main__':run()
