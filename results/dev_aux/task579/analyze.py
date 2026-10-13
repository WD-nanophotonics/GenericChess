import json,time,hashlib
from fractions import Fraction
from pathlib import Path
R=Path.cwd();O=R/'results/dev_aux/task579';start=time.perf_counter();rows=[];total=0
for study,tasks in [(553,[554,555]),(564,[565,566])]:
 d=json.loads((R/f'results/dev_aux/task{study}/declaration.json').read_bytes());nf=sum(f['phase']=='train' for f in d['roots']);assert nf==32
 for task in tasks:
  p=R/f'results/dev_aux/task{task}/endpoints.json';e=json.loads(p.read_bytes())
  for u in e['updates']:
   gs=[[Fraction(v) for v in c['goals']] for c in u['candidates']];assert all(len(v)==64 for v in gs);means=[sum(v)/64 for v in gs];best=max(range(3),key=lambda j:means[j]);assert best==u['selected_index'];loo=[]
   for f in range(32):
    scores=[(sum(v)-sum(v[2*f:2*f+2]))/62 for v in gs];b=max(range(3),key=lambda j:scores[j]);loo.append(dict(omitted_family=f,selected_index=b,strict_gain=str(scores[b]-scores[0]),changes_full_choice=b!=best));total+=1
   rows.append(dict(study=study,task=task,opponent=e['opponent'],family=u['family'],iteration=u['iteration'],full_selected_index=best,full_strict_gain=str(means[best]-means[0]),accepted=best!=0,leave_one=loo,choice_changes=sum(x['changes_full_choice'] for x in loo),accepted_survives_all_omissions=best!=0 and all(x['selected_index']==best and Fraction(x['strict_gain'])>0 for x in loo)))
summary=[]
for study,tasks in [(553,[554,555]),(564,[565,566])]:
 for task in tasks:
  for family in ['unit','random2514']:
   rr=[r for r in rows if r['task']==task and r['family']==family];assert len(rr)==24;summary.append(dict(study=study,task=task,family=family,accepted=sum(r['accepted'] for r in rr),accepted_samepositive_choice_all32=sum(r['accepted_survives_all_omissions'] for r in rr),rounds_any_choice_changed=sum(r['choice_changes']>0 for r in rr),leave_one_choice_changes=sum(r['choice_changes'] for r in rr),total_omissions=24*32))
out=dict(status='PASS_EXACT_LEAVE_ONE',proposal_rounds=len(rows),family_omissions=total,summary=summary,rows=rows,new_go=0,seconds=time.perf_counter()-start,scope='ALL192actualproposalrounds/32independentfamilyomissions exactsamebase/plus/minus context. Decisionstabilitydiagnostic only, notleave-one trainedtrajectory/newholdout/futureparameterfit orautomaticlongerH/epochs. Sourcehumanprices notused.');(O/'result.json').write_text(json.dumps(out,indent=2),encoding='utf-8');print(json.dumps({k:v for k,v in out.items() if k!='rows'}))
