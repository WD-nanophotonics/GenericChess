import sys
from pathlib import Path
sys.path=[p for p in sys.path if Path(p).resolve()!=Path(__file__).resolve().parent]
import json,ast,importlib.util,collections,random,time,functools,hashlib,array
R=Path.cwd();runid=int(sys.argv[1]);outid=int(sys.argv[2]);O=R/f'results/dev_aux/task{outid}';O.mkdir(exist_ok=False);D=R/f'results/dev_aux/task{runid}';plan=json.loads((D/'start.json').read_bytes())['plan'];run=json.loads((D/'result.json').read_bytes());assert run['status']=='COMPLETE' and run['exit_code']==0;start=time.perf_counter()
sp=importlib.util.spec_from_file_location('T',R/plan['model']);T=importlib.util.module_from_spec(sp);sp.loader.exec_module(T)
tree=ast.parse((R/'results/dev_aux/task1688/qualify_literal_fixed.py').read_text(encoding='utf-8-sig'));fn=next(x for x in tree.body if isinstance(x,ast.FunctionDef) and x.name=='ref')
fn.body[-1]=ast.Return(value=ast.Tuple(elts=[fn.body[-1].value,ast.Call(func=ast.Name(id='check',ctx=ast.Load()),args=[ast.Name(id='d',ctx=ast.Load()),ast.Name(id='c',ctx=ast.Load())],keywords=[])],ctx=ast.Load()));ast.fix_missing_locations(fn);ns={};exec(compile(ast.Module(body=[fn],type_ignores=[]),'independentactors','exec'),ns);ref=functools.lru_cache(maxsize=100000)(ns['ref']);cc=collections.Counter();cache={};domain=(plan['model_sha256'],plan['binary_sha256'],plan['variant_sha256'],'GLOBAL_ALIGNED')

wdl=(R/plan['rank_wdl']).read_bytes();rank=array.array('H');rank.frombytes((R/plan['rank_dtm']).read_bytes());rp=json.loads((R/plan['rank_proof']).read_bytes());assert hashlib.sha256(wdl).hexdigest()==rp['wdl_sha256'] and hashlib.sha256(rank.tobytes()).hexdigest()==rp['rank_sha256']
assert json.loads((R/'results/dev_aux/task1749/result.json').read_bytes())['status']=='PASS_EXHAUSTIVE_INDEPENDENT_KRK_RULE_EQUIVALENCE'
def table(s):
 ps=[v for v in s[:-1] if v not in('.','K','k')]
 if len(ps)!=1 or ps[0].upper()!='R':return None
 owner=int(ps[0].islower());n=tuple(v.swapcase() for v in s[:-1])+(1-s[-1],) if owner else tuple(s);k=n[:-1].index('K');b=n[:-1].index('k');r=n[:-1].index('R');i=(((k*64+b)*64+r)*2+n[-1]);assert wdl[i]!=255
 return dict(id=i,owner=owner,R_turn=n[-1]==0,wdl=wdl[i],DTM=rank[i])
old=R/f"results/dev_aux/task{plan['source_native_run']}"
assert hashlib.sha256((old/'choices.jsonl').read_bytes()).hexdigest()==plan['reused_native_choice_sha256']
assert json.loads((R/f"results/dev_aux/task{plan['source_native_audit']}/result.json").read_bytes())['status'].startswith('PASS')
oldplan=json.loads((old/'start.json').read_bytes())['plan'];assert all(plan[k]==oldplan[k] for k in ('model_sha256','binary_sha256','variant_sha256','candidate_nodes','opponents'))
for x in map(json.loads,(old/'choices.jsonl').open()):
 assert tuple(x['domain'])==domain;cache[domain,x['nodes'],tuple(x['price']),tuple(x['state'])]=x['move']
assert len(cache)==run['old_paid_choice_cache_entries']
tabletrace=[json.loads(l) for l in (D/'table_choices.jsonl').open()];tableindex=0
assert hashlib.sha256((R/plan['model']).read_bytes()).hexdigest()==domain[0]
proof=json.loads((R/plan['stockproof']).read_bytes());assert proof['status']=='PROVED_NO_MATE_IN_COMPLETE_CLOSED_SINGLE_N_B_OR_BARE_STOCK' and proof['model_sha256']==domain[0] and proof['width']==8
def stock(s):
 ps=[p.upper() for p in s[:-1] if p not in('.','K','k')]
 return not ps or len(ps)==1 and ps[0] in ('N','B')
