import json,sys,time,math,random,hashlib,itertools
from pathlib import Path
from fractions import Fraction
R=Path.cwd();O=R/'results/dev_aux/task630';O.mkdir(exist_ok=True);d=json.loads((R/'results/dev_aux/task627/declaration.json').read_bytes());freeze=json.loads((R/'results/dev_aux/task627/roots_frozen.json').read_bytes());start=time.perf_counter()
for n in [360,364,381]:sys.path.insert(0,str(R/f'results/dev_aux/task{n}'))
import adapter as A,run as G,audit as V
s=(R/'results/dev_aux/task522/audit.py').read_text(encoding='utf-8');exec(compile(s[s.index('def tables('):s.index('nativegames=0')],'tablesonly','exec'));s=(R/'results/dev_aux/task600/audit.py').read_text(encoding='utf-8');s=s[s.index('def game('):s.index('for task,opp in')].replace('cap=12;','cap=g["cap"];').replace("dict(kind='cap12' if cap==12 else 'cap24',winner=None)","dict(kind='cap'+str(cap),winner=None)");counts=dict(games=0,actual_go=0,PV_moves=0,Python_actual_actions=0,random_draws=0,sorted_legal_arrays=0,price_ACK_entries=0);exec(compile(s,'independentactualsetupandprobe','exec'));sources={};setups=[];coverage={}
for task,stage in [(628,'setup'),(629,'probe')]:
 P=R/f'results/dev_aux/task{task}';r=json.loads((P/'result.json').read_bytes());raw=iter((P/'queries.jsonl').open(encoding='utf-8'));seen=set();d['seed_base']=d['setup_seed_base'] if task==628 else d['probe_seed_base']
 for i,line in enumerate((P/'games.jsonl').open(encoding='utf-8'),1):
  g=json.loads(line);f=g['root'];assert g['stage']==stage and g['cap']==(48 if task==628 else 12)
  if task==628:assert g['weights']==d['generator_profiles'][g['generator']]['weights'] and f['seed']==d['independent_seeds'][f['index']] and not f['history'];cell=(g['generator'],f['index'],g['color']);setups.append(g)
  else:assert g['weights']==d['probe_profiles'][g['profile']]['weights'] and f==freeze['roots'][f['index']];cell=(g['profile'],f['index'],g['color'])
  assert cell not in seen;seen.add(cell);game(g,'random',raw)
  if i%256==0:print('balancedPython',task,i,round(time.perf_counter()-start,1),flush=True)
 assert next(raw,None) is None;expected=set(itertools.product(range(2),range(8),[0,1])) if task==628 else set(itertools.product(range(6),range(len(freeze['roots'])),[0,1]));assert seen==expected;coverage[task]=len(seen);counts['price_ACK_entries']+=tables(r['price_acks']);sources[task]={n:hashlib.sha256((P/n).read_bytes()).hexdigest() for n in ['games.jsonl','queries.jsonl','price_acks.json','result.json']}
expected=[];missing=[]
for line,g in enumerate(setups,1):
 f=g['root'];seed=f['seed'];c=g['color'];pi=g['generator']
 if g['termination']['kind']!='checkmate':missing.append(dict(generator=pi,family=seed,color=c,reason='no_mate_within48',termination=g['termination']));continue
 for offset in d['offsets']:
  n=len(g['actions'])-offset
  if n<0:missing.append(dict(generator=pi,family=seed,color=c,offset=offset,reason='mate_before_offset'));continue
  h=[a['move'] for a in g['actions'][:n]];sf=g['actions'][n-1]['after_sfen'] if n else f['initial_sfen'];root=dict(index=len(expected),seed=seed,phase='independent_balanced_probe',initial_sfen=f['initial_sfen'],history=h,expected_sfen=sf,source_family=seed,generator=pi,setup_color=c,offset=offset,setup_source=dict(file='results/dev_aux/task628/games.jsonl',line=line));b,k,ch,mo=G.full_root(root);assert G.terminal(b,k,ch,mo) is None;expected.append(root)
assert expected==freeze['roots'] and missing==freeze['unavailable'];assert freeze['before_any_probe'];out=dict(status='PASS_ALL_NEW_BALANCED_SETUP_PROBES',counts=counts,coverage=coverage,eligible_roots=len(expected),eligible_families=len({f['seed'] for f in expected}),nomate_setup_count=len(missing),source_sha256=sources,new_go=0,seconds=time.perf_counter()-start,scope='ALL32newsetup andALL629priceprobe physicalpaths independentPython/PV/material/fullhistory/terminal/RNG/table/rawjournal/reset andALLeligibility/unavailability reconstructed. Rootbias conditionalmate remains, bothgeneratorpolicies/setupcolors/offsets grouped by8originalseedfamilies; seveneligiblefamilies not56independentroots. No sourceprices/selector/resampling/pricelearning/generalhumanrecovery proof.');(O/'result.json').write_text(json.dumps(out,indent=2),encoding='utf-8');print(json.dumps({k:v for k,v in out.items() if k!='source_sha256'}))