import json,sys,time,math,random,hashlib,copy
from pathlib import Path
from fractions import Fraction
F=Fraction
R=Path.cwd();O=R/'results/dev_aux/task806';D=R/'results/dev_aux/task803/declaration.json';d=json.loads(D.read_bytes());start=time.perf_counter()
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
assert all(json.loads((R/f'results/dev_aux/task{n}/result.json').read_bytes())['status'].startswith('PASS_ALL_') for n in [789,792])
manifest=json.loads((R/'results/dev_aux/task803/cached_source_manifest.json').read_bytes())
for n,files in manifest['source_sha256'].items():
 for name,sha in files.items():assert hashlib.sha256((R/f'results/dev_aux/task{n}'/name).read_bytes()).hexdigest()==sha
 summ[int(n)]=[json.loads(t) for t in (R/f'results/dev_aux/task{n}/games.jsonl').open(encoding='utf-8')]
for task in [804]:
 p=R/f'results/dev_aux/task{task}';raw=iter((p/'queries.jsonl').open(encoding='utf-8'));gs=[]
 for i,text in enumerate((p/'games.jsonl').open(encoding='utf-8'),1):
  g=json.loads(text);assert g['cap']==(12 if task==804 else 24) and g['root']==d['roots'][g['root']['index']];d['fixed_opponent']=d['opponents'][g['opponent']];z=game(g,'unit',raw);b,k,ch,mo=G.full_root(g['root'])
  for a in g['actions'][:12]:
   assert G.terminal(b,k,ch,mo) is None;m=A.shogi.Move.from_usi(a['move']);assert m in b.legal_moves;mo.append(b.turn);b.push(m);ch.append(b.is_check());k.append(G.key(b))
  q12=G.quantity(b,g['color']);t12=G.terminal(b,k,ch,mo);fit=F(q12,19) if t12 is None else F(0 if t12['winner'] is None else 1 if t12['winner']==g['color'] else -1);assert q12==g['quantity12'] and g['quantity24']==(z['raw_quantity'] if task==788 else None) and str(fit)==g['fitness'];z.update(opponent=g['opponent'],quantity12=q12,quantity_final=z['raw_quantity'],fitness=str(fit),terminal12=t12);gs.append(z);counts['prefixes']+=1
  if i%512==0:print('FIXED_PYTHON',task,i,round(time.perf_counter()-start,1),flush=True)
 assert next(raw,None) is None;counts['price_ACK_entries']+=tables(json.loads((p/'price_acks.json').read_bytes()));summ[task]=gs;sources[task]={n:hashlib.sha256((p/n).read_bytes()).hexdigest() for n in ['games.jsonl','queries.jsonl','price_acks.json','result.json']};(O/f'physical_stage_{task}.json').write_text(json.dumps(dict(stage=task,counts=dict(counts),source_sha256=sources[task]),indent=2),encoding='utf-8')
 if task==788:break
 ep=json.loads((p/'endpoints.json').read_bytes());assert ep['declaration_sha256']==hashlib.sha256(D.read_bytes()).hexdigest();train=[f for f in d['roots'] if f['phase']=='train'];cells=[(opp,f,c) for opp in d['opponents'] for f in train for c in [0,1]]
 for initial in d['initial_profiles']:
  w=list(initial['weights']);base=None;updates=[u for u in ep['updates'] if u['start']==initial['name']];assert len(updates)==12
  for i,u in enumerate(updates):
   axis=d['axes'][i];assert u['iteration']==i and u['axis']==axis and u['start_weights']==w;expected=[]
   for mult in d['multipliers']:
    ww=list(w);ww[axis]=max(32,min(4096,math.floor(w[axis]*mult+.5)));expected.append(ww)
   cs=u['candidates'];assert [x['weights'] for x in cs]==expected
   for c in cs:
    rg=[summ[int(x['file'].split('/')[-2][4:])][x['line']-1] for x in c['sources']];assert [(g.get('opponent','unit'),g['root'],g['color']) for g in rg]==cells and all(g['weights']==c['weights'] for g in rg);assert c['objective']=='terminal_first_else_quantitymagnitude12' and c['goals']==[g['fitness'] for g in rg] and c['quantity12']==[g['quantity12'] for g in rg] and c['quantity_final']==[g['raw_quantity'] for g in rg] and c['terminations']==[g['termination'] for g in rg];assert F(c['mean_goal'])==sum(F(g['fitness']) for g in rg)/64;counts['batches']+=1
   mu=[]
   for c in cs:
    tt=c['terminations'];loss=sum(not t['kind'].startswith('cap') and t['winner'] is not None and t['winner']!=j%2 for j,t in enumerate(tt));win=sum(not t['kind'].startswith('cap') and t['winner']==j%2 for j,t in enumerate(tt));mu.append((-loss,win,F(c['mean_goal'])))
   best=max(range(7),key=lambda j:mu[j]);assert best==u['selected_index'] and F(cs[best]['mean_goal'])-F(cs[0]['mean_goal'])==F(u['accepted_gain']);assert u['lex_keys']==[[z[0],z[1],str(z[2])] for z in mu] and u['accepted']==(mu[best]>mu[0]);assert base is None or mu[0]==base;w=list(cs[best]['weights']);base=mu[best];assert w==u['after_weights'];counts['proposal_rounds']+=1
  assert next(x['endpoint'] for x in ep['endpoints'] if x['start']==initial['name'])==w
assert all(immutable(x)==signature for x,signature in cache.values());out=dict(status='PASS_ALL_MIXED_OPPONENT_NEW_AND_QUALIFIED_CACHE',counts=counts,root_cache_stats=cache_stats,source_sha256=sources,new_go=0,seconds=time.perf_counter()-start,scope='ALL804NEW plusqualified787791unitcells H12fit independentPython fullhistory/legal/PV/material/terminal/ACK/rawquery plusH12 literalquantityfeedback andALL24lexicographic coordinateupdate decisions/168logicalgridpoints. Immutable16trainroot validatedconstructor/deepclones no skippedchecks, no newgo. Allendpoints before anyD/Edevelopment.');(O/'result.json').write_text(json.dumps(out,indent=2),encoding='utf-8');print(json.dumps({k:v for k,v in out.items() if k!='source_sha256'}))
