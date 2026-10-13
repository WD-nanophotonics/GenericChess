from pathlib import Path
import json,collections,random
from fractions import Fraction as F
R=Path.cwd();O=R/'results/dev_aux/task1129';O.mkdir(exist_ok=False)
def load(t):return [json.loads(x) for x in (R/f'results/dev_aux/task{t}/games.jsonl').read_text().splitlines()]
def canonical(q):
 z=json.loads(json.dumps(q));z.pop('game');lines=[]
 for line in z['metadata']['uci_info']:
  f=line.split();r=[];i=0
  while i<len(f):
   if f[i] in ['time','nps']:i+=2
   else:r.append(f[i]);i+=1
  lines.append(' '.join(r))
 z['metadata']['uci_info']=lines;return z
controls=[];summ=[]
for t in [1118,1121,1127]:
 gs=load(t);j={(g['price'],g['opponent'],g['root']['seed'],g['color']):g for g in gs if g['arm']=='J'};n=0
 for g in gs:
  if g['arm']!='L' or g['price']!=90:continue
  old=j[(90,g['opponent'],g['root']['seed'],g['color'])];assert g['actions']==old['actions'] and g['label']==old['label'] and g['final_fen']==old['final_fen'];assert [canonical(q) for q in g['queries']]==[canonical(q) for q in old['queries']];n+=1
 controls.append(dict(task=t,J90_L90_matched_games=n,all_decisionfields_equal=True))
 for arm in ['J','L']:
  for p in sorted(set(g['price'] for g in gs)):
   xx=[g for g in gs if g['arm']==arm and g['price']==p];cc=collections.Counter(g['label'] for g in xx);summ.append(dict(task=t,arm=arm,price=p,N=len(xx),J24=str(F(cc['W']-cc['L'],len(xx))),counts=dict(cc)))
gs=load(1127);ix={(g['arm'],g['price'],g['opponent'],g['root']['seed'],g['color']):g for g in gs};seeds=sorted(set(g['root']['seed'] for g in gs));comp={g['root']['seed']:g['root']['composition'] for g in gs};groups=[[s for s in seeds if comp[s]==c] for c in sorted(set(comp.values()))];val=lambda g:(g['label']=='W')-(g['label']=='L');unc=[]
for arm,p in [('J',164),('L',671),('J',671),('L',164)]:
 ds={s:sum(val(ix[arm,p,op,s,c])-val(ix[arm,90,op,s,c]) for op in ['unit_search','uniform_random'] for c in [False,True]) for s in seeds};rng=random.Random(2026209999);samples=sorted(sum(ds[rng.choice(group)] for group in groups for _ in group)/256 for _ in range(10000));unc.append(dict(arm=arm,price=p,selected_in_training=(arm,p) in [('J',164),('L',671)],mixed_delta=str(F(sum(ds.values()),256)),bootstrap95=[samples[249],samples[9749]],family_delta_by_composition={c:str(F(sum(ds[s] for s in seeds if comp[s]==c),64)) for c in sorted(set(comp.values()))}))
(O/'result.json').write_text(json.dumps(dict(status='PASS_ALL_BASELINE_CONTROLS_AND64_FAMILY_TRANSFER',controls=controls,rows=summ,uncertainty=unc,new_go=0,scope='Stratifiedfamilydescriptivebootstrap; correlatedcolors/opponents, no equivalence/universalratio orhumanfitnessclaim. No devrefit'),indent=2),encoding='utf-8');print('CONTROLS',controls);print(unc)
