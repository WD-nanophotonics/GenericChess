from pathlib import Path
import json,ast,importlib.util,collections,time,random
R=Path.cwd();O=R/'results/dev_aux/task1700';O.mkdir(exist_ok=False);P=R/'results/dev_aux/task1696';plan=json.loads((R/'results/dev_aux/task1695/plan.json').read_bytes());run=json.loads((P/'result.json').read_bytes());assert run['status']=='COMPLETE' and run['exit_code']==0;start=time.monotonic();deadline=start+900
sp=importlib.util.spec_from_file_location('T',R/plan['model']);T=importlib.util.module_from_spec(sp);sp.loader.exec_module(T)
sp=importlib.util.spec_from_file_location('STOP',R/'results/dev_aux/task166/run.py');STOP=importlib.util.module_from_spec(sp);sp.loader.exec_module(STOP)
tree=ast.parse((R/'results/dev_aux/task1675/qualify_literal.py').read_text(encoding='utf-8-sig'));node=next(x for x in tree.body if isinstance(x,ast.FunctionDef) and x.name=='ref');node.name='reference';node.body[-1]=ast.Return(value=ast.Tuple(elts=[node.body[-1].value,ast.Call(func=ast.Name(id='check',ctx=ast.Load()),args=[ast.Name(id='d',ctx=ast.Load()),ast.Name(id='c',ctx=ast.Load())],keywords=[])],ctx=ast.Load()));ast.fix_missing_locations(node);ns={};exec(compile(ast.Module(body=[node],type_ignores=[]),'independentactor','exec'),ns);ref=ns['reference'];legalcache={};valuecache={};refnodes=0;refhits=0;counts=collections.Counter();owncache={};nativecache={};BASE=tuple(plan['baseline'])
def legal(s):
 if s in legalcache:return legalcache[s]
 ll,ch=ref(s)
 if len(legalcache)<60000:legalcache[s]=(ll,ch)
 return ll,ch
def reference_minimax(s,d,price,c,ply):
 global refnodes,refhits
 key=s,d,price,c,ply
 if key in valuecache:refhits+=1;return valuecache[key]
 refnodes+=1
 if refnodes%1024==0:STOP.stop();assert time.monotonic()<deadline
 ll,ch=legal(s)
 if not ll:v=(-(32000-ply) if s[16]==c else 32000-ply) if ch else 0
 elif sum(p!='.' for p in s[:16])==2:v=0
 elif d==0:
  weights=dict(zip('RNBP',price));v=sum((1 if p.islower()==bool(c) else -1)*weights.get(p.upper(),0) for p in s[:16] if p!='.')
 else:
  vv=[reference_minimax(t,d-1,price,c,ply+1) for u,t in ll];v=max(vv) if s[16]==c else min(vv)
 if len(valuecache)<120000:valuecache[key]=v
 return v
for line in (P/'full_choices.jsonl').open():
 x=json.loads(line);p=tuple(x['price']);s=tuple(x['state']);assert (p,s) not in owncache and x['fen']==T.fen(s) and x['depth']==3;ll,ch=legal(s);assert ll==T.moves(s);scores=[{'move':u,'score':reference_minimax(t,2,p,s[16],1)} for u,t in ll];best=min(scores,key=lambda z:(-z['score'],z['move']));assert scores==x['scores'] and (best['move'],best['score'])==(x['move'],x['value']);owncache[p,s]=x['move'];counts['all_independently_exact_D3_rootvalues']+=1;counts['all_root_action_values']+=len(scores)
 if counts['all_independently_exact_D3_rootvalues']%1000==0:print('EXACT_REFERENCE',counts['all_independently_exact_D3_rootvalues'],refnodes,round(time.monotonic()-start,2),flush=True)
for folder in ['task1678','task1696']:
 for line in (R/f'results/dev_aux/{folder}/choices.jsonl').open():
  x=json.loads(line)
  if tuple(x['price'])!=BASE:assert folder=='task1678';continue
  s=tuple(x['state']);assert x['move'] in dict(legal(s)[0]) and x['fen']==T.fen(s)
  if s in nativecache:assert nativecache[s]==x['move']
  nativecache[s]=x['move']
  if folder=='task1696':
   counts['Native_newgo']+=1
   for info in x['uci_info']:
    a=info.split()
    if 'pv' in a:
     t=s
     for u in a[a.index('pv')+1:]:t=dict(T.moves(t))[u];counts['Native_PVmoves']+=1
