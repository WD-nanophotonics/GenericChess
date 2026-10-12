"""Gradient/target feedback decomposition onallactualupdates, no newtraining/games."""
import json,math,hashlib,statistics
from pathlib import Path
R=Path.cwd();O=R/'results/dev_aux/task217';P=R/'results/dev_aux/task214';C=json.loads((P/'controller.json').read_bytes());assert C['complete'];by={c['context']['name']:c for c in C['calls']};rows=[];groups=[]
def report(meta):
 lines=[s for s in meta['uci_info'] if ' score ' in s and ' pv ' in s and 'lowerbound' not in s and 'upperbound' not in s]
 if not lines:return None
 f=lines[-1].split();i=f.index('score');kind=f[i+1];v=int(f[i+2]);return None if kind=='mate' and v==0 else math.tanh(v/400) if kind=='cp' else 1 if v>0 else -1
for run in C['runs']:
 sub=[]
 for z in run['rounds']:
  targets={(r['game'],r['index']):r for r in z['all_transitions']}
  for u in z['updates']:
   tr=targets[(u['game'],u['index'])];meta=by[u['game']]['result']['search_records'][u['index']];rv=report(meta);gn=math.sqrt(sum(g*g for g in u['gradient']));correct=u['delta'];mixed=None if rv is None else u['target']-rv;theta=u['before'];after=u['after'];phi=tr['features'];hypothetic=[max(math.log(.25),min(math.log(16),t+u['alpha']*mixed*g)) for t,g in zip(theta,u['gradient'])] if mixed is not None else None;vv=math.tanh((phi[0]+sum(p*math.exp(t) for p,t in zip(phi[1:],hypothetic)))/4) if hypothetic else None
   r=dict(seed=run['seed'],mode=run['mode'],game=u['game'],index=u['index'],target_kind=tr['target_kind'],student_value=u['value'],target=u['target'],correct_residual=correct,current_search_value=rv,mixed_residual=mixed,gradient_norm=gn,parameter_step_norm=math.sqrt(sum((a-b)**2 for a,b in zip(theta,after))),zero_features=all(p==0 for p in phi[1:]),saturated95=abs(u['value'])>=.95,strict_mixed_sign_conflict=mixed is not None and correct*mixed<0 and gn>1e-12,mixed_zero_but_correct_nonzero=mixed is not None and abs(mixed)<1e-12 and abs(correct)>1e-6 and gn>1e-12,hypothetic_mixed_loss=None if vv is None else (u['target']-vv)**2,mixed_increases_correctloss=vv is not None and (u['target']-vv)**2>u['loss_before']+1e-12);sub.append(r);rows.append(r)
 for kind in ('true_terminal','search_bootstrap'):
  use=[r for r in sub if r['target_kind']==kind]
  if use:groups.append(dict(seed=run['seed'],mode=run['mode'],target_kind=kind,updates=len(use),zero_features=sum(r['zero_features'] for r in use),saturated95=sum(r['saturated95'] for r in use),gradient_norm_mean=statistics.mean(r['gradient_norm'] for r in use),parameter_step_norm_sum=sum(r['parameter_step_norm'] for r in use),strict_mixed_conflicts=sum(r['strict_mixed_sign_conflict'] for r in use),mixed_zero_lost_signal=sum(r['mixed_zero_but_correct_nonzero'] for r in use),mixed_loss_increases=sum(r['mixed_increases_correctloss'] for r in use)))
out=dict(complete=True,groups=groups,rows=rows,source_sha256=hashlib.sha256((P/'controller.json').read_bytes()).hexdigest(),scope='Recordedcorrectupdates +samegradientcounterfactualmixed residual, no newtrajectory/currentsearchgradient claim.95pct saturation isdescriptiveposthoc, allnormsretained. Feedbackdiagnostic notproof λ-return gains/causalprice/intrinsicdifficulty.')
(O/'analysis.json').write_text(json.dumps(out,indent=2),encoding='utf-8');print(json.dumps(groups,indent=2))
