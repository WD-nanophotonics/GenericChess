import sys
from pathlib import Path
import json,ast,importlib.util,collections,random,time
R=Path.cwd();planid,runid,outid=map(int,sys.argv[1:4]);O=R/f'results/dev_aux/task{outid}';O.mkdir(exist_ok=False);D=R/f'results/dev_aux/task{runid}';plan=json.loads((R/f'results/dev_aux/task{planid}/plan.json').read_bytes());run=json.loads((D/'result.json').read_bytes());assert run['status']=='COMPLETE' and run['exit_code']==0;start=time.monotonic()
sp=importlib.util.spec_from_file_location('T',R/plan['model']);T=importlib.util.module_from_spec(sp);sp.loader.exec_module(T)
tree=ast.parse((R/'results/dev_aux/task1688/qualify_literal_fixed.py').read_text(encoding='utf-8-sig'));fnode=next(x for x in tree.body if isinstance(x,ast.FunctionDef) and x.name=='ref');fnode.name='reference';fnode.body[-1]=ast.Return(value=ast.Tuple(elts=[fnode.body[-1].value,ast.Call(func=ast.Name(id='check',ctx=ast.Load()),args=[ast.Name(id='d',ctx=ast.Load()),ast.Name(id='c',ctx=ast.Load())],keywords=[])],ctx=ast.Load()));ast.fix_missing_locations(fnode);ns={};exec(compile(ast.Module(body=[fnode],type_ignores=[]),'independentactor8','exec'),ns);ref=ns['reference'];BASE=tuple(plan['baseline']);cache={};counts=collections.Counter();new=[];depths=collections.Counter();nodework=0
reuse=[] if plan.get('aligned_tables') else [1693]
for oldtask in reuse:
 for line in (R/f'results/dev_aux/task{oldtask}/choices.jsonl').open():
  x=json.loads(line)
  if tuple(x['price'])!=BASE:continue
  s=tuple(x['state']);assert T.fen(s)==x['fen'] and x['move'] in dict(ref(s)[0]);cache[64,BASE,s]=x['move']
for line in (D/'choices.jsonl').open():
 x=json.loads(line);n=int(x['command'].split()[-1]);assert n in (64,4096) and x.get('nodes',n)==n;p=tuple(x['price']);s=tuple(x['state']);assert (n,p,s) not in cache and x['fen']==T.fen(s) and x['move'] in dict(ref(s)[0]);cache[n,p,s]=x['move'];counts[f'newgo_nodes{n}']+=1;new.append(x);maxnodes=0;maxdepth=0
 for info in x['uci_info']:
  a=info.split()
  if 'nodes' in a:maxnodes=max(maxnodes,int(a[a.index('nodes')+1]))
  if 'depth' in a:maxdepth=max(maxdepth,int(a[a.index('depth')+1]))
  if 'pv' in a:
   q=s
   for u in a[a.index('pv')+1:]:q=dict(T.moves(q))[u];assert T.valid(q);counts['PVmoves']+=1
 nodework+=maxnodes;depths[n,maxdepth]+=1;counts['overshoot_queries']+=maxnodes>n
acks=[json.loads(l) for l in (D/'acks.jsonl').open()];jj=[json.loads(l) for l in (D/'go_journal.jsonl').open()];assert len(new)==run['actual_go']==len(acks) and len(jj)==2*len(new)
for i,(a,x) in enumerate(zip(acks,new)):
 p=x['price'];assert (a['price'],a['state'])==(p,x['state']);nat=p if plan.get('aligned_tables') else [720]*4;expected='info string DEV_AUX leafRNBP '+' '.join(map(str,p))+f' nativeP {nat[3]} nativeR {nat[0]} nativeN {nat[1]} nativeB {nat[2]} captureP {nat[3]} captureR {nat[0]} captureN {nat[1]} captureB {nat[2]}';assert expected in a['ack'];assert jj[2*i]['event']=='INTENT' and jj[2*i+1]['event']=='SENT' and jj[2*i]['state']==jj[2*i+1]['state']==x['state'] and jj[2*i]['price']==jj[2*i+1]['price']==p
