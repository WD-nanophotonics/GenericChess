import sys
from pathlib import Path
sys.path=[p for p in sys.path if Path(p).resolve()!=Path(__file__).resolve().parent]
import json,ast,importlib.util,collections,random,time,functools,hashlib
R=Path.cwd();runid=int(sys.argv[1]);outid=int(sys.argv[2]);O=R/f'results/dev_aux/task{outid}';O.mkdir(exist_ok=False);D=R/f'results/dev_aux/task{runid}';plan=json.loads((D/'start.json').read_bytes())['plan'];run=json.loads((D/'result.json').read_bytes());assert run['status']=='COMPLETE' and run['exit_code']==0;start=time.perf_counter()
sp=importlib.util.spec_from_file_location('T',R/plan['model']);T=importlib.util.module_from_spec(sp);sp.loader.exec_module(T)
tree=ast.parse((R/'results/dev_aux/task1688/qualify_literal_fixed.py').read_text(encoding='utf-8-sig'));fn=next(x for x in tree.body if isinstance(x,ast.FunctionDef) and x.name=='ref')
fn.body[-1]=ast.Return(value=ast.Tuple(elts=[fn.body[-1].value,ast.Call(func=ast.Name(id='check',ctx=ast.Load()),args=[ast.Name(id='d',ctx=ast.Load()),ast.Name(id='c',ctx=ast.Load())],keywords=[])],ctx=ast.Load()));ast.fix_missing_locations(fn);ns={};exec(compile(ast.Module(body=[fn],type_ignores=[]),'independentactors','exec'),ns);ref=functools.lru_cache(maxsize=100000)(ns['ref']);cc=collections.Counter();cache={};domain=(plan['model_sha256'],plan['binary_sha256'],plan['variant_sha256'],'GLOBAL_ALIGNED')
assert hashlib.sha256((R/plan['model']).read_bytes()).hexdigest()==domain[0]
proof=json.loads((R/plan['stockproof']).read_bytes());assert proof['status']=='PROVED_NO_MATE_IN_COMPLETE_CLOSED_SINGLE_N_B_OR_BARE_STOCK' and proof['model_sha256']==domain[0] and proof['width']==8
def stock(s):
 ps=[p.upper() for p in s[:-1] if p not in('.','K','k')]
 return not ps or len(ps)==1 and ps[0] in ('N','B')
