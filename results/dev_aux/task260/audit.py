import json,time,hashlib,importlib.util,sys
from pathlib import Path
from fractions import Fraction
import chess
R=Path.cwd();O=R/'results/dev_aux/task260';assert not (O/'audit.json').exists();D=json.loads((R/'results/dev_aux/task258/declaration.json').read_bytes());X=json.loads((R/'results/dev_aux/task258/result.json').read_bytes());T=json.loads((R/'results/dev_aux/task258/tree.json').read_bytes());start=time.monotonic();checks=0;actual_terminal_rows=[]
s=importlib.util.spec_from_file_location('p',R/'results/dev_aux/task166/run.py');P=importlib.util.module_from_spec(s);s.loader.exec_module(P)
# Independently reconstruct every treeboard and terminal/count/goal field.
for f,tree in zip(D['roots'],T['roots']):
 b=chess.Board(f['initial_fen'])
 for t in f['history']:assert chess.Move.from_uci(t) in b.legal_moves;b.push_uci(t)
 assert b.fen()==f['fen'] and b.is_valid();actor=b.turn
 assert [a['move'] for a in tree['actions']]==sorted(m.uci() for m in b.legal_moves)
 def verify(ld,ply):
  global checks
  checks+=1
  if checks%4096==0:P.A.guard(start+300,P.stop)
  assert ld['fen']==b.fen();out=b.outcome(claim_draw=False)
  if out:
   sign=0 if out.winner is None else 1 if out.winner==actor else -1
   assert ld==dict(terminal=sign*(100000000-ply),goal=sign*100,fen=b.fen());actual_terminal_rows.append(dict(root=f['id'],history=[m.uci() for m in b.move_stack],termination=out.termination.name,winner=out.winner))
  else:
   vv=[len(b.pieces(t,actor))-len(b.pieces(t,not actor)) for t in range(1,6)];assert ld==dict(vector=vv,goal=sum(vv),fen=b.fen())
 for a in tree['actions']:
  b.push_uci(a['move'])
  if b.is_game_over(claim_draw=False):assert len(a['branches'])==1;verify(a['branches'][0]['terminal'],1)
  else:
   assert [z['reply'] for z in a['branches']]==sorted(m.uci() for m in b.legal_moves)
   for z in a['branches']:
    b.push_uci(z['reply']);verify(z['leaf2'],2)
    if b.is_game_over(claim_draw=False):assert len(z['children'])==1;verify(z['children'][0]['leaf'],2)
    else:
     assert [c['move'] for c in z['children']]==sorted(m.uci() for m in b.legal_moves)
     for c in z['children']:b.push_uci(c['move']);verify(c['leaf'],3);b.pop()
    b.pop()
  b.pop()
 print('BOARD',f['id'],checks,round(time.monotonic()-start,3),flush=True)
# PurePython/Fraction evaluator, noNumPy; sameleaf goals andfullyindependentreduce.
cache={};policychecks=0
for tree in T['roots']:
 for pi,w in enumerate(X['profiles']):
  if pi%32==0:P.A.guard(start+300,P.stop)
  def value(ld):
   if 'terminal' in ld:return ld['terminal']
   key=(tuple(ld['vector']),pi)
   if key not in cache:cache[key]=sum(w[k]*n for k,n in zip('PNBRQ',key[0]))
   return cache[key]
  for depth in (2,3):
   actions=[]
   for a in tree['actions']:
    branchvals=[];goals=[]
    for br in a['branches']:
     if 'terminal' in br:ld=br['terminal'];vv=value(ld);goal=ld['goal']
     elif depth==2:ld=br['leaf2'];vv=value(ld);goal=ld['goal']
     else:
      cand=[(value(z['leaf']),z['leaf']['goal']) for z in br['children']];best=max(v for v,g in cand);vv,goal=next((v,g) for v,g in cand if v==best)
     branchvals.append(vv);goals.append(goal)
    actions.append(dict(move=a['move'],min=min(branchvals),uniform_mean=Fraction(sum(branchvals),len(branchvals)),uniform_quantity=str(Fraction(sum(goals),len(goals))),worst_quantity=min(goals)))
   for op in ('min','uniform_mean'):
    best=max(a[op] for a in actions);ties=[a['move'] for a in actions if a[op]==best];win=next(a for a in actions if a[op]==best);actual=next(z for z in X['rows'] if z['root']==tree['root'] and z['depth']==depth and z['operator']==op)['policies'][pi]
    assert actual['move']==win['move'] and actual['argmax']==ties and actual['uniform_quantity']==win['uniform_quantity'] and actual['worst_quantity']==win['worst_quantity'];assert Fraction(actual['value'])==best;policychecks+=1
 print('PRICE',tree['root'],policychecks,round(time.monotonic()-start,3),flush=True)
out=dict(complete=True,board_leaf_checks=checks,all625_policy_score_goal_argmax_checks=policychecks,terminal_rows=actual_terminal_rows,seconds=time.monotonic()-start,source_hashes={str(p.relative_to(R)):hashlib.sha256(p.read_bytes()).hexdigest() for p in (R/'results/dev_aux/task258/declaration.json',R/'results/dev_aux/task258/tree.json',R/'results/dev_aux/task258/result.json')},scope='Everyboard/history/leaf checkedindependently; every625x4x2x2policy reducedwithscalar exactFraction, noengine/PV assumptions. Syntheticgoal quantitynotfullWDL.')
(O/'audit.json').write_text(json.dumps(out,indent=2),encoding='utf-8');print(json.dumps(out,indent=2))
