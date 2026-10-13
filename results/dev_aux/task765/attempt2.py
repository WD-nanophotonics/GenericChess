import json,sys,time,math,random,hashlib,copy
from pathlib import Path
from fractions import Fraction
F=Fraction
R=Path.cwd();O=R/'results/dev_aux/task765';D=R/'results/dev_aux/task762/declaration.json';d=json.loads(D.read_bytes());start=time.perf_counter()
for n in [360,364,381]:sys.path.insert(0,str(R/f'results/dev_aux/task{n}'))
import adapter as A,run as G,audit as V
constructor=G.full_root;cache={};cache_stats=dict(original_constructions=0,clone_lookups=0)
def immutable(x):return (x[0].sfen(),tuple(x[1]),tuple(x[2]),tuple(x[3]))
def cloned(f):
 key=json.dumps(f,sort_keys=True,separators=(',',':'))
 if key not in cache:
  x=constructor(f);cache[key]=(x,immutable(x));cache_stats['original_constructions']+=1
 x,signature=cache[key];assert immutable(x)==signature;z=(copy.deepcopy(x[0]),list(x[1]),list(x[2]),list(x[3]));assert immutable(z)==signature;cache_stats['clone_lookups']+=1;return z
G.full_root=cloned
s=(R/'results/dev_aux/task522/audit.py').read_text(encoding='utf-8');exec(compile(s[s.index('def tables('):s.index('nativegames=0')],'tablesonly','exec'));s=(R/'results/dev_aux/task600/audit.py').read_text(encoding='utf-8');s=s[s.index('def game('):s.index('for task,opp in')].replace('cap=12;','cap=g["cap"];').replace("dict(kind='cap12' if cap==12 else 'cap24',winner=None)","dict(kind='cap'+str(cap),winner=None)");counts=dict(games=0,actual_go=0,PV_moves=0,Python_actual_actions=0,random_draws=0,sorted_legal_arrays=0,price_ACK_entries=0,batches=0,proposal_rounds=0,prefixes=0);exec(compile(s,'independentphysical','exec'));summ={};sources={}
manifest=json.loads((R/'results/dev_aux/task762/cached_source_manifest.json').read_bytes())
for n,names in manifest['source_sha256'].items():
 for name,sha in names.items():assert hashlib.sha256((R/f'results/dev_aux/task{n}'/name).read_bytes()).hexdigest()==sha
 summ[int(n)]=[json.loads(t) for t in (R/f'results/dev_aux/task{n}/games.jsonl').open(encoding='utf-8')]
for qn in [745,751]:
 qual=json.loads((R/f'results/dev_aux/task{qn}/result.json').read_bytes());assert qual['status'].startswith('PASS_ALL_')
 for n,names in qual['source_sha256'].items():
  for name,sha in names.items():assert hashlib.sha256((R/f'results/dev_aux/task{n}'/name).read_bytes()).hexdigest()==sha
def signgoal(g):
 t=g['termination'];q=g['quantity12'];return str(F((q>0)-(q<0)) if t['kind'].startswith('cap') else F(0 if t['winner'] is None else 1 if t['winner']==g['color'] else -1))
def states(c):
 return ['win' if t['winner']==i%2 else 'loss' if t['winner'] is not None else 'draw' if not t['kind'].startswith('cap') else 'unfinished' for i,t in enumerate(c['terminations'])]
def feasible(base,c):
 return all(not(x!='loss' and y=='loss') and not(x=='win' and y!='win') for x,y in zip(states(base),states(c)))
