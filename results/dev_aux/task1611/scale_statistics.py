from pathlib import Path
import json,collections,random,importlib.util
R=Path.cwd();P=R/'results/dev_aux/task1621';O=R/'results/dev_aux/task1632';O.mkdir(exist_ok=False);plan=json.loads((R/'results/dev_aux/task1618/plan.json').read_bytes());states=list(map(tuple,json.loads((R/'results/dev_aux/task1583/states.json').read_bytes())));ix={s:i for i,s in enumerate(states)};oracle=json.loads((R/'results/dev_aux/task1583/values.json').read_bytes())['value'];sp=importlib.util.spec_from_file_location('T',R/'results/dev_aux/task1581/rules.py');T=importlib.util.module_from_spec(sp);sp.loader.exec_module(T);counts=collections.Counter();data={};choices={}
for file in sorted(P.glob('*_choices.jsonl')):
 rows=[];raw=list(map(json.loads,file.open()));seen=set()
 for x in raw:
  key=x['R'],x['N'],x['B'];sid=x['sid'];assert sid not in seen;seen.add(sid);q=states[sid];assert ix[dict(T.moves(q))[x['move']]]==x['child'];assert -oracle[x['child']]==x['onechoice_perfect_future_WDL'];counts['records']+=1;counts['reused' if x.get('reused') else 'new_go']+=1;rows.append([x['family'],x['onechoice_perfect_future_WDL']]);choices[key,sid]=x['move']
  for line in x['uci_info']:
   ss=line.split()
   if 'pv' in ss:
    q=states[sid]
    for u in ss[ss.index('pv')+1:]:q=dict(T.moves(q))[u];counts['PVmoves']+=1
 z=json.loads(file.with_name(file.name.replace('_choices.jsonl','_result.json')).read_bytes());assert rows==z['root_values'] and z['mean']==sum(v for f,v in rows)/len(rows);assert len(rows)==256;data[key]=z
run=json.loads((P/'result.json').read_bytes());assert run['status']=='COMPLETE' and run['actual_go']==counts['new_go']==1792 and counts['records']==2304 and run['all_owned_engines_closed']
contrasts=[];delta={}
for tag in ['A49','B49','C50']:
 cases=[x for x in plan['cases'] if x['tag']==tag];base=next(x for x in cases if x['scale']==1);key0=base['R'],base['N'],base['B'];a=data[key0]
 for x in cases:
  if x['scale']==1:continue
  key=x['R'],x['N'],x['B'];b=data[key];dd=collections.defaultdict(list)
  for (f,av),(ff,bv) in zip(a['root_values'],b['root_values']):assert f==ff;dd[f].append(bv-av)
  vals=[sum(z)/2 for f,z in sorted(dd.items())];label=tag+':'+str(x['scale']);delta[label]=vals;roots=[i for f in plan['families'] if f['phase']=='DEV' for i in f['state_ids']];contrasts.append({'label':label,'mean_gain':sum(vals)/128,'base_mean':a['mean'],'scaled_mean':b['mean'],'changed_moves':sum(choices[key,sid]!=choices[key0,sid] for sid in roots),'changed_root_WDL':sum(av!=bv for (_,av),(_,bv) in zip(a['root_values'],b['root_values']))})
rng=random.Random(2026677200);bs={k:[] for k in delta};err=[]
for _ in range(10000):
 ids=rng.choices(range(128),k=128);ee=[]
 for k,d in delta.items():
  y=sum(d[i] for i in ids)/128;bs[k].append(y);ee.append(abs(y-sum(d)/128))
 err.append(max(ee))
err.sort();radius=err[9499]
for x in contrasts:
 v=sorted(bs[x['label']]);x['family95']=[v[249],v[9749]];x['shared95']=[x['mean_gain']-radius,x['mean_gain']+radius]
# FullpolicyC50 scales paired withSAMEnewexposedDEV andfullRNBidentity.
Q=R/'results/dev_aux/task1622';fullbase=json.loads((Q/'R1440_N720_B720_DEV_result.json').read_bytes());full=[]
for name,scale in [('R720_N360_B360',.5),('R2880_N1440_B1440',2)]:
 x=json.loads((Q/(name+'_DEV_result.json')).read_bytes());d=collections.defaultdict(list)
 for (f,a),(ff,b) in zip(fullbase['root_values'],x['root_values']):assert f==ff;d[f].append(b-a)
 vals=[sum(z)/2 for f,z in sorted(d.items())];rng=random.Random(2026677300+int(scale*2));vv=sorted(sum(rng.choices(vals,k=128))/128 for _ in range(10000));full.append({'scale':scale,'base_mean':fullbase['mean'],'scaled_mean':x['mean'],'gain':sum(vals)/128,'family95':[vv[249],vv[9749]],'WDL':x['WDL']})
out={'status':'PASS_ALL_SCALE_FIRST_CHOICES_PV_RULE_LABELS_AND_PAIRED_STATS','counts':dict(counts),'firstchoice_contrasts':contrasts,'firstchoice_shared95_radius':radius,'fullpolicy_C50':full,'scope':'9fixedRNBprofiles, nativeorderingall720, SAMEexposedDEV; no bestscalefit. Changingchoices isnotgain; exactruleWDL effects reportedseparately. Full3Cscales independentaudit1625PASS, RNBkey preventsNalias. Bootstrapsharedbands descriptive onexposedmechanism cohort, notnewvalidation.'};(O/'result.json').write_text(json.dumps(out,indent=2));print(out)
