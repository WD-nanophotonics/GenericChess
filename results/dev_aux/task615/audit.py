import json,sys,time,math,random,hashlib,itertools
from pathlib import Path
from fractions import Fraction
R=Path.cwd();O=R/'results/dev_aux/task615';O.mkdir(exist_ok=True);D=R/'results/dev_aux/task596/declaration.json';d=json.loads(D.read_bytes());start=time.perf_counter()
for n in [360,364,381]:sys.path.insert(0,str(R/f'results/dev_aux/task{n}'))
import adapter as A,run as G,audit as V
s=(R/'results/dev_aux/task522/audit.py').read_text(encoding='utf-8');exec(compile(s[s.index('def tables('):s.index('nativegames=0')],'ACKonly','exec'));s=(R/'results/dev_aux/task600/audit.py').read_text(encoding='utf-8');counts=dict(games=0,actual_go=0,PV_moves=0,Python_actual_actions=0,random_draws=0,sorted_legal_arrays=0,price_ACK_entries=0);exec(compile(s[s.index('def game('):s.index('for task,opp in')],'independentphysicalgameonly','exec'));sources={};countertotals={};coverage={};profiles=json.loads((R/'results/dev_aux/task599/result.json').read_bytes())['profiles'];qual=json.loads((R/'results/dev_aux/task613/declaration.json').read_bytes())
for task in [613,614]:
 r=json.loads((R/f'results/dev_aux/task{task}/result.json').read_bytes());P=R/f'results/dev_aux/task{task}';raw=iter((P/'queries.jsonl').open(encoding='utf-8'));seen=set()
 for i,line in enumerate((P/'games.jsonl').open(encoding='utf-8'),1):
  g=json.loads(line);assert g['weights']==profiles[g['profile']]['weights'];f=g['root'];assert f==d['roots'][f['index']];game(g,'random',raw)
  if task==613:
   cell=(g['profile'],f['index'],g['color'],g['implementation']);mode=0 if g['implementation']=='prototype_mode0' else None
  else:cell=(g['profile'],f['index'],g['color'],g['mode']);mode=g['mode']
  assert cell not in seen;seen.add(cell)
  for q in g['queries']:
   if mode is None:assert 'capture_diag' not in q;continue
   z=q['capture_diag'];assert z['mode']==mode and all(isinstance(v,int) and v>=0 for v in z.values());e=z['eligible'];assert all(v<=e for k,v in z.items() if k!='mode');assert z['old_pruned']-z['new_pruned']==z['rescued_by_new']-z['newly_pruned_by_new'];assert z['new_gain_larger']+z['new_gain_smaller']<=e;ct=countertotals.setdefault(f'{task}:{mode}',{k:0 for k in z if k!='mode'})
   for k in ct:ct[k]+=z[k]
  if i%256==0:print('actualPython',task,i,round(time.perf_counter()-start,1),flush=True)
 assert next(raw,None) is None;expected=set(itertools.product(range(4),[f['index'] for f in (qual['roots'] if task==613 else d['roots'])],[0,1],['original','prototype_mode0'] if task==613 else [0,1]));assert seen==expected;coverage[task]=len(seen);counts['price_ACK_entries']+=tables(r['price_acks']);sources[task]={n:hashlib.sha256((P/n).read_bytes()).hexdigest() for n in ['games.jsonl','queries.jsonl','price_acks.json','result.json','declaration.json']}
out=dict(status='PASS_ALL_PHYSICAL_QUAL_AND_PANEL',counts=counts,counter_totals=countertotals,coverage=coverage,source_sha256=sources,new_go=0,seconds=time.perf_counter()-start,scope='ALLactualmode0original/prototypequalification176 andALL6141152 pairedpanel actualpaths FULLindependentPython/PV/metadata/material/history/terminal/RNG/ACK/rawquery/cell/reset audit. All7parsedstdout diagnostic counters rawJSON/identities checked; exactinternal context rows notlogged soaggregatesarevisited-tree counterfactualdecisions notmatchedpostdivergencenodes. Same1024request/stoppolicy notactualequalnodes. No pricelearning/humanfitting orold29duplicateclaim.');(O/'result.json').write_text(json.dumps(out,indent=2),encoding='utf-8');print(json.dumps({k:v for k,v in out.items() if k!='source_sha256'}))