for task in [763,764]:
 p=R/f'results/dev_aux/task{task}';raw=iter((p/'queries.jsonl').open(encoding='utf-8'));gs=[]
 for i,text in enumerate((p/'games.jsonl').open(encoding='utf-8'),1):
  g=json.loads(text);assert g['cap']==(12 if task==763 else 24) and g['root']==d['roots'][g['root']['index']];z=game(g,'unit',raw);b,k,ch,mo=G.full_root(g['root'])
  for a in g['actions'][:12]:
   assert G.terminal(b,k,ch,mo) is None;m=A.shogi.Move.from_usi(a['move']);assert m in b.legal_moves;mo.append(b.turn);b.push(m);ch.append(b.is_check());k.append(G.key(b))
  q12=G.quantity(b,g['color']);t12=G.terminal(b,k,ch,mo);fit=F((q12>0)-(q12<0)) if t12 is None else F(0 if t12['winner'] is None else 1 if t12['winner']==g['color'] else -1);assert q12==g['quantity12'] and g['quantity24']==(z['raw_quantity'] if task==764 else None) and str(fit)==g['fitness'];z.update(quantity12=q12,quantity_final=z['raw_quantity'],fitness=str(fit),terminal12=t12);gs.append(z);counts['prefixes']+=1
  if i%512==0:print('FIXED_PYTHON',task,i,round(time.perf_counter()-start,1),flush=True)
 assert next(raw,None) is None;counts['price_ACK_entries']+=tables(json.loads((p/'price_acks.json').read_bytes()));summ[task]=gs;sources[task]={n:hashlib.sha256((p/n).read_bytes()).hexdigest() for n in ['games.jsonl','queries.jsonl','price_acks.json','result.json']};(O/f'physical_stage_{task}.json').write_text(json.dumps(dict(stage=task,counts=dict(counts),source_sha256=sources[task]),indent=2),encoding='utf-8')
 if task==764:break
 ep=json.loads((p/'endpoints.json').read_bytes());assert ep['declaration_sha256']==hashlib.sha256(D.read_bytes()).hexdigest();train=[f for f in d['roots'] if f['phase']=='train'];cells=[(f,c) for f in train for c in [0,1]]
 for initial in d['initial_profiles']:
  w=list(initial['weights']);base=None;updates=[u for u in ep['updates'] if u['start']==initial['name']];assert len(updates)==12
  for i,u in enumerate(updates):
   axis=d['axes'][i];assert u['iteration']==i and u['axis']==axis and u['start_weights']==w;expected=[]
   for mult in d['multipliers']:
    ww=list(w);ww[axis]=max(32,min(4096,math.floor(w[axis]*mult+.5)));expected.append(ww)
   cs=u['candidates'];assert [x['weights'] for x in cs]==expected
   for c in cs:
    rg=[summ[int(x['file'].split('/')[-2][4:])][x['line']-1] for x in c['sources']];assert [(g['root'],g['color']) for g in rg]==cells and all(g['weights']==c['weights'] for g in rg);assert c['objective']=='terminal_first_else_quantitysign12' and c['goals']==[signgoal(g) for g in rg] and c['quantity12']==[g['quantity12'] for g in rg] and c['quantity_final']==[g['raw_quantity'] for g in rg] and c['terminations']==[g['termination'] for g in rg];assert F(c['mean_goal'])==sum(F(z) for z in c['goals'])/32;counts['batches']+=1
   mu=[F(c['mean_goal']) for c in cs];allowed=[feasible(cs[0],c) for c in cs];assert allowed==u['guard_feasible'] and allowed[0];best=max([j for j in range(7) if allowed[j]],key=lambda j:mu[j]);assert best==u['selected_index'] and mu[best]-mu[0]==F(u['accepted_gain']);assert base is None or mu[0]==base;w=list(cs[best]['weights']);base=mu[best];assert w==u['after_weights'];counts['proposal_rounds']+=1
  assert next(x['endpoint'] for x in ep['endpoints'] if x['start']==initial['name'])==w
freeze=json.loads((R/'results/dev_aux/task762/all_endpoints_frozen.json').read_bytes());assert freeze['before_any_new_development'] and freeze['endpoint_sha256']==hashlib.sha256((R/'results/dev_aux/task763/endpoints.json').read_bytes()).hexdigest();r=json.loads((R/'results/dev_aux/task764/result.json').read_bytes());dev=[f for f in d['roots'] if f['phase']=='development'];cells=[(f,c) for f in dev for c in [0,1]]
for row in r['rows']:
 rg=[summ[int(x['file'].split('/')[-2][4:])][x['line']-1] for x in row['batch']['sources']];assert [(g['root'],g['color']) for g in rg]==cells and all(g['weights']==row['batch']['weights'] for g in rg);expected=[]
 for g in rg:
  bb,kk,cc,mm=G.full_root(g['root'])
  for act in g['actions'][:12]:mm.append(bb.turn);bb.push(A.shogi.Move.from_usi(act['move']));cc.append(bb.is_check());kk.append(G.key(bb))
  tt=G.terminal(bb,kk,cc,mm);qq=G.quantity(bb,g['color']);expected.append(str(F((qq>0)-(qq<0)) if tt is None else F(0 if tt['winner'] is None else 1 if tt['winner']==g['color'] else -1)))
 assert row['batch']['goals']==expected
assert all(immutable(x)==signature for x,signature in cache.values());out=dict(status='PASS_ALL_CELL_TERMINAL_GUARDED_LEARNING_AND_DEV',counts=counts,root_cache_stats=cache_stats,source_sha256=sources,new_go=0,seconds=time.perf_counter()-start,scope='ALL763NEWcap12fit/764NEWcap24dev plussamequalified743749744750cache independentPython rules/fullhistory/PV/nativequeries/ACK/material/terminal/H12prefix-royalfirstsignfitness plusALL24guardedcoordinateupdates/168logicalgridpoints; ALLchosenupdates nonewtrainloss/lostwin percell, allendpoints beforeNEWdev. Exactcanonicalfullroot firstvalidatedconstruction/deepclone preservesimmutablekeys/check/mover andboard, no skippedrule/price/source verification. Deterministicfixedunit opponent, no fakeRNGreplicates, Guard protectsobservedH12TRAINcells only, postABdev exploratorymethod construction; no source/humanfitness/universalhumanprices claim.');(O/'result.json').write_text(json.dumps(out,indent=2),encoding='utf-8');print(json.dumps({k:v for k,v in out.items() if k!='source_sha256'}))