def frame(s,fx,sw):
 q=['.']*64
 for z,p in enumerate(s[:-1]):q[(7-z%8 if fx else z%8)+8*(7-z//8 if sw else z//8)]=p.swapcase() if sw else p
 return tuple(q+[1-s[-1] if sw else s[-1]])
def fullorbit(s):
 out=set()
 for flip in (0,1):
  for rot in range(4):
   for sw in (0,1):
    q=['.']*64
    for i,v in enumerate(s[:-1]):
     x,y=i%8,i//8
     if flip:x=7-x
     for _ in range(rot):x,y=7-y,x
     q[x+8*y]=v.swapcase() if sw else v
    out.add(tuple(q+[1-s[-1] if sw else s[-1]]))
 return out
old={tuple(s) for old in plan['root_exclusions'] for f in json.loads((R/f'results/dev_aux/task{old}/plan.json').read_bytes())['families'] for s in f['orbit_states']};seen=set();fam={f['family']:f for f in plan['families']}
for f in fam.values():
 s=tuple(f['roots'][0]);oo=fullorbit(s) if plan.get('symmetry')=='D4_COLOR_16' else {frame(s,fx,sw) for fx in (0,1) for sw in (0,1)}
 assert oo==set(map(tuple,f['orbit_states'])) and len(oo)==(16 if plan.get('symmetry')=='D4_COLOR_16' else 4) and not(oo&(old|seen));seen|=oo
 assert tuple(f['roots'][1])==(tuple(v.swapcase() for v in s[:-1])+(1-s[-1],) if plan.get('symmetry')=='D4_COLOR_16' else frame(s,0,1))
 ll,ch=ref(s)
 assert not any(not ref(t)[0] and ref(t)[1] for u,t in ll)
 if plan.get('root_kind') in ('EIGHTACTOR_EXCHANGE','EIGHTACTOR_RNB'):
  assert not ch and len(ll)>=4 and sorted(p for p in s[:-1] if p!='.')==sorted('KkRNBrnb' if plan.get('root_kind')=='EIGHTACTOR_RNB' else 'KkRNPrnp')
  kd=max(abs(T.king(s,0)%8-T.king(s,1)%8),abs(T.king(s,0)//8-T.king(s,1)//8));assert 2<=kd<=4
  cap=[];quiet=[]
  for u,t in ll:
   a=ord(u[0])-97+8*(int(u[1])-1);b=ord(u[2])-97+8*(int(u[3])-1)
   if s[a].upper()!='K':(cap if s[b]!='.' else quiet).append(u)
  assert cap and quiet
 else:
  assert ch and len(ll)>=2 and sum(p!='.' and p.isupper() for p in s[:-1])==(3 if f['family']%2==0 else 2)
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
  assert x['policy_id']==plan['policy_id']
  if step['policy_source']=='EXACT_KRK_RANK_MOVE':
   parent=table(s);assert parent and parent['R_turn'] and parent['wdl']==1;eligible=[]
   for u,t in ll:
    child=table(t);assert child
    if child['wdl']==2 and child['DTM']==parent['DTM']-1:eligible.append(u)
   assert step['move']==min(eligible) and tabletrace[tableindex]==dict(state=list(s),move=step['move'],parent=parent,eligible=eligible);tableindex+=1;cc['tablemoves']+=1
  else:
   assert step['policy_source']==('NATIVE' if len(ll)>1 else 'FORCED')
   assert step['move']==(cache[domain,n,pp,s] if len(ll)>1 else ll[0][0])
  visited.append(s);s=dict(ll)[step['move']];cc['plies']+=1;cc['promotions']+=len(step['move'])==5
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

assert tableindex==len(tabletrace)==run['table_moves']
scores={tuple(p):sum(x['payoff'] or 0 for x in groups[tuple(p),'TRAIN']) for p in plan['prices']}
assert len(run['TRAIN'])==len(plan['prices'])
sel={'POOLED':min(scores,key=lambda p:(-scores[p],p)),'FIXED_NATIVE':tuple(plan['fixed_native_candidate'])}
assert sel=={k:tuple(v) for k,v in run['selected'].items()}
expected=set(sel.values())|{tuple(plan['baseline'])};devphase='DEV'
assert {p for p,ph in groups if ph==devphase}==expected
assert len(games)==run['actual_games'] and cc['new_reported_nodes']==run['actual_reported_nodes']
rng=random.Random(2026701523+runid);contrasts=[];base=tuple(plan['baseline'])
for p in sorted(expected-{base}):
 for opid in ['MIXTURE']+list(opps):
  a=[x for x in groups[p,devphase] if opid=='MIXTURE' or x['opponent']==opid];b=[x for x in groups[base,devphase] if opid=='MIXTURE' or x['opponent']==opid]
  by=lambda rows,k:{f:sum((z[k] or 0) for z in rows if z['family']==f)/sum(z['family']==f for z in rows) for f in sorted({z['family'] for z in rows})}
  aa={k:by(a,k) for k in ('payoff','lower','upper')};bb={k:by(b,k) for k in aa};ids=sorted(aa['payoff']);g=[aa['payoff'][f]-bb['payoff'][f] for f in ids];lo=[aa['lower'][f]-bb['upper'][f] for f in ids];hi=[aa['upper'][f]-bb['lower'][f] for f in ids];bo=[];bl=[];bh=[]
  for _ in range(10000):
   ss=rng.choices([i for i,f in enumerate(ids) if f%2==0],k=len(ids)//2)+rng.choices([i for i,f in enumerate(ids) if f%2],k=len(ids)//2);bo.append(sum(g[i] for i in ss)/len(ids));bl.append(sum(lo[i] for i in ss)/len(ids));bh.append(sum(hi[i] for i in ss)/len(ids))
  bo.sort();bl.sort();bh.sort();contrasts.append(dict(price=p,opponent=opid,gain=sum(g)/len(g),family95=[bo[249],bo[9749]],infinite_gain_bounds=[sum(lo)/len(lo),sum(hi)/len(hi)],infinite_family95=[bl[249],bh[9749]]))
out=dict(status='PASS_HYBRID_PHYSICAL_PLAY_ALL_PV_RANK_ACTIONS_TERMINALS_AND_SELECTION',run=runid,counts=dict(cc),selected=sel,contrasts=contrasts,seconds=time.perf_counter()-start,reference_cache=ref.cache_info()._asdict(),scope='AllPV viaindependentactors,everygame/root/terminal/cycle, globalprice/budgetprotocol. Rule rankchoosers verifiedeverymove; noKRK WDLadjudication; priorpaidNativecache boundchecked, actualnewNativework only. Exposedmechanismnotfreshholdout. Familycluster bootstrap, arbitrarypredeclaredparitygroups notrole/independentcolor samples.')
(O/'result.json').write_text(json.dumps(out,indent=2));print(out)
