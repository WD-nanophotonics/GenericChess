from pathlib import Path
import json,chess,random,collections,ast
from fractions import Fraction as F
R=Path.cwd();O=R/'results/dev_aux/task1279';O.mkdir(exist_ok=False);script=(R/'results/dev_aux/task1130/run.py').read_text(encoding='utf-8-sig');module=ast.parse(script);keep=[n for n in module.body if isinstance(n,ast.FunctionDef) and n.name in ['inside','legal5','fen5','term5']];exec(compile(ast.Module(body=keep,type_ignores=[]),'minihelper','exec'))
def reachable(d,s,t):
 p,c=d[s];x,y=s%8,s//8;u,v=t%8,t//8;dx,dy=u-x,v-y
 if p==6:return max(abs(dx),abs(dy))==1
 if p==2:return sorted([abs(dx),abs(dy)])==[1,2]
 assert p==4
 if dx and dy or not(dx or dy):return False
 sx=(dx>0)-(dx<0);sy=(dy>0)-(dy<0);x+=sx;y+=sy
 while (x,y)!=(u,v):
  if x+8*y in d:return False
  x+=sx;y+=sy
 return True
def attacked(d,s,side):return any(c==side and reachable(d,t,s) for t,(p,c) in d.items())
def literal(b):
 d={s:(p.piece_type,p.color) for s,p in b.piece_map().items()};assert all(inside(s) and p in [2,4,6] for s,(p,c) in d.items());side=b.turn;result=[]
 for s,(p,c) in d.items():
  if c!=side:continue
  for rank in range(8):
   for file in range(8):
    t=rank*8+file
    if t in d and (d[t][1]==side or d[t][0]==6):continue
    if not reachable(d,s,t):continue
    q=dict(d);del q[s];q[t]=(p,c);king=next(sq for sq,(pt,col) in q.items() if pt==6 and col==side)
    if not attacked(q,king,not side):result.append(chess.square_name(s)+chess.square_name(t))
 return sorted(result)

D=json.loads((R/'results/dev_aux/task1275/result.json').read_bytes());specs=json.loads((R/'results/dev_aux/task1251/plan.json').read_bytes())['roots'];counts=collections.Counter()
for row,spec in zip(D['rows'],specs):
 assert (row['seed'],row['variant'])==(spec['root']['seed'],spec['root']['variant'])
 b=chess.Board(spec['root']['fen8']);color=b.turn;legal=literal(b);assert legal==sorted(row['tree'])
 for u in legal:
  b.push_uci(u);replies=literal(b);assert replies==legal5(b);counts['literal_frontiers']+=1;zz=[]
  if not replies or b.is_insufficient_material():
   t=(-1 if b.turn==color else 1) if not replies and b.is_check() else 0;zz=[dict(terminal=t)]
  else:
   for v in replies:
    b.push_uci(v);ll=literal(b);assert ll==legal5(b);counts['literal_frontiers']+=1
    if not ll: q=dict(terminal=(-1 if b.turn==color else 1) if b.is_check() else 0)
    elif b.is_insufficient_material():q=dict(terminal=0)
    else:q=dict(R=len(b.pieces(4,color))-len(b.pieces(4,not color)),N=len(b.pieces(2,color))-len(b.pieces(2,not color)))
    zz.append(q);b.pop();counts['leaf_replays']+=1
  assert zz==row['tree'][u];b.pop()
 assert b.fen()==spec['root']['fen8']
 assert row['all_interior_same']
(O/'result.json').write_text(json.dumps(dict(status='PASS_FULL_TREE_MATERIAL_CELL_INDEPENDENT_LITERAL_REPLAY',counts=dict(counts),rows=len(D['rows']),new_go=0),indent=2));print(dict(counts))
