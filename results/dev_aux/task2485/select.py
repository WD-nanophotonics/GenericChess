
"""Closed four-family D4 calibration and old D3 context; no reserve activation."""
from pathlib import Path
from collections import Counter
import json,hashlib,time,datetime
OUT=Path('results/dev_aux/task2485')
def load(t):
 f=Path(f'results/dev_aux/task{t}');return json.loads((f/'slots.json').read_text()),{g['slot']:g for g in map(json.loads,(f/'games.jsonl').read_text().splitlines())}
def run():
 t=time.perf_counter();slots,games=load(2479);done=json.loads(Path('results/dev_aux/task2479/completion.json').read_text());rows=[]
 for q in(0.,.5,1.,2.):
  picked=[s for s in slots if s['N_hand']==q];counts=Counter();blocks=[]
  for f in range(4):
   bounds=[]
   for s in picked:
    if s['root']!=f:continue
    g=games.get(s['slot']);r=None if g is None else g['reward'];counts['U'if r is None else g['outcome']]+=1;bounds.append((-1,1)if r is None else(r,r))
   assert len(bounds)==2;blocks.append([sum(b[i]for b in bounds)/2 for i in(0,1)])
  rows.append(dict(N_hand=q,counts=dict(counts),family_bounds=blocks,mean_bounds=[sum(b[i]for b in blocks)/4 for i in(0,1)]))
 base=next(r for r in rows if r['N_hand']==1.);eligible=[r for r in rows if r['mean_bounds'][0]>base['mean_bounds'][1]];selected=min(eligible,key=lambda r:(-r['mean_bounds'][0],r['N_hand']))if eligible else base
 oldplans=[json.loads(Path(f'results/dev_aux/task{x}/plan.json').read_text())for x in(2441,2461)];p=json.loads(Path('results/dev_aux/task2479/plan.json').read_text())
 for old in oldplans:
  assert {k:v for k,v in old['candidate'].items()if k not in('normal_depth','normal_seconds','normal_nodes')}=={k:v for k,v in p['candidate'].items()if k not in('normal_depth','normal_seconds','normal_nodes')}
  assert old['opponents']==[{k:v for k,v in o.items()if k!='normal_depth'}for o in p['opponents']]
  assert old['H']==p['H']==96
 r=dict(status='CLOSED_D4_TRAIN_ONLY_NHAND_CALIBRATION',rows=rows,selected_N_hand=selected['N_hand'],baseline_N_hand=1.,strict_improvement=bool(eligible),actual_new_games=len(games),unreturned=len(slots)-len(games),seconds=time.perf_counter()-t,utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),source_sha=hashlib.sha256(Path('results/dev_aux/task2479/games.jsonl').read_bytes()).hexdigest(),scope='All32NEWfourfamilyTRAIN/D4candidate/fixedoldD3foe. Candidate normal budget12s/65536 differsfromD3old3s/8192; depth+costpolicychange notsame-resourcecausality. Allprooflimits/foe/H96 preserved. Withinnewprices samecandidateceilings. Old32D3calibration notnewreplication. Noholdoutactivation/refit/uniquetrueNclaim. 2481activationusescompletion/strictdepthONLY, nevertheseW-Lprices.')
 (OUT/'selection.json').write_text(json.dumps(r,indent=2));print(json.dumps(r))
if __name__=='__main__':run()
