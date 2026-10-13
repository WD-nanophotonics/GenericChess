import sys,json,time,math,random,hashlib,os
from pathlib import Path
from fractions import Fraction
R=Path.cwd();O=R/'results/dev_aux/task568';D=R/'results/dev_aux/task564/declaration.json';d=json.loads(D.read_bytes());start=time.perf_counter()
for n in [360,364,381]:sys.path.insert(0,str(R/f'results/dev_aux/task{n}'))
import adapter as A,run as G,audit as V
s=(R/'results/dev_aux/task522/audit.py').read_text();s=s[s.index('def tables('):s.index('nativegames=0')];exec(compile(s,'independentACKonly','exec'))
counts=dict(games=0,actual_go=0,PV_moves=0,Python_actual_actions=0,random_draws=0,sorted_legal_arrays=0,price_ACK_entries=0,joint_batches=0,proposal_rounds=0);sources={};summaries={}
def game(g,opp,raw):
 b,keys,checks,movers=G.full_root(g['root']);assert b.sfen()==g['root']['expected_sfen'];h=list(g['root']['history']);qi=0;ri=0;rolecounts={}
 for ply,a in enumerate(g['actions']):
  assert G.terminal(b,keys,checks,movers) is None;actor=b.turn;assert a['actor']==actor and a['before_sfen']==b.sfen();m=A.shogi.Move.from_usi(a['move']);assert m in b.legal_moves
  if actor==g['color'] or opp=='unit':
   q=g['queries'][qi];qi+=1;assert V.bare(q)==json.loads(next(raw));counts['actual_go']+=1;assert q['initial_sfen']==g['root']['initial_sfen'] and q['history']==h and q['ply']==ply and q['bestmove']==a['move'] and q['nodes_limit']==1024 and q['command']=='go nodes 1024';role='candidate' if actor==g['color'] else 'unit';assert q['player']==role and q['weights']==(g['weights'] if role=='candidate' else d['fixed_opponent']);parts=q['state'].split(' ',7);cached,full,stm=map(int,parts[3:6]);material=A.material(b,q['weights']);assert cached==full==material and stm==(material if actor==0 else -material);counts['PV_moves']+=V.query(q);assert q['reset_policy']=='warm_game' and q['cold_isready']==[] and q['game_start_ready'][-1]=='readyok' and q['query_index_in_game']==rolecounts.get(role,0);rolecounts[role]=rolecounts.get(role,0)+1
  else:
   legal=sorted(m.usi() for m in b.legal_moves);seed=(d['seed_base']+2*g['root']['index']+g['color']+(100 if g['root']['phase']=='development' else 0))*100+ri;ix=random.Random(seed).randrange(len(legal));assert a['random_draw']==dict(legal=legal,index=ix,seed=seed,opponent_turn=ri) and a['move']==legal[ix];ri+=1;counts['random_draws']+=1;counts['sorted_legal_arrays']+=1
  cap=b.piece_at(m.to_square);p=b.piece_at(m.from_square) if m.from_square is not None else None;assert a['captured']==(str(cap) if cap else None) and a['moving']==(str(p) if p else None) and a['promotion']==bool(m.promotion) and a['drop']==m.drop_piece_type;movers.append(actor);b.push(m);h.append(a['move']);keys.append(G.key(b));checks.append(b.is_check());assert a['after_sfen']==b.sfen();counts['Python_actual_actions']+=1
 assert qi==len(g['queries']);t=G.terminal(b,keys,checks,movers);cap=12 if g['root']['phase']=='train' else 24;assert len(g['actions'])==cap or t is not None;assert g['termination']==(t or dict(kind='cap12' if cap==12 else 'cap24',winner=None));qty=G.quantity(b,g['color']);assert qty==g['raw_quantity'];goal=Fraction(qty,19) if t is None else Fraction(0) if t['winner'] is None else Fraction(32 if t['winner']==g['color'] else -32);assert str(goal)==g['goal'] and g['final_sfen']==b.sfen();counts['games']+=1
 return {k:g[k] for k in ['weights','root','color','termination','raw_quantity','goal']}
