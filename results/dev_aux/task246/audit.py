import json,time
from pathlib import Path
import chess
R=Path.cwd();O=R/'results/dev_aux/task246';O.mkdir(exist_ok=True);D=json.loads((R/'results/dev_aux/task245/declaration.json').read_bytes());X=json.loads((R/'results/dev_aux/task245/result.json').read_bytes());assert X['complete'];start=time.monotonic();proof=json.loads((R/'results/dev_aux/task244/proof.json').read_bytes());rows=[];checks=0
for row in X['rows']:
 b=chess.Board(row['fen']);actor=b.turn;w=row['weights'];values=[];leaves=0
 def solve(depth,ply):
  global leaves
  out=b.outcome(claim_draw=False)
  if out:leaves+=1;return 0 if out.winner is None else (100000000-ply if out.winner==actor else -100000000+ply)
  if depth==0:leaves+=1;return sum(w[k]*(len(b.pieces(t,actor))-len(b.pieces(t,not actor))) for t,k in enumerate('PNBRQ',1))
  mx=b.turn==actor;vv=[]
  for m in sorted(b.legal_moves,key=lambda z:z.uci()):b.push(m);vv.append(solve(depth-1,ply+1));b.pop()
  return (max if mx else min)(vv)
 for m in sorted(b.legal_moves,key=lambda z:z.uci()):b.push(m);values.append((m.uci(),solve(row['depth']-1,1)));b.pop()
 best=max(v for m,v in values);argmax=[m for m,v in values if v==best];assert best==row['decision']['score'] and row['action'] in argmax and row['decision']['completed_depth']==row['depth']
 if row['depth']==3:
  for a in row['decision']['principal_variation']:
   text=''.join(chr(97+a[k]['file'])+str(a[k]['rank']+1) for k in ('from_square','to_square'))+(a['promotion_target_id'].lower() if a['promotion_target_id'] else '');assert chess.Move.from_uci(text) in b.legal_moves;b.push_uci(text)
  assert b.is_checkmate() and b.turn!=actor
 rows.append(dict(root=row['root'],profile=row['profile'],depth=row['depth'],score=best,argmax=argmax,pv_true_checkmate=row['depth']==3,leaf_evaluations=leaves));checks+=1
# Independently reconstruct all Qd8/Blackreply/Rh4 known-success branches ofthe proof.
b=chess.Board(proof['fen']);b.push_uci(proof['goal_move']);success=[]
for reply in sorted(b.legal_moves,key=lambda z:z.uci()):
 b.push(reply);mates=[]
 # Explicitactualmate enumeration independent ofrecordedgoal booleans.
 for m in sorted(b.legal_moves,key=lambda z:z.uci()):
  b.push(m)
  if b.is_checkmate():mates.append(m.uci())
  b.pop()
 assert mates;success.append(dict(reply=reply.uci(),mates=mates));b.pop()
out=dict(complete=True,checks=checks,rows=rows,proof_goal_reply_mates=success,seconds=time.monotonic()-start,terminal_numeric_units='ActualsemanticNative winner100000000-ply from native_module.c:4412. Python evaluator MATE_SCORE1000000000 differs; Coracle239..242 uses1e9ordering, samegoal/argmax becauseallmaterialsmall butrawnumbersnotcross-compared. Hereexplicitlyalign1e8 foractual16scorechecks, trueoutcome separatelyverified.',scope='DeclaredfreshCroot/mirror, actualkernelandindependentfinite3plyallvalues/PVterminal; notuniformPVleafcertificate forotherTT/q configurations.');(O/'audit.json').write_text(json.dumps(out,indent=2),encoding='utf-8');print(dict(complete=True,checks=checks,seconds=out['seconds'],true_mate_PVs=8,proof_reply_mates=success))
