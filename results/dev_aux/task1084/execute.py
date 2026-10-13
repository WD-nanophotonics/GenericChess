from pathlib import Path
import json,ast,chess,time
from fractions import Fraction as F
R=Path.cwd();O=R/'results/dev_aux/task1085';O.mkdir(exist_ok=False);g=dict(chess=chess)
for file,names in [('task1016/qualify.py',['inside','legal5','fen5','term5']),('task1016/audit_pilot.py',['reachable','attacked','literal'])]:
 t=ast.parse((R/'results/dev_aux'/file).read_text(encoding='utf-8-sig'));exec(compile(ast.Module(body=[n for n in t.body if isinstance(n,ast.FunctionDef) and n.name in names],type_ignores=[]),'independent_parametric_rules','exec'),g)
start=time.monotonic();records=[];counts=dict(roots=0,children=0,leaves=0,literal_frontiers=0);roots=json.loads((R/'results/dev_aux/task1078/roots.json').read_bytes())['roots'];treefile=O/'trees.jsonl'
def leaf(b,color):
 term=g['term5'](b)
 if term:return dict(a=0,b=0,c=0 if term['winner'] is None else 1000000 if term['winner']==color else -1000000,termination=term,fen=b.fen())
 a=len(b.pieces(4,color))-len(b.pieces(4,not color));n=len(b.pieces(2,color))-len(b.pieces(2,not color));return dict(a=a,b=n,c=0,termination=None,fen=b.fen())
def evaluate(children,price):
 vals=[min(x['a']*price+x['b']*90+x['c'] for x in row['leaves']) for row in children];best=max(vals);moves=[row['move'] for row,v in zip(children,vals) if v==best];return dict(price=price,value=best,all_best=moves,chosen=moves[0])
with treefile.open('x',encoding='utf-8') as f:
 for r in roots:
  assert time.monotonic()-start<120;b=chess.Board(r['fen8']);color=b.turn;k=len(b.pieces(2,True))+len(b.pieces(2,False));assert k<=6;children=[];legal=g['literal'](b);assert legal==g['legal5'](b)==r['legal'];counts['literal_frontiers']+=1
  for move in legal:
   b.push_uci(move);t=g['term5'](b)
   if t:ls=[leaf(b,color)]
   else:
    replies=g['literal'](b);assert replies==g['legal5'](b);counts['literal_frontiers']+=1;ls=[]
    for reply in replies:b.push_uci(reply);ls.append(leaf(b,color));b.pop()
   b.pop();children.append(dict(move=move,leaves=ls));counts['children']+=1;counts['leaves']+=len(ls)
  material=[l for row in children for l in row['leaves'] if l['c']==0];assert max(l['b'] for l in material)-min(l['b'] for l in material)<=k
  allcoeff=set((l['a'],l['b']) for l in material);boundaries=sorted(set(F(-90*(bb-b),aa-a) for a,b in allcoeff for aa,bb in allcoeff if aa!=a and 0<F(-90*(bb-b),aa-a)<=3328));assert not boundaries or max(boundaries)<=90*k
  prices=sorted(set([64,90,102,164,262,270,271,419,540,541,671,1074,1718,3328,90*k+1]));curve=[evaluate(children,p) for p in prices];above=[x for x in curve if x['price']>90*k];assert len(set(x['chosen'] for x in above))==1 and len(set(tuple(x['all_best']) for x in above))==1
  record=dict(root=r,knight_stock=k,ranking_bound=90*k,leaf_coefficients=[list(x) for x in sorted(allcoeff)],pairwise_positive_boundaries=[str(x) for x in boundaries],curve=curve,children=children);f.write(json.dumps(record)+'\n');f.flush();records.append({key:value for key,value in record.items() if key!='children'});counts['roots']+=1
(O/'result.json').write_text(json.dumps(dict(status='PASS_COMPLETE_PARAMETRIC_TWO_PLY_AND_ABOVE_BOUND_INVARIANCE',counts=counts,roots=records,new_engine_go=0,seconds=time.monotonic()-start,scope='Completefixedtree materialdecisioninvariance, notFairyselectivesearch ortrueW-Lgain. Fitnessnevermaterialproxy'),indent=2),encoding='utf-8');print(counts,round(time.monotonic()-start,3))
