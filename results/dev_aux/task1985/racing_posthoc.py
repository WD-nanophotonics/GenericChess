"""Posthoc racing schedules on the complete observed32family TRAIN table.
No new physical game, prospective optimizer qualification, price selection or DEV read.
"""
from pathlib import Path
import json
OUT=Path('results/dev_aux/task1985')
def run():
 cells={};prices=None
 for cohort in (0,1):
  folder=Path('results/dev_aux/task1979')/f'cohort{cohort}';p=json.loads((folder/'run-plan.json').read_text());prices=p['prices']
  with (folder/'games.jsonl').open() as f:
   for _ in range(416):
    g=json.loads(next(f));assert g['phase']!='DEV';cells[cohort,g['family'],g['R'],g['candidate_side']]=g
 assert len(cells)==832
 full={r:sum(g['finite_event_score'] for (c,f,price,s),g in cells.items() if price==r) for r in prices};best=min(prices,key=lambda r:(-full[r],r));results=[]
 schedules={'cohort0_then1':[(c,f) for c in (0,1) for f in range(16)],'alternate_balanced4familyblocks':[(c,f) for block in range(4) for c in (0,1) for f in range(block*4,block*4+4)]}
 for name,order in schedules.items():
  active=list(prices);seen={};previous=0;rounds=[]
  for end,keep in zip((4,8,16,32),(7,4,2,1)):
   for c,f in order[previous:end]:
    for r in active:
     for side in (0,1):seen[c,f,r,side]=cells[c,f,r,side]
   scores={r:sum(g['finite_event_score'] for (c,f,price,s),g in seen.items() if price==r) for r in active};active=sorted(active,key=lambda r:(-scores[r],r))[:keep];rounds.append(dict(families=end,keep=active,scores=scores));previous=end
  assert len(seen)==288
  selected=active[0];results.append(dict(schedule=name,selected_R=selected,ratio=selected/720,observed_table_calls=288,FULL832_regret=full[best]-full[selected],observed_record_cost_sum=sum(g['seconds'] for g in seen.values()),rounds=rounds))
 result=dict(status='POSTHOC_OBSERVED_TABLE_RACING_NOT_NEW_EXPERIMENT',full_best_R=best,full_best_set=[r for r in prices if full[r]==full[best]],schedules=results,scope='Only first416TRAINrows percohort, no DEV data. Different caseorder not physicallyrerun: wall-dependent policy/time need freshprospective qualification. Observedrecordcostsum is neither new measuredwalltime nor guaranteedtiminggain. Report BOTHchronologies, no favorable selection/defaultadoption or new independentlearner claim.')
 with (OUT/'racing-posthoc.json').open('x') as f:json.dump(result,f,indent=2)
 print(json.dumps({k:v for k,v in result.items() if k!='schedules'}|{'schedules':[{k:v for k,v in s.items() if k!='rounds'} for s in results]}))
if __name__=='__main__':run()
