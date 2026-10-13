import json,hashlib,time,sys,os,math,cshogi as C
from pathlib import Path
from fractions import Fraction as F
R=Path.cwd();O=R/'results/dev_aux/task831';d=json.loads((O/'declaration.json').read_bytes());old=json.loads((R/'results/dev_aux/task596/declaration.json').read_bytes());d['opponents']={x['name']:x['weights'] for x in old['initial_profiles']};d['fixed_opponent']=old['initial_profiles'][0]['weights'];d['executable_sha256']=old['executable_sha256'];assert json.loads((R/'results/dev_aux/task820/result.json').read_bytes())['status']=='PASS_ALL_FROZEN_D_E_F_G_PRICES_CROSSED_BUDGETS';start=time.monotonic();deadline=start+120
for n in [360,364,381,509]:sys.path.insert(0,str(R/f'results/dev_aux/task{n}'))
import adapter as A,run as G,audit as V
from warm_adapter import ControlledEngine
sys.path.insert(0,str(R/'results/dev_aux/task583'));from controller_curriculum import native_game
A.EXE=R/'.local_agent/yaneura27/yaneura-material1-hand-see.exe';assert hashlib.sha256(A.EXE.read_bytes()).hexdigest()==d['executable_sha256'];save=lambda p,x:p.write_text(json.dumps(x,indent=2),encoding='utf-8')
def qty12(g):
 b=C.Board(g['root']['initial_sfen'])
 for u in g['root']['history']:m=b.move_from_usi(u);assert b.is_legal(m);b.push(m)
 for a in g['actions'][:12]:assert b.sfen()==a['before_sfen'];m=b.move_from_usi(a['move']);assert b.is_legal(m);b.push(m)
 n=[0,0]
 for pc in b.pieces:
  if pc and pc%16!=8:n[0 if pc<16 else 1]+=1
 for i,h in enumerate(b.pieces_in_hand):n[i]+=sum(h)
 assert sum(n)==38;return n[g['color']]-n[1-g['color']]

plan=json.loads((O/'plan.json').read_bytes());profiles=[dict(weights=plan['ablation'],names=['G-random2514-promotion_ablation'])]
pools=[dict(name='development',roots=[x for x in json.loads((R/'results/dev_aux/task784/roots_frozen.json').read_bytes())['roots'] if x['phase']=='development']),dict(name='independent_validation',roots=json.loads((R/'results/dev_aux/task808/roots_frozen.json').read_bytes())['roots'])]
assert [len(x['roots']) for x in pools]==[8,16] and all(x['phase']=='independent_validation' for x in pools[1]['roots'])
save(O/'execution_inputs.json',{**d,'profiles':profiles,'pools':pools,'before_any_opponent_probes':True});P=R/'results/dev_aux/task832';assert not(P/'games.jsonl').exists();rows=[];games=go=0;acks=[]
with (P/'queries.jsonl').open('w') as qj,(P/'games.jsonl').open('w') as gj:
 for opponent,oppweights in d['opponents'].items():
  d['fixed_opponent']=oppweights
  for profile in profiles:
   e=ControlledEngine(profile['weights'],qj,'warm_game');eu=ControlledEngine(oppweights,qj,'warm_game');acks.extend([dict(role='candidate',opponent=opponent,weights=e.w,prices=e.prices),dict(role='unit',opponent=opponent,weights=eu.w,prices=eu.prices)]);save(P/'price_acks.json',acks)
   try:
    for pool in pools:
     refs=[];goals=[];q12s=[];q24s=[];terms=[]
     for f in pool['roots']:
      for color in [0,1]:
       e.begin_game();eu.begin_game();g=native_game(e,eu,e.w,f,color,None,d,deadline);q12=qty12(g);q24=g['raw_quantity'];fit=F(q12+q24,38);g.update(pool=pool['name'],opponent=opponent,cap=24,quantity12=q12,quantity24=q24,fitness=str(fit));gj.write(json.dumps(g)+'\n');gj.flush();os.fsync(gj.fileno());games+=1;go+=len(g['queries']);refs.append(dict(file=P.relative_to(R).as_posix()+'/games.jsonl',line=games));goals.append(str(fit));q12s.append(q12);q24s.append(q24);terms.append(g['termination'])
     rows.append(dict(names=profile['names'],pool=pool['name'],opponent=opponent,batch=dict(weights=e.w,sources=refs,goals=goals,quantity12=q12s,quantity24=q24s,terminations=terms,mean_goal=str(sum(map(F,goals))/len(goals)))));print('NEW_VALIDATE',opponent,profile['names'],games,go,round(time.monotonic()-start,1),flush=True)
   finally:e.close();eu.close()
save(P/'result.json',dict(status='COMPLETE_ALL_FIXED_OPPONENT_PROBES',actual_games=games,actual_go=go,rows=rows,profiles=profiles,seconds=time.monotonic()-start,scope=d['scope']));assert games==96
