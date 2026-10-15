from pathlib import Path
import json,ast,importlib.util,collections,random
R=Path.cwd();O=R/'results/dev_aux/task1697';O.mkdir(exist_ok=False);plan=json.loads((R/'results/dev_aux/task1692/plan.json').read_bytes());P=R/'results/dev_aux/task1693';run=json.loads((P/'result.json').read_bytes());assert run['status']=='COMPLETE' and run['exit_code']==0
sp=importlib.util.spec_from_file_location('T',R/plan['model']);T=importlib.util.module_from_spec(sp);sp.loader.exec_module(T)
tree=ast.parse((R/'results/dev_aux/task1688/qualify_literal_fixed.py').read_text(encoding='utf-8-sig'));node=next(x for x in tree.body if isinstance(x,ast.FunctionDef) and x.name=='ref');node.name='reference';node.body[-1]=ast.Return(value=ast.Tuple(elts=[node.body[-1].value,ast.Call(func=ast.Name(id='check',ctx=ast.Load()),args=[ast.Name(id='d',ctx=ast.Load()),ast.Name(id='c',ctx=ast.Load())],keywords=[])],ctx=ast.Load()));ast.fix_missing_locations(node);ns={};exec(compile(ast.Module(body=[node],type_ignores=[]),'independent8actor','exec'),ns);ref=ns['reference'];cache={};counts=collections.Counter();rows=[]
for line in (P/'choices.jsonl').open():
 x=json.loads(line);p=tuple(x['price']);s=tuple(x['state']);assert (p,s) not in cache and T.valid(s) and x['fen']==T.fen(s) and x['move'] in dict(ref(s)[0]);assert x['command']=='go nodes 64';cache[p,s]=x['move'];rows.append(x);counts['newgo']+=1
 for info in x['uci_info']:
  a=info.split()
  if 'pv' in a:
   t=s
   for u in a[a.index('pv')+1:]:t=dict(T.moves(t))[u];assert T.valid(t);counts['PVmoves']+=1
acks=[json.loads(l) for l in (P/'acks.jsonl').open()];jj=[json.loads(l) for l in (P/'go_journal.jsonl').open()];assert len(rows)==run['actual_go']==len(acks) and len(jj)==len(rows)*2
for i,(a,x) in enumerate(zip(acks,rows)):
 assert (a['price'],a['state'])==(x['price'],x['state']);assert 'info string DEV_AUX leafRNBP '+' '.join(map(str,x['price']))+' nativeP 720 nativeR 720 nativeN 720 nativeB 720 captureP 720 captureR 720 captureN 720 captureB 720' in a['ack'];assert jj[2*i]['event']=='INTENT' and jj[2*i+1]['event']=='SENT' and jj[2*i]['state']==jj[2*i+1]['state']==x['state']
families={f['family']:f for f in plan['families']};orbits=set();BASE=tuple(plan['baseline']);C=tuple(plan['fixed_candidate']);groups=collections.defaultdict(list)
def frame(s,fx,swap):
 q=['.']*64
 for i,p in enumerate(s[:64]):q[(7-i%8 if fx else i%8)+8*(7-i//8 if swap else i//8)]=p.swapcase() if swap else p
 return tuple(q+[1-s[64] if swap else s[64]])
for f in families.values():
 s=tuple(f['roots'][0]);oo={frame(s,x,c) for x in [False,True] for c in [False,True]};assert oo==set(map(tuple,f['orbit_states'])) and len(oo)==4 and not oo.intersection(orbits);orbits|=oo;assert tuple(f['roots'][1])==frame(s,False,True);ll,checked=ref(s);assert checked and len(ll)>=2 and T.valid(s) and all(not(not ref(t)[0] and ref(t)[1]) for u,t in ll);assert sum(p!='.' and p.isupper() for p in s[:64])==(3 if f['family']%2==0 else 2)
seen=set()
for line in (P/'games.jsonl').open():
 x=json.loads(line);p=tuple(x['price']);f=families[x['family']];s=tuple(f['roots'][x['color']]);assert tuple(x['root'])==s;assert (p,x['family'],x['color']) not in seen;seen.add((p,x['family'],x['color']));c=s[64];visited=[];counts['games']+=1
 for step in x['trajectory']:
  assert tuple(step['state'])==s and s not in visited and not T.bare(s);ll,ch=ref(s);assert ll==T.moves(s) and ll;pp=p if s[64]==c else BASE;assert step['move']==(cache[pp,s] if len(ll)>1 else ll[0][0]);assert step['own']==(s[64]==c);u=step['move'];visited.append(s);s=dict(ll)[u];counts['plies']+=1;counts['promotion_moves']+=len(u)==5
 assert s==tuple(x['end']);ll,ch=ref(s)
 if not ll:pay=(-1 if s[64]==c else 1) if ch else 0;cat='PHYSICAL_MATE' if ch else 'PHYSICAL_STALE'
 elif T.bare(s):pay=0;cat='BARE_KINGS_DRAW'
 elif s in visited:assert x['repeat']==[visited.index(s),len(visited)];pay=0;cat='PROVED_POLICY_CYCLE_DRAW'
 else:assert len(visited)==plan['H'];pay=None;cat='UNRESOLVED'
 assert (pay,cat)==(x['payoff'],x['category']) and x['lower']==(-1 if pay is None else pay) and x['upper']==(1 if pay is None else pay);counts[cat]+=1;groups[p].append(x)
assert counts['games']==512
for z in run['DEV']:
 aa=groups[tuple(z['price'])];assert z['games']==len(aa) and z['finite_net']==sum(x['payoff'] or 0 for x in aa)/len(aa)
def means(p,k):
 dd=collections.defaultdict(list)
 for x in groups[p]:dd[x['family']].append(x[k] or 0)
 assert all(len(z)==2 for z in dd.values());return {f:sum(z)/2 for f,z in dd.items()}
aa={k:means(C,k) for k in ['payoff','lower','upper']};bb={k:means(BASE,k) for k in aa};ids=sorted(aa['payoff']);g=[aa['payoff'][f]-bb['payoff'][f] for f in ids];lo=[aa['lower'][f]-bb['upper'][f] for f in ids];hi=[aa['upper'][f]-bb['lower'][f] for f in ids];rng=random.Random(2026695600);boot=[]
for _ in range(10000):
 ss=rng.choices([i for i,f in enumerate(ids) if f%2==0],k=64)+rng.choices([i for i,f in enumerate(ids) if f%2==1],k=64);boot.append(sum(g[i] for i in ss)/128)
boot.sort();out={'status':'PASS_8BOARD_PRICE_TRANSFER_ALLRULE_POLICY_ACK_PV_ACTUALWDL','counts':dict(counts),'fixed4TRAINcandidate':C,'gain':sum(g)/128,'family95':[boot[249],boot[9749]],'infinite_gain_bounds':[sum(lo)/128,sum(hi)/128],'scope':'Fresh8board pressure128family/2color actualcold64 bothpolicies; rule4to8 androotdistribution changed; no8training/DEVwinner, notpuregeometrycausalcomparison/humanpricegeneralization. Exactcachedpolicycycles legitimateDraw, terminalrare notUNKNOWN here.'};(O/'result.json').write_text(json.dumps(out,indent=2));print(out)
