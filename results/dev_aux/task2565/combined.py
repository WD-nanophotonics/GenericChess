"""Combined actualcosts/allstrata/behavior; no newfitness or posthoc model selection."""
from pathlib import Path
from collections import Counter
import json,hashlib,ast
D=Path('results/dev_aux/task2565')
def run():
 train=[json.loads((D/x/'result.json').read_text())for x in ['chess','generic']];ev=[json.loads((D/x/'eval-result.json').read_text())for x in ['chess','chess-curve','generic']];cost=dict(train_nodes=sum(t['nodes']for t in train),eval_nodes=sum(x['nodes']for x in ev),producer_nodes=sum(t['nodes']for t in train)+sum(x['nodes']for x in ev),producer_seconds=sum(t['seconds']for t in train)+sum(x['seconds']for x in ev),train_trajectories=sum(t['counts']['games']for t in train),train_actual_terminal=sum(t['counts']['actual_terminal']for t in train),train_unknown=sum(t['counts']['unknown']for t in train),train_queries=sum(t['counts']['queries']for t in train),train_td_terms=sum(t['counts']['terms']for t in train),eval_planned=sum(x['expected']for x in ev),eval_executed=sum(x['actual']for x in ev),eval_actual_terminal=sum(x['actual_terminal']for x in ev),eval_unknown=sum(x['unknown']for x in ev),eval_missing=sum(x['missing']for x in ev),eval_queries=sum(x['queries']for x in ev));behavior={};strata={};orders={};unique=set();witnesses=0;rootnodes=0
 for domain in ['chess','generic']:
  sums=json.loads((D/domain/'summary.json').read_text());strata[domain]=[r for r in sums['contrasts']if r['right']=='initial'or(r['right']=='Fixed'and r['stratum']=='all')];rows={tuple(x['slot']):x for x in map(json.loads,(D/domain/'eval-games.jsonl').open())};b=Counter()
  for k,g in rows.items():
   if k[4]!='Fixed':continue
   other=rows.get(k[:4]+('initial',)+k[5:])
   if other is None:b['missing_pair']+=1;continue
   b['pairs']+=1;b['identical_fullrecords']+=g['record']==other['record'];b['different_fullrecords']+=g['record']!=other['record'];a,c=g['reward'],other['reward']
   if a is None or c is None:b['paired_unknown']+=1
   else:b['improved'if a>c else'worse'if a<c else'same_reward']+=1
  behavior[domain]=dict(b)
  arms=json.loads((D/domain/'result.json').read_text())['arms'];ordrows=[]
  for gs in sorted({a['generator_seed']for a in arms}):
   for method in ['Fixed','SelfCandidate','SelfEvery']:
    aa=[a for a in arms if a['generator_seed']==gs and a['method']==method];oo=[sorted(range(len(a['weights'])),key=lambda j:(a['weights'][j],j))for a in aa];ordrows.append(dict(rule=gs,method=method,all4=len(aa)==4,all_raw_total_orders_equal=all(x==oo[0]for x in oo),orders=oo))
  orders[domain]=ordrows;un=json.loads((D/domain/'unpruned.json').read_text());witnesses+=un['verified'];rootnodes+=un['nodes']
  for row in json.loads((D/domain/'witness-queries.json').read_text()):
   q=row['query'];key=dict(domain=domain,rule=q['generator_seed'],record=q['record_before'],weights=q['weights'],depth=2);unique.add(hashlib.sha256(json.dumps(key,sort_keys=True).encode()).hexdigest())
 out=dict(status='ALL96_RECORDED_COSTS_AND_PANELS',cost=cost,behavior=behavior,ordering=orders,witness_checks=witnesses,witness_unique_rule_history_weight_depth_inputs=len(unique),witness_nodes=rootnodes,contrasts=strata,scope='All executed study96 searchnodes inclopponents/initials/failures; TRAINchargedonce, ALLextra snapshotdeploymentcharged. Wall notCPU; audits/engineering/transport additional. Finitebounds notconfidenceintervals; roots/rules exposed asreported. No no-loss/convergence/populationinference from count/rank/order diagnostics.')
 (D/'combined-summary.json').write_text(json.dumps(out,indent=2));print(json.dumps(dict(cost=cost,behavior=behavior,witnesses=witnesses,unique=len(unique),rootnodes=rootnodes,any_unanimous_order={d:any(r['all_raw_total_orders_equal']for r in v)for d,v in orders.items()})))
 print(json.dumps([r for r in strata['generic']if r['left']=='Fixed'and(r['stratum'].startswith('seed')or r['stratum'].startswith('rule'))]))
if __name__=='__main__':run()
