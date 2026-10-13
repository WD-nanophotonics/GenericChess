import json,sys,time,math,random,hashlib,itertools

from pathlib import Path

from fractions import Fraction
F=Fraction

R=Path.cwd();O=R/'results/dev_aux/task778';D=R/'results/dev_aux/task769/execution_inputs.json';d=json.loads(D.read_bytes());start=time.perf_counter()

for n in [360,364,381]:sys.path.insert(0,str(R/f'results/dev_aux/task{n}'))

import adapter as A,run as G,audit as V

import copy
assert json.loads((R/'results/dev_aux/task765/result.json').read_bytes())['status']=='PASS_ALL_CELL_TERMINAL_GUARDED_LEARNING_AND_DEV'
constructor=G.full_root;rootcache={};cache_stats=dict(original_constructions=0,clone_lookups=0)
def immutable(x):return (x[0].sfen(),tuple(x[1]),tuple(x[2]),tuple(x[3]))
def clone_root(f):
 key=json.dumps(f,sort_keys=True,separators=(',',':'))
 if key not in rootcache:
  x=constructor(f);rootcache[key]=(x,immutable(x));cache_stats['original_constructions']+=1
 x,signature=rootcache[key];assert immutable(x)==signature;z=(copy.deepcopy(x[0]),list(x[1]),list(x[2]),list(x[3]));assert immutable(z)==signature;cache_stats['clone_lookups']+=1;return z
G.full_root=clone_root
s=(R/'results/dev_aux/task522/audit.py').read_text(encoding='utf-8');exec(compile(s[s.index('def tables('):s.index('nativegames=0')],'tablesonly','exec'));s=(R/'results/dev_aux/task600/audit.py').read_text(encoding='utf-8');s=s[s.index('def game('):s.index('for task,opp in')].replace('cap=12;','cap=g["cap"];').replace("dict(kind='cap12' if cap==12 else 'cap24',winner=None)","dict(kind='cap'+str(cap),winner=None)");counts=dict(games=0,actual_go=0,PV_moves=0,Python_actual_actions=0,random_draws=0,sorted_legal_arrays=0,price_ACK_entries=0,batches=0,proposal_rounds=0,prefixes=0);exec(compile(s,'independentphysical','exec'));summ={};sources={}

for task in [777]:

 P=R/f'results/dev_aux/task{task}';raw=iter((P/'queries.jsonl').open(encoding='utf-8'));gs=[]

 for i,text in enumerate((P/'games.jsonl').open(encoding='utf-8'),1):

  g=json.loads(text);d['fixed_opponent']=d['opponents'][g['opponent']];assert g['cap']==24;assert g['root'] in next(p['roots'] for p in d['pools'] if p['name']==g['pool']);z=game(g,'unit',raw);b,k,ch,mo=G.full_root(g['root'])

  for a in g['actions'][:12]:

   assert G.terminal(b,k,ch,mo) is None;m=A.shogi.Move.from_usi(a['move']);assert m in b.legal_moves;mo.append(b.turn);b.push(m);ch.append(b.is_check());k.append(G.key(b))

  q12=G.quantity(b,g['color']);q24=z['raw_quantity'];fitness=F(q12+q24,38);assert q12==g['quantity12'] and q24==g['quantity24'] and str(fitness)==g['fitness'];z.update(pool=g['pool'],opponent=g['opponent'],quantity12=q12,quantity24=q24,fitness=str(fitness));gs.append(z);counts['prefixes']+=1

  if i%1024==0:print('multiPython',task,i,round(time.perf_counter()-start,1),flush=True)

 assert next(raw,None) is None;counts['price_ACK_entries']+=tables(json.loads((P/'price_acks.json').read_bytes()));summ[task]=gs;sources[task]={n:hashlib.sha256((P/n).read_bytes()).hexdigest() for n in ['games.jsonl','queries.jsonl','price_acks.json','result.json']};(O/f'physical_stage_{task}.json').write_text(json.dumps(dict(stage=task,counts=dict(counts),source_sha256=sources[task]),indent=2),encoding='utf-8')


plan=json.loads((R/'results/dev_aux/task776/declaration.json').read_bytes());assert len(summ[777])==len(plan['remaining'])==250
for z,cell in zip(summ[777],plan['remaining']):assert (z['opponent'],z['weights'],z['root'],z['color'])==(cell['opponent'],cell['weights'],cell['root'],cell['color'])
result=json.loads((R/'results/dev_aux/task777/result.json').read_bytes());assert result['status']=='COMPLETE_ALL250_ORIGINAL_MISSING_CASES' and result['original769_fuse_failure_retained'] and not result['original769_complete']

out=dict(status='PASS_ALL250_TECHNICAL_COMPLETION_CASES',root_cache_stats=cache_stats,counts=counts,source_sha256=sources,new_go=0,seconds=time.perf_counter()-start,scope='ALL777NEW missingcasesH24 BOTHfixedprice opponents paths independentPython rules/PV/fullhistory/metadata/material/terminal/RNG/legalarrays/reset/ACK plusALLphysicalH12prefix/count/fitness and Exactly250originalmissingcases, no extra sample/fixedopponenttable/warmreset BOTHplayers, exactaliases. Deterministicopponent no fakeRNGreplication; allprofiles beforeprobes, alreadyexposedrootpools exploratory. Allclippedpricealiases explicitsources notnewgames. 769bothfixedunit/random2514price opponents; rootcache immutability holds, Original769failed120fuse unchanged;775198closed+12partialgoqualified andALL250missingcases match776manifest, no completedgame rerun orrestoredoriginalbudgetstatus. No engine/general speedup claim orsource/humanfitness.');assert all(immutable(x)==signature for x,signature in rootcache.values());(O/'result.json').write_text(json.dumps(out,indent=2),encoding='utf-8');print(json.dumps({k:v for k,v in out.items() if k!='source_sha256'}))

