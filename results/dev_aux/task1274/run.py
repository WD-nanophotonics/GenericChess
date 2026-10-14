from pathlib import Path
from fractions import Fraction as F
import json,chess,collections,time
R=Path.cwd();O=R/'results/dev_aux/task1275';O.mkdir(exist_ok=False)
D=json.loads((R/'results/dev_aux/task1274/plan.json').read_bytes());specs=json.loads((R/'results/dev_aux/task1251/plan.json').read_bytes())['roots'];ratios=list(map(F,D['ratios']));start=time.monotonic();rows=[];nodes=0
breaks=set()
for Rtot,Ntot in [(3,2),(2,3)]:
 for a in range(-2*Rtot,2*Rtot+1):
  for b in range(-2*Ntot,2*Ntot+1):
   if a and F(-b,a)>0:breaks.add(F(-b,a))
assert not any(F(2)<x<F(5,2) for x in breaks)
def leaf(b,color):
 global nodes
 nodes+=1;legal=list(b.legal_moves)
 if not legal:return dict(terminal=(-1 if b.turn==color else 1) if b.is_check() else 0)
 if b.is_insufficient_material():return dict(terminal=0)
 return dict(R=len(b.pieces(4,color))-len(b.pieces(4,not color)),N=len(b.pieces(2,color))-len(b.pieces(2,not color)))
def val(q,x):return F(q['terminal']*1000000) if 'terminal' in q else q['R']*x+q['N']
for spec in specs:
 b=chess.Board(spec['root']['fen8']);color=b.turn;tree={};assert len(b.move_stack)==0
 for u in sorted(m.uci() for m in b.legal_moves):
  b.push_uci(u)
  replies=sorted(m.uci() for m in b.legal_moves)
  if not replies or b.is_insufficient_material():tree[u]=[leaf(b,color)]
  else:
   tree[u]=[]
   for v in replies:b.push_uci(v);tree[u].append(leaf(b,color));b.pop()
  b.pop()
 scores={str(x):{u:min(val(q,x) for q in ls) for u,ls in tree.items()} for x in ratios}
 choices={x:min(u for u,z in vv.items() if z==max(vv.values())) for x,vv in scores.items()}
 interior=[str(x) for x in ratios if F(2)<x<F(5,2)];assert len(set(choices[x] for x in interior))==1
 rows.append(dict(seed=spec['root']['seed'],variant=spec['root']['variant'],tree=tree,choices=choices,scores={x:{u:str(v) for u,v in z.items()} for x,z in scores.items()},all_interior_same=True))
result=dict(status='PASS_ALL24_FULL_TREE_D2_PRICE_CELL_CONTROLS',rows=rows,conservative_breakpoints=[str(x) for x in sorted(breaks)],leaf_visits=nodes,seconds=time.monotonic()-start,scope=D,new_go=0)
(O/'result.json').write_text(json.dumps(result,indent=2));print('FINITE_CELLS',len(rows),nodes,round(result['seconds'],3))
