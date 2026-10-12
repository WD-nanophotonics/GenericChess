import json,time,hashlib,sys,importlib.util
from pathlib import Path
import chess
R=Path.cwd();sys.path.insert(0,str(R));O=R/'results/dev_aux/task231';O.mkdir(exist_ok=True);D=json.loads((R/'results/dev_aux/task228/declaration.json').read_bytes());X=json.loads((R/'results/dev_aux/task228/result.json').read_bytes());decl=dict(task_id='231',question='Doall12completedD3Nativefullroot scores realize independentlyenumeratedpurematerialminimax?',roots=D['roots'],profiles=D['profiles'],depth=3,cost='3fullorthodox3plytrees, simultaneous4pricevalues, estimate6s/60sguard, no engine rerun or training.',scope='3exposedWesternhistoryroots only; projectterminalusescheckmate/stalemate anddeclaredhistory rules, omittedautomaticinsufficient/75draw countrecorded. Independentnodework notsamebudgetmatureenginecontrol; noallgamerules orPVgeneralclaim.');(O/'declaration.json').write_text(json.dumps(decl,indent=2),encoding='utf-8')
from generic_chess.ai.evaluation.config import MATE_SCORE
s=importlib.util.spec_from_file_location('p',R/'results/dev_aux/task166/run.py');P=importlib.util.module_from_spec(s);s.loader.exec_module(P);start=time.monotonic();profiles=list(D['profiles']);weights=[D['profiles'][p] for p in profiles];counts=dict(visited=0,leaves=0,otherdraw=0);results=[]
for oi,f in enumerate(D['roots']):
 b=P.board(f);actor=b.turn
 def solve(depth,ply):
  counts['visited']+=1
  if counts['visited']%1024==0:P.A.guard(start+60,P.stop)
  if b.is_checkmate():counts['leaves']+=1;v=MATE_SCORE-ply if b.turn!=actor else -MATE_SCORE+ply;return [v]*len(weights)
  if b.is_stalemate():counts['leaves']+=1;return [0]*len(weights)
  if depth==0:
   counts['leaves']+=1;counts['otherdraw']+=b.outcome(claim_draw=False) is not None;features=[len(b.pieces(t,actor))-len(b.pieces(t,not actor)) for t in range(1,6)];return [sum(w[k]*x for k,x in zip('PNBRQ',features)) for w in weights]
  choices=[];maximize=b.turn==actor
  for move in sorted(b.legal_moves,key=lambda z:z.uci()):b.push(move);choices.append(solve(depth-1,ply+1));b.pop()
  return [(max if maximize else min)(c[j] for c in choices) for j in range(len(weights))]
 roots=[]
 for move in sorted(b.legal_moves,key=lambda z:z.uci()):b.push(move);roots.append(dict(move=move.uci(),values=solve(2,1)));b.pop()
 for j,profile in enumerate(profiles):
  score=max(z['values'][j] for z in roots);argmax=[z['move'] for z in roots if z['values'][j]==score];r=next(z for z in X['rows'] if z['root']==oi and z['profile']==profile and z['requested_depth']==3);assert r['decision']['score']==score and r['action_uci'] in argmax;results.append(dict(root=oi,profile=profile,score=score,argmax=argmax,actual=r['action_uci'],all_root_values=[dict(move=z['move'],value=z['values'][j]) for z in roots]))
out=dict(complete=True,checks=len(results),counts=counts,seconds=time.monotonic()-start,results=results,scope=decl['scope']);(O/'audit.json').write_text(json.dumps(out,indent=2),encoding='utf-8');print({k:out[k] for k in ('complete','checks','counts','seconds')})
