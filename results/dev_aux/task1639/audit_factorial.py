from pathlib import Path
import json,random,collections,importlib.util
R=Path.cwd();O=R/'results/dev_aux/task1657';O.mkdir(exist_ok=False);sp=importlib.util.spec_from_file_location('T',R/'results/dev_aux/task1626/rules.py');T=importlib.util.module_from_spec(sp);sp.loader.exec_module(T)
cache={};counts=collections.Counter()
for folder in ['task1631','task1634','task1641','task1644','task1652','task1656']:
 for p in (R/f'results/dev_aux/{folder}').glob('*choices.jsonl'):
  for line in p.open():
   x=json.loads(line);nodes=x.get('nodes',64);key=nodes,tuple(x['price']),tuple(x['state']);assert x['command']=='go nodes '+str(nodes);assert T.fen(key[2])==x['position'];assert x['move'] in dict(T.moves(key[2]))
   if key in cache:assert cache[key]==x['move']
   cache[key]=x['move']
   if folder=='task1656':
    counts['newgo']+=1;counts['newgo_'+str(nodes)]+=1
    for info in x['uci_info']:
     a=info.split()
     if 'pv' in a:
      q=key[2]
      for u in a[a.index('pv')+1:]:q=dict(T.moves(q))[u];counts['PVmoves']+=1
plan=json.loads((R/'results/dev_aux/task1655/plan.json').read_bytes());families={f['family']:f for f in plan['families']};proof=json.loads((R/'results/dev_aux/task1649/result.json').read_bytes());slots=proof['slots'];safe=set(proof['proved_no_mate_masks']);groups=collections.defaultdict(list);seen=set();reused={}
for line in (R/'results/dev_aux/task1652/games.jsonl').open():
 x=json.loads(line)
 if x['phase']=='DEV':reused[tuple(x['price']),x['family'],x['color_index'],x['seed']]=x
tacticalcache={}
def tactical(s,ll):
 if s in tacticalcache:return tacticalcache[s]
 scored=[]
 for m,t in ll:
  replies=T.moves(t);mate=not replies and T.attacked(t,t[4*t[8]],1-t[8]);losing=False
  for u,q in replies:
   if not T.moves(q) and T.attacked(q,q[4*q[8]],1-q[8]):losing=True;break
  score=(int(mate),int(not losing),int(T.attacked(t,t[4*t[8]],1-t[8])),int(sum(z!=16 for z in t[:8])<sum(z!=16 for z in s[:8])));scored.append((score,m,t))
 best=max(a for a,m,t in scored);a=[(m,t) for v,m,t in scored if v==best];tacticalcache[s]=a;return a
for line in (R/'results/dev_aux/task1656/games.jsonl').open():
 x=json.loads(line);price=tuple(x['price']);nodes=x['nodes'];op=x['opponent'];fam=families[x['family']];s=tuple(fam['roots'][x['color_index']]);c=s[8];rng=random.Random(2026678600+x['family']*100+x['seed']);key=nodes,price,op,x['family'],x['color_index'],x['seed'];assert key not in seen;seen.add(key)
 if x.get('reused_game'):
  old=reused[price,x['family'],x['color_index'],x['seed']]
  assert nodes==64 and op=='UNIFORM' and all(x[k]==old[k] for k in ['trajectory','root','end','category','payoff','lower','upper','H']);counts['reused_games']+=1
 for step in x['trajectory']:
  assert tuple(step['state'])==s;ll=T.moves(s);assert ll;u=rng.random();assert u==step['uniform'] and step['own']==(s[8]==c)
  if s[8]==c:m=cache[nodes,price,s] if len(ll)>1 else ll[0][0]
  else:
   choices=ll;q=u
   if op=='TACTICAL50':choices=tactical(s,ll) if u<.5 else ll;q=2*u if u<.5 else 2*u-1
   m=choices[min(int(q*len(choices)),len(choices)-1)][0]
  assert step['move']==m;s=dict(ll)[m];counts['plies']+=1
 assert s==tuple(x['end']);ll=T.moves(s)
 if not ll:pay=(-1 if s[8]==c else 1) if T.attacked(s,s[4*s[8]],1-s[8]) else 0;cat='PHYSICAL_MATE' if pay else 'PHYSICAL_STALE'
 elif sum(1<<i for i,k in enumerate(slots) if s[k]!=16) in safe:pay=0;cat='RULE_NO_MATE_DRAW'
 else:assert len(x['trajectory'])==48;pay=None;cat='UNRESOLVED'
 assert pay==x['payoff'] and cat==x['category'];counts['games']+=1;counts[cat]+=1;groups[nodes,op,price].append(x)
run=json.loads((R/'results/dev_aux/task1656/result.json').read_bytes());assert run['status']=='COMPLETE' and run['exit_code']==0 and counts['newgo']==run['actual_go'] and counts['games']==8192 and counts['reused_games']==2048
for z in run['DEV']:
 a=groups[z['nodes'],z['opponent'],tuple(z['price'])];assert len(a)==1024 and z['finite_net']==sum(x['payoff'] or 0 for x in a)/1024 and z['lower']==sum(x['lower'] for x in a)/1024 and z['upper']==sum(x['upper'] for x in a)/1024
def familymean(a):
 dd=collections.defaultdict(list)
 for x in a:dd[x['family']].append(x['payoff'] or 0)
 return {f:sum(y)/8 for f,y in dd.items()}
base=tuple(plan['profiles'][0]);candidate=tuple(plan['profiles'][1]);deltas={};rng=random.Random(2026681100);contrasts=[]
for nodes in [64,4096]:
 for op in ['UNIFORM','TACTICAL50']:
  a=familymean(groups[nodes,op,base]);b=familymean(groups[nodes,op,candidate]);deltas[nodes,op]=[b[f]-a[f] for f in sorted(a)]
vectors={str(k):v for k,v in deltas.items()}
vectors['budget_interaction_UNIFORM']=[x-y for x,y in zip(deltas[4096,'UNIFORM'],deltas[64,'UNIFORM'])]
vectors['budget_interaction_TACTICAL50']=[x-y for x,y in zip(deltas[4096,'TACTICAL50'],deltas[64,'TACTICAL50'])]
vectors['opponent_interaction_64']=[x-y for x,y in zip(deltas[64,'TACTICAL50'],deltas[64,'UNIFORM'])]
vectors['opponent_interaction_4096']=[x-y for x,y in zip(deltas[4096,'TACTICAL50'],deltas[4096,'UNIFORM'])]
for name,v in vectors.items():
 bs=sorted(sum(v[i] for i in rng.choices(range(128),k=128))/128 for _ in range(10000));contrasts.append({'contrast':name,'mean':sum(v)/128,'family95':[bs[249],bs[9749]]})
out={'status':'PASS_FULL_FACTORIAL_PRICE_NODE_KEYS_TACTICAL_RULE_POLICY_TRAJECTORIES_AND_REUSED_GAMES','counts':dict(counts),'contrasts':contrasts,'scope':'128exposedDEVfamilies mechanism, notnewholdout. Physical48finiteeventgain, UNKNOWNinfiniteWDL. PriorrandomTRAINprice fixed beforeallnew4096/tacticalruns; noDEVwinner. Colors/seedsdependent.'};(O/'result.json').write_text(json.dumps(out,indent=2));print(out)

