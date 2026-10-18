"""Bounded audit of a closed prefix while the registered producer continues."""
from pathlib import Path
from collections import Counter
from math import isclose
import json,time,hashlib
from results.dev_aux.task2565.train import restore
from results.dev_aux.task2565.audit import advance_env,outcome
from results.dev_aux.task2392.reader import SharedDeleteStopReader
D=Path('results/dev_aux/task2571')
def run():
 began=time.perf_counter();p=json.loads((D/'eval-plan.json').read_text());arms={(a['seed'],a['method']):a for a in json.loads((D/'result.json').read_text())['arms']};stop=SharedDeleteStopReader(Path.cwd());counts=Counter();raw=[]
 with(D/'eval-games.jsonl').open()as f:
  for i in range(384):
   l=f.readline();assert l.endswith(chr(10));raw.append(l)
 qq=iter((D/'eval-queries.jsonl').open());q=json.loads(next(qq));seen=set()
 for l in raw:
  stop();g=json.loads(l);slot=g['slot'];assert slot in p['slots']and tuple(slot)not in seen;seen.add(tuple(slot));gs,seed,fam,color,label,foe=slot;a=arms[seed,'TD'if label=='initial'else label];w=a['initial']if label=='initial'else a['weights'];assert w==g['weights'];e=restore(0,None,g['initial_record']);nodes=nq=0
  while q['slot']==slot:
   assert e.record()==q['record_before']and e.player()==q['actor']and outcome(e,0)is None and q['ply']==nq
   assert q['weights']==(w if e.player()==color else p['foes'][foe]);assert q['ordering_seed']==fam*1000+nq+p['ordering_seed_offset'];assert 0<q['nodes']<=p['nodes_per_query']
   if q['complete']:
    if q['pv_terminal']:assert q['pv_phi']is None and q['value']in(-1000000.,0.,1000000.)
    else:assert isclose(q['value'],sum(x*y for x,y in zip(q['weights'],q['pv_phi'])),rel_tol=1e-12,abs_tol=1e-12)
   else:assert q['pv_phi']is None and q['value']is None
   advance_env(e,0,q['record_after'],q['complete']);nodes+=q['nodes'];nq+=1
   line=next(qq,None);q=None if line is None else json.loads(line)
   if q is None:break
  assert e.record()==g['record']and e.terminal()==g['outcome']and nodes==g['nodes']and nq==g['queries'];assert g['reward']==(None if g['outcome']is None else g['outcome']*(1 if color==0 else-1));counts.update(dict(games=1,nodes=nodes,queries=nq,actual_terminal=g['outcome']is not None,unknown=g['outcome']is None))
 result=dict(status='PASS_CLOSED_PREFIX384_ONLY',counts=dict(counts),games_prefix_sha=hashlib.sha256(''.join(raw).encode()).hexdigest(),seconds=time.perf_counter()-began,scope='First384alreadyclosedgames actualmodels/foes/fullhistory/PV/cost replay whileproducercontinues; NOTfull832completion or extraexperiment/fakeoutcomes. Finalfullaudit remainsrequired.')
 (D/'prefix-audit.json').write_text(json.dumps(result,indent=2));print(json.dumps(result))
if __name__=='__main__':run()
