"""Replay legal random choices, complete UCI histories/PVs, true finite terminal fitness."""
import json,time,random,math,collections
from pathlib import Path
from fractions import Fraction as F
import chess
R=Path.cwd();O=R/'results/dev_aux/task321';O.mkdir(exist_ok=False);D=json.loads((R/'results/dev_aux/task320/declaration.json').read_bytes());X=json.loads((R/'results/dev_aux/task320/result.json').read_bytes());assert X['complete'];start=time.monotonic();queries=0;groups=[]
for z in X['calls']:
 f=D['roots'][z['root']];b=chess.Board(f['initial_fen'])
 for u in f['history']:b.push_uci(u)
 rng=random.Random(z['seed']);ss={r['ply']:r['record'] for r in z['search_records']};rs={r['ply']:r for r in z['random_choices']}
 for ply,u in enumerate(z['actions']):
  assert not b.is_game_over(claim_draw=False);m=chess.Move.from_uci(u);assert m in b.legal_moves
  if b.turn==z['color']:
   meta=ss[ply];assert meta['full_history']==[m.uci() for m in b.move_stack] and meta['root_fen']==f['initial_fen'];lines=[l.split() for l in meta['uci_info'] if ' pv ' in l];assert lines;pv=lines[-1][lines[-1].index('pv')+1:];assert pv[0]==u;c=b.copy(stack=True)
   for t in pv:assert chess.Move.from_uci(t) in c.legal_moves;c.push_uci(t)
   assert meta['reported_nodes']>=1024;queries+=1
  else:
   legal=sorted(b.legal_moves,key=lambda m:m.uci());ix=rng.randrange(len(legal));assert rs[ply]==dict(ply=ply,index=ix,legal_count=len(legal),move=legal[ix].uci()) and legal[ix]==m
  b.push(m)
 assert b.fen()==z['final_fen'];oo=b.outcome(claim_draw=False);kind='UNKNOWN_CUTOFF' if oo is None else oo.termination.name;assert kind==z['termination'];sign=0 if oo is None or oo.winner is None else 1 if oo.winner==z['color'] else -1;fitness=F(49-len(z['actions']),48) if kind=='CHECKMATE' and sign==1 else F(-1) if kind=='CHECKMATE' and sign==-1 else F(0);assert str(fitness)==z['fitness'];assert z['table_ack']['prices']=={str(i+1):[z['weights'][k]]*2 for i,k in enumerate('PNBRQ')}
 for p in z['leaf_probes']:assert abs(p['measured_white_pawns']-z['weights'][p['type']]/208)<.011
for name in D['profiles']:
 zz=[z for z in X['calls'] if z['name']==name];groups.append(dict(profile=name,games=len(zz),wins=sum(z['finite_mate_sign']==1 for z in zz),losses=sum(z['finite_mate_sign']==-1 for z in zz),unknown=sum(z['termination']=='UNKNOWN_CUTOFF' for z in zz),mean_fitness=str(sum(F(z['fitness']) for z in zz)/len(zz)),mean_completed_mate_plies=sum(len(z['actions']) for z in zz if z['termination']=='CHECKMATE')/sum(z['termination']=='CHECKMATE' for z in zz)))
contr=[]
for name in ('semantic','s703-base'):
 dif=[]
 for ri in range(2):
  for color in D['colors']:
   for seed in D['random_seeds']:
    pair=[next(z for z in X['calls'] if (z['name'],z['root'],z['color'],z['seed'])==(n,ri,color,seed)) for n in ('unit',name)];dif.append(dict(root=ri,color=color,seed=seed,delta=str(F(pair[1]['fitness'])-F(pair[0]['fitness']))))
 contr.append(dict(profile=name,paired_differences=dif,positive=sum(F(z['delta'])>0 for z in dif),negative=sum(F(z['delta'])<0 for z in dif)))
out=dict(complete=True,games=24,actual_queries=queries,all_full_history_legal_random_and_PV_checks=True,groups=groups,contrasts=contr,pilot_wall=X['seconds'],audit_seconds=time.monotonic()-start,decision='Denseactualterminalsignal23/24mate. Fitnessrankingunit>semantic>s703, unlike oldsearchopponentbaseline. Proceed oneboundedpredeclaredcoordinatelearning withroot/color/seed diagnostics; nohumanadoption.',scope='Randomopponentgoal local: highwinratealone notpricelearning; mate-speed differenttarget, uniformlegalreply bias observed300 remains. 8correlatedcells eachprofile; notconfidencebounds/generalstrength.')
(O/'audit.json').write_text(json.dumps(out,indent=2),encoding='utf-8');print(json.dumps({k:v for k,v in out.items() if k!='contrasts'},indent=2))