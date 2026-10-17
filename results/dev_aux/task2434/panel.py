"""Complete D3 trees of the frozen TRAIN identities; no reserve query."""
from pathlib import Path
import json,time,hashlib,datetime
from results.dev_aux.task2392.reader import SharedDeleteStopReader
from results.dev_aux.task2430 import margin
OUT=Path('results/dev_aux/task2434')
def run():
 assert not(OUT/'started.json').exists();p=json.loads((OUT/'plan.json').read_text());roots=json.loads(Path(p['input']).read_text());assert hashlib.sha256(Path(p['input']).read_bytes()).hexdigest()==p['input_sha'];stop=SharedDeleteStopReader(Path.cwd());t=time.perf_counter();(OUT/'started.json').write_text(json.dumps(dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),cap=p['cap_seconds'])));results=[]
 for root in roots[:8]:
  stop()
  if time.perf_counter()-t>=p['cap_seconds']:break
  folder=OUT/('family-'+str(root['index']));folder.mkdir();r=dict(root,role='side_to_move',ply=len(root['record']['actions']),saved=[],all_saved_matching_points=[]);(folder/'root.json').write_text(json.dumps(r,indent=2));cp=dict(depth=3,depths=[1,2,3],grid=p['grid'],max_nodes=p['max_nodes_each'],cap_seconds=min(p['cap_seconds']-(time.perf_counter()-t),60.),scope=p['scope'],pins={root['rules']:hashlib.sha256(Path(root['rules']).read_bytes()).hexdigest()});(folder/'plan.json').write_text(json.dumps(cp,indent=2));margin.OUT=folder;margin.run();res=json.loads((folder/'result.json').read_text());vectors=[r['local_PV_feature_difference'][:2]for r in res['margins']if r['finite']and any(r['local_PV_feature_difference'][:2])];rank=0 if not vectors else 2 if any(a[0]*b[1]!=a[1]*b[0]for a in vectors for b in vectors)else 1
  results.append(dict(family=root['index'],status=res['status'],nodes=res['nodes'],active_finite_rank=rank,vectors=vectors,depth_summary=[dict(depth=d,choices=len({json.dumps(x['choice'],sort_keys=True)for x in res['rows']if x['depth']==d}),terminal_chosen=sum(any(a['terminal_priority']and a['choice']==x['choice']for a in x['all_choices'])for x in res['rows']if x['depth']==d))for d in(1,2,3)]))
 vectors=[v for r in results for v in r['vectors']];rank=0 if not vectors else 2 if any(a[0]*b[1]!=a[1]*b[0]for a in vectors for b in vectors)else 1
 out=dict(status='CLOSED_PREFIT_ACTIVE_DIRECTION_FEASIBILITY'if len(results)==8 else'PARTIAL',rows=results,pooled_active_finite_rank=rank,nodes=sum(r['nodes']for r in results),seconds=time.perf_counter()-t,reserve_queries=0,price_fitness_queries=0,scope=p['scope']);(OUT/'result.json').write_text(json.dumps(out,indent=2));print('SUMMARY='+json.dumps({k:v for k,v in out.items()if k!='rows'}))
if __name__=='__main__':run()
