"""Dot reply 1792416458.862699: per-seed ledger for hybrid rules from RAW TRAIN query/game records.
Uses the code's own math (task2565/audit): pred=tanh(value/10) (value is White-perspective minimax, like z),
grad=phi*(1-tanh(w.phi/10)^2)/10 (0 if PV terminal), errors = successive-prediction (bootstrap) diffs plus a
final (z - last pred) when z is actual; credit_j = sum_k e_k * sum_{i<=k} lambda^(k-i) grad_ij.
Each game's eta*(bootstrap+terminal) is reconciled to the recorded weight change. U kept undetermined.
Refinement (terminal part found identically 0: last observed search already sees the terminal): bootstrap steps are
split by whether the TARGET prediction is a PV-terminal (outcome-seen) search or a heuristic leaf."""
from pathlib import Path
from math import tanh,isclose
import json,collections
D=Path('results/dev_aux/task2590');LAM=.95;ETA=.05
def run():
 qs=collections.defaultdict(list)
 for line in(D/'generic'/'queries.jsonl').open():
  q=json.loads(line)
  if q['observed']:qs[q['gameid']].append(q)
 led=collections.defaultdict(lambda:dict(W=0,D=0,L=0,U=0,terms=0,updates=0,boot=[0.]*6,term=[0.]*6,boot_to_seen_terminal=[0.]*6,boot_heuristic=[0.]*6,term_err_sign=collections.Counter(),max_recon_err=0.))
 for g in map(json.loads,(D/'generic'/'games.jsonl').open()):
  key=f"{g['generator_seed']}/{g['seed']}";L=led[key];w=g['initial_weights'];z=g['outcome'];r=None if z is None else z*(1 if g['color']==0 else-1)
  L['U'if r is None else'W'if r>0 else'L'if r<0 else'D']+=1
  preds=[];grads=[];pvt=[]
  for q in qs.get(g['gameid'],[]):
   preds.append(tanh(q['value']/10));phi=q['pv_phi'];pvt.append(q['pv_terminal'])
   grads.append([0.]*6 if q['pv_terminal']else[x*(1-tanh(sum(a*b for a,b in zip(w,phi))/10)**2)/10 for x in phi])
  errs=[(preds[i+1]-preds[i],'boot_seen'if pvt[i+1]else'boot_heur')for i in range(len(preds)-1)]
  if preds and z is not None:errs.append((z-preds[-1],'term'))
  boot=[0.]*6;term=[0.]*6;bs=[0.]*6;bh=[0.]*6
  for k,(e,kind) in enumerate(errs):
   for j in range(6):
    s=sum(LAM**(k-i)*grads[i][j]for i in range(k+1));(term if kind=='term'else boot)[j]+=e*s
    if kind!='term':(bs if kind=='boot_seen'else bh)[j]+=e*s
  for j in range(6):
   L['boot'][j]+=ETA*boot[j];L['term'][j]+=ETA*term[j];L['boot_to_seen_terminal'][j]+=ETA*bs[j];L['boot_heuristic'][j]+=ETA*bh[j]
   L['max_recon_err']=max(L['max_recon_err'],abs(w[j]+ETA*(boot[j]+term[j])-g['weights'][j]))
  L['terms']+=len(errs);L['updates']+=g['weights']!=w
  if z is not None and preds:
   te=z-preds[-1];L['term_err_sign']['term_err_toward_candidate_win'if te*(1 if g['color']==0 else-1)>0 else'toward_candidate_loss'if te*(1 if g['color']==0 else-1)<0 else'zero']+=1
 out={k:dict(v,term_err_sign=dict(v['term_err_sign']),conflict_channels=[j for j in range(6)if v['boot_heuristic'][j]*v['boot_to_seen_terminal'][j]<0 and abs(v['boot_heuristic'][j])>.05 and abs(v['boot_to_seen_terminal'][j])>.05])for k,v in sorted(led.items())}
 res=dict(status='EXISTING_RAW_RECORDS_ONLY',channels=['board P','board A','board X','hand A','hand P','hand X'],ledger=out,reconciliation_max_abs_error=max(v['max_recon_err']for v in out.values()),scope='Diagnostic on realized trajectories vs uniform foe; terminal outcomes are not optimal state values; channel credit split is not a causal intervention.')
 (D/'credit-split.json').write_text(json.dumps(res,indent=2))
 print('recon max err',res['reconciliation_max_abs_error'])
 for k,v in out.items():print(k,{x:v[x]for x in('W','L','U')},'seen',[round(x,2)for x in v['boot_to_seen_terminal']],'heur',[round(x,2)for x in v['boot_heuristic']],'term',round(sum(map(abs,v['term'])),4),'conflict',v['conflict_channels'])
if __name__=='__main__':run()
