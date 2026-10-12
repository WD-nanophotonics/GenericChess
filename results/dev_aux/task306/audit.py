import json,time,importlib.util
from pathlib import Path
import chess
R=Path.cwd();O=R/'results/dev_aux/task306';O.mkdir(exist_ok=False);D=json.loads((R/'results/dev_aux/task295/declaration.json').read_bytes());TAG='$dev_aux_constant_telemetry_v1'
def hook(d):
 if set(d)=={TAG}:z=d[TAG];return [z['value']]*z['count']
 return d
X=json.loads((R/'results/dev_aux/task295/result.json').read_bytes(),object_hook=hook);assert X['complete'];sp=importlib.util.spec_from_file_location('p',R/'results/dev_aux/task166/run.py');P=importlib.util.module_from_spec(sp);sp.loader.exec_module(P);P.stop();start=time.monotonic();visits=0;rows=[]
for z in X['rows']:
 f=D['roots'][z['root']];b=chess.Board(f['initial_fen'])
 for t in f['history']:b.push_uci(t)
 actor=b.turn;w=z['weights']
 def ab(depth,ply,lo,hi):
  global visits
  visits+=1
  if visits%1024==0:P.A.guard(start+180,P.stop)
  oo=b.outcome(claim_draw=False) if b.is_checkmate() or b.is_stalemate() or b.is_fivefold_repetition() else None
  if oo is not None:return 0 if oo.winner is None else 100000000-ply if oo.winner==actor else -100000000+ply
  if not depth:return sum(w[k]*(len(b.pieces(i+1,actor))-len(b.pieces(i+1,not actor))) for i,k in enumerate('PNBRQ'))
  maximize=b.turn==actor;best=-10**9 if maximize else 10**9
  for m in sorted(b.legal_moves,key=lambda m:(not b.is_capture(m),m.uci())):
   b.push(m);vv=ab(depth-1,ply+1,lo,hi);b.pop()
   if maximize:best=max(best,vv);lo=max(lo,best)
   else:best=min(best,vv);hi=min(hi,best)
   if lo>=hi:break
  return best
 scores={}
 for m in sorted(b.legal_moves,key=lambda m:m.uci()):b.push(m);scores[m.uci()]=ab(3,1,-10**9,10**9);b.pop()
 best=max(scores.values());raw=z['result'];assert raw['score']==best and scores[z['action']]==best and raw['completed_depth']==4 and not raw['used_fallback']
 pv=[]
 for a in raw['principal_variation']:
  fr=a['from_square'];to=a['to_square'];t=chess.square_name(chess.square(fr['file'],fr['rank']))+chess.square_name(chess.square(to['file'],to['rank']))+(a.get('promotion_target_id') or '').lower();m=chess.Move.from_uci(t);assert m in b.legal_moves;b.push(m);pv.append(t)
 oo=b.outcome(claim_draw=False) if b.is_checkmate() or b.is_stalemate() or b.is_fivefold_repetition() else None;literal=(0 if oo.winner is None else 100000000-len(pv) if oo.winner==actor else -100000000+len(pv)) if oo is not None else sum(w[k]*(len(b.pieces(i+1,actor))-len(b.pieces(i+1,not actor))) for i,k in enumerate('PNBRQ'));assert literal==raw['score'] and (len(pv)==4 or oo is not None);rows.append(dict(root=z['root'],profile=z['profile'],score=best,argmax=[m for m,v in scores.items() if v==best],action=z['action'],PV_leaf=literal));print(z['root'],z['profile'],best,visits,round(time.monotonic()-start,3),flush=True)
out=dict(complete=True,independent_complete_D4_queries=8,oracle_visits=visits,checks=rows,seconds=time.monotonic()-start,scope='EightactualD4rootqueries295 independentnoTT/python-chess fullhistory/argmax/literalPV; failed2943s gamepilot remainsincomplete, norescue orbroadergameclaim.')
(O/'audit.json').write_text(json.dumps(out,indent=2),encoding='utf-8');print('COMPLETE',out['seconds'])