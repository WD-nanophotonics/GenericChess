"""Actual mature root query versus complete legal final-quantity target tree."""
import json,time,hashlib,importlib.util
from pathlib import Path
import chess
R=Path.cwd();O=R/'results/dev_aux/task180';D=json.loads((O/'declaration.json').read_bytes())
s=importlib.util.spec_from_file_location('P180',R/'results/dev_aux/task166/run.py');P=importlib.util.module_from_spec(s);s.loader.exec_module(P);M=P.M;A=P.A
def quantity(b,color):return sum(len(b.pieces(t,color))-len(b.pieces(t,not color)) for t in range(1,6))
def oracle(b,color):
 rows=[];nodes=0
 for move in sorted(b.legal_moves,key=lambda x:x.uci()):
  b.push(move)
  if b.is_game_over(claim_draw=False):values=[quantity(b,color)];nodes+=1
  else:
   values=[]
   for reply in sorted(b.legal_moves,key=lambda x:x.uci()):
    b.push(reply);values.append(quantity(b,color));nodes+=1;b.pop()
  rows.append(dict(move=move.uci(),worst=min(values),reply_count=len(values),terminal_after_first=b.is_game_over(claim_draw=False),quantity_after_first=quantity(b,color)));b.pop()
 best=max(r['worst'] for r in rows);return dict(value=best,best_moves=[r['move'] for r in rows if r['worst']==best],rows=rows,leaf_nodes=nodes)
def execute():
 if (O/'result.json').exists():raise FileExistsError('frozen')
 assert json.loads((R/'results/dev_aux/task179/games.json').read_bytes())['complete']
 started=time.monotonic();deadline=started+D['deadline_seconds'];P.stop();binary=R/'.local_agent/alignment-order/fairy-order-toggle.exe';assert hashlib.sha256(binary.read_bytes()).hexdigest()==D['binary_sha256']
 outrows=[]
 for profile,w in D['profiles'].items():
  e=M.start(binary,3,deadline,P.stop)
  try:
   for root in D['roots']:
    b=chess.Board(root['fen']);assert b.turn==root['agent_color'];q=oracle(b.copy(stack=True),root['agent_color']);probes,ack=M.configure(e,w,O/'variant.ini',deadline,P.stop);move,meta=M.M.search(e,b.copy(stack=True),deadline,P.stop);b.push(move)
    outcome=b.outcome(claim_draw=False);sc=P.G.score(b,root['agent_color'],1,16);outrows.append(dict(profile=profile,weights=w,root=root,oracle=q,selected=move.uci(),metadata=meta,probes=probes,table_ack=ack,selected_in_quantity_optimal_set=move.uci() in q['best_moves'],selected_actual_mate=b.is_checkmate() and outcome.winner==root['agent_color'],selected_count_difference=quantity(b,root['agent_color']),selected_true_score=sc,selected_quantity_reward=quantity(b,root['agent_color'])/15,final_fen=b.fen()))
  finally:e.close()
 out=dict(complete=True,rows=outrows,searches=len(outrows),mature_mate_outside_quantity_argmax=sum(r['selected_actual_mate'] and not r['selected_in_quantity_optimal_set'] for r in outrows),wall_seconds=time.monotonic()-started,binary_sha256=D['binary_sha256'],scope='Onelegalfinitegoal mismatch, colorsmirrored/3fixedprofiles; notgeneral enginebug, policygainorwholelearning failure attribution. Complete2plyobjective differsfrommature selective search tree.')
 A.atomic_json(O/'result.json',out);print(json.dumps({k:v for k,v in out.items() if k!='rows'}))
if __name__=='__main__':execute()
