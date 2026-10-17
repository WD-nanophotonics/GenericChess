"""Full planned-matrix contrasts and descriptive family-cluster uncertainty."""
from pathlib import Path
from collections import Counter
import json,time
import numpy as np
OUT=Path('results/dev_aux/task2406')
def panel(task):
 f=Path(f'results/dev_aux/task{task}');slots=json.loads((f/'slots.json').read_text());games={g['slot']:g for g in map(json.loads,(f/'games.jsonl').read_text().splitlines())};prices=sorted(set((s['ratio'],s['hand_ratio'])for s in slots));data={};rows=[]
 for price in prices:
  arr=[];counts=Counter()
  for family in range(8):
   bounds=[]
   for role in(0,1):
    s,=[s for s in slots if(s['ratio'],s['hand_ratio'])==price and s['root']==family and s['candidate_color']==role];g=games.get(s['slot']);r=None if g is None else g['reward'];counts['U'if r is None else g['outcome']]+=1;bounds.append((-1,1)if r is None else(r,r))
   arr.append([sum(x[i]for x in bounds)/2 for i in(0,1)])
  data[price]=np.array(arr,dtype=float);rows.append(dict(price=price,counts={k:counts[k]for k in'WLDU'},mean_bounds=data[price].mean(axis=0).tolist()))
 return data,rows,games,slots

def contrast(a,b,rng):
 low=a[:,0]-b[:,1];high=a[:,1]-b[:,0];idx=rng.integers(0,len(a),size=(10000,len(a)));return dict(family_gain_bounds=np.stack([low,high],axis=1).tolist(),mean_gain_bounds=[float(low.mean()),float(high.mean())],descriptive_cluster_bootstrap_envelope=[float(np.quantile(low[idx].mean(axis=1),.025)),float(np.quantile(high[idx].mean(axis=1),.975))])
def run():
 start=time.perf_counter();rng=np.random.default_rng(840606);selection=json.loads(Path('results/dev_aux/task2405/selection.json').read_text());train,rows,gs,ss=panel(2401);chosen=tuple(selection['selected']);base=(1.5,1.5);contrasts=[]
 for b in(.75,1.5):
  for h in(0.,.75):contrasts.append(dict(board_R=b,hand_R_contrast=[h,1.5],**contrast(train[(b,h)],train[(b,1.5)],rng)))
 interactions=[]
 for h in(0.,.75):
  # Difference of paired hand effects at fixed board values, not two separately selected policy gains.
  a=train[(1.5,h)];b=train[(1.5,1.5)];c=train[(.75,h)];d=train[(.75,1.5)];lo=a[:,0]-b[:,1]-c[:,1]+d[:,0];hi=a[:,1]-b[:,0]-c[:,0]+d[:,1];interactions.append(dict(hand_contrast=[h,1.5],board_contrast=[1.5,.75],bounds=[float(lo.mean()),float(hi.mean())]))
 lofo=[]
 for drop in range(8):
  keep=[i for i in range(8)if i!=drop];bp=train[base][keep].mean(axis=0);eligible=[p for p,a in train.items()if a[keep,0].mean()>bp[1]];sel=min(eligible,key=lambda p:(-train[p][keep,0].mean(),p))if eligible else base;lofo.append(dict(omitted_family=drop,selected=list(sel)))
 reserve,rrows,rgs,rss=panel(2402);rgain=None if chosen==base else contrast(reserve[chosen],reserve[base],rng)
 result=dict(status='CLOSED_ACTUAL_WL_TWO_CHANNEL_TRAIN_RESERVE',selected=selection['selected'],baseline=list(base),train_rows=rows,TRAIN_selected_gain=contrast(train[chosen],train[base],rng)if chosen!=base else None,TRAIN_leave_one_family_out=lofo,TRAIN_hand_effects_fixed_board=contrasts,TRAIN_hand_by_board_interactions=interactions,reserve_rows=rrows,reserve_selected_gain=rgain,reserve_families=8,reserve_evaluated_prices=len(reserve),seconds=time.perf_counter()-start,scope='All planned slots included, U/missing[-1,1], pairdifferences[-2,2]. Baseline-only reserve means no comparative gain evidence, not demonstratedequivalence. Bootstrapdescriptive8familyclusters/finitecandidate selection conditional, not posterior/globalprice/random-startconvergence. Different reserve generation measure vs exposedteacher-guided TRAIN. Nohuman/quantityreward/82Crefit/oldcapextension/defaultadoption. Interactions compare fixedparameter contrasts, not two independentlyselectedpolicies.')
 (OUT/'result.json').write_text(json.dumps(result,indent=2));print(json.dumps(result))
if __name__=='__main__':run()
