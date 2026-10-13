import json,sys,time,math,random,hashlib,itertools

from pathlib import Path

from fractions import Fraction
F=Fraction

R=Path.cwd();O=R/'results/dev_aux/task710';D=R/'results/dev_aux/task708/execution_inputs.json';d=json.loads(D.read_bytes());start=time.perf_counter()

for n in [360,364,381]:sys.path.insert(0,str(R/f'results/dev_aux/task{n}'))

import adapter as A,run as G,audit as V

s=(R/'results/dev_aux/task522/audit.py').read_text(encoding='utf-8');exec(compile(s[s.index('def tables('):s.index('nativegames=0')],'tablesonly','exec'));s=(R/'results/dev_aux/task600/audit.py').read_text(encoding='utf-8');s=s[s.index('def game('):s.index('for task,opp in')].replace('cap=12;','cap=g["cap"];').replace("dict(kind='cap12' if cap==12 else 'cap24',winner=None)","dict(kind='cap'+str(cap),winner=None)");counts=dict(games=0,actual_go=0,PV_moves=0,Python_actual_actions=0,random_draws=0,sorted_legal_arrays=0,price_ACK_entries=0,batches=0,proposal_rounds=0,prefixes=0);exec(compile(s,'independentphysical','exec'));summ={};sources={}

for task in [709]:

 P=R/f'results/dev_aux/task{task}';raw=iter((P/'queries.jsonl').open(encoding='utf-8'));gs=[]

 for i,text in enumerate((P/'games.jsonl').open(encoding='utf-8'),1):

  g=json.loads(text);d['seed_base']=d['seed_bases'][g['replica']];assert g['seed_base']==d['seed_base'] and g['cap']==12 and g['root']==d['roots'][g['root']['index']];z=game(g,'random',raw);b,k,ch,mo=G.full_root(g['root'])

  for a in g['actions'][:12]:

   assert G.terminal(b,k,ch,mo) is None;m=A.shogi.Move.from_usi(a['move']);assert m in b.legal_moves;mo.append(b.turn);b.push(m);ch.append(b.is_check());k.append(G.key(b))

  q12=G.quantity(b,g['color']);q24=z['raw_quantity'];fitness=F(q12+q24,38);assert q12==g['quantity12'] and q24==g['quantity24'] and str(fitness)==g['fitness'];z.update(replica=g['replica'],quantity12=q12,quantity24=q24,fitness=str(fitness));gs.append(z);counts['prefixes']+=1

  if i%1024==0:print('multiPython',task,i,round(time.perf_counter()-start,1),flush=True)

 assert next(raw,None) is None;counts['price_ACK_entries']+=tables(json.loads((P/'price_acks.json').read_bytes()));summ[task]=gs;sources[task]={n:hashlib.sha256((P/n).read_bytes()).hexdigest() for n in ['games.jsonl','queries.jsonl','price_acks.json','result.json']};(O/f'physical_stage_{task}.json').write_text(json.dumps(dict(stage=task,counts=dict(counts),source_sha256=sources[task]),indent=2),encoding='utf-8')


import copy,re
assert json.loads((R/'results/dev_aux/task697/result.json').read_bytes())['status']=='PASS_ALL_PAIRED_H12_CONTROL_CACHED_AND_NEW'
old=[json.loads(t) for t in (R/'results/dev_aux/task696/games.jsonl').open(encoding='utf-8')];new=[json.loads(t) for t in (R/'results/dev_aux/task709/games.jsonl').open(encoding='utf-8')];assert len(old)==len(new)==128
qualified=json.loads((R/'results/dev_aux/task697/result.json').read_bytes())
for n,sha in qualified['source_sha256']['696'].items():assert hashlib.sha256((R/'results/dev_aux/task696'/n).read_bytes()).hexdigest()==sha
def semq(q):
 x=copy.deepcopy(q);x.pop('seconds',None);x['lines']=[re.sub(r'\b(?:nps|time) \d+',lambda m:m[0].split()[0]+' OMIT',a) for a in x['lines']];return x
for a,b in zip(old,new):
 assert (a['weights'],a['root'],a['replica'],a['color'])==(b['weights'],b['root'],b['replica'],b['color']);n=min(12,len(a['actions']));assert b['actions']==a['actions'][:n] and a['quantity12']==b['quantity12']==b['quantity24'];assert [semq(q) for q in b['queries']]==[semq(q) for q in a['queries'] if q['ply']<n]

out=dict(status='PASS_ALL128_ACTUAL_CAP12_PREFIX_CONTROLS',counts=counts,source_sha256=sources,new_go=0,seconds=time.perf_counter()-start,scope='ALL709 actualcap12paths plusexactqualified696cap24prefix independentPython rules/PV/fullhistory/metadata/material/terminal/RNG/legalarrays/reset/ACK plusALLphysicalH12prefix/count/fitness andALL128independentactualcap12 controls, not justcachedoldprefix. TwofullydisjointRNGsets averaged BEFOREselection, no newlearning; ALL4profile callerqualification. Allclippedpricealiases explicitsources notnewgames. No source/humanfitness oruniversalvalueproof.');(O/'result.json').write_text(json.dumps(out,indent=2),encoding='utf-8');print(json.dumps({k:v for k,v in out.items() if k!='source_sha256'}))

