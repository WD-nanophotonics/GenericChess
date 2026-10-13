import json,sys,time,random,hashlib,copy
from pathlib import Path
from fractions import Fraction
R=Path.cwd();O=R/'results/dev_aux/task843';O.mkdir(exist_ok=False);start=time.perf_counter();d=json.loads((R/'results/dev_aux/task840/plan.json').read_bytes());profiles=json.loads((R/'results/dev_aux/task596/declaration.json').read_bytes())['initial_profiles'];opps={p['name']:p['weights'] for p in profiles};roots=json.loads((R/'results/dev_aux/task841/roots_frozen.json').read_bytes())['roots']
for n in [360,364,381]:sys.path.insert(0,str(R/f'results/dev_aux/task{n}'))
import adapter as A,run as G,audit as V
s=(R/'results/dev_aux/task522/audit.py').read_text(encoding='utf-8-sig');exec(compile(s[s.index('def tables('):s.index('nativegames=0')],'ACKaudit','exec'));s=(R/'results/dev_aux/task600/audit.py').read_text(encoding='utf-8-sig');s=s[s.index('def game('):s.index('for task,opp in')].replace('cap=12;','cap=g["cap"];').replace("dict(kind='cap12' if cap==12 else 'cap24',winner=None)","dict(kind='cap'+str(cap),winner=None)").replace("q['nodes_limit']==1024","q['nodes_limit']==d['nodes']").replace("q['command']=='go nodes 1024'","q['command']=='go nodes '+str(d['nodes'])");counts=dict(games=0,actual_go=0,PV_moves=0,Python_actual_actions=0,random_draws=0,sorted_legal_arrays=0,price_ACK_entries=0);exec(compile(s,'physicalaudit','exec'));cache={};orig=G.full_root

def clone(f):
 k=json.dumps(f,sort_keys=True)
 if k not in cache:cache[k]=orig(f)
 b,keys,checks,movers=cache[k];return copy.deepcopy(b),list(keys),list(checks),list(movers)
G.full_root=clone
P=R/'results/dev_aux/task842';raw=iter((P/'queries.jsonl').open(encoding='utf-8'));observed=[]
for line in (P/'games.jsonl').open(encoding='utf-8'):
 g=json.loads(line);assert g['root'] in roots and g['root']['phase']=='train';d['fixed_opponent']=opps[g['opponent']];game(g,'unit',raw);observed.append((g['initial_profile'],g['opponent'],g['root']['seed'],g['color']))
assert next(raw,None) is None;expected=[(p['name'],o['name'],r['seed'],c) for p in profiles for o in profiles for r in roots if r['phase']=='train' for c in [0,1]];assert observed==expected;counts['price_ACK_entries']=tables(json.loads((P/'price_acks.json').read_bytes()));out=dict(status='PASS_ALL128_MC_TRAIN_ACTUAL',counts=counts,seconds=time.perf_counter()-start,source_sha256={n:hashlib.sha256((P/n).read_bytes()).hexdigest() for n in ['queries.jsonl','games.jsonl','price_acks.json']},new_go=0,scope='Allphysical128trajectories/Pythonrules/fullhistory/repetition/terminal/quantity/material/PV/priceACK/rawqueries/exactroot-opponent-color inventory. Coldrootclone skipsnosemanticchecks.');(O/'result.json').write_text(json.dumps(out,indent=2),encoding='utf-8');print(out)
