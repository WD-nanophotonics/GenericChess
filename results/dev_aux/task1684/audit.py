from pathlib import Path
import json,ast,importlib.util,collections,random,hashlib
R=Path.cwd();O=R/'results/dev_aux/task1694';O.mkdir(exist_ok=False);runpath=R/'results/dev_aux/task1686';plan=json.loads((R/'results/dev_aux/task1685/plan.json').read_bytes());run=json.loads((runpath/'result.json').read_bytes());assert run['status']=='COMPLETE' and run['exit_code']==0
sp=importlib.util.spec_from_file_location('T',R/plan['model']);T=importlib.util.module_from_spec(sp);sp.loader.exec_module(T)
source=(R/'results/dev_aux/task1675/qualify_literal.py').read_text(encoding='utf-8-sig');tree=ast.parse(source);refnode=next(x for x in tree.body if isinstance(x,ast.FunctionDef) and x.name=='ref');ns={};exec(compile(ast.Module(body=[refnode],type_ignores=[]),'independent-ref','exec'),ns);ref=ns['ref']
cache={};counts=collections.Counter();choices=[]
for oldline in (R/'results/dev_aux/task1678/choices.jsonl').open():
 old=json.loads(oldline);key=tuple(old['price']),tuple(old['state']);assert old['fen']==T.fen(key[1]) and old['move'] in dict(ref(key[1]));cache[key]=old['move']

for line in (runpath/'choices.jsonl').open():
 x=json.loads(line);s=tuple(x['state']);p=tuple(x['price']);key=p,s;assert key not in cache and x['fen']==T.fen(s) and x['move'] in dict(ref(s));cache[key]=x['move'];choices.append(x);counts['newgo']+=1
 for info in x['uci_info']:
  a=info.split()
  if 'pv' in a:
   q=s
   for u in a[a.index('pv')+1:]:q=dict(T.moves(q))[u];assert T.valid(q);counts['PVmoves']+=1
acks=[json.loads(l) for l in (runpath/'acks.jsonl').open()];journal=[json.loads(l) for l in (runpath/'go_journal.jsonl').open()];assert len(acks)==len(choices)==run['actual_go'] and len(journal)==2*len(choices)
for i,(a,x) in enumerate(zip(acks,choices)):
 assert a['price']==x['price'] and a['state']==x['state'];expected='info string DEV_AUX leafRNBP '+' '.join(map(str,x['price']))+' nativeP 720 nativeR 720 nativeN 720 nativeB 720 captureP 720 captureR 720 captureN 720 captureB 720';assert expected in a['ack'];assert journal[2*i]=={'event':'INTENT','price':x['price'],'state':x['state']} and journal[2*i+1]=={'event':'SENT','price':x['price'],'state':x['state']}