families={f['family']:f for f in plan['families']};groups=collections.defaultdict(list);seen=set()
for line in (P/'games.jsonl').open():
 x=json.loads(line);price=tuple(x['price']);f=families[x['family']];s=tuple(f['roots'][x['color']]);assert s==tuple(x['root']) and f['phase']==x['phase'];c=s[16];visited=[];key=price,x['phase'],x['family'],x['color'];assert key not in seen;seen.add(key)
 for step in x['trajectory']:
  ll,ch=legal(s);assert ll==T.moves(s) and ll and s not in visited and not T.bare(s) and step['state']==list(s);u=(owncache[price,s] if s[16]==c else nativecache[s]) if len(ll)>1 else ll[0][0];assert step['move']==u and step['own']==(s[16]==c);visited.append(s);s=dict(ll)[u];counts['plies']+=1
 ll,ch=legal(s);assert s==tuple(x['end'])
 if not ll:pay=(-1 if s[16]==c else 1) if ch else 0;cat='PHYSICAL_MATE' if ch else 'PHYSICAL_STALE'
 elif T.bare(s):pay=0;cat='BARE_KINGS_DRAW'
 elif s in visited:assert x['repeat']==[visited.index(s),len(visited)];pay=0;cat='PROVED_POLICY_CYCLE_DRAW'
 else:assert len(visited)==plan['H'];pay=None;cat='UNRESOLVED'
 assert (pay,cat)==(x['payoff'],x['category']) and x['lower']==(-1 if pay is None else pay) and x['upper']==(1 if pay is None else pay);groups[price,x['phase']].append(x);counts['games']+=1;counts[cat]+=1
assert counts['Native_newgo']==run['actual_go'] and counts['games']==1536+128*len(run['DEV']);assert counts['all_independently_exact_D3_rootvalues']==run['unique_full_choices']
sel={phase:tuple(min([x for x in run['TRAIN'] if x['phase']==phase],key=lambda x:(-x['finite_net'],x['price']))['price']) for phase in ['TRAIN1','TRAIN2']};pooled={tuple(x['price']):sum(z['finite_net'] for z in run['TRAIN'] if z['price']==x['price'])/2 for x in run['TRAIN']};sel['POOLED']=min(pooled,key=lambda p:(-pooled[p],p));assert sel=={k:tuple(v) for k,v in run['selected'].items()}
for z in run['TRAIN']+run['DEV']:
 xx=groups[tuple(z['price']),z['phase']];assert z['games']==len(xx) and z['finite_net']==sum(x['payoff'] or 0 for x in xx)/len(xx)
C=tuple(plan['fixed_native_candidate']);old=[json.loads(l) for l in (R/'results/dev_aux/task1678/games.jsonl').open() if json.loads(l)['phase']=='DEV'];og=collections.defaultdict(list)
for x in old:og[tuple(x['price']),'DEV'].append(x)
def means(group,p):
 dd=collections.defaultdict(list)
 for x in group[p,'DEV']:dd[x['family']].append(x['payoff'] or 0)
 assert all(len(z)==2 for z in dd.values());return {f:sum(z)/2 for f,z in dd.items()}
b=means(groups,BASE);a=means(groups,C);ob=means(og,BASE);oa=means(og,C);ids=sorted(a);g=[a[f]-b[f] for f in ids];interaction=[a[f]-b[f]-oa[f]+ob[f] for f in ids];rng=random.Random(2026696600);bs=[];bi=[]
for _ in range(10000):
 ss=rng.choices([i for i,f in enumerate(ids) if f%2==0],k=32)+rng.choices([i for i,f in enumerate(ids) if f%2==1],k=32);bs.append(sum(g[i] for i in ss)/64);bi.append(sum(interaction[i] for i in ss)/64)
bs.sort();bi.sort();out={'status':'PASS_ALL_COMPLETE_D3_VALUES_INDEPENDENT_ACTOR_EXPLICIT_MINIMAX_AND_ALLPHYSICAL_POLICIES','counts':dict(counts),'selected':sel,'fixed_candidate_gain':sum(g)/64,'fixed_candidate_family95':[bs[249],bs[9749]],'gain_change_COMPLETE_D3_minus_Native64':sum(interaction)/64,'gain_change_family95':[bi[249],bi[9749]],'independent_reference_expanded':refnodes,'reference_cache_hits':refhits,'seconds':time.monotonic()-start,'scope':'CompleteD3candidate vsSAMEactualNativeunitcold64op. Sameexposedroot/cohorts andpricegrid; changedcandidate algorithm+workbudget. Noequalresource/matureoptimality/fullGeneric/humanratio uniqueness claim. IndependentALLrootactionfinite3values, noNNUE/quantityfitness/oracleWIN.'};(O/'result.json').write_text(json.dumps(out,indent=2));print(out)
