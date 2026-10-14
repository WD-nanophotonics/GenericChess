from pathlib import Path
import json,collections,random,importlib.util
R=Path.cwd();P=R/'results/dev_aux/task1604';O=R/'results/dev_aux/task1607';O.mkdir(exist_ok=False);study=json.loads((R/'results/dev_aux/task1601/plan.json').read_bytes());s=list(map(tuple,json.loads((R/'results/dev_aux/task1583/states.json').read_bytes())));ix={q:i for i,q in enumerate(s)};v=json.loads((R/'results/dev_aux/task1583/values.json').read_bytes())['value'];sp=importlib.util.spec_from_file_location('T',R/'results/dev_aux/task1581/rules.py');T=importlib.util.module_from_spec(sp);sp.loader.exec_module(T);counts=collections.Counter();seen=set();rows={}
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
train=[z for (r,b,phase),z in rows.items() if phase=='TRAIN'];selected=min(train,key=lambda x:(-x['mean'],x['R'],x['B']));run=json.loads((P/'result.json').read_bytes());assert run['status']=='COMPLETE' and run['all_owned_engines_closed'] and run['actual_go']==counts['actual_queries']==2048 and run['selected']==[selected['R'],selected['B']]
a=rows[720,720,'DEV'];b=rows[selected['R'],selected['B'],'DEV'];dd=collections.defaultdict(list)
for (fam,x),(ff,y) in zip(a['root_values'],b['root_values']):assert fam==ff;dd[fam].append(y-x)
d=[sum(x)/2 for f,x in sorted(dd.items())];rng=random.Random(2026676001);bs=sorted(sum(rng.choices(d,k=128))/128 for _ in range(10000));out={'status':'PASS_ALL_FAST_LEARNING_RAW_CHOICES_PV_LABELS_FIXED_SELECTOR','counts':dict(counts),'selected':[selected['R'],selected['B']],'baseline_mean':a['mean'],'selected_mean':b['mean'],'DEV_gain':sum(d)/128,'family95':[bs[249],bs[9749]],'scope':'TrueonechoiceperfectfuturecompositeWDL; rootfamiliesindependentunit/colorpairsdependent. NOTwholeactualnativepolicy. Fullvalidation1606pendingseparate; no humanfit orDEVselection.'};(O/'result.json').write_text(json.dumps(out,indent=2));print(out)
