from pathlib import Path
import json,collections,random,importlib.util
R=Path.cwd();O=R/'results/dev_aux/task1635';O.mkdir(exist_ok=False)
sp=importlib.util.spec_from_file_location('T',R/'results/dev_aux/task1581/rules.py');T=importlib.util.module_from_spec(sp);sp.loader.exec_module(T)
states=list(map(tuple,json.loads((R/'results/dev_aux/task1583/states.json').read_bytes())));ix={s:i for i,s in enumerate(states)};v=json.loads((R/'results/dev_aux/task1583/values.json').read_bytes())['value']
study=json.loads((R/'results/dev_aux/task1623/study.json').read_bytes());counts=collections.Counter();rows={}
for p in (R/'results/dev_aux/task1624').glob('*_choices.jsonl'):
 data=list(map(json.loads,p.open()));z=json.loads(p.with_name(p.name.replace('_choices.jsonl','_result.json')).read_bytes())
 assert [(x['family'],x['sid']) for x in data]==[(f['family'],i) for f in study['families'] if f['phase']==z['phase'] for i in f['state_ids']]
 for x in data:
  s=states[x['sid']];assert x['position']=='position fen '+T.fen(s);assert ix[dict(T.moves(s))[x['move']]]==x['child'];assert x['onechoice_perfect_future_WDL']==-v[x['child']];counts['reuse' if x.get('reused') else 'newgo']+=1
  for line in x['uci_info']:
   a=line.split()
   if 'pv' in a:
    q=s
    for u in a[a.index('pv')+1:]:q=dict(T.moves(q))[u];counts['PVmoves']+=1
 assert z['root_values']==[[x['family'],x['onechoice_perfect_future_WDL']] for x in data];assert z['mean']==sum(x['onechoice_perfect_future_WDL'] for x in data)/len(data)
 rows[z['R'],z['B'],z['phase']]=z
selected={}
for phase in ['TRAIN1','TRAIN2','TRAIN3']:
 pp=[x for (r,b,p),x in rows.items() if p==phase];assert len(pp)==12;b=min(pp,key=lambda x:(-x['mean'],x['R'],x['B']));selected[phase]=[b['R'],b['B']]
pool={(r,b):sum(rows[r,b,p]['mean'] for p in ['TRAIN1','TRAIN2','TRAIN3'])/3 for r in study['R_grid'] for b in study['B_grid']};selected['POOLED']=list(min(pool,key=lambda p:(-pool[p],p)))
run=json.loads((R/'results/dev_aux/task1624/result.json').read_bytes());assert selected==run['selected'] and counts['newgo']==run['actual_go'] and run['status']=='COMPLETE'
def gains(folder):
 dd=collections.defaultdict(list)
 a=json.loads((R/f'results/dev_aux/{folder}/R720_B720_DEV_result.json').read_bytes());b=json.loads((R/f'results/dev_aux/{folder}/R1440_B720_DEV_result.json').read_bytes())
 for (f,x),(ff,y) in zip(a['root_values'],b['root_values']):assert f==ff;dd[f].append(y-x)
 return [sum(z)/len(z) for f,z in sorted(dd.items())]
a=gains('task1613');b=gains('task1624');assert len(a)==len(b)==128;d=[y-x for x,y in zip(a,b)]
rng=random.Random(2026678700);out=[]
for name,vec in [('canonical2_gain',a),('uniform8_gain',b),('paired_gain8_minus_gain2',d)]:
 bs=sorted(sum(vec[i] for i in rng.choices(range(128),k=128))/128 for _ in range(10000));out.append({'contrast':name,'mean':sum(vec)/128,'family95':[bs[249],bs[9749]]})
z={'status':'PASS_ALL_ORBIT_CHOICES_PV_LABEL_SELECTORS','counts':dict(counts),'selected':selected,'Dot_fixedC50_diagnostic':out,'scope':'Exposed128DEVfamilymechanism; 8dependentmembers perorbit, firstchoice-perfectfuture ONLY; nofull5policy result orgeometric-equivariance/equivalence claim.'};(O/'result.json').write_text(json.dumps(z,indent=2));print(z)

