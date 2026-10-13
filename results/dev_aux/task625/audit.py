import json,sys,time,math,random,hashlib,itertools
from pathlib import Path
from fractions import Fraction
R=Path.cwd();O=R/'results/dev_aux/task625';O.mkdir(exist_ok=True);D=R/'results/dev_aux/task624/declaration.json';d=json.loads(D.read_bytes());start=time.perf_counter()
for n in [360,364,381]:sys.path.insert(0,str(R/f'results/dev_aux/task{n}'))
import adapter as A,run as G,audit as V
s=(R/'results/dev_aux/task522/audit.py').read_text(encoding='utf-8');exec(compile(s[s.index('def tables('):s.index('nativegames=0')],'tableonly','exec'));s=(R/'results/dev_aux/task600/audit.py').read_text(encoding='utf-8');ss=s[s.index('def game('):s.index('for task,opp in')];ss=ss.replace("q['nodes_limit']==1024 and q['command']=='go nodes 1024'","q['nodes_limit']==g['budget'] and q['command']=='go nodes '+str(g['budget'])");counts=dict(games=0,actual_go=0,PV_moves=0,Python_actual_actions=0,random_draws=0,sorted_legal_arrays=0,price_ACK_entries=0);exec(compile(ss,'independentphysicalvariablebudget','exec'));P=R/'results/dev_aux/task624';r=json.loads((P/'result.json').read_bytes());assert r['status']=='COMPLETE_ALL_BUDGET_CELLS';raw=iter((P/'queries.jsonl').open(encoding='utf-8'));seen=set();diag={};gs=[]
for i,line in enumerate((P/'games.jsonl').open(encoding='utf-8'),1):
 g=json.loads(line);assert g['root']==d['roots'][g['root']['index']] and g['weights']==d['profiles'][g['profile']]['weights'] and g['budget'] in [1024,8192];game(g,'random',raw);key=(g['profile'],g['budget'],g['root']['index'],g['color']);assert key not in seen;seen.add(key);gs.append(dict(key=key,goal=g['goal'],termination=g['termination'],plies=len(g['actions']),go=len(g['queries'])))
 for q in g['queries']:
  z=q['capture_diag'];assert z['mode']==0 and z['old_pruned']-z['new_pruned']==z['rescued_by_new']-z['newly_pruned_by_new'];assert all(v>=0 and v<=z['eligible'] for k,v in z.items() if k!='mode');ct=diag.setdefault(str(g['budget']),{k:0 for k in z if k!='mode'})
  for k in ct:ct[k]+=z[k]
 if i%256==0:print('budgetPython',i,round(time.perf_counter()-start,1),flush=True)
assert next(raw,None) is None;expected={(p,n,f['index'],c) for p in range(6) for n in [1024,8192] for f in d['roots'] for c in [0,1] if n==8192 or p>=4};assert seen==expected and len(seen)==1152;counts['price_ACK_entries']=tables(r['price_acks']);old=R/'results/dev_aux/task614/games.jsonl';assert hashlib.sha256(old.read_bytes()).hexdigest()==d['cached_source_sha256']==json.loads((R/'results/dev_aux/task615/result.json').read_bytes())['source_sha256']['614']['games.jsonl'];cached={}
for i,line in enumerate(old.open(encoding='utf-8'),1):
 g=json.loads(line)
 if g['mode']==0:cached[i]=g
source_seen=set()
for row in r['rows']:
 source=(row['source']['file'],row['source']['line']);assert source not in source_seen;source_seen.add(source)
 if row['reused']:
  assert row['nodes']==1024 and row['source']['file']=='results/dev_aux/task614/games.jsonl';g=cached[row['source']['line']];assert g['profile']==row['profile'] and g['root']==d['roots'][row['root']] and g['color']==row['color'] and g['weights']==d['profiles'][row['profile']]['weights'];assert row['goal']==g['goal'] and row['termination']==g['termination'] and row['go']==len(g['queries']) and row['plies']==len(g['actions'])
 else:
  x=gs[row['source']['line']-1];assert tuple(x['key'])==(row['profile'],row['nodes'],row['root'],row['color']) and x['goal']==row['goal'] and x['termination']==row['termination'] and x['go']==row['go'] and x['plies']==row['plies']
assert len(source_seen)==1728
out=dict(status='PASS_ALL_NEW_BUDGET_PHYSICAL_AND_CACHE_SOURCES',counts=counts,logical_games=1728,reused_games=576,diagnostic=diag,source_sha256={n:hashlib.sha256((P/n).read_bytes()).hexdigest() for n in ['games.jsonl','queries.jsonl','price_acks.json','result.json','declaration.json']},new_go=0,seconds=time.perf_counter()-start,scope='ALL1152NEWphysicalpaths independentPython/PV/RNG/fullhistory/goal/material/terminal/reset/table/request8192or1024 andrawjournals;ALL576614cachedsources readback exact/prior615physicalaudithashunchanged. 1728uniquephysicalsource references no orphan queries; no strictnode/time fairness/newtraining/holdout claim.');(O/'result.json').write_text(json.dumps(out,indent=2),encoding='utf-8');print(json.dumps({k:v for k,v in out.items() if k!='source_sha256'}))