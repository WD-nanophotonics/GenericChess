"""Supplemental common actual-terminal priority; preserve raw2060 diagnostic."""
from pathlib import Path
import json,numpy as np
from results.dev_aux.task2060.compare import features
OUT=Path('results/dev_aux/task2061')
def run():
 labels=[json.loads(x) for x in Path('results/dev_aux/task2058/labels.jsonl').read_text().splitlines()];models=json.loads(Path('results/dev_aux/task2060/models.json').read_text());splits=[json.loads(x) for x in Path('results/dev_aux/task2060/split.jsonl').read_text().splitlines()];dev=[x['index'] for x in splits if x['phase']=='DEV'];result={}
 for name,w in models.items():
  scores=[]
  for l in labels:
   ids,vals=features(tuple(l['board']));scores.append(sum(w[i]*v for i,v in zip(ids,vals)))
  count=0;optimistic=pessimistic=avg=alloptimal=0.;ties=0
  for i in dev:
   edges=labels[i]['actions'];qs=[-e['child_value'] for e in edges]
   if max(qs)==min(qs):continue
   predicted=[]
   for e in edges:
    child=labels[e['child']]
    # Only actual child terminal facts get infinite priority, not arbitrary exactWDL lookahead.
    v=-scores[e['child']] if child['status']=='ongoing' else (float('inf') if -e['child_value']==1 else -float('inf') if -e['child_value']==-1 else 0.)
    predicted.append(v)
   maximum=max(predicted);top=[j for j,v in enumerate(predicted) if v==maximum or abs(v-maximum)<=1e-9];regret=[max(qs)-qs[j] for j in top]
   count+=1;optimistic+=min(regret);pessimistic+=max(regret);avg+=sum(regret)/len(regret);alloptimal+=max(regret)==0;ties+=len(top)
  result[name]=dict(n=count,optimistic_regret=optimistic/count,pessimistic_regret=pessimistic/count,tie_average_regret=avg/count,all_top_actions_optimal_fraction=alloptimal/count,mean_top_ties=ties/count)
 summary=dict(status='COMPLETE_COMMON_RULE_TERMINAL_PRIORITY_SUPPLEMENT',reason='Raw2060 uses untrained terminal-child heuristics; deployed complete player gives actual rule terminals precedence. Keep raw result; no modelrefit/DEVselection, applysame rule toALLmodels.',models=result,scope='One-step canonicalroot actions only; terminal facts known fromCore, ongoingchildren uselearnedheuristic, not exactQoracle. No actualstrengthclaim.')
 (OUT/'result.json').write_text(json.dumps(summary,indent=2));print(json.dumps(summary))
if __name__=='__main__':run()
