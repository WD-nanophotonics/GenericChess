from pathlib import Path
import json,random,collections,importlib.util
R=Path.cwd();O=R/'results/dev_aux/task1653';O.mkdir(exist_ok=False);P=R/'results/dev_aux/task1652';plan=json.loads((R/'results/dev_aux/task1651/plan.json').read_bytes())
sp=importlib.util.spec_from_file_location('T',R/'results/dev_aux/task1626/rules.py');T=importlib.util.module_from_spec(sp);sp.loader.exec_module(T)
states=list(map(tuple,json.loads((R/'results/dev_aux/task1627/states.json').read_bytes())));ix={s:i for i,s in enumerate(states)};v=json.loads((R/'results/dev_aux/task1627/values.json').read_bytes())['value'];cache={};counts=collections.Counter()
for folder in ['task1631','task1634','task1652']:
 for p in (R/f'results/dev_aux/{folder}').glob('*choices.jsonl'):
  for line in p.open():
   x=json.loads(line);key=tuple(x['price']),tuple(x['state']);assert T.fen(key[1])==x['position'] and x['move'] in dict(T.moves(key[1]))
   if key in cache:assert cache[key]==x['move']
   cache[key]=x['move']
   if folder=='task1652':
    counts['newgo']+=1
    for info in x['uci_info']:
     a=info.split()
     if 'pv' in a:
      q=key[1]
      for u in a[a.index('pv')+1:]:q=dict(T.moves(q))[u];counts['PVmoves']+=1
proof=json.loads((R/'results/dev_aux/task1649/result.json').read_bytes());safe=set(proof['proved_no_mate_masks']);slots=proof['slots'];families={f['family']:f for f in plan['families']};oldorbits={tuple(s) for file in ['task1630','task1633','task1640'] for f in json.loads((R/f'results/dev_aux/{file}/plan.json').read_bytes())['families'] for s in f['orbit_states']};seenorbits=set()
for f in families.values():
 oo=set(map(tuple,f['orbit_states']));assert len(oo)==16 and not oo.intersection(oldorbits|seenorbits);seenorbits.update(oo);root=tuple(f['roots'][0]);assert root in oo and root[8]==0 and tuple(f['roots'][1])==root[4:8]+root[:4]+(1,);assert T.valid(root) and T.attacked(root,root[0],1) and len(T.moves(root))>=2
 assert not any(not T.moves(t) and T.attacked(t,t[4*t[8]],1-t[8]) for u,t in T.moves(root))
groups=collections.defaultdict(list);seen=set()
for line in (P/'games.jsonl').open():
 x=json.loads(line);counts['games']+=1;price=tuple(x['price']);phase=x['phase'];fam=families[x['family']];assert fam['phase']==('DEV' if phase=='PHYSICAL96' else phase);s=tuple(fam['roots'][x['color_index']]);assert s==tuple(x['root']);c=s[8];rng=random.Random(2026678600+x['family']*100+x['seed'])
 key=price,phase,x['family'],x['color_index'],x['seed'];assert key not in seen;seen.add(key)
 for step in x['trajectory']:
  assert tuple(step['state'])==s and sum(1<<i for i,k in enumerate(slots) if s[k]!=16) not in safe;ll=T.moves(s);assert ll;u=rng.random();assert u==step['uniform'] and step['own']==(s[8]==c)
  assert step['move']==((cache[price,s] if len(ll)>1 else ll[0][0]) if s[8]==c else ll[min(int(u*len(ll)),len(ll)-1)][0]);s=dict(ll)[step['move']];counts['plies']+=1
 assert s==tuple(x['end']);ll=T.moves(s)
 if not ll:pay=(-1 if s[8]==c else 1) if T.attacked(s,s[4*s[8]],1-s[8]) else 0;cat='PHYSICAL_MATE' if pay else 'PHYSICAL_STALE'
 elif sum(1<<i for i,k in enumerate(slots) if s[k]!=16) in safe:pay=0;cat='RULE_NO_MATE_DRAW'
 else:assert len(x['trajectory'])==x['H'];pay=None;cat='UNRESOLVED'
 assert cat==x['category'] and pay==x['payoff'];assert x['lower']==(-1 if pay is None else pay) and x['upper']==(1 if pay is None else pay);counts[cat]+=1;groups[price,phase].append(x)
run=json.loads((P/'result.json').read_bytes());assert run['status']=='COMPLETE' and run['exit_code']==0 and counts['newgo']==run['actual_go'];assert counts['games']==12416
for z in run['TRAIN']+run['DEV']+run['diagnostics']:
 xx=groups[tuple(z['price']),z['phase']];assert len(xx)==z['games'] and z['lower']==sum(y['lower'] for y in xx)/len(xx) and z['upper']==sum(y['upper'] for y in xx)/len(xx)
selected={phase:min([z for z in run['TRAIN'] if z['phase']==phase],key=lambda x:(-x['finite_net'],x['price']))['price'] for phase in ['TRAIN1','TRAIN2']}
pooled={tuple(x['price']):sum(z['finite_net'] for z in run['TRAIN'] if z['price']==x['price'])/2 for x in run['TRAIN']};selected['POOLED']=list(min(pooled,key=lambda p:(-pooled[p],p)));assert selected==run['selected']
for f in P.glob('ACK_*.json'):
 a=json.loads(f.read_bytes());assert any('nativeP 720 nativeR 720 nativeN 720 nativeB 720 captureP 720 captureR 720 captureN 720 captureB 720' in z for z in a);counts['price_ACK']+=1
def means(price):
 dd=collections.defaultdict(list)
 for x in groups[price,'DEV']:dd[x['family']].append(x)
 return {f:(sum(x['lower'] for x in a)/8,sum(x['upper'] for x in a)/8,sum(x['payoff'] or 0 for x in a)/8) for f,a in dd.items()}
base=means((720,720,720));rng=random.Random(2026679700);contrasts=[]
for p in sorted({tuple(x) for x in selected.values()}|{(720,720,360)}):
 b=means(p);assert set(base)==set(b);lo=[b[f][0]-base[f][1] for f in sorted(base)];hi=[b[f][1]-base[f][0] for f in sorted(base)];finite=[b[f][2]-base[f][2] for f in sorted(base)];bslo=[];bshi=[];bsfinite=[]
 for _ in range(10000):
  ss=rng.choices(range(128),k=128);bslo.append(sum(lo[i] for i in ss)/128);bshi.append(sum(hi[i] for i in ss)/128);bsfinite.append(sum(finite[i] for i in ss)/128)
 bslo.sort();bshi.sort();bsfinite.sort();contrasts.append({'price':p,'primary':list(p)==selected['POOLED'],'gain_lower':sum(lo)/128,'gain_upper':sum(hi)/128,'infinite_family95_conservative':[bslo[249],bshi[9749]],'finite_gain':sum(finite)/128,'finite_family95':[bsfinite[249],bsfinite[9749]]})
out={'status':'PASS_FRESH_PHYSICAL_LEARNING_ALL_CHOICES_RULE_DRAWS_TRAJECTORIES_FINITE_SELECTORS','counts':dict(counts),'selected':selected,'DEV_contrasts':contrasts,'scope':'Actualphysicalmate/stale orprovedstockDraw, H48finiteeventselector, no winningoracle/quantity reward. two newTRAIN64+newDEV128 fullorbitsdisjoint; colors/seedsdependent, infinityUNKNOWNbounds andH96 diagnostic separate, no uniquehumanprice.'};(O/'result.json').write_text(json.dumps(out,indent=2));print(out)

