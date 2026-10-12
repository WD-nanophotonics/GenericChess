import json,time,sys,importlib.util
from pathlib import Path
import chess
R=Path.cwd();O=R/'results/dev_aux/task239';D=json.loads((O/'declaration.json').read_bytes());assert not (O/'result.json').exists();profiles=list(D['profiles']);weights=[D['profiles'][k] for k in profiles];MATE=1000000000;start=time.monotonic();nodes=leaves=terminals=0;results=[]
s=importlib.util.spec_from_file_location('p',R/'results/dev_aux/task166/run.py');P=importlib.util.module_from_spec(s);s.loader.exec_module(P)
for fixture in D['roots']:
 b=chess.Board(fixture['fen']);actor=b.turn;root=b.fen();frontiers=[]
 def solve(depth,ply):
  global nodes,leaves,terminals
  nodes+=1
  if nodes%1024==0:P.A.guard(start+D['deadline_seconds'],P.stop)
  out=b.outcome(claim_draw=False)
  if out:
   leaves+=1;terminals+=1;v=0 if out.winner is None else (MATE-ply if out.winner==actor else -MATE+ply);return [v]*len(weights)
  if depth==0:
   leaves+=1;f=[len(b.pieces(t,actor))-len(b.pieces(t,not actor)) for t in range(1,6)];return [sum(w[k]*x for k,x in zip('PNBRQ',f)) for w in weights]
  maximizing=b.turn==actor;vv=[]
  for m in sorted(b.legal_moves,key=lambda z:z.uci()):b.push(m);vv.append(solve(depth-1,ply+1));b.pop()
  return [(max if maximizing else min)(z[j] for z in vv) for j in range(len(weights))]
 for m in sorted(b.legal_moves,key=lambda z:z.uci()):b.push(m);vv=solve(2,1);b.pop();frontiers.append(dict(move=m.uci(),values=vv))
 rows=[]
 for i,profile in enumerate(profiles):
  best=max(z['values'][i] for z in frontiers);argmax=[z['move'] for z in frontiers if z['values'][i]==best];rows.append(dict(profile=profile,best=best,argmax=argmax,known_forced_mate_within3=best>MATE-10))
 assert b.fen()==root;results.append(dict(name=fixture['name'],fen=root,all10_argmax_equal=all(z['argmax']==rows[0]['argmax'] for z in rows),rows=rows,all_root_values=frontiers))
out=dict(complete=True,roots=len(results),excluded=D['excluded'],nodes=nodes,leaves=leaves,terminal_leaf_visits=terminals,seconds=time.monotonic()-start,results=results,all_family_price_invariant=all(r['all10_argmax_equal'] for r in results),scope=D['scope']);(O/'result.json').write_text(json.dumps(out,indent=2),encoding='utf-8');print(json.dumps(dict(complete=True,roots=len(results),nodes=nodes,leaves=leaves,seconds=out['seconds'],all_price_invariant=out['all_family_price_invariant'],families=[dict(name=r['name'],mate=r['rows'][0]['known_forced_mate_within3'],argmax=r['rows'][0]['argmax']) for r in results]),indent=2))
