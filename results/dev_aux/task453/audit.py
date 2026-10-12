import json,sys,random,math,hashlib,time
from pathlib import Path
from fractions import Fraction
import cshogi as C
R=Path.cwd();sys.path.insert(0,str(R/'results/dev_aux/task381'));import audit as V
O=R/'results/dev_aux/task453';O.mkdir(exist_ok=True);d=json.loads((R/'results/dev_aux/task445/declaration.json').read_text(encoding='utf-8'));axes=d['axes'];t0=time.perf_counter()
# Derive independent native random-game checker from the already audited finite source.
text=(R/'results/dev_aux/task426/audit.py').read_text(encoding='utf-8');a=text.index('def random_audit(');b=text.index("folder=R/'results/dev_aux/task425'",a);exec(compile(text[a:b],'independent_native_random_game','exec'))
def tables(acks):
 count=0
 for ack in acks:
  w=ack['weights'];seen=[]
  for line in ack['prices']:
   if not line.startswith('info string auxprice '):continue
   pc,val,sgn,cap,prom=map(int,line.split()[3:]);pt=pc%16;base=pt-8 if pt in range(9,15) else pt
   assert val==w[pt] and sgn==(w[pt] if pc<16 else -w[pt]) and cap==(0 if pt in (0,8,15) else w[pt]+w[base]) and prom==(w[base+8]-w[base] if base in range(1,7) else 0);seen.append(pc);count+=1
  assert sorted(seen)==list(range(32))
 return count
nativegames=0;go=0;pv=0;draws=0;batch_checks=0;price_entries=0;fit_endpoints={}
for task,budget,label in [(449,1024,'terminal_only'),(450,1024,'fast_terminal')]:
 d['nodes']=budget;folder=R/f'results/dev_aux/task{task}';games=[json.loads(x) for x in (folder/'games.jsonl').open(encoding='utf-8')];raw=[json.loads(x) for x in (folder/'queries.jsonl').open(encoding='utf-8')];expected=[]
 for g in games:
  n,qs,nd=random_audit(g);pv+=n;draws+=nd;expected.extend(qs);assert g['training_objective']==label;expectedfitness=Fraction(0) if g['termination']['winner'] is None else ((1 if g['termination']['winner']==g['color'] else -1)*(32+Fraction(24-len(g['actions']),24))) if label=='fast_terminal' else Fraction(g['goal']);assert Fraction(g['training_goal'])==expectedfitness
 assert expected==raw;nativegames+=len(games);go+=len(raw)
 ep=json.loads((folder/'endpoints.json').read_text(encoding='utf-8'));fit_endpoints[label]=ep
 for initial in d['initial_profiles']:
  w=list(initial['weights']);base_mean=None;updates=[u for u in ep['updates'] if u['family']==initial['name']];assert len(updates)==24
  for i,u in enumerate(updates):
   assert u['iteration']==i and u['direction']==d['directions'][initial['name']][i] and u['start_weights']==w;plus=list(w);minus=list(w)
   for axis,sign in zip(axes,u['direction']):
    plus[axis]=max(32,min(4096,math.floor(w[axis]*math.exp(.25*sign)+.5)));minus[axis]=max(32,min(4096,math.floor(w[axis]*math.exp(-.25*sign)+.5)))
   cs=u['candidates'];assert [x['weights'] for x in cs]==[w,plus,minus]
   for row in cs:
    gs=[games[s['line']-1] for s in row['sources']];train=[f for f in d['roots'] if f['phase']=='train'];assert [(g['root'],g['color']) for g in gs]==[(f,c) for f in train for c in (0,1)];assert all(g['weights']==row['weights'] for g in gs);assert row['goals']==[g['training_goal'] for g in gs] and Fraction(row['mean_goal'])==sum(Fraction(g['training_goal']) for g in gs)/8;batch_checks+=1
   means=[Fraction(x['mean_goal']) for x in cs];best=max(range(3),key=lambda j:means[j]);assert best==u['selected_index'] and means[best]-means[0]==Fraction(u['accepted_strict_gain']);assert base_mean is None or means[0]==base_mean;new=cs[best]['weights'];assert u['after_weights']==new and u['changed_integer_axes']==sum(a!=b for a,b in zip(w,new));w=list(new);base_mean=means[best]
  assert next(e['endpoint'] for e in ep['endpoints'] if e['family']==initial['name'])==w
 price_entries+=tables(json.loads((folder/'price_acks.json').read_text(encoding='utf-8')))
folder=R/'results/dev_aux/task451';r=json.loads((folder/'result.json').read_text(encoding='utf-8'));games=[json.loads(x) for x in (folder/'games.jsonl').open(encoding='utf-8')];raw=[json.loads(x) for x in (folder/'queries.jsonl').open(encoding='utf-8')];expected=[];seen=set()
for g,row in zip(games,r['rows']):
 budget=g['nodes_limit'];d['nodes']=budget;assert budget in d['development_node_budgets'];assert g['root']['phase']=='development' and g['root'] in d['roots']
 if g['opponent_arm']=='unit':pv+=V.game(g);expected.extend(V.bare(q) for q in g['queries'])
 else:n,qs,nd=random_audit(g);pv+=n;draws+=nd;expected.extend(qs)
 assert row['goal']==g['goal'] and row['quantity']==g['raw_quantity'] and row['weights']==g['weights'] and row['nodes']==budget and row['opponent']==g['opponent_arm'];k=(budget,g['opponent_arm'],tuple(g['weights']),g['root']['index'],g['color']);assert k not in seen;seen.add(k)
assert len(games)==len(r['rows'])==len(r['profiles'])*4*2*2 and expected==raw;nativegames+=len(games);go+=len(raw);price_entries+=tables(r['price_acks'])
qresult=json.loads((R/'results/dev_aux/task452/result.json').read_text(encoding='utf-8'));assert qresult['status']=='PASS';price_entries+=tables(qresult['price_acks'])
freeze=json.loads((R/'results/dev_aux/task445/all_endpoints_frozen.json').read_text(encoding='utf-8'))
for task,label in [(449,'terminal_only'),(450,'fast_terminal')]:assert hashlib.sha256((R/f'results/dev_aux/task{task}/endpoints.json').read_bytes()).hexdigest()==freeze['both_endpoints'][label]
out=dict(status='PASS',games=nativegames,actual_game_go=go,PV_move_checks=pv,random_draws=draws,joint_batch_checks=batch_checks,fulltable_entries=price_entries,all_cross_cells=len(seen),seconds=time.perf_counter()-t0,scope='actual445..452 pure-vs-fast true-terminal objective; fullnative legal/history/rule/quantity/RNG/PV/journal/acceptedintegersteps andALLcrosscells. Originalphysicalgoal preserved; fitnessseparatelydecoded, no unexecutedpathclaim.');(O/'result.json').write_text(json.dumps(out,indent=2),encoding='utf-8');print(out)
