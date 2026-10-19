"""Actual reset-mixture exposure and information, no new search or labels."""
from pathlib import Path
from collections import defaultdict,Counter
from math import sqrt
import json,sys
D=Path('results/dev_aux/task2580')
def run(directory=None):
 d=D if directory is None else Path(directory);plan=json.loads((d/'plan.json').read_text());done=json.loads((d/'result.json').read_text());signals=json.loads((d/'signals.json').read_text());credits={(tuple(r['key']),r['index']):r['credit']for r in signals};counts=defaultdict(Counter);loss=Counter();net=defaultdict(lambda:[0.]*5);abscredit=defaultdict(lambda:[0.]*5);gmap={};roots=defaultdict(set)
 for g in map(json.loads,(d/'games.jsonl').open()):
  k=str((g['seed'],g['method'],g['prefix_plies']));cc=counts[k];cc.update(dict(games=1,nodes=g['nodes'],queries=g['queries'],terms=g['stats']['samples'],actual_terminal=g['outcome']is not None,unknown=g['outcome']is None));cc['role'+str(g['color'])]+=1;loss[k]+=(g['stats']['loss']or 0)*g['stats']['samples'];gmap[g['gameid']]=(k,g)
  roots[k].add(json.dumps(g['initial_record'],sort_keys=True));v=credits[((g['seed'],g['method']),g['index'])]
  for j,x in enumerate(v):net[k][j]+=x;abscredit[k][j]+=abs(x)
 for q in map(json.loads,(d/'queries.jsonl').open()):
  k,g=gmap[q['gameid']];cc=counts[k];cc['candidate_nodes'if q['actor']==g['color']else'foe_nodes']+=q['nodes'];cc['failed_nodes']+=0 if q['complete']else q['nodes']
  if q['observed']:
   cc['observations']+=1;cc['terminal_PV']+=q['pv_terminal'];cc['free_phi_nonzero']+=q['pv_phi']is not None and any(q['pv_phi'][1:])
 rows={}
 for k,c in counts.items():
  assert c['nodes']==c['candidate_nodes']+c['foe_nodes'];v=net[k];a=abscredit[k];rows[k]=dict(counts=dict(c),root_records=len(roots[k]),terms_per_M_all_paid_nodes=c['terms']*1e6/max(1,c['nodes']),nonzero_PV_per_M_all_paid_nodes=c['free_phi_nonzero']*1e6/max(1,c['nodes']),changing_data_loss=loss[k]/max(1,c['terms']),net_credit=v,absolute_episode_credit=a,credit_coherence=[abs(x)/y if y else None for x,y in zip(v,a)])
 assert sum(v['counts']['nodes']for v in rows.values())==done['nodes']
 r=dict(status='PASS_ACTUAL_PREFIX_COUNTS_COSTS_AND_CREDITS',rows=rows,scope='Balanced scheduled episode-cycle is not equal node mixture. Prefix subgroups differ family/weight/visitation/episode cost, not randomized fixed-theta causal credit or strength comparisons. All seeds/prefixes/censored/failed/opponent costs retained; no new label/query/model selection.')
 (d/'distribution.json').write_text(json.dumps(r,indent=2));print(json.dumps({k:dict(games=v['counts']['games'],nodes=v['counts']['nodes'],terms_per_M=v['terms_per_M_all_paid_nodes'])for k,v in rows.items()}))
if __name__=='__main__':run(sys.argv[1]if len(sys.argv)>1 else None)
