import json,time,importlib.util
from pathlib import Path
import chess
R=Path.cwd();O=R/'results/dev_aux/task240';D=json.loads((O/'declaration.json').read_bytes());assert not (O/'result.json').exists();MATE=1000000000;profiles=list(D['profiles']);weights=[D['profiles'][p] for p in profiles];start=time.monotonic();rootresults=[];nodes=matechecks=unknown=0
s=importlib.util.spec_from_file_location('p',R/'results/dev_aux/task166/run.py');P=importlib.util.module_from_spec(s);s.loader.exec_module(P)
for f in D['roots']:
 b=chess.Board(f['fen']);actor=b.turn;rows=[]
 def value(ply):
  out=b.outcome(claim_draw=False)
  if out:return [0 if out.winner is None else (MATE-ply if out.winner==actor else -MATE+ply)]*len(profiles)
  phi=[len(b.pieces(t,actor))-len(b.pieces(t,not actor)) for t in range(1,6)];return [sum(w[k]*x for k,x in zip('PNBRQ',phi)) for w in weights]
 for move in sorted(b.legal_moves,key=lambda m:m.uci()):
  P.A.guard(start+90,P.stop);b.push(move);terminal=b.outcome(claim_draw=False);pairs=[]
  if terminal:vals=value(1);success=int(terminal.winner==actor);categories=dict(terminal=1,unknown=0)
  else:
   for reply in sorted(b.legal_moves,key=lambda m:m.uci()):
    b.push(reply);nodes+=1;v=value(2);term=b.outcome(claim_draw=False);canmate=bool(term and term.winner==actor)
    if term is None:
     for third in sorted(b.legal_moves,key=lambda m:m.uci()):
      b.push(third);matechecks+=1;out=b.outcome(claim_draw=False)
      if out and out.winner==actor:canmate=True
      elif out is None:unknown+=1
      b.pop()
    pairs.append(dict(reply=reply.uci(),leaf_values=v,success_within3=int(canmate),terminal_after2=term is not None));b.pop()
   vals=[min(z['leaf_values'][j] for z in pairs) for j in range(len(profiles))];success=sum(z['success_within3'] for z in pairs)/len(pairs);categories=dict(terminal=sum(z['terminal_after2'] for z in pairs),unknown=sum(not z['terminal_after2'] for z in pairs))
  b.pop();rows.append(dict(move=move.uci(),minimax2_values=vals,goal_success_probability=success,replies=pairs,categories=categories))
 goalmax=max(z['goal_success_probability'] for z in rows);pr=[]
 for j,profile in enumerate(profiles):
  best=max(z['minimax2_values'][j] for z in rows);argmax=[z for z in rows if z['minimax2_values'][j]==best];selected=argmax[0];pr.append(dict(profile=profile,best=best,argmax=[z['move'] for z in argmax],chosen=selected['move'],success=selected['goal_success_probability'],regret=goalmax-selected['goal_success_probability']))
 rootresults.append(dict(name=f['name'],fen=f['fen'],optimal_goal_probability=goalmax,profiles=pr,all_price_policies_equal=len({z['chosen'] for z in pr})==1,rows=rows))
out=dict(complete=True,roots=len(rootresults),reply_nodes=nodes,third_ply_terminal_checks=matechecks,unknown_nonterminal_third_visits=unknown,seconds=time.monotonic()-start,all_policies_equal=all(z['all_price_policies_equal'] for z in rootresults),results=rootresults,scope=D['scope']);(O/'result.json').write_text(json.dumps(out,indent=2),encoding='utf-8');print(json.dumps(dict(complete=True,seconds=out['seconds'],all_policies_equal=out['all_policies_equal'],reply_nodes=nodes,matechecks=matechecks,mean_goal_regret={p:sum(next(z['regret'] for z in f['profiles'] if z['profile']==p) for f in rootresults)/len(rootresults) for p in profiles}),indent=2))
