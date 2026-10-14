from pathlib import Path
import json,random,collections,importlib.util
R=Path.cwd();O=R/'results/dev_aux/task1637';O.mkdir(exist_ok=False);P=R/'results/dev_aux/task1634';plan=json.loads((R/'results/dev_aux/task1633/plan.json').read_bytes())
sp=importlib.util.spec_from_file_location('T',R/'results/dev_aux/task1626/rules.py');T=importlib.util.module_from_spec(sp);sp.loader.exec_module(T)
states=list(map(tuple,json.loads((R/'results/dev_aux/task1627/states.json').read_bytes())));ix={s:i for i,s in enumerate(states)};v=json.loads((R/'results/dev_aux/task1627/values.json').read_bytes())['value'];cache={};counts=collections.Counter()
for folder in ['task1631','task1634']:
 for p in (R/f'results/dev_aux/{folder}').glob('*choices.jsonl'):
  for line in p.open():
   x=json.loads(line);key=tuple(x['price']),tuple(x['state']);assert dict(T.moves(key[1]))[x['move']]==tuple(x.get('child',dict(T.moves(key[1]))[x['move']]));assert T.fen(key[1])==x['position']
   if key in cache:assert cache[key]==x['move']
   cache[key]=x['move']
   if folder=='task1634':
    counts['newgo']+=1
    for info in x['uci_info']:
     a=info.split()
     if 'pv' in a:
      q=key[1]
      for u in a[a.index('pv')+1:]:q=dict(T.moves(q))[u];counts['PVmoves']+=1
families={f['family']:f for f in plan['families']};pilot={f['family']:f for f in json.loads((R/'results/dev_aux/task1630/plan.json').read_bytes())['families']}
pilotbounds={}
for p in (R/'results/dev_aux/task1631').glob('*_result.json'):
 x=json.loads(p.read_bytes());pilotbounds[tuple(x['price'])]={(f,c):lo for f,lo,hi in x['root_bounds'] for c in []}
 for j,(f,lo,hi) in enumerate(x['root_bounds']):pilotbounds[tuple(x['price'])][f,j%2]=lo
groups=collections.defaultdict(list);seen=set()
for line in (P/'games.jsonl').open():
 x=json.loads(line);counts['games']+=1;price=tuple(x['price']);phase=x['phase'];fam=(pilot if phase=='PILOT' else families)[x['family']];s=tuple(fam['roots'][x['color_index']]);assert s==tuple(x['root']);c=s[8];rng=random.Random(2026678600+x['family']*100+x['seed'])
 key=price,phase,x['family'],x['color_index'],x['seed'];assert key not in seen;seen.add(key)
 for step in x['trajectory']:
  assert tuple(step['state'])==s and sum(y!=16 for y in s[:8])==5;ll=T.moves(s);assert ll;u=rng.random();assert u==step['uniform'] and step['own']==(s[8]==c)
  if s[8]==c:assert step['move']==(cache[price,s] if len(ll)>1 else ll[0][0])
  else:assert step['move']==ll[min(int(u*len(ll)),len(ll)-1)][0]
  s=dict(ll)[step['move']];counts['plies']+=1
 assert s==tuple(x['end']);ll=T.moves(s)
 if not ll:pay=(-1 if s[8]==c else 1) if T.attacked(s,s[4*s[8]],1-s[8]) else 0;cat='PHYSICAL_MATE' if pay else 'PHYSICAL_STALE'
 elif sum(y!=16 for y in s[:8])<=4:pay=v[ix[s]]*(1 if s[8]==c else -1);cat='PERFECT4_HANDOFF'
 else:assert len(x['trajectory'])==x['H'];pay=None;cat='UNRESOLVED'
 assert cat==x['category'] and pay==x['payoff'];assert x['lower']==(-1 if pay is None else pay) and x['upper']==(1 if pay is None else pay);counts[cat]+=1
 if phase=='PILOT' and pay is not None:assert pay>=pilotbounds[price][x['family'],x['color_index']];counts['pilot_ALLlower_checks']+=1
 groups[price,phase].append(x)
run=json.loads((P/'result.json').read_bytes());assert run['status']=='COMPLETE' and run['exit_code']==0 and counts['newgo']==run['actual_go'];assert counts['games']==5120
for z in run['TRAIN']+run['DEV']+run['diagnostics']:
 xx=groups[tuple(z['price']),z['phase']];assert len(xx)==z['games'] and z['lower']==sum(y['lower'] for y in xx)/len(xx) and z['upper']==sum(y['upper'] for y in xx)/len(xx)
best=min(run['TRAIN'],key=lambda x:(-x['lower'],x['price']));assert best==run['selected']
def familymeans(price,phase):
 dd=collections.defaultdict(list)
 for x in groups[price,phase]:dd[x['family']].append(x['lower'])
 return {f:sum(v)/len(v) for f,v in dd.items()}
base=familymeans((720,720,720),'DEV');rng=random.Random(2026678800);contrasts=[]
for p in [tuple(best['price']),(1440,720,720)]:
 b=familymeans(p,'DEV');assert set(base)==set(b);d=[b[f]-base[f] for f in sorted(base)];bs=sorted(sum(d[i] for i in rng.choices(range(64),k=64))/64 for _ in range(10000));contrasts.append({'price':p,'primary':list(p)==best['price'],'gain':sum(d)/64,'family95':[bs[249],bs[9749]]})
for price in [(720,720,720),(1440,720,720)]:
 a={(x['family'],x['color_index'],x['seed']):x for x in groups[price,'DEV'] if x['family'] in {f['family'] for f in plan['families'] if f['phase']=='DEV'} and x['family']<80}
 b=groups[price,'H48'];assert len(a)==len(b)==128
 for x in b:y=a[x['family'],x['color_index'],x['seed']];assert y['trajectory']==x['trajectory'] and y['payoff']==x['payoff'];counts['H24_H48_identical']+=1
out={'status':'PASS_ALL_TRAJECTORIES_RANDOM_QUANTILES_POLICY_CACHE_RULE_LABELS_TRAIN_SELECTOR','counts':dict(counts),'selected':best['price'],'DEV_contrasts':contrasts,'scope':'64newDEVrootfamilies, colors/seedsdependent; randomopponentuntilcapture thenBOTHperfect4; exacthandoffWDLisnotphysicalmatewithin24. Sharedteachercontinuations notnewholdout. OneTRAINcohort, no stablehumanprice claim.'};(O/'result.json').write_text(json.dumps(out,indent=2));print(out)

