import json,time,sys
from pathlib import Path
from fractions import Fraction
import chess,numpy as np
R=Path.cwd();O=R/'results/dev_aux/task248';O.mkdir(exist_ok=True);D=json.loads((R/'results/dev_aux/task247/declaration.json').read_bytes());X=json.loads((R/'results/dev_aux/task247/result.json').read_bytes());S=json.loads((R/'results/dev_aux/task241/result.json').read_bytes());assert X['complete'];start=time.monotonic();names=list(D['profiles']);W=np.array([[D['profiles'][p][k] for k in 'PNBRQ'] for p in names],dtype=np.int64);checks=[];leaves=nodes=0
for root in D['roots']:
 b=chess.Board(root['fen']);actor=b.turn;rows=[]
 def solve(depth,ply):
  global leaves,nodes
  nodes+=1;out=b.outcome(claim_draw=False)
  if out:leaves+=1;v=0 if out.winner is None else (100000000-ply if out.winner==actor else -100000000+ply);return np.full(len(W),v,dtype=np.int64)
  if depth==0:leaves+=1;f=np.array([len(b.pieces(t,actor))-len(b.pieces(t,not actor)) for t in range(1,6)]);return W@f
  mx=b.turn==actor;vv=[]
  for m in sorted(b.legal_moves,key=lambda z:z.uci()):b.push(m);vv.append(solve(depth-1,ply+1));b.pop()
  return (np.max if mx else np.min)(vv,axis=0)
 for m in sorted(b.legal_moves,key=lambda z:z.uci()):b.push(m);rows.append((m.uci(),solve(2,1)));b.pop()
 reference=next(r for r in S['results'] if r['name']==root['name'])
 for j,p in enumerate(names):
  raw=next(r for r in X['rows'] if r['root']==root['name'] and r['profile']==p);best=max(v[j] for m,v in rows);argmax=[m for m,v in rows if v[j]==best];assert raw['decision']['score']==int(best) and raw['action'] in argmax and raw['decision']['completed_depth']==3
  pvboard=chess.Board(root['fen'])
  for a in raw['decision']['principal_variation']:
   text=''.join(chr(97+a[k]['file'])+str(a[k]['rank']+1) for k in ('from_square','to_square'))+(a['promotion_target_id'].lower() if a['promotion_target_id'] else '');assert chess.Move.from_uci(text) in pvboard.legal_moves;pvboard.push_uci(text)
  outcome=pvboard.outcome(claim_draw=False);ply=len(raw['decision']['principal_variation']);leaf=0 if outcome and outcome.winner is None else (100000000-ply if outcome.winner==actor else -100000000+ply) if outcome else sum(D['profiles'][p][k]*(len(pvboard.pieces(t,actor))-len(pvboard.pieces(t,not actor))) for t,k in enumerate('PNBRQ',1));assert leaf==int(best)
  source=next(z for z in reference['rows'] if z['move']==raw['action']);goal=Fraction(sum(r['success_within3'] for r in source['replies']),len(source['replies'])) if source['replies'] else Fraction(int(source['goal_success_probability']));old=next(z for z in reference['profiles'] if z['profile']==('unit' if p=='unit' else p));oldrow=next(z for z in reference['rows'] if z['move']==old['chosen']);oldgoal=Fraction(sum(r['success_within3'] for r in oldrow['replies']),len(oldrow['replies'])) if oldrow['replies'] else Fraction(int(oldrow['goal_success_probability']));bestgoal=max(Fraction(sum(r['success_within3'] for r in z['replies']),len(z['replies'])) if z['replies'] else Fraction(int(z['goal_success_probability'])) for z in reference['rows']);checks.append(dict(root=root['name'],phase=root['phase'],profile=p,score=int(best),action=raw['action'],argmax=argmax,goal=str(goal),D2_goal=str(oldgoal),oracle_goal=str(bestgoal),pv_leaf_value_equal=True))
summary=[]
for phase in ('train','heldout'):
 for p in names:
  rr=[r for r in checks if r['phase']==phase and r['profile']==p];d3=sum(Fraction(r['goal']) for r in rr)/len(rr);d2=sum(Fraction(r['D2_goal']) for r in rr)/len(rr);summary.append(dict(phase=phase,profile=p,D2_goal=float(d2),D3_goal=float(d3),depth_gain=float(d3-d2),scope='Samegoal/evaluation/minbackprop/geometry, changedonlyfinite2->3ply; notcross-budgetlearningcomparison.'))
out=dict(complete=True,actualNativechecks=len(checks),nodes=nodes,leaves=leaves,seconds=time.monotonic()-start,native_batch_seconds=X['seconds'],summary=summary,checks=checks,scope=D['scope']);(O/'audit.json').write_text(json.dumps(out,indent=2),encoding='utf-8');print(json.dumps({k:out[k] for k in ('complete','actualNativechecks','nodes','leaves','seconds','native_batch_seconds','summary')},indent=2))