def frame(s,fx,sw):
 q=['.']*64
 for z,p in enumerate(s[:-1]):q[(7-z%8 if fx else z%8)+8*(7-z//8 if sw else z//8)]=p.swapcase() if sw else p
 return tuple(q+[1-s[-1] if sw else s[-1]])
old={tuple(s) for old in plan['root_exclusions'] for f in json.loads((R/f'results/dev_aux/task{old}/plan.json').read_bytes())['families'] for s in f['orbit_states']};seen=set();fam={f['family']:f for f in plan['families']}
for f in fam.values():
 s=tuple(f['roots'][0]);oo={frame(s,fx,sw) for fx in (0,1) for sw in (0,1)};assert oo==set(map(tuple,f['orbit_states'])) and len(oo)==4 and not(oo&(old|seen));seen|=oo;assert tuple(f['roots'][1])==frame(s,0,1)
 ll,ch=ref(s);assert ch and len(ll)>=2 and not any(not ref(t)[0] and ref(t)[1] for u,t in ll)
 assert sum(p!='.' and p.isupper() for p in s[:-1])==(3 if f['family']%2==0 else 2)
choices=[json.loads(l) for l in (D/'choices.jsonl').open()];acks=[json.loads(l) for l in (D/'acks.jsonl').open()];journal=[json.loads(l) for l in (D/'go_journal.jsonl').open()]
assert len(choices)==len(acks)==run['actual_go'] and len(journal)==2*len(choices);current=None
for i,(x,a) in enumerate(zip(choices,acks)):
 p=tuple(x['price']);s=tuple(x['state']);n=x['nodes'];key=domain,n,p,s;assert key not in cache and tuple(x['domain'])==domain and x['fen']==T.fen(s) and x['command']=='go nodes '+str(n)
 assert x['move'] in dict(ref(s)[0]) and a['state']==x['state'] and a['price']==x['price'] and a['nodes']==n and a['explicit_clear_commands']==x['explicit_clear_commands']==1 and x['elapsed_ns']>0
 assert a['price_changed']==(current!=p)
 if current!=p:
  expected='info string DEV_AUX leafRNBP '+' '.join(map(str,p))+f' nativeP {p[3]} nativeR {p[0]} nativeN {p[1]} nativeB {p[2]} captureP {p[3]} captureR {p[0]} captureN {p[1]} captureB {p[2]}'
  assert expected in a['ack'] and any(z.startswith('info string variant '+plan['variant_names'][str(p)]+' files 8 ranks 8 ') for z in a['variant_ack']);cc['price_changes']+=1
 else:assert not a['variant_ack'];cc['same_price_cold_reset']+=1
 current=p;nn=0
 for info in x['uci_info']:
  t=info.split()
  if 'nodes' in t:nn=max(nn,int(t[t.index('nodes')+1]))
  if 'pv' in t:
   q=s
   for u in t[t.index('pv')+1:]:q=dict(ref(q)[0])[u];cc['PVmoves']+=1
 assert x['reported_nodes']==nn;cc['new_reported_nodes']+=nn;cc['overshoot_queries']+=nn>n;cc['newgo_nodes'+str(n)]+=1
 for ev,tag in [(journal[2*i],'INTENT'),(journal[2*i+1],'SENT')]:assert ev['event']==tag and ev['price']==x['price'] and ev['state']==x['state'] and ev['nodes']==n and tuple(ev['domain'])==domain
 cache[key]=x['move']
games=[json.loads(l) for l in (D/'games.jsonl').open()];groups=collections.defaultdict(list);gamekeys=set();opps={o['id']:o for o in plan['opponents']}
for x in games:
 p=tuple(x['price']);f=fam[x['family']];op=opps[x['opponent']];assert x['phase']==f['phase'] and x['opponent_price']==op['price'] and x['opponent_nodes']==op['nodes'];s=tuple(f['roots'][x['color']]);assert x['root']==list(s);c=s[-1];visited=[];key=p,x['phase'],x['family'],x['color'],x['opponent'];assert key not in gamekeys;gamekeys.add(key)
 for step in x['trajectory']:
  assert step['state']==list(s) and s not in visited and not stock(s);ll,ch=ref(s);assert ll==T.moves(s) and ll;own=s[-1]==c;assert step['own']==own;pp=p if own else tuple(op['price']);n=plan['candidate_nodes'] if own else op['nodes']
  assert step['move']==(cache[domain,n,pp,s] if len(ll)>1 else ll[0][0]);visited.append(s);s=dict(ll)[step['move']];cc['plies']+=1;cc['promotions']+=len(step['move'])==5
 ll,ch=ref(s);assert x['end']==list(s)
 if not ll:pay=(-1 if s[-1]==c else 1) if ch else 0;cat='PHYSICAL_MATE' if ch else 'PHYSICAL_STALE'
 elif stock(s):pay=0;cat='PROVED_SINGLE_STOCK_DRAW'
 elif s in visited:pay=0;cat='PROVED_POLICY_CYCLE_DRAW';assert x['repeat']==[visited.index(s),len(visited)]
 else:assert len(visited)==plan['H'];pay=None;cat='UNRESOLVED'
 assert (pay,cat)==(x['payoff'],x['category']) and x['lower']==(-1 if pay is None else pay) and x['upper']==(1 if pay is None else pay);groups[p,x['phase']].append(x);cc[cat]+=1;cc['games']+=1
for row in run['TRAIN']+run['DEV']:
 aa=groups[tuple(row['price']),row['phase']];assert len(aa)==row['games'] and all(row[k]==sum(z[k] if z[k] is not None else 0 for z in aa)/len(aa) for k in ('lower','upper'))
 assert row['finite_net']==sum(z['payoff'] or 0 for z in aa)/len(aa)
 for f in fam.values():
  if f['phase']==row['phase']:assert sum(z['family']==f['family'] for z in aa)==4
scores={(tuple(p),ph):sum(x['payoff'] or 0 for x in groups[tuple(p),ph]) for p in plan['prices'] for ph in ('TRAIN1','TRAIN2')}
sel={ph:min(map(tuple,plan['prices']),key=lambda p:(-scores[p,ph],p)) for ph in ('TRAIN1','TRAIN2')}
sel['POOLED']=min(map(tuple,plan['prices']),key=lambda p:(-sum(scores[p,ph] for ph in ('TRAIN1','TRAIN2')),p))
assert sel=={k:tuple(v) for k,v in run['selected'].items()},('SELECTOR_INTEGER_V_FLOAT',sel,run['selected'])
assert len(games)==run['actual_games'] and cc['new_reported_nodes']==run['actual_reported_nodes']
expected=set(sel.values())|{tuple(plan['baseline'])}
assert {p for p,ph in groups if ph=='DEV'}==expected
rng=random.Random(2026701503);contrasts=[];base=tuple(plan['baseline'])
for p in sorted(expected-{base}):
 for opid in ['MIXTURE']+list(opps):
  a=[x for x in groups[p,'DEV'] if opid=='MIXTURE' or x['opponent']==opid];b=[x for x in groups[base,'DEV'] if opid=='MIXTURE' or x['opponent']==opid]
  by=lambda rows,k:{f:sum((z[k] or 0) for z in rows if z['family']==f)/sum(z['family']==f for z in rows) for f in sorted({z['family'] for z in rows})}
  aa={k:by(a,k) for k in ('payoff','lower','upper')};bb={k:by(b,k) for k in aa};ids=sorted(aa['payoff']);g=[aa['payoff'][f]-bb['payoff'][f] for f in ids];lo=[aa['lower'][f]-bb['upper'][f] for f in ids];hi=[aa['upper'][f]-bb['lower'][f] for f in ids];bo=[];bl=[];bh=[]
  for _ in range(10000):
   ss=rng.choices([i for i,f in enumerate(ids) if f%2==0],k=len(ids)//2)+rng.choices([i for i,f in enumerate(ids) if f%2],k=len(ids)//2);bo.append(sum(g[i] for i in ss)/len(ids));bl.append(sum(lo[i] for i in ss)/len(ids));bh.append(sum(hi[i] for i in ss)/len(ids))
  bo.sort();bl.sort();bh.sort();contrasts.append(dict(price=p,opponent=opid,gain=sum(g)/len(g),family95=[bo[249],bo[9749]],infinite_gain_bounds=[sum(lo)/len(lo),sum(hi)/len(hi)],infinite_family95=[bl[249],bh[9749]]))
out=dict(status='PASS_INDEPENDENT_ACTOR_PV_ALL_TRAJECTORIES_ACK_DOMAIN_CYCLE_AND_INTEGER_SELECTION',run=runid,counts=dict(cc),selected=sel,contrasts=contrasts,seconds=time.perf_counter()-start,reference_cache=ref.cache_info()._asdict(),scope='AllPV viaindependentactors, everygame/root/terminal/cycle andfullprice/budgetprotocol; stockDraw bound exact1706qualifiedmodel. Familycluster stratifiedownstock bootstrap, opponent/coloredtrajectories not independent samples.')
(O/'result.json').write_text(json.dumps(out,indent=2));print(out)

