import json,sys,time,math,random,hashlib,itertools

from pathlib import Path

from fractions import Fraction
F=Fraction

R=Path.cwd();O=R/'results/dev_aux/task829';D=R/'results/dev_aux/task827/execution_inputs.json';d=json.loads(D.read_bytes());start=time.perf_counter()

for n in [360,364,381]:sys.path.insert(0,str(R/f'results/dev_aux/task{n}'))

import adapter as A,run as G,audit as V

import copy
assert d['blocks']==['A','B','B','A']
constructor=G.full_root;rootcache={};cache_stats=dict(original_constructions=0,clone_lookups=0)
def immutable(x):return (x[0].sfen(),tuple(x[1]),tuple(x[2]),tuple(x[3]))
def clone_root(f):
 key=json.dumps(f,sort_keys=True,separators=(',',':'))
 if key not in rootcache:
  x=constructor(f);rootcache[key]=(x,immutable(x));cache_stats['original_constructions']+=1
 x,signature=rootcache[key];assert immutable(x)==signature;z=(copy.deepcopy(x[0]),list(x[1]),list(x[2]),list(x[3]));assert immutable(z)==signature;cache_stats['clone_lookups']+=1;return z
G.full_root=clone_root
s=(R/'results/dev_aux/task522/audit.py').read_text(encoding='utf-8');exec(compile(s[s.index('def tables('):s.index('nativegames=0')],'tablesonly','exec'));s=(R/'results/dev_aux/task600/audit.py').read_text(encoding='utf-8');s=s[s.index('def game('):s.index('for task,opp in')].replace('cap=12;','cap=g["cap"];').replace("dict(kind='cap12' if cap==12 else 'cap24',winner=None)","dict(kind='cap'+str(cap),winner=None)");counts=dict(games=0,actual_go=0,PV_moves=0,Python_actual_actions=0,random_draws=0,sorted_legal_arrays=0,price_ACK_entries=0,batches=0,proposal_rounds=0,prefixes=0);exec(compile(s,'independentphysical','exec'));summ={};sources={}

for task in [828]:

 P=R/f'results/dev_aux/task{task}';raw=iter((P/'queries.jsonl').open(encoding='utf-8'));gs=[]

 for i,text in enumerate((P/'games.jsonl').open(encoding='utf-8'),1):

  g=json.loads(text);assert g['cap']==12;assert g['root'] in next(p['roots'] for p in d['pools'] if p['name']==g['pool']);z=game(g,'unit',raw);b,k,ch,mo=G.full_root(g['root'])

  for a in g['actions'][:12]:

   assert G.terminal(b,k,ch,mo) is None;m=A.shogi.Move.from_usi(a['move']);assert m in b.legal_moves;mo.append(b.turn);b.push(m);ch.append(b.is_check());k.append(G.key(b))

  q12=G.quantity(b,g['color']);q24=z['raw_quantity'];fitness=F(q12+q24,38);assert q12==g['quantity12'] and g['quantity24'] is None and g['fitness']==g['goal'];z.update(opponent='unit',pool=g['pool'],quantity12=q12,quantity24=q24,fitness=str(fitness));gs.append(z);counts['prefixes']+=1

  if i%1024==0:print('multiPython',task,i,round(time.perf_counter()-start,1),flush=True)

 assert next(raw,None) is None;counts['price_ACK_entries']+=tables(json.loads((P/'price_acks.json').read_bytes()));summ[task]=gs;sources[task]={n:hashlib.sha256((P/n).read_bytes()).hexdigest() for n in ['games.jsonl','queries.jsonl','price_acks.json','result.json']};(O/f'physical_stage_{task}.json').write_text(json.dumps(dict(stage=task,counts=dict(counts),source_sha256=sources[task]),indent=2),encoding='utf-8')


import re,copy
actual=[json.loads(x) for x in (R/'results/dev_aux/task828/games.jsonl').open(encoding='utf-8')];assert len(actual)==64
def sem(g):
 z=copy.deepcopy(g)
 for k in ['block','journal_policy','seconds']:z.pop(k,None)
 for q in z['queries']:
  q.pop('seconds',None);q['lines']=[re.sub(r'\b(?:nps|time) \d+',lambda m:m[0].split()[0]+' OMIT',t) for t in q['lines']]
 return z
for i in range(16):
 base=sem(actual[i])
 for bi in [1,2,3]:assert sem(actual[bi*16+i])==base,(bi,i)
out=dict(all64_non_time_results_equal=True,status='PASS_ALL64_ACTUAL_ABBA_IO_AND_SEMANTIC_EQUALITY',root_cache_stats=cache_stats,counts=counts,source_sha256=sources,new_go=0,seconds=time.perf_counter()-start,scope='ALL828actual64ABBA/H12 fullindependentPython rules/history/PV/material/terminal/ACK/raw metadata/pairedcells; allnegativekept. Immutablecanonicalrootcache no skippedchecks. Shortwindow notwholeWDL/source/human/general-domainproof.');assert all(immutable(x)==signature for x,signature in rootcache.values());(O/'result.json').write_text(json.dumps(out,indent=2),encoding='utf-8');print(json.dumps({k:v for k,v in out.items() if k!='source_sha256'}))