counts['ACKs']=len(acks);families={x['family']:x for x in plan['families']};orbitseen=set();oldorbits={tuple(s) for f in json.loads((R/'results/dev_aux/task1677/plan.json').read_bytes())['families'] for s in f['orbit_states']}
def frame(s,fx,swap):
 q=['.']*16
 for z,p in enumerate(s[:16]):q[(3-z%4 if fx else z%4)+4*(3-z//4 if swap else z//4)]=p.swapcase() if swap else p
 return tuple(q+[1-s[16] if swap else s[16]])
for f in families.values():
 s=tuple(f['roots'][0]);oo={frame(s,fx,sw) for fx in (False,True) for sw in (False,True)};assert oo==set(map(tuple,f['orbit_states'])) and len(oo)==4 and not oo.intersection(orbitseen|oldorbits);orbitseen|=oo;assert tuple(f['roots'][1])==frame(s,False,True) and T.valid(s) and T.attacked(s,T.king(s,0),1) and len(T.moves(s))>=2;assert sum(p!='.' and p.isupper() for p in s[:16])==(3 if f['family']%2==0 else 2);assert not any(not T.moves(t) and T.attacked(t,T.king(t,t[16]),1-t[16]) for u,t in T.moves(s))
 for q in oo:
  expect={(u,frame(t,True,False)) for u,t in []};assert T.valid(q);assert T.moves(q)==ref(q)
groups=collections.defaultdict(list);seen=set();BASE=tuple(plan['baseline']);familyrows=collections.defaultdict(list)
for line in (runpath/'games.jsonl').open():
 x=json.loads(line);price=tuple(x['price']);fam=families[x['family']];s=tuple(fam['roots'][x['color']]);assert s==tuple(x['root']) and (fam['phase']!='DEV' if x['phase']=='TRAIN' else fam['phase']=='DEV');key=price,x['phase'],x['family'],x['color'];assert key not in seen;seen.add(key);c=s[16];visited=[];counts['games']+=1
 for step in x['trajectory']:
  assert tuple(step['state'])==s and not T.bare(s) and s not in visited;ll=T.moves(s);assert ll==ref(s) and ll and step['own']==(s[16]==c);p=price if s[16]==c else BASE;assert step['move']==(cache[p,s] if len(ll)>1 else ll[0][0]);u=step['move'];child=dict(ll)[u];counts['plies']+=1;counts['promotion_moves']+=len(u)==5;counts['capture_moves']+=sum(z!='.' for z in child[:16])<sum(z!='.' for z in s[:16]);counts['duplicate_kind_plies']+=any(s[:16].count(z)+s[:16].count(z.lower())>1 for z in 'RNB');visited.append(s);s=child
 assert s==tuple(x['end']);ll=T.moves(s)
 if not ll:pay=(-1 if s[16]==c else 1) if T.attacked(s,T.king(s,s[16]),1-s[16]) else 0;cat='PHYSICAL_MATE' if pay else 'PHYSICAL_STALE'
 elif T.bare(s):pay=0;cat='BARE_KINGS_DRAW'
 elif s in visited:assert x['repeat']==[visited.index(s),len(visited)];pay=0;cat='PROVED_POLICY_CYCLE_DRAW'
 else:assert len(visited)==plan['H'];pay=None;cat='UNRESOLVED'
 assert (pay,cat)==(x['payoff'],x['category']) and x['lower']==(-1 if pay is None else pay) and x['upper']==(1 if pay is None else pay);counts[cat]+=1;groups[price,x['phase']].append(x);familyrows[x['phase'],x['family'],x['color']].append(x)
assert counts['games']==128*(len(run['TRAIN'])+len(run['DEV']))
for z in run['TRAIN']+run['DEV']:
 xx=groups[tuple(z['price']),z['phase']];assert len(xx)==z['games'] and all(z[k]==sum(x[k] for x in xx)/len(xx) for k in ('lower','upper'));assert z['finite_net']==sum(x['payoff'] or 0 for x in xx)/len(xx)

score={tuple(x['price']):x['finite_net'] for x in run['TRAIN']};assert len(score)==len(run['TRAIN']);paths=run['paths'];assert len(paths)==2
import math
rng0=random.Random(plan['initial_seed']);frozen=[]
while len(frozen)<2:
 rr=18*round(math.exp(rng0.uniform(math.log(90),math.log(2880)))/18);pp=18*round(math.exp(rng0.uniform(math.log(90),math.log(1440)))/18);q=(max(90,min(2880,rr)),720,720,max(90,min(1440,pp)))
 if q not in frozen:frozen.append(q)
assert list(map(tuple,plan['initials']))==frozen
def neighbors(p):
 out=set()
 for i,(lo,hi) in [(0,(90,2880)),(3,(90,1440))]:
  for factor in [.5,2]:
   q=list(p);q[i]=max(lo,min(hi,18*round(p[i]*factor/18)));q=tuple(q)
   if q!=p:out.add(q)
 return sorted(out)
allvisited=set()
for i,path in enumerate(paths):
 p=frozen[i];assert tuple(path['initial'])==p and path['initial_score']==score[p];accepted=[p];allvisited.add(p);ending='ROUND_CAP'
 for j in range(plan['round_cap']):
  direct=neighbors(p);allvisited.update(direct);best=min(direct+[p],key=lambda q:(-score[q],q));examined=list(direct);bridge=None
  if score[best]<=score[p]:
   neutral=[q for q in direct if score[q]==score[p]];candidates=[]
   for mid in neutral[:2]:
    for q in neighbors(mid):examined.append(q);allvisited.add(q);candidates.append((q,mid))
   if candidates:
    q,mid=min(candidates,key=lambda z:(-score[z[0]],z[0],z[1]))
    if score[q]>score[p]:best=q;bridge=mid
  step={'round':j,'current':list(p),'score':score[p],'examined':list(map(list,sorted(set(examined)))),'best':list(best),'best_score':score[best],'neutral_bridge':list(bridge) if bridge else None};assert path['steps'][j]==step
  if score[best]<=score[p]:ending='NO_IMPROVEMENT_AFTER_BOUNDED_NEUTRAL_FRONTIERS';break
  if bridge:assert score[bridge]==score[p];accepted.append(bridge)
  p=best;accepted.append(p)
 assert tuple(path['endpoint'])==p and path['endpoint_score']==score[p] and list(map(tuple,path['accepted']))==accepted and path['ending']==ending
assert set(score)==allvisited;assert len(run['TRAIN'])==len(allvisited)
sel={f'PATH{i}':tuple(x['endpoint']) for i,x in enumerate(paths)};sel['PRIMARY']=min(sel.values(),key=lambda q:(-score[q],q));assert sel=={k:tuple(v) for k,v in run['selected'].items()}
def means(p,k):
 dd=collections.defaultdict(list)
 for x in groups[p,'DEV']:dd[x['family']].append(x[k] if x[k] is not None else 0)
 assert all(len(a)==2 for a in dd.values());return {f:sum(v)/2 for f,v in dd.items()}
contrasts=[];rng=random.Random(2026694600)
for i,path in enumerate(paths):
 p=tuple(path['endpoint'])
 for label,q in [('INITIAL',tuple(path['initial'])),('BASELINE',BASE)]:
  a={k:means(p,k) for k in ['payoff','lower','upper']};b={k:means(q,k) for k in a};ids=sorted(a['payoff']);gg=[a['payoff'][f]-b['payoff'][f] for f in ids];lo=[a['lower'][f]-b['upper'][f] for f in ids];hi=[a['upper'][f]-b['lower'][f] for f in ids];bb=[]
  for _ in range(10000):
   ss=rng.choices([j for j,f in enumerate(ids) if f%2==0],k=32)+rng.choices([j for j,f in enumerate(ids) if f%2==1],k=32);bb.append(sum(gg[j] for j in ss)/64)
  bb.sort();contrasts.append({'path':i,'endpoint':p,'comparison':label,'reference':q,'gain':sum(gg)/64,'family95':[bb[249],bb[9749]],'infinite_gain_bounds':[sum(lo)/64,sum(hi)/64]})
p0,p1=map(tuple,[x['endpoint'] for x in paths]);xx={(x['family'],x['color']):x for x in groups[p0,'DEV']};yy={(x['family'],x['color']):x for x in groups[p1,'DEV']};same=sum(xx[k]['trajectory']==yy[k]['trajectory'] and xx[k]['end']==yy[k]['end'] and xx[k]['payoff']==yy[k]['payoff'] for k in xx)
out={'status':'PASS_RANDOMINITIAL_ACTUAL_LOCALLEARNING_PATHS_AND_ALL_POLICY_WDL','counts':dict(counts),'TRAIN_price_evaluations':len(score),'paths':paths,'selected':sel,'DEV_contrasts':contrasts,'endpoint_same_full_DEV_trajectories':same,'DEV_trajectories_per_endpoint':128,'scope':'Actual2randominitialpaths onSAMEfresh64TRAINfamilies; neutralbridge bounded2frontiers,6roundcap; adaptivequeriesfreezealgorithm notprelistedallcandidatevalues. Fresh64DEVfamilyWDL; noDEVpricechoice/humanfit/globalargmaxconvergence/independenttrainingcohortclaim. 128identicalendpoliciesonsampledDEV doNOTidentifynumericratio.'};(O/'result.json').write_text(json.dumps(out,indent=2));print({k:v for k,v in out.items() if k!='paths'})
