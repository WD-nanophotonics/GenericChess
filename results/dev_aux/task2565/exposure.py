"""Recipe/complete-history overlap, no automatic holdout reclassification."""
from pathlib import Path
from collections import Counter,defaultdict
import json,hashlib,sys
from results.dev_aux.task2565.train import compiled,environment,prefix,restore

def h(r):return hashlib.sha256(json.dumps(r,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def run(directory):
 d=Path(directory);p=json.loads((d/'plan.json').read_text());ep=json.loads((d/'eval-plan.json').read_text());roots=defaultdict(set);counts=Counter();terminal_prefixes=Counter();prefix_plies=Counter();by=defaultdict(Counter)
 for line in(d/'games.jsonl').open():
  g=json.loads(line);k=g['generator_seed'],g['family'];roots[k].add(h(g['initial_record']));method=g['method'];counts[method]+=1;prefix_plies[method]+=len(g['initial_record']['moves']if p['domain']=='chess'else g['initial_record'].get('actions',[]));by[method][h(g['initial_record'])]+=1;terminal_prefixes[method]+=g['queries']==0
 allhash={x for v in roots.values()for x in v};ev=[];ccs={gs:compiled(gs)for gs in ep['rules']}
 for gs in ep['rules']:
  for family in sorted({s[2]for s in ep['slots']}):
   e=environment(gs,ccs[gs]);prefix(e,gs,family,p['prefix_plies']);rr=e.record();ev.append(dict(rule=gs,family=family,record_hash=h(rr),terminal=e.terminal(),current_training_record_overlap=h(rr)in allhash))
 result=dict(status='EXACT_RECIPE_HISTORY_AUDIT',training_games=dict(counts),unique_training_recipe_rules=len(roots),unique_training_fullrecords=len(allhash),unique_roots_by_method={m:len(v)for m,v in by.items()},zeroquery_games=dict(terminal_prefixes),prefix_plies=dict(prefix_plies),eval_roots=ev,eval_unique_fullrecords=len({x['record_hash']for x in ev}),eval_train_overlap=sum(x['current_training_record_overlap']for x in ev),scope='Current96 TRAIN fullrecords only, not all historicalexposure. Fresh recipe IDs do not prove unseen states. Per-role/model/seed repetitions are not independentroots; generated rules TRAINexposed. Prefix and replay work costs are in wall time/explicitplies, not in searchnode budget. Zeroquerygames actualterminalinitialprefixes generate no TD sample.')
 (d/'exposure.json').write_text(json.dumps(result,indent=2));print(json.dumps(result))
if __name__=='__main__':run(sys.argv[1])
