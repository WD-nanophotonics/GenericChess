import json,sys,time,math,random,hashlib,itertools
from pathlib import Path
from fractions import Fraction
R=Path.cwd();O=R/'results/dev_aux/task648';O.mkdir(exist_ok=True);D=R/'results/dev_aux/task645/declaration.json';d=json.loads(D.read_bytes());start=time.perf_counter()
for n in [360,364,381]:sys.path.insert(0,str(R/f'results/dev_aux/task{n}'))
import adapter as A,run as G,audit as V
s=(R/'results/dev_aux/task522/audit.py').read_text(encoding='utf-8');exec(compile(s[s.index('def tables('):s.index('nativegames=0')],'tableonly','exec'));s=(R/'results/dev_aux/task600/audit.py').read_text(encoding='utf-8');counts=dict(games=0,actual_go=0,PV_moves=0,Python_actual_actions=0,random_draws=0,sorted_legal_arrays=0,price_ACK_entries=0,proposal_rounds=0,batches=0);exec(compile(s[s.index('def game('):s.index('for task,opp in')],'independentPythonphysicalonly','exec'));sources={};summ={}
def fast(g):return Fraction(g['raw_quantity'],19)
for task in [646,647]:
 P=R/f'results/dev_aux/task{task}';raw=iter((P/'queries.jsonl').open(encoding='utf-8'));gs=[]
 for i,line in enumerate((P/'games.jsonl').open(encoding='utf-8'),1):
  g=json.loads(line);assert g['root']==d['roots'][g['root']['index']];z=game(g,'random',raw);z['plies']=len(g['actions']);gs.append(z)
  if i%512==0:print('fastPython',task,i,round(time.perf_counter()-start,1),flush=True)
 assert next(raw,None) is None;counts['price_ACK_entries']+=tables(json.loads((P/'price_acks.json').read_bytes()));sources[task]={n:hashlib.sha256((P/n).read_bytes()).hexdigest() for n in ['games.jsonl','queries.jsonl','price_acks.json','result.json']};summ[task]=gs;(O/f'physical_stage_{task}.json').write_text(json.dumps(dict(stage=task,physicalpaths_passed=True,cumulative_counts=dict(counts),source_sha256=sources[task]),indent=2),encoding='utf-8')
 if task==647:break
 ep=json.loads((P/'endpoints.json').read_bytes());assert ep['declaration_sha256']==hashlib.sha256(D.read_bytes()).hexdigest();train=[f for f in d['roots'] if f['phase']=='train']
 for initial in d['initial_profiles']:
  w=list(initial['weights']);base=None;updates=[u for u in ep['updates'] if u['start']==initial['name']];assert len(updates)==12
  for i,u in enumerate(updates):
   assert u['iteration']==i and u['direction']==d['directions'][initial['name']][i] and u['start_weights']==w;plus=list(w);minus=list(w)
   for axis,sign in zip(d['axes'],u['direction']):plus[axis]=max(32,min(4096,math.floor(w[axis]*math.exp(.25*sign)+.5)));minus[axis]=max(32,min(4096,math.floor(w[axis]*math.exp(-.25*sign)+.5)))
   cs=u['candidates'];assert [c['weights'] for c in cs]==[w,plus,minus]
   for c in cs:
    rg=[gs[s['line']-1] for s in c['sources']];assert [(g['root'],g['color']) for g in rg]==[(f,color) for f in train for color in [0,1]];assert all(g['weights']==c['weights'] for g in rg);fitness=[str(fast(g)) for g in rg];assert c['objective']=='actual_quantity_only12' and c['goals']==fitness and c['physical_mixed_goals']==[g['goal'] for g in rg] and c['actual_plies']==[g['plies'] for g in rg] and c['terminations']==[g['termination'] for g in rg] and Fraction(c['mean_goal'])==sum(map(Fraction,fitness))/104;counts['batches']+=1
   mu=[Fraction(c['mean_goal']) for c in cs];best=max(range(3),key=lambda j:mu[j]);assert best==u['selected_index'] and mu[best]-mu[0]==Fraction(u['accepted_gain']);assert base is None or mu[0]==base;w=list(cs[best]['weights']);base=mu[best];assert u['after_weights']==w;counts['proposal_rounds']+=1
  assert next(e['endpoint'] for e in ep['endpoints'] if e['start']==initial['name'])==w
freeze=json.loads((R/'results/dev_aux/task645/all_endpoints_frozen.json').read_bytes());assert freeze['before_any_new_development'] and freeze['endpoint_sha256']==hashlib.sha256((R/'results/dev_aux/task646/endpoints.json').read_bytes()).hexdigest();r=json.loads((R/'results/dev_aux/task647/result.json').read_bytes());seen=set();dev=[f for f in d['roots'] if f['phase']=='development']
for row in r['rows']:
 rg=[summ[647][s['line']-1] for s in row['batch']['sources']];assert [(g['root'],g['color']) for g in rg]==[(f,c) for f in dev for c in [0,1]];assert row['batch']['goals']==[str(fast(g)) for g in rg] and row['batch']['physical_mixed_goals']==[g['goal'] for g in rg];assert all(g['weights']==row['batch']['weights'] for g in rg)
out=dict(status='PASS_ALL_FAST_LEARNING_AND_NEWDEV',counts=counts,source_sha256=sources,new_go=0,seconds=time.perf_counter()-start,scope='ALL619/620physical actualpaths independentPython/PV/fullhistory/material/terminal/RNG/table/reset/rawjournal andALL24jointproposalrounds/72logicalcandidatebatches; rawmixedscore separatelyfromactualshortestmatefitness, ALL2endpoints beforeNEWdev. Existing599initialdevreuse tocheckseparately beforegainanalysis; exposedpriorroots notindependentnewholdout. No source/human fitness oruniversalvalueproof.');(O/'result.json').write_text(json.dumps(out,indent=2),encoding='utf-8');print(json.dumps({k:v for k,v in out.items() if k!='source_sha256'}))