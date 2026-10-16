from pathlib import Path
from functools import lru_cache
from copy import copy
import time,json,hashlib
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.serialization import deserialize_ruleset
from generic_chess.session.session import GameSession
from scripts.generic_proof_rnb_bridge import actor_state,uci
from results.dev_aux.task2068.teacher import CanonicalTeacher
from results.dev_aux.task2131.stop_reader import ParsedStopReader
OUT=Path('results/dev_aux/task2141')
def run():
 if(OUT/'started.json').exists():raise RuntimeError('single180cap neverrestart')
 start=time.perf_counter();deadline=start+180;stop=ParsedStopReader(Path.cwd());stop()
 (OUT/'started.json').write_text(json.dumps(dict(source_sha=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),cap_seconds=180)),encoding='utf-8')
 t=CanonicalTeacher('results/dev_aux/task2097','results/dev_aux/task2098','results/dev_aux/task2099');load=time.perf_counter()-start
 rows={r['index']:r for r in t.rows.values()};calls=0
 def poll():
  stop()
  if time.perf_counter()>=deadline:raise TimeoutError('original180cap')
 def edges(r):return [e for e in r['actions']if r['label']=='LOSS'or e['action']==r['winning_action']]
 @lru_cache(None)
 def count(i):
  nonlocal calls
  calls+=1
  if calls%256==0:poll()
  r=rows[i];assert r['label']!='DRAW'and r['rank']is not None
  ee=edges(r)
  if r['rank']==0:assert not ee;return (1,1,0)
  assert ee and all(rows[e['child']]['rank']<r['rank']for e in ee)
  child=[count(e['child'])for e in ee]
  return (1+sum(v[0]for v in child),sum(v[1]for v in child),max(v[2]for v in child)+1)
 inputs=json.loads(Path('results/dev_aux/task2100/inputs.json').read_text(encoding='utf-8'))['roots'];lookup={r['family']:r for r in(json.loads(x)for x in Path('results/dev_aux/task2126/queries-corrected.jsonl').read_text(encoding='utf-8').splitlines())if r['kind']=='INITIAL'and r['depth']==2};result=[]
 for f in (12,30,11):
  c=compile_ruleset_for_execution(deserialize_ruleset(Path(inputs[f]['rules']).read_text(encoding='utf-8')));s=GameSession(c);prior=t.rows[t.key(actor_state(s.state))]['index'];legal={uci(a):a for a in s.legal_actions()}
  cases=[('ROOT_OWN_WIN',s,0)]if f==11 else[(name,copy(s),1)for name in lookup[f]['regions'][0]['top_actions']]
  for name,child,target in cases:
   poll()
   if f!=11:child.submit(legal[name])
   r=t.rows[t.key(actor_state(child.state))];value={'WIN':1,'DRAW':0,'LOSS':-1}[r['label']];value=value if child.state.position.side_to_move==target else-value
   out=dict(family=f,action=name,target=target,positional_target_value=value,rank=r['rank'],prefix_plies=child.state.ply_count,remaining_plies=96-child.state.ply_count)
   if value==1:
    tree,leaves,depth=count(r['index']);seen=set();stack=[r['index']];dag_edges=0
    while stack:
     i=stack.pop()
     if i in seen:continue
     seen.add(i);ee=edges(rows[i]);dag_edges+=len(ee);stack.extend(e['child']for e in ee)
    out.update(unrolled_nodes=tree,unrolled_leaves=leaves,depth=depth,distinct_positional_nodes=len(seen),dag_edges=dag_edges,exceeds1024=tree>1024,prior_root_reachable=(f!=11 and prior in seen),rank_fits_horizon=r['rank']<=96-child.state.ply_count)
   result.append(out)
 out=dict(status='COMPLETE_STORED_STRATEGY_COUNTS_ONLY',rows=result,DP_states=calls,teacher_load_seconds=load,seconds=time.perf_counter()-start,scope='Position graph lowerrepresentationcost diagnostic only; actualhistory maydraw/reject somepaths. NOT fullhistorycertificate orminimumproofsize. No freeDAGverifier ordeploymentclaim.')
 (OUT/'result.json').write_text(json.dumps(out,indent=2),encoding='utf-8');print(json.dumps(out),flush=True)
if __name__=='__main__':run()
