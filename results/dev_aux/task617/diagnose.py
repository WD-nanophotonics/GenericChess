import json,hashlib
from pathlib import Path
from fractions import Fraction as F
R=Path.cwd();O=R/'results/dev_aux/task617';O.mkdir(exist_ok=True);r=json.loads((R/'results/dev_aux/task607/result.json').read_bytes());lookup={(x['source']['file'],x['source']['line']):x for x in r['rows']};d=json.loads((R/'results/dev_aux/task596/declaration.json').read_bytes());rows=[]
# New declaredhypothesis, notfittingmode0prices: within12, reward+13-actualplies forwin, -13 forloss,0draw/unfinished.
plan=dict(question='Does shortestactualmateobjective change decision signal inexistingcandidatebatches, beforepayingforanynewfit?',goal='WIN:13-actualplies, LOSS:-13, DRAW/UNFINISHED:0; cutoff12, no quantity orreferenceprice term',all_updates=48,source='ALLsaved596597598actualcandidatebatches/basecache references, notnewcounterfactualtrainingpath',no_price_distance_selection=True);(O/'declaration.json').write_text(json.dumps(plan,indent=2),encoding='utf-8')
def score(x):return F(0) if x['termination']['winner'] is None else F(13-x['actions']) if x['termination']['winner']==x['color'] else F(-13)
for task,objective in [(597,'terminal'),(598,'mixed')]:
 e=json.loads((R/f'results/dev_aux/task{task}/endpoints.json').read_bytes())
 for u in e['updates']:
  batches=[[lookup[(s['file'],s['line'])] for s in c['sources']] for c in u['candidates']];vals=[[score(x) for x in a] for a in batches];mu=[sum(v)/104 for v in vals];choice=max(range(3),key=lambda j:mu[j]);families=sorted({x['family'] for x in batches[0]});loo=[]
  for f in families:
   ix=[i for i,x in enumerate(batches[0]) if x['family']!=f];scores=[sum(v[i] for i in ix)/len(ix) for v in vals];b=max(range(3),key=lambda j:scores[j]);loo.append(dict(omit=f,selected=b,gain=str(scores[b]-scores[0])))
  rows.append(dict(original_objective=objective,start=u['family'],iteration=u['iteration'],original_selected=u['selected_index'],fast_selected=choice,fast_gain=str(mu[choice]-mu[0]),fast_means=list(map(str,mu)),choice_changed=choice!=u['selected_index'],same_positive_choice_all8=choice!=0 and all(x['selected']==choice and F(x['gain'])>0 for x in loo),leave_one=loo))
summ=[]
for obj in ['terminal','mixed']:
 for st in ['unit','random2514']:
  a=[x for x in rows if x['original_objective']==obj and x['start']==st];summ.append(dict(original_objective=obj,start=st,rounds=len(a),choice_changes=sum(x['choice_changed'] for x in a),fast_positive_choices=sum(x['fast_selected']!=0 for x in a),robust_fast_positive_choices=sum(x['same_positive_choice_all8'] for x in a)))
out=dict(status='PASS_ALL_LOCAL_FAST_CHOICES',summary=summ,rows=rows,new_go=0,scope='PoststudyZEROgo exactlocalproposal diagnostic only. Changingreward atlatersteps would changefutureweights/physicalpaths, soNOnewfastlearning/endpointclaim. Bothpreviousobjectivefits physicallysame, duplicatecontexts notindependent. No reference/axis/root/model selection oroldfit extension.');(O/'result.json').write_text(json.dumps(out,indent=2),encoding='utf-8');print(json.dumps(summ))