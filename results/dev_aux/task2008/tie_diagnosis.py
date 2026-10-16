"""Observed racing tie-bias diagnosis, complete existing TRAIN table only."""
from pathlib import Path
import json,random
ROOT=Path('results/dev_aux/task1997');OUT=Path('results/dev_aux/task2008')
def run():
 p=json.loads((ROOT/'run-plan.json').read_text());full=json.loads((ROOT/'FULL-lock-before-dev.json').read_text());race=json.loads((ROOT/'RACE-lock-before-control.json').read_text());rows=[]
 with(ROOT/'games.jsonl').open()as f:
  for _ in range(832):
   g=json.loads(next(f));assert g['phase']!='DEV';rows.append(g)
 grid=p['prices'];cells={(x['family'],x['candidate_side'],x['R']):x for x in rows};assert len(cells)==832
 permutation=list(grid);random.Random(20261016672008).shuffle(permutation);rank={r:i for i,r in enumerate(permutation)}
 results=[]
 for name,tie in [('ACTUAL_NUMERIC',lambda r:r),('ONE_FIXED_RANDOM_TIE',lambda r:rank[r])]:
  active=list(grid);prev=0;selected=[];rounds=[]
  for end,keep in zip((4,8,16,32),(7,4,2,1)):
   selected.extend(cells[f,s,r]for f in range(prev,end)for r in active for s in (0,1))
   scores={r:sum(cells[f,s,r]['finite_event_score']for f in range(end)for s in (0,1))for r in active}
   ordered=sorted(active,key=lambda r:(-scores[r],tie(r)));cut=scores[ordered[keep-1]]
   active=ordered[:keep];rounds.append(dict(families=end,scores=scores,retained=active,cutoff_score=cut,tied_at_cutoff=[r for r,v in scores.items()if v==cut]));prev=end
  chosen=active[0];score=sum(cells[f,s,chosen]['finite_event_score']for f in range(32)for s in (0,1));regret=max(full['scores'].values())-score
  assert len(selected)==288
  results.append(dict(name=name,selected_R=chosen,ratio=chosen/720,FULLtrain_score=score,raw_regret=regret,mean_regret=regret/64,lookup_game_cells=288,lookup_recorded_seconds=sum(g['seconds']for g in selected),rounds=rounds))
 assert results[0]['selected_R']==race['selected_R']and results[0]['raw_regret']==full['RACE_fullTRAIN_regret']
 result=dict(status='PASS_TRAIN_ONLY_POSTHOC_DIAGNOSIS',random_seed=20261016672008,random_tie_permutation=permutation,FULL_R=full['selected_R'],results=results,source='Onlyfirst832TRAINrows read, zeroDEV/newsearch. ONEfixedrandompermutation, noseedselection/actualreplacement. Recordedcellsums notnewchronologicalruntime or prospectiveguarantee.')
 with(OUT/'result.json').open('x')as f:json.dump(result,f,indent=2)
 print(json.dumps({k:v for k,v in result.items()if k!='results'}));print(json.dumps([{k:v for k,v in x.items()if k!='rounds'}for x in results]))
if __name__=='__main__':run()
