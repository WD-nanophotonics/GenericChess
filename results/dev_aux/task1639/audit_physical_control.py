from pathlib import Path
import json,collections,random,importlib.util
R=Path.cwd();O=R/'results/dev_aux/task1648';O.mkdir(exist_ok=False);sp=importlib.util.spec_from_file_location('T',R/'results/dev_aux/task1626/rules.py');T=importlib.util.module_from_spec(sp);sp.loader.exec_module(T)
cache={};counts=collections.Counter()
for folder in ['task1631','task1634','task1641','task1644']:
 for p in (R/f'results/dev_aux/{folder}').glob('*choices.jsonl'):
  for line in p.open():
   x=json.loads(line);k=tuple(x['price']),tuple(x['state']);assert x['move'] in dict(T.moves(k[1])) and T.fen(k[1])==x['position']
   if k in cache:assert cache[k]==x['move']
   cache[k]=x['move']
   if folder=='task1644':
    counts['newgo']+=1
    for info in x['uci_info']:
     a=info.split()
     if 'pv' in a:
      q=k[1]
      for u in a[a.index('pv')+1:]:q=dict(T.moves(q))[u];counts['PVmoves']+=1
plan=json.loads((R/'results/dev_aux/task1643/plan.json').read_bytes());families={f['family']:f for f in plan['families']};groups=collections.defaultdict(list);seen=set()
for line in (R/'results/dev_aux/task1644/games.jsonl').open():
 x=json.loads(line);price=tuple(x['price']);s=tuple(families[x['family']]['roots'][x['color_index']]);assert s==tuple(x['root']);c=s[8];rng=random.Random(2026678600+x['family']*100+x['seed']);key=price,x['phase'],x['family'],x['color_index'],x['seed'];assert key not in seen;seen.add(key)
 for step in x['trajectory']:
  assert s==tuple(step['state']);ll=T.moves(s);assert ll;u=rng.random();assert u==step['uniform'] and step['own']==(s[8]==c);assert step['move']==((cache[price,s] if len(ll)>1 else ll[0][0]) if s[8]==c else ll[min(int(u*len(ll)),len(ll)-1)][0]);s=dict(ll)[step['move']];counts['plies']+=1
 assert s==tuple(x['end']);ll=T.moves(s)
 if not ll:pay=(-1 if s[8]==c else 1) if T.attacked(s,s[4*s[8]],1-s[8]) else 0;cat='PHYSICAL_MATE' if pay else 'PHYSICAL_STALE'
 else:assert len(x['trajectory'])==x['H'];pay=None;cat='UNRESOLVED'
 assert pay==x['payoff'] and cat==x['category'] and x['lower']==(-1 if pay is None else pay) and x['upper']==(1 if pay is None else pay);groups[price,x['phase']].append(x);counts[cat]+=1;counts['games']+=1
run=json.loads((R/'results/dev_aux/task1644/result.json').read_bytes());assert counts['games']==4352 and counts['newgo']==run['actual_go'] and run['exit_code']==0 and run['status']=='COMPLETE'
composite={}
for line in (R/'results/dev_aux/task1641/games.jsonl').open():
 x=json.loads(line)
 if x['phase']=='DEV':composite[tuple(x['price']),x['family'],x['color_index'],x['seed']]=x
for (price,phase),rows in groups.items():
 if phase=='PHYSICAL48':
  for x in rows:
   y=composite[price,x['family'],x['color_index'],x['seed']];assert x['trajectory'][:len(y['trajectory'])]==y['trajectory'];counts['paired_prefixes']+=1
def famrows(price,phase):
 dd=collections.defaultdict(list)
 for x in groups[price,phase]:dd[x['family']].append(x)
 return {f:[sum(x['payoff'] or 0 for x in a)/len(a),sum(x['lower'] for x in a)/len(a),sum(x['upper'] for x in a)/len(a)] for f,a in dd.items()}
base=famrows((720,720,720),'PHYSICAL48');rng=random.Random(2026680000);contrasts=[]
for price in map(tuple,plan['profiles']):
 if price==(720,720,720):continue
 b=famrows(price,'PHYSICAL48');delta=[b[f][0]-base[f][0] for f in sorted(base)];c_delta=[];lo=[];hi=[]
 for f in sorted(base):
  yy=[(composite[price,f,c,k]['payoff'] or 0)-(composite[(720,720,720),f,c,k]['payoff'] or 0) for c in [0,1] for k in range(4)];c_delta.append(sum(yy)/8);lo.append(b[f][1]-base[f][2]);hi.append(b[f][2]-base[f][1])
 d=[x-y for x,y in zip(delta,c_delta)];out={'price':price,'physical_finite_gain':sum(delta)/128,'physical_infinite_gain_bounds':[sum(lo)/128,sum(hi)/128],'physical_minus_composite_pricegain':sum(d)/128}
 for name,vec in [('physical_finite95',delta),('paired_gain_change95',d)]:
  bs=sorted(sum(vec[i] for i in rng.choices(range(128),k=128))/128 for _ in range(10000));out[name]=[bs[249],bs[9749]]
 contrasts.append(out)
result={'status':'PASS_ALL_PHYSICAL_CHOICES_PV_RANDOM_TRAJECTORY_TERMINAL_AND_PAIRED_PREFIX','counts':dict(counts),'contrasts':contrasts,'scope':'PhysicalH48 finiteeventgain distinct infiniteWDL uncertainbounds. Paired gain-change switchesBOTH continuationplayers anddeadline/teacher scope, notisolatedcandidate conversion. NoDEVselection.128families/colors/seedsdependent; H96 onlyfirst16.'};(O/'result.json').write_text(json.dumps(result,indent=2));print(result)

