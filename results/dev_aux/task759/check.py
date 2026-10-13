import json,hashlib
from pathlib import Path
from fractions import Fraction as F
R=Path.cwd();O=R/'results/dev_aux/task759';rows=[]
def state(t,color,q):
 if not t['kind'].startswith('cap'):return 'draw' if t['winner'] is None else 'win' if t['winner']==color else 'loss'
 return '+' if q>0 else '-' if q<0 else '0'
for task,label in [(743,'A_sign'),(749,'B_magnitude')]:
 ep=json.loads((R/f'results/dev_aux/task{task}/endpoints.json').read_bytes())
 for u in ep['updates']:
  cs=u['candidates'];states=[[state(t,i%2,q) for i,(t,q) in enumerate(zip(c['terminations'],c['quantity12']))] for c in cs];base=states[0];feasible=[];reasons=[]
  for ss in states:
   enters=[i for i,(x,y) in enumerate(zip(base,ss)) if x!='loss' and y=='loss'];loses=[i for i,(x,y) in enumerate(zip(base,ss)) if x=='win' and y!='win'];feasible.append(not enters and not loses);reasons.append(dict(enter_true_loss=enters,lose_true_win=loses))
  assert feasible[0];means=[F(c['mean_goal']) for c in cs];chosen=max([i for i in range(7) if feasible[i]],key=lambda j:means[j]);rows.append(dict(method=label,start=u['start'],iteration=u['iteration'],axis=u['axis'],original_selected=u['selected_index'],original_selection_feasible=feasible[u['selected_index']],original_accepted=F(u['accepted_gain'])>0,guarded_local_selected=chosen,guarded_local_gain=str(means[chosen]-means[0]),all_feasible=feasible,reasons=reasons))
summary=[]
for label in ['A_sign','B_magnitude']:
 for start in ['unit','random2514']:
  rr=[r for r in rows if r['method']==label and r['start']==start];summary.append(dict(method=label,start=start,grids=len(rr),accepted_updates=sum(r['original_accepted'] for r in rr),accepted_updates_violate_terminal_guard=sum(r['original_accepted'] and not r['original_selection_feasible'] for r in rr),grids_with_positive_guarded_candidate=sum(F(r['guarded_local_gain'])>0 for r in rr),guarded_local_choice_changes=sum(r['guarded_local_selected']!=r['original_selected'] for r in rr)))
out=dict(status='ALL48_VISITED_GRID_TERMINAL_GUARD_FEASIBILITY_CHECKED',summary=summary,rows=rows,new_go=0,scope='Observed757masked true-terminal damage motivatesfinite updatepredicate check onALREADYvisitedA/B grids. Guard prevents newlyentering trueloss andlosingtruewin peroriginal32traincells atH12; all7candidates kept. Localalternatechoice NOTnewendpoint/offpolicytraining; actualfuturepath needsactualcached matching fullvectors/newexecution. No unseen dev/stability/humanpriceproof.');(O/'result.json').write_text(json.dumps(out,indent=2),encoding='utf-8');print(json.dumps(summary))
