from pathlib import Path
import json,collections,random,importlib.util
R=Path.cwd();P=R/'results/dev_aux/task1613';O=R/'results/dev_aux/task1614';O.mkdir(exist_ok=False);study=json.loads((R/'results/dev_aux/task1612/study.json').read_bytes());s=list(map(tuple,json.loads((R/'results/dev_aux/task1583/states.json').read_bytes())));ix={q:i for i,q in enumerate(s)};v=json.loads((R/'results/dev_aux/task1583/values.json').read_bytes())['value'];sp=importlib.util.spec_from_file_location('T',R/'results/dev_aux/task1581/rules.py');T=importlib.util.module_from_spec(sp);sp.loader.exec_module(T);counts=collections.Counter();seen=set();rows={}
for path in sorted(P.glob('*_choices.jsonl')):
 data=[]
 for line in path.open():
  x=json.loads(line);key=x['R'],x['B'],x['phase'],x['sid'];assert key not in seen;seen.add(key);q=s[x['sid']];assert T.fen(q)==' '.join(x['position'].split()[2:]);assert ix[dict(T.moves(q))[x['move']]]==x['child'];assert x['onechoice_perfect_future_WDL']==-v[x['child']];counts['actual_queries']+=1;data.append([x['family'],x['onechoice_perfect_future_WDL']])
  for info in x['uci_info']:
   ss=info.split()
   if 'pv' in ss:
    q=s[x['sid']]
    for u in ss[ss.index('pv')+1:]:q=dict(T.moves(q))[u];counts['PVmoves']+=1
 z=json.loads(path.with_name(path.name.replace('_choices.jsonl','_result.json')).read_bytes());assert z['root_values']==data and z['mean']==sum(y for f,y in data)/len(data);expected=[(f['family'],i) for f in study['families'] if f['phase']==z['phase'] for i in f['state_ids']];actual=[(x['family'],x['sid']) for x in map(json.loads,path.open())];assert actual==expected;rows[z['R'],z['B'],z['phase']]=z
run=json.loads((P/'result.json').read_bytes());assert run['status']=='COMPLETE' and run['all_owned_engines_closed'] and run['actual_go']==counts['actual_queries']
selected={}
for phase in ['TRAIN1','TRAIN2','TRAIN3']:
 train=[z for (r,b,p),z in rows.items() if p==phase];assert len(train)==12;best=min(train,key=lambda x:(-x['mean'],x['R'],x['B']));selected[phase]=[best['R'],best['B']]
pooled={(r,b):sum(rows[r,b,p]['mean'] for p in ['TRAIN1','TRAIN2','TRAIN3'])/3 for r in study['R_grid'] for b in study['B_grid']};selected['POOLED']=list(min(pooled,key=lambda p:(-pooled[p],p)));assert selected==run['selected']
a=rows[720,720,'DEV'];fd={};contrasts=[]
for key in sorted({tuple(p) for p in selected.values()}):
 b=rows[key[0],key[1],'DEV'];dd=collections.defaultdict(list)
 for (fam,x),(ff,y) in zip(a['root_values'],b['root_values']):assert fam==ff;dd[fam].append(y-x)
 d=[sum(x)/2 for f,x in sorted(dd.items())];assert len(d)==128;fd[key]=d;contrasts.append({'R_B':key,'primaryPOOLED':list(key)==selected['POOLED'],'mean':b['mean'],'gain':sum(d)/128,'WDL':b['WDL']})
rng=random.Random(2026677001);bs={k:[] for k in fd};maxerr=[]
for _ in range(10000):
 sample=rng.choices(range(128),k=128);error=[]
 for k,d in fd.items():
  z=sum(d[i] for i in sample)/128;bs[k].append(z);error.append(abs(z-sum(d)/128))
 maxerr.append(max(error))
maxerr.sort();radius=maxerr[9499]
for x in contrasts:
 k=tuple(x['R_B']);bs[k].sort();x['family95']=[bs[k][249],bs[k][9749]];x['shared95']=[x['gain']-radius,x['gain']+radius]
out={'status':'PASS_ALL36TRAIN3DEV_RAW_CHOICES_PV_RULE_WDL_FIXED_SELECTORS','counts':dict(counts),'selectors':selected,'baselineDEV_mean':a['mean'],'DEV_contrasts':contrasts,'shared95_radius':radius,'scope':'Samefirstchoice/perfectfuture objective acrossTHREEdisjointTRAINroot samples; rootfamilyunit/colorpairsdependent. SelectorsfixedbeforeDEV; allcontinuationstatesnotunexposed. Nativewholefivepolicyvalidationseparate.'};(O/'result.json').write_text(json.dumps(out,indent=2));print(out)
