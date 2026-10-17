from pathlib import Path
import json,time
from collections import Counter
D=Path('results/dev_aux/task2527');O=Path('results/dev_aux/task2529')
def run():
 start=time.perf_counter();p=json.loads((D/'registration.json').read_text());bad=[];endings=Counter();wdl=Counter();lengths=[];gaps=[]
 for line in(D/'queries.jsonl').open():
  q=json.loads(line)
  if not q['complete']:bad.append({k:q[k]for k in('generator_seed','seed','game','ply','nodes','total_nodes','effective_node_limit','effective_wall_limit','reason')})
 for line in(D/'episodes.jsonl').open():
  e=json.loads(line);endings[e['ending']]+=1;wdl['U'if e['outcome']is None else'D'if e['outcome']==0 else'W0'if e['outcome']==1 else'W1']+=1;lengths.append(len(e['record']['actions'])-len(e['initial_record']['actions']))
 r=json.loads((D/'result.json').read_text())
 for a in r['arms']:
  for s in a['snapshots']:gaps.append(dict(generator_seed=a['generator_seed'],seed=a['seed'],target=s['target_nodes'],actual=s['nodes'],gap=s['target_nodes']-s['nodes'],closed_game=s['game']))
 out=dict(status='CLOSED_ACTUAL_RESOURCE_AND_CHECKPOINT_DIAGNOSTICS',failed_queries=bad,failed_work_nodes=sum(q['nodes']for q in bad),ordinary_full4096_failures=sum(q['effective_node_limit']==p['nodes_per_query']for q in bad),all_failures_last_small_pool=all(q['effective_node_limit']<p['nodes_per_query']and q['total_nodes']==p['nodes_per_arm']for q in bad),endings=dict(endings),actual_train_outcomes=dict(wdl),episode_play_length=dict(min=min(lengths),max=max(lengths),median=sorted(lengths)[len(lengths)//2]),checkpoint_bindings=gaps,max_checkpoint_lag=max(s['gap']for s in gaps),scope='Eachfailedquery/exacteffectivebudget/ending retained; nodepoolfailure notHdraw/OSfault. Nominalmidpointtargets canlagactualclosedepisodework; finalnodesincludesfailedquerywork withnoaction/target. TRAINselfplayoutcomesnotindependentstrength/foeperformance.',seconds=time.perf_counter()-start);(O/'resource-diagnostics.json').write_text(json.dumps(out,indent=2));print(json.dumps({k:v for k,v in out.items()if k not in('failed_queries','checkpoint_bindings')}))
if __name__=='__main__':run()
