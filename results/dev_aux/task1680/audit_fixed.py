from pathlib import Path
import json,ast,importlib.util,collections,random,hashlib
R=Path.cwd();O=R/'results/dev_aux/task1687';O.mkdir(exist_ok=False);runpath=R/'results/dev_aux/task1682';plan=json.loads((R/'results/dev_aux/task1680/plan.json').read_bytes());run=json.loads((runpath/'result.json').read_bytes());assert run['status']=='COMPLETE' and run['exit_code']==0
sp=importlib.util.spec_from_file_location('T',R/plan['model']);T=importlib.util.module_from_spec(sp);sp.loader.exec_module(T)
sp2=importlib.util.spec_from_file_location('ON_T',R/'results/dev_aux/task1675/rules.py');ON_T=importlib.util.module_from_spec(sp2);sp2.loader.exec_module(ON_T)
source=(R/'results/dev_aux/task1680/qualify_literal.py').read_text(encoding='utf-8-sig');tree=ast.parse(source);refnode=next(x for x in tree.body if isinstance(x,ast.FunctionDef) and x.name=='ref');ns={};exec(compile(ast.Module(body=[refnode],type_ignores=[]),'independent-ref','exec'),ns);ref=ns['ref']
cache={};counts=collections.Counter();choices=[]
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
counts['ACKs']=len(acks);families={x['family']:x for x in plan['families']};orbitseen=set()
def frame(s,fx,swap):
 q=['.']*16
 for z,p in enumerate(s[:16]):q[(3-z%4 if fx else z%4)+4*(3-z//4 if swap else z//4)]=p.swapcase() if swap else p
 return tuple(q+[1-s[16] if swap else s[16]])
for f in families.values():
 s=tuple(f['roots'][0]);oo={frame(s,fx,sw) for fx in (False,True) for sw in (False,True)};assert oo==set(map(tuple,f['orbit_states'])) and len(oo)==4 and not oo.intersection(orbitseen);orbitseen|=oo;assert tuple(f['roots'][1])==frame(s,False,True) and T.valid(s) and T.attacked(s,T.king(s,0),1) and len(ON_T.moves(s))>=2;assert sum(p!='.' and p.isupper() for p in s[:16])==(3 if f['family']%2==0 else 2);assert not any(not ON_T.moves(t) and ON_T.attacked(t,ON_T.king(t,t[16]),1-t[16]) for u,t in ON_T.moves(s))
 for q in oo:
  assert T.valid(q);assert T.moves(q)==ref(q)
groups=collections.defaultdict(list);seen=set();BASE=tuple(plan['baseline']);familyrows=collections.defaultdict(list)
for line in (runpath/'games.jsonl').open():
 x=json.loads(line);price=tuple(x['price']);fam=families[x['family']];s=tuple(fam['roots'][x['color']]);assert s==tuple(x['root']) and fam['phase']==x['phase'];key=price,x['phase'],x['family'],x['color'];assert key not in seen;seen.add(key);c=s[16];visited=[];counts['games']+=1
 for step in x['trajectory']:
  assert tuple(step['state'])==s and not T.bare(s) and s not in visited;ll=T.moves(s);assert ll==ref(s) and ll and step['own']==(s[16]==c);p=price if s[16]==c else BASE;assert step['move']==(cache[p,s] if len(ll)>1 else ll[0][0]);u=step['move'];child=dict(ll)[u];counts['plies']+=1;counts['promotion_moves']+=len(u)==5;counts['capture_moves']+=sum(z!='.' for z in child[:16])<sum(z!='.' for z in s[:16]);counts['duplicate_kind_plies']+=any(s[:16].count(z)+s[:16].count(z.lower())>1 for z in 'RNB');visited.append(s);s=child
 assert s==tuple(x['end']);ll=T.moves(s)
 if not ll:pay=(-1 if s[16]==c else 1) if T.attacked(s,T.king(s,s[16]),1-s[16]) else 0;cat='PHYSICAL_MATE' if pay else 'PHYSICAL_STALE'
 elif T.bare(s):pay=0;cat='BARE_KINGS_DRAW'
 elif s in visited:assert x['repeat']==[visited.index(s),len(visited)];pay=0;cat='PROVED_POLICY_CYCLE_DRAW'
 else:assert len(visited)==plan['H'];pay=None;cat='UNRESOLVED'
 assert (pay,cat)==(x['payoff'],x['category']) and x['lower']==(-1 if pay is None else pay) and x['upper']==(1 if pay is None else pay);counts[cat]+=1;groups[price,x['phase']].append(x);familyrows[x['phase'],x['family'],x['color']].append(x)
assert counts['games']==256 and counts['promotion_moves']==0
for z in run['TRAIN']+run['DEV']:
 xx=groups[tuple(z['price']),z['phase']];assert len(xx)==z['games'] and all(z[k]==sum(x[k] for x in xx)/len(xx) for k in ('lower','upper'));assert z['finite_net']==sum(x['payoff'] or 0 for x in xx)/len(xx)

ON=json.loads((R/'results/dev_aux/task1678/result.json').read_bytes());selection=json.loads((R/'results/dev_aux/task1678/selection.json').read_bytes());candidate=tuple(selection['selected']['POOLED']);assert candidate==tuple(plan['fixed_candidate'])==tuple(run['selected']['FIXED_ON_TRAIN']);onrows=[json.loads(l) for l in (R/'results/dev_aux/task1678/games.jsonl').open()];ongroups=collections.defaultdict(list)
for x in onrows:
 if x['phase']=='DEV':ongroups[tuple(x['price']),'DEV'].append(x)
def fammeans(group,p,k):
 dd=collections.defaultdict(list)
 for x in group[p,'DEV']:dd[x['family']].append(x[k] if x[k] is not None else 0)
 assert all(len(a)==2 for a in dd.values());return {f:sum(a)/2 for f,a in dd.items()}
a={rule:{p:{k:fammeans(group,p,k) for k in ['payoff','lower','upper']} for p in [BASE,candidate]} for rule,group in [('ON',ongroups),('OFF',groups)]};ids=sorted(a['ON'][BASE]['payoff']);assert ids==sorted(families)
I=[];lo=[];hi=[]
for f in ids:
 I.append(a['ON'][candidate]['payoff'][f]-a['ON'][BASE]['payoff'][f]-a['OFF'][candidate]['payoff'][f]+a['OFF'][BASE]['payoff'][f]);lo.append(a['ON'][candidate]['lower'][f]-a['ON'][BASE]['upper'][f]-a['OFF'][candidate]['upper'][f]+a['OFF'][BASE]['lower'][f]);hi.append(a['ON'][candidate]['upper'][f]-a['ON'][BASE]['lower'][f]-a['OFF'][candidate]['lower'][f]+a['OFF'][BASE]['upper'][f])
rng=random.Random(2026691600);bs=[];bl=[];bh=[]
for z in range(10000):
 ss=rng.choices([i for i,f in enumerate(ids) if f%2==0],k=32)+rng.choices([i for i,f in enumerate(ids) if f%2==1],k=32);bs.append(sum(I[i] for i in ss)/64);bl.append(sum(lo[i] for i in ss)/64);bh.append(sum(hi[i] for i in ss)/64)
bs.sort();bl.sort();bh.sort();divergences=[]
onlookup={(tuple(x['price']),x['family'],x['color']):x for x in onrows if x['phase']=='DEV'}
for f in ids:
 for color in [0,1]:
  x=onlookup[candidate,f,color];y=onlookup[BASE,f,color];assert x['root']==y['root'];first=None
  for j,(u,v) in enumerate(zip(x['trajectory'],y['trajectory'])):
   assert u['state']==v['state']
   if u['move']!=v['move']:
    assert u['own'] and v['own'];first={'family':f,'color':color,'ply':j,'state':u['state'],'candidate_move':u['move'],'baseline_move':v['move'],'candidate_payoff':x['payoff'],'baseline_payoff':y['payoff']};break
  if first:divergences.append(first)
  else:assert x['trajectory']==y['trajectory'] and x['end']==y['end'] and x['payoff']==y['payoff']
(O/'first_divergences.json').write_text(json.dumps(divergences,indent=2));cells={rule:{str(p):{k:sum(vals.values())/64 for k,vals in kk.items()} for p,kk in prices.items()} for rule,prices in a.items()};out={'status':'PASS_PROMOTION_OFF_ALLPOLICY_AND_TRUEWDL_PAIRED_RULE_INTERACTION','counts':dict(counts),'fixedcandidate':candidate,'cells':cells,'interaction_ON_gain_minus_OFF_gain':sum(I)/64,'interaction_family95':[bs[249],bs[9749]],'interaction_infinite_bounds':[sum(lo)/64,sum(hi)/64],'interaction_infinite_family95_conservative':[bl[249],bh[9749]],'first_divergence_count':len(divergences),'first_divergence_families':len({x['family'] for x in divergences}),'ON_reused_games':256,'OFF_new_games':256,'cache_isolation':'OFFonlyfreshfullstate-pricecache, ONchoicesneverloaded','scope':'Sameexposed64DEVfamilies2colors each, fixedONTRAINselection noOFFtraining/DEVwinner; changesbothplayersrule/searchdomain. Thisidentifiesfixedcandidate gaininteraction, notuniversalprice/rootdistributionorisolatedcandidatepromotioncause.'};(O/'result.json').write_text(json.dumps(out,indent=2));print(out)