for task,opp in [(565,'unit'),(566,'random'),(567,'both')]:
 F=R/f'results/dev_aux/task{task}';gs=[];raw=iter((F/'queries.jsonl').open())
 with (F/'games.jsonl').open() as gj:
  for i,line in enumerate(gj,1):
   g=json.loads(line);actualopp=opp if opp!='both' else ('unit' if any(q['player']=='unit' for q in g['queries']) else 'random');gs.append(game(g,actualopp,raw))
   if i%512==0:print('Pythonrules',task,i,round(time.perf_counter()-start,1),flush=True)
 assert next(raw,None) is None;summaries[task]=gs;counts['price_ACK_entries']+=tables(json.loads((F/'price_acks.json').read_bytes()));sources[task]={name:hashlib.sha256((F/name).read_bytes()).hexdigest() for name in ['games.jsonl','queries.jsonl','price_acks.json']}
 if task==567:break
 ep=json.loads((F/'endpoints.json').read_bytes());assert ep['declaration_sha256']==hashlib.sha256(D.read_bytes()).hexdigest();train=[f for f in d['roots'] if f['phase']=='train']
 for initial in d['initial_profiles']:
  w=list(initial['weights']);base=None;us=[u for u in ep['updates'] if u['family']==initial['name']];assert len(us)==24
  for i,u in enumerate(us):
   assert u['iteration']==i and u['direction']==d['directions'][initial['name']][i] and u['start_weights']==w;plus=list(w);minus=list(w)
   for axis,sign in zip(d['axes'],u['direction']):plus[axis]=max(32,min(4096,math.floor(w[axis]*math.exp(.25*sign)+.5)));minus[axis]=max(32,min(4096,math.floor(w[axis]*math.exp(-.25*sign)+.5)))
   cs=u['candidates'];assert [x['weights'] for x in cs]==[w,plus,minus]
   for row in cs:
    rg=[gs[s['line']-1] for s in row['sources']];assert [(g['root'],g['color']) for g in rg]==[(f,c) for f in train for c in (0,1)];assert all(g['weights']==row['weights'] for g in rg);fitness=[g['goal'] for g in rg];assert row['objective']=='mixed_cap12' and row['goals']==fitness and row['physical_goals']==[g['goal'] for g in rg] and Fraction(row['mean_goal'])==sum(map(Fraction,fitness))/len(rg);counts['joint_batches']+=1
   means=[Fraction(x['mean_goal']) for x in cs];best=max(range(3),key=lambda j:means[j]);assert best==u['selected_index'] and means[best]-means[0]==Fraction(u['accepted_strict_gain']);assert base is None or means[0]==base;w=list(cs[best]['weights']);base=means[best];assert u['after_weights']==w;counts['proposal_rounds']+=1
  assert next(e['endpoint'] for e in ep['endpoints'] if e['family']==initial['name'])==w
freeze=json.loads((R/'results/dev_aux/task564/all_endpoints_frozen.json').read_bytes());assert freeze['before_any_development'] and freeze['endpoint_sha256']=={opp:hashlib.sha256((R/f'results/dev_aux/task{task}/endpoints.json').read_bytes()).hexdigest() for opp,task in [('unit',565),('random',566)]};out=dict(status='PASS',counts=counts,source_sha256=sources,seconds=time.perf_counter()-start,new_go=0,scope='IndependentPythonrules allactualtrajectories/material/metadata/fullhistory/terminal/RNG+nativePV readback; exactjointproposals/goals/table/reset/rawjournal andALLendpointfreeze. Finite standardShogi cap12mixed train/cap24physicaldev1024caller, no genericdomain/humanrecovery proof. QA cost separatefromphysicallearning wall.')
(O/'result.json').write_text(json.dumps(out,indent=2),encoding='utf-8');print(json.dumps(out))
