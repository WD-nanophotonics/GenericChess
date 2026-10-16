"""Matched trigger-by-budget contrasts, actual outcomes/costs/first divergences."""
from pathlib import Path
from collections import defaultdict,Counter
import json,time,numpy as np
from generic_chess.session.serialization import deserialize_game_record
OUT=Path('results/dev_aux/task2318')
def run():
 t=time.perf_counter();cells={'LOW8':(2307,'LOW_ONLY_INCREMENTAL'),'LOW60':(2313,'LOW_ONLY_INCREMENTAL'),'TWO8':(2316,'TWO_REGIME_INCREMENTAL'),'TWO60':(2289,'TWO_REGIME_INCREMENTAL')};read=lambda p:json.loads(Path(p).read_text());gs={};ds={};plans={};summary={};key=lambda g:(g['root'],g['ratio'],g['candidate_color'])
 for name,(task,arm)in cells.items():
  f=Path(f'results/dev_aux/task{task}');assert(f/'completion.json').exists();plans[name]=read(f/'plan.json');allgames=list(map(json.loads,(f/'games.jsonl').read_text().splitlines()));gg=[g for g in allgames if g['arm']==arm];gs[name]={key(g):g for g in gg};dd=list(map(json.loads,(f/'decisions.jsonl').read_text().splitlines()));by=defaultdict(list)
  for d in dd:by[d['slot']].append(d)
  ds[name]={key(g):by[g['slot']]for g in gg};summary[name]=dict(actual_games=len(gg),outcomes=dict(Counter(g['outcome']for g in gg)),actual_game_seconds=sum(g['seconds']for g in gg),candidate_choice_seconds=sum(d['measured_seconds']for g in gg for d in by[g['slot']]if d['is_candidate']),foe_choice_seconds=sum(d['measured_seconds']for g in gg for d in by[g['slot']]if not d['is_candidate']),unknown=sum(g['reward']is None for g in gg),planned_slots=32)
 for name in cells:
  p=plans[name];q=plans['LOW8'];assert p['opponents']==q['opponents']and p['H']==q['H']and p['step_seconds']==q['step_seconds'];assert all(p['candidate'][k]==q['candidate'][k]for k in q['candidate']if k not in('proof_seconds','verification_seconds'));assert json.loads(Path(p['input']).read_text())==json.loads(Path(q['input']).read_text())
 assert read('results/dev_aux/task2308/result.json')['games']==32 and read('results/dev_aux/task2297/result.json')['games']==64
 for task in(2313,2316):assert read(f'results/dev_aux/task2317/task{task}-audit.json')['status']=='PASS_FULL_ACTUAL_RECORDS_PHASES_CERTIFICATES_SINGLEAXIS_CONTRACT'
 families=sorted({k[0]for k in gs['LOW8']});assert len(families)==8;contrasts={};rng=np.random.default_rng(20261017802318);differences=[]
 def bounds(cell,k):
  g=gs[cell].get(k);return(-1.,1.)if g is None or g['reward']is None else(float(g['reward']),)*2
 def contrast(label,terms,price):
  family=[];missing=0
  for f in families:
   vv=[]
   for role in(0,1):
    lo=hi=0.;k=(f,price,role)
    for cell,sign in terms:
     a,b=bounds(cell,k);lo+=sign*(a if sign>0 else b);hi+=sign*(b if sign>0 else a)
     if a!=b:missing+=1
    vv.append((lo,hi))
   family.append((sum(v[0]for v in vv)/2,sum(v[1]for v in vv)/2))
  lo=np.array([x[0]for x in family]);hi=np.array([x[1]for x in family]);i=rng.integers(0,8,size=(10000,8));contrasts[label+':'+str(price)]=dict(family_blocks=8,missing_term_occurrences=missing,lower=float(lo.mean()),upper=float(hi.mean()),descriptive95_envelope=[float(np.quantile(lo[i].mean(axis=1),.025)),float(np.quantile(hi[i].mean(axis=1),.975))],per_family=family)
 for price in(1.,2.):
  for label,a,b in(('budget_at_LOW','LOW60','LOW8'),('budget_at_TWO','TWO60','TWO8'),('HIGH_at_8','TWO8','LOW8'),('HIGH_at_60','TWO60','LOW60')):contrast(label,[(a,1),(b,-1)],price)
  contrast('budget_by_HIGH_interaction',[('TWO60',1),('TWO8',-1),('LOW60',-1),('LOW8',1)],price)
 for a,b in(('LOW8','LOW60'),('TWO8','TWO60'),('LOW8','TWO8'),('LOW60','TWO60')):
  for k in sorted(gs['LOW8']):
   x=gs[a].get(k);y=gs[b].get(k)
   if x is None or y is None:differences.append(dict(left=a,right=b,key=k,status='MISSING'));continue
   ax=deserialize_game_record(json.dumps(x['record'])).actions;ay=deserialize_game_record(json.dumps(y['record'])).actions;n=next((i for i,(u,v)in enumerate(zip(ax,ay))if u!=v),None);r=dict(left=a,right=b,key=k,rewards=[x['reward'],y['reward']],same_record=x['record']==y['record'],first_divergence=None)
   if n is not None:
    # Journal ply is relative to each frozen initial record, not fullrecord index.
    px=len(deserialize_game_record(json.dumps(ds[a][k][0]['root_record'])).actions);off=n-px;xx=ds[a][k][off];yy=ds[b][k][off];assert xx['root_record']==yy['root_record']and xx['side']==yy['side'];r['first_divergence']=dict(fullrecord_ply=n,journal_ply=off,is_candidate=xx['is_candidate'],sources=[xx['source'],yy['source']],normal_depths=[None if z['normal_receipt']is None else z['normal_receipt']['completed_depth']for z in(xx,yy)],classification='CANDIDATE_INTERVENTION_OR_NORMAL'if xx['is_candidate']else'FIXED_CONFIG_FOE_WALL_BUDGET_ACTION_VARIATION')
   elif len(ax)!=len(ay):r['first_divergence']=dict(classification='PREFIX_LENGTH_OR_UNKNOWN')
   differences.append(r)
 result=dict(status='PASS_ACTUAL_TRIGGER_BUDGET_FACTORIAL',cells=summary,contrasts=contrasts,paired_record_comparisons=differences,new_actual_games=summary['LOW60']['actual_games']+summary['TWO8']['actual_games'],reused_game_slots=64,first_divergence_classes=dict(Counter((x.get('first_divergence')or{}).get('classification','IDENTICAL')for x in differences)),seconds=time.perf_counter()-t,scope='ALLsame8families/2prices/2roles;2NEW32arms+2reused32arms, not128newgames. FixedfoeCONFIGnotfixedactions; firstcommonhistorydivergenceclass explicit. Fourcontrasts isolatetrigger/budget atdeclaredresource levels; interactionfamily8/noequivalenceor universalpriceclaim. Missing/U retain[-1,+1] bounds; no rewardfill/fit/DEV/selection/defaultadoption. Retrospectivepilot4arm estimates notnewholdout.')
 with(OUT/'result.json').open('x')as f:json.dump(result,f,indent=2)
 print(json.dumps({k:v for k,v in result.items()if k not in('paired_record_comparisons','contrasts')}))
if __name__=='__main__':run()
