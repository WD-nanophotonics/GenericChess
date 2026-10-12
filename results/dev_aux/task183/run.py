"""Finite complete/partial depth3 dual-objective trees on all frozen actual divergences."""
import json,time,hashlib,importlib.util
from pathlib import Path
import chess
R=Path.cwd();O=R/'results/dev_aux/task183';D=json.loads((O/'declaration.json').read_bytes())
sp=importlib.util.spec_from_file_location('P183',R/'results/dev_aux/task166/run.py');P=importlib.util.module_from_spec(sp);sp.loader.exec_module(P)
class NodeCap(Exception):pass
def target(b,color):
 q=sum(len(b.pieces(t,color))-len(b.pieces(t,not color)) for t in range(1,6));out=b.outcome(claim_draw=False)
 w=q if out is None else (0 if out.winner is None else (1000000 if out.winner==color else -1000000))
 return q,w
def execute():
 if (O/'result.json').exists():raise FileExistsError('frozen')
 started=time.monotonic();deadline=started+D['deadline_seconds'];P.stop();results=[];totalnodes=0
 for case in D['cases']:
  if time.monotonic()>=deadline:break
  P.stop();b=chess.Board(case['initial_fen'])
  for m in case['history']:b.push_uci(m)
  assert b.fen()==case['expected_fen'] and b.turn==case['color'];nodes=0;leaves=0;rows=[];rootfen=b.fen();stack=[m.uci() for m in b.move_stack];timer=time.monotonic();complete=True;error=None
  def visit(depth):
   nonlocal nodes,leaves
   nodes+=1
   if nodes>D['per_case_node_cap']:raise NodeCap('fixed nodecap')
   if nodes%1024==0:
    P.stop()
    if time.monotonic()>=deadline:raise TimeoutError('fixed overallfuse')
   if depth==0 or b.is_game_over(claim_draw=False):leaves+=1;return target(b,case['color'])
   maximize=b.turn==case['color'];values=[]
   for move in sorted(b.legal_moves,key=lambda m:m.uci()):
    b.push(move)
    try:values.append(visit(depth-1))
    finally:b.pop()
   choose=max if maximize else min
   return tuple(choose(v[i] for v in values) for i in (0,1))
  try:
   for move in sorted(b.legal_moves,key=lambda m:m.uci()):
    P.stop();b.push(move)
    try:value=visit(D['depth']-1)
    finally:b.pop()
    rows.append(dict(move=move.uci(),quantity=value[0],terminal_priority=value[1]))
  except (NodeCap,TimeoutError) as ex:complete=False;error=str(ex)
  assert b.fen()==rootfen and [m.uci() for m in b.move_stack]==stack
  by={r['move']:r for r in rows};opt={key:[r['move'] for r in rows if r[key]==max(t[key] for t in rows)] for key in ('quantity','terminal_priority')} if complete else None
  pair=[by.get(case[k]) for k in ('initial_move','final_move')];ranking=None
  if all(x is not None for x in pair):ranking={key:pair[1][key]-pair[0][key] for key in ('quantity','terminal_priority')}
  results.append(dict(case=case,complete=complete,error=error,nodes=nodes,leaves=leaves,completed_root_actions=len(rows),all_root_actions=b.legal_moves.count(),rows=rows,optimal_sets=opt,goal_optimal_sets_intersect=bool(set(opt['quantity'])&set(opt['terminal_priority'])) if complete else None,actual_action_values=pair,final_minus_initial_finite_value=ranking,wall_seconds=time.monotonic()-timer))
  totalnodes+=nodes
  (O/'progress.json').write_text(json.dumps(dict(cases=len(results),nodes=totalnodes,seconds=time.monotonic()-started)),encoding='utf-8')
  if error=='fixed overallfuse':break
 out=dict(complete=len(results)==len(D['cases']),all_cases_complete_trees=all(r['complete'] for r in results),cases=len(results),identical_pairs=len(D['identical_pairs']),nodes=totalnodes,full_trees=sum(r['complete'] for r in results),partial_trees=sum(not r['complete'] for r in results),goal_set_disjoint_full_trees=sum(r['complete'] and not r['goal_optimal_sets_intersect'] for r in results),opposite_quantity_vs_priority_rankings=sum(r['final_minus_initial_finite_value'] is not None and r['final_minus_initial_finite_value']['quantity']*r['final_minus_initial_finite_value']['terminal_priority']<0 for r in results),results=results,wall_seconds=time.monotonic()-started,declaration_sha256=hashlib.sha256((O/'declaration.json').read_bytes()).hexdigest(),scope='Posthoc actualstate3ply attribution, not16plywholepolicy/WDL certificate; partialroot membershipunknown andfailedcapsnever extended. No newenginegames orworkers.')
 (O/'result.json').write_text(json.dumps(out,indent=2),encoding='utf-8');print(json.dumps({k:v for k,v in out.items() if k!='results'},indent=2))
if __name__=='__main__':execute()
