from pathlib import Path
import json,time,sys,os
import cshogi as C
R=Path.cwd();O=R/'results/dev_aux/task934';O.mkdir(exist_ok=False);sys.path.insert(0,str(R/'results/dev_aux/task381'));import audit as V
cases=[json.loads(l) for l in (R/'results/dev_aux/task932/cases.jsonl').open() if json.loads(l)['status']=='PROVED_FORCE_WIN_WITHIN6'];rows=[];start=time.monotonic()
for row in cases:
 root=row['root'];attacker=row['attacker'];b=C.Board(root['initial_sfen']);states=[' '.join(b.sfen().split()[:3])];movers=[];checks=[];nodes=0;deadline=time.monotonic()+10
 def proof(depth):
  global nodes
  nodes+=1;assert time.monotonic()<deadline and nodes<=500000
  term=V.terminal(b,states,movers,checks)
  if term:return dict(sfen=b.sfen(),terminal=term) if term['winner']==attacker else None
  if depth==0:return None
  actor=b.turn;children=[];sf=b.sfen()
  for m in sorted(list(b.legal_moves),key=C.move_to_usi):
   u=C.move_to_usi(m);movers.append(actor);b.push(m);checks.append(bool(b.is_check()));states.append(' '.join(b.sfen().split()[:3]))
   try:child=proof(depth-1)
   finally:states.pop();checks.pop();b.pop();movers.pop()
   if actor==attacker:
    if child:return dict(sfen=sf,actor=actor,children=[dict(move=u,proof=child)])
   else:
    if child is None:return None
    children.append(dict(move=u,proof=child))
  return dict(sfen=sf,actor=actor,children=children) if actor!=attacker else None
 tree=proof(6);assert tree is not None and b.sfen()==root['initial_sfen'];r=dict(root=root,attacker=attacker,horizon=6,nodes=nodes,proof=tree);rows.append(r);print('PROOF',root['seed'],nodes)
(O/'certificates.json').write_text(json.dumps(dict(status='THREE_STOCK_SAFE_FINITE_FORCE_CERTIFICATES',cases=rows,seconds=time.monotonic()-start,new_go=0),indent=2))