families={f['family']:f for f in plan['families']};orbitseen=set();oldorbits={tuple(s) for old in plan.get('root_exclusions',[]) for f in json.loads((R/f'results/dev_aux/{old}/plan.json').read_bytes())['families'] for s in f['orbit_states']}
def frame(s,fx,sw):
 q=['.']*64
 for z,p in enumerate(s[:64]):q[(7-z%8 if fx else z%8)+8*(7-z//8 if sw else z//8)]=p.swapcase() if sw else p
 return tuple(q+[1-s[64] if sw else s[64]])
for f in families.values():
 s=tuple(f['roots'][0]);oo={frame(s,fx,sw) for fx in [False,True] for sw in [False,True]};assert oo==set(map(tuple,f['orbit_states'])) and len(oo)==4 and not oo.intersection(orbitseen|oldorbits);orbitseen|=oo;assert tuple(f['roots'][1])==frame(s,False,True);ll,ch=ref(s);assert ch and len(ll)>=2 and T.valid(s) and all(not(not ref(t)[0] and ref(t)[1]) for u,t in ll);assert sum(p!='.' and p.isupper() for p in s[:64])==(3 if f['family']%2==0 else 2)
groups=collections.defaultdict(list);seen=set()
for line in (D/'games.jsonl').open():
 x=json.loads(line);p=tuple(x['price']);phase=x['phase'];f=families[x['family']];assert f['phase']==('DEV' if phase=='DEV_STRONG' else phase);s=tuple(f['roots'][x['color']]);assert x['root']==list(s);c=s[64];visited=[];key=p,phase,x['family'],x['color'];assert key not in seen;seen.add(key)
 for step in x['trajectory']:
  assert step['state']==list(s) and s not in visited and not T.bare(s);ll,ch=ref(s);assert ll==T.moves(s) and ll and step['own']==(s[64]==c);pp=p if s[64]==c else BASE;n=plan['candidate_nodes'] if s[64]==c else(plan['strong_DEV_opponent_nodes'] if phase=='DEV_STRONG' else plan['opponent_nodes']);assert step['move']==(cache[n,pp,s] if len(ll)>1 else ll[0][0]);u=step['move'];visited.append(s);s=dict(ll)[u];counts['plies']+=1;counts['promotion_moves']+=len(u)==5
 ll,ch=ref(s);assert x['end']==list(s)
 if not ll:pay=(-1 if s[64]==c else 1) if ch else 0;cat='PHYSICAL_MATE' if ch else 'PHYSICAL_STALE'
 elif T.bare(s):pay=0;cat='BARE_KINGS_DRAW'
 elif s in visited:assert x['repeat']==[visited.index(s),len(visited)];pay=0;cat='PROVED_POLICY_CYCLE_DRAW'
 else:assert len(visited)==plan['H'];pay=None;cat='UNRESOLVED'
 assert (pay,cat)==(x['payoff'],x['category']) and x['lower']==(-1 if pay is None else pay) and x['upper']==(1 if pay is None else pay);groups[p,phase].append(x);counts['games']+=1;counts[cat]+=1
for z in run['TRAIN']+run['DEV']:
 aa=groups[tuple(z['price']),z['phase']];assert len(aa)==z['games'] and z['finite_net']==sum(x['payoff'] or 0 for x in aa)/len(aa) and all(z[k]==sum(x[k] for x in aa)/len(aa) for k in ('lower','upper'))
if run['TRAIN']:
 sel={phase:tuple(min([x for x in run['TRAIN'] if x['phase']==phase],key=lambda x:(-x['finite_net'],x['price']))['price']) for phase in ['TRAIN1','TRAIN2']};pooled={tuple(x['price']):sum(z['finite_net'] for z in run['TRAIN'] if z['price']==x['price'])/2 for x in run['TRAIN']};sel['POOLED']=min(pooled,key=lambda p:(-pooled[p],p));assert sel=={k:tuple(v) for k,v in run['selected'].items()}
else:sel={k:tuple(v) for k,v in run['selected'].items()}
def means(p,phase,k):
 dd=collections.defaultdict(list)
 for x in groups[p,phase]:dd[x['family']].append(x[k] if x[k] is not None else 0)
 assert all(len(a)==2 for a in dd.values());return {f:sum(a)/2 for f,a in dd.items()}
rng=random.Random(2026698600+outid);contrasts=[]
for phase in sorted({x['phase'] for x in run['DEV']}):
 for p in sorted({tuple(x['price']) for x in run['DEV'] if x['phase']==phase and tuple(x['price'])!=BASE}):
  aa={k:means(p,phase,k) for k in ['payoff','lower','upper']};bb={k:means(BASE,phase,k) for k in aa};ids=sorted(aa['payoff']);gg=[aa['payoff'][f]-bb['payoff'][f] for f in ids];lo=[aa['lower'][f]-bb['upper'][f] for f in ids];hi=[aa['upper'][f]-bb['lower'][f] for f in ids];boot=[];bl=[];bh=[];half=len(ids)//2
  for _ in range(10000):
   ss=rng.choices([i for i,f in enumerate(ids) if f%2==0],k=half)+rng.choices([i for i,f in enumerate(ids) if f%2==1],k=half);boot.append(sum(gg[i] for i in ss)/len(ids));bl.append(sum(lo[i] for i in ss)/len(ids));bh.append(sum(hi[i] for i in ss)/len(ids))
  boot.sort();bl.sort();bh.sort();contrasts.append({'price':p,'phase':phase,'families':len(ids),'gain':sum(gg)/len(ids),'family95':[boot[249],boot[9749]],'infinite_gain_bounds':[sum(lo)/len(ids),sum(hi)/len(ids)],'infinite_family95_conservative':[bl[249],bh[9749]]})
out={'status':'PASS_GENERIC8_NATIVE_BUDGET_PRICE_RULE_PV_ACK_AND_ACTUALWDL_AUDIT','run':runid,'plan':planid,'counts':dict(counts),'actual_new_reported_nodes':nodework,'depth_histogram':{str(k):v for k,v in depths.items()},'selected':sel,'DEV_contrasts':contrasts,'aligned_tables':bool(plan.get('aligned_tables')),'seconds':time.monotonic()-start,'scope':plan['interpretation'] if 'interpretation' in plan else plan['scope']};(O/'result.json').write_text(json.dumps(out,indent=2));print({k:v for k,v in out.items() if k!='depth_histogram'})
