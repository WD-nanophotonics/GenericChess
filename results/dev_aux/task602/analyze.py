import json,re,time
from pathlib import Path
from fractions import Fraction as F
R=Path.cwd();O=R/'results/dev_aux/task602';O.mkdir(exist_ok=True);start=time.perf_counter();d=json.loads((R/'results/dev_aux/task596/declaration.json').read_bytes());train=[f for f in d['roots'] if f['phase']=='train'];families=sorted({f['source_family'] for f in train});cellfamilies=[f['source_family'] for f in train for c in [0,1]];assert len(cellfamilies)==104;rows=[];eps={}
for task,objective in [(597,'terminal'),(598,'mixed')]:
 e=json.loads((R/f'results/dev_aux/task{task}/endpoints.json').read_bytes());eps[objective]=e
 for u in e['updates']:
  vs=[[F(x) for x in c['goals']] for c in u['candidates']];assert all(len(v)==104 for v in vs);means=[sum(v)/104 for v in vs];best=max(range(3),key=lambda j:means[j]);assert best==u['selected_index'];loo=[]
  for f in families:
   ix=[i for i,x in enumerate(cellfamilies) if x!=f];mu=[sum(v[i] for i in ix)/len(ix) for v in vs];b=max(range(3),key=lambda j:mu[j]);loo.append(dict(omit=f,remaining_cells=len(ix),selected=b,gain=str(mu[b]-mu[0])))
  rows.append(dict(objective=objective,start=u['family'],iteration=u['iteration'],selected=best,gain=str(means[best]-means[0]),leave_one=loo,accepted=best!=0,robust=best!=0 and all(x['selected']==best and F(x['gain'])>0 for x in loo)))
# Bothobjectives' SAMEinitial+first +/- physicalbatches have identicalcomplete non-time paths/querymetadata.
need={};pairs=[]
for family in ['unit','random2514']:
 us=[next(u for u in eps[o]['updates'] if u['family']==family and u['iteration']==0) for o in ['terminal','mixed']]
 for j in range(3):
  assert us[0]['candidates'][j]['weights']==us[1]['candidates'][j]['weights']
  for a,b in zip(us[0]['candidates'][j]['sources'],us[1]['candidates'][j]['sources']):
   pairs.append((a,b));need.setdefault(a['file'],set()).add(a['line']);need.setdefault(b['file'],set()).add(b['line'])
actual={}
for path,lines in need.items():
 for i,line in enumerate((R/path).open(),1):
  if i in lines:actual[(path,i)]=json.loads(line)
semq=lambda q:{k:([' '.join(re.sub(r'\b(?:time|nps) \d+','',l).split()) for l in v] if k=='lines' else v) for k,v in q.items() if k!='seconds'}
semg=lambda g:{k:([semq(q) for q in v] if k=='queries' else v) for k,v in g.items() if k!='seconds'}
for a,b in pairs:assert semg(actual[(a['file'],a['line'])])==semg(actual[(b['file'],b['line'])])
summ=[]
for objective in ['terminal','mixed']:
 for family in ['unit','random2514']:
  rr=[x for x in rows if x['objective']==objective and x['start']==family];assert len(rr)==12;summ.append(dict(objective=objective,start=family,accepted=sum(x['accepted'] for x in rr),same_positive_choice_all8=sum(x['robust'] for x in rr)))
out=dict(status='PASS',actual_initial_and_firstdirection_pairs=len(pairs),non_time_fullquery_and_action_equal=True,rounds=len(rows),family_omissions=len(rows)*8,summary=summ,rows=rows,new_go=0,seconds=time.perf_counter()-start,scope='ALL48actualrounds/8originalseedfamilyomissions, all4offsets/bothsetupcolors/candidatecolors kept together. Actual624pairedphysicalgames sameinitial+first +/- prove SAMEconfigured warm/RNG/non-time inputs forobjectivecontrast, notallfutureTTcontexts. Notcounterfactualretrained paths, independentholdout orpriceidentifiability proof.');(O/'result.json').write_text(json.dumps(out,indent=2),encoding='utf-8');print(json.dumps({k:v for k,v in out.items() if k!='rows'}))