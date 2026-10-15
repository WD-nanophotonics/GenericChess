"""Paid-only inference/cost assessment; no new policy rollout or root exclusion."""
from pathlib import Path
from collections import defaultdict,Counter
from itertools import product
import json,time
O=Path('results/dev_aux/task1932')
def main():
 start=time.perf_counter();games=[json.loads(x) for x in Path('results/dev_aux/task1920/games.jsonl').read_text().splitlines()];moves=[json.loads(x) for x in Path('results/dev_aux/task1920/moves.jsonl').read_text().splitlines()];p=json.loads(Path('results/dev_aux/task1920/run-plan.json').read_text());by=defaultdict(list)
 for m in moves:by[m['slot']].append(m)
 index={(g['family'],g['candidate_side'],g['ratio']):g for g in games};phase=[]
 for name,ids in [('TRAIN',range(16)),('DEV',range(16,32))]:
  transitions=Counter();first=Counter();deltas=[];nonflat=[];flatdiff=0
  for family in ids:
   fd=[];sv=[]
   for role in (0,1):
    a,b=index[family,role,1.],index[family,role,3.];d=b['finite_event_score']-a['finite_event_score'];fd.append(d);sv.append(tuple(index[family,role,r]['finite_event_score'] for r in (1.,2.,3.,4.)));transitions[a['outcome']+'->'+b['outcome']]+=1;left,right=by[a['slot']],by[b['slot']];diff=next((i for i,(x,y) in enumerate(zip(left,right)) if x['choice']!=y['choice']),None)
    if diff is None:first['same_path' if len(left)==len(right) else 'shared_prefix_only']+=1
    else:
     x,y=left[diff],right[diff];assert x['before_state_sha']==y['before_state_sha'];first[('candidate' if x['side']==role else 'fixedopponent')+':'+x['source']+'|'+y['source']]+=1
     if d==0:flatdiff+=1
   deltas.append(sum(fd)/2)
   if any(len(set(v))>1 for v in sv):nonflat.append(family)
  nz=[d for d in deltas if d];observed=abs(sum(nz));extreme=sum(abs(sum(s*v for s,v in zip(signs,nz)))>=observed for signs in product((-1,1),repeat=len(nz)));phase.append(dict(phase=name,family_deltas=deltas,nonflat_grid_families=nonflat,nonzero_selected_vs_baseline_families=len(nz),first_action_categories=dict(first),changed_path_same_event_role_groups=flatdiff,transitions=dict(transitions),symmetric_independent_sign_null_two_sided=extreme/(2**len(nz)),null_scope='sensitivityunderindependentRademachereffectsignsymmetry, NOTrandomizedtrial/exactarbitrarymeanzerotest or multiplicityadjustedclaim'))
 train={r:sum(g['finite_event_score'] for g in games if g['phase']=='TRAIN' and g['ratio']==r) for r in (1.,2.,3.,4.)};leave=[]
 for drop in range(16):
  scores={r:train[r]-sum(index[drop,side,r]['finite_event_score'] for side in (0,1)) for r in train};best=max(scores.values());leave.append(dict(removed_family=drop,optimal_set=[r for r,v in scores.items() if v==best]))
 out=dict(status='PAID_ONLY_ASSESSMENT',phase=phase,train_leave_one_family_out=leave,leave_one_out_scope='DiagnosticTRAINreuse only; no newselection/independenttrainingseeds/DEVrepair. FourinitialpathsusedSAME128gamefitnesssurface, notfourindependentruns.',cost=dict(total_games=256,wall_seconds=json.loads(Path('results/dev_aux/task1920/completion.json').read_text())['seconds'],proof_seconds=sum(m['proof_seconds'] for m in moves),normal_seconds=sum(m['normal_seconds'] for m in moves),current_verifier_seconds=sum(m['verification_seconds'] for m in moves),nonzero_param_survey='No extra opportunityscreen/filter/monitoring built; outputonlyalready-paidstates.'),seconds=time.perf_counter()-start,scope='ActualW-Lfiniteeventreward only, UNKNOWNseparate, fixedN720/oneRtwoNmu/modifiedmatureengine. StableTRAINfinitegridoptimum isnotheldoutperformance, continuousprice/humanagreement orabsenceofselective-searchbias.')
 with (O/'result.json').open('x') as f:json.dump(out,f,indent=2)
 print(json.dumps({k:out[k] for k in ['status','phase','seconds']}))
if __name__=='__main__':main()
