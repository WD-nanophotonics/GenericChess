"""Finite fullwidth2ply material control; no matureengine or search heuristics."""
import json,time,random,hashlib,importlib.util
from pathlib import Path
import chess
R=Path.cwd();O=R/'results/dev_aux/task197'
s=importlib.util.spec_from_file_location('P197',R/'results/dev_aux/task166/run.py');P=importlib.util.module_from_spec(s);s.loader.exec_module(P);G=P.G

def value(b,color,w):
 out=b.outcome(claim_draw=False)
 if out:return 0 if out.winner is None else (1000000 if out.winner==color else -1000000)
 return sum(w[k]*(len(b.pieces(i+1,color))-len(b.pieces(i+1,not color))) for i,k in enumerate('PNBRQ'))
def search(b,w,deadline):
 started=time.monotonic();color=b.turn;root=b.fen();history=[m.uci() for m in b.move_stack];rows=[];nodes=0
 for move in sorted(b.legal_moves,key=lambda x:x.uci()):
  P.A.guard(deadline,P.stop);b.push(move)
  if b.is_game_over(claim_draw=False):values=[value(b,color,w)];nodes+=1
  else:
   values=[]
   for reply in sorted(b.legal_moves,key=lambda x:x.uci()):
    b.push(reply);values.append(value(b,color,w));nodes+=1;b.pop()
  b.pop();rows.append(dict(move=move.uci(),worst=min(values),reply_count=len(values)))
 assert b.fen()==root and [m.uci() for m in b.move_stack]==history;best=max(r['worst'] for r in rows);chosen=next(r['move'] for r in rows if r['worst']==best)
 return chess.Move.from_uci(chosen),dict(backend='EXACT_ORTHODOX_MATERIAL_2PLY',root_fen=root,full_history=history,rows=rows,leaf_nodes=nodes,value=best,seconds=time.monotonic()-started)
def execute():
 D=json.loads((O/'declaration.json').read_bytes());assert json.loads((R/'results/dev_aux/task193/games.json').read_bytes())['complete'];assert not (O/'games.json').exists();started=time.monotonic();deadline=started+D['deadline_seconds'];calls=[];P.stop()
 for name,w in D['profiles'].items():
  for oi,fixture in enumerate(D['roots']):
   for color in (True,False):
    b=P.board(fixture);rng=random.Random(D['random_seeds'][oi]);moves=[];records=[]
    for ply in range(16):
     P.A.guard(deadline,P.stop)
     if b.is_game_over(claim_draw=False):break
     if b.turn==color:m,r=search(b,w,deadline);records.append(r)
     else:m=rng.choice(sorted(b.legal_moves,key=lambda x:x.uci()))
     b.push(m);moves.append(m.uci())
    score=G.score(b,color,len(moves),16);r=dict(root_fen=fixture['initial_fen'],opening_history=fixture['history'],opening_fen=fixture['expected_fen'],agent_color=color,actions=moves,search_records=records,opponent_records=[],final_fen=b.fen(),score=score,reward=score['reward']);calls.append(dict(name=f'{name}-random-o{oi}-c{int(color)}',profile=name,opponent='random',opening_index=oi,random_seed=D['random_seeds'][oi],weights=w,result=r))
 out=dict(complete=True,calls=calls,wall_seconds=time.monotonic()-started,declaration_sha256=hashlib.sha256((O/'declaration.json').read_bytes()).hexdigest());P.A.atomic_json(O/'games.json',out);print(json.dumps(dict(complete=True,games=len(calls),seconds=out['wall_seconds'],leaf_nodes=sum(r['leaf_nodes'] for c in calls for r in c['result']['search_records']))))
if __name__=='__main__':execute()
