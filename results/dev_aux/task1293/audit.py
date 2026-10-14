from pathlib import Path
import json,chess,random,collections,ast
from fractions import Fraction as F
R=Path.cwd();O=R/'results/dev_aux/task1294';O.mkdir(exist_ok=False);script=(R/'results/dev_aux/task1130/run.py').read_text(encoding='utf-8-sig');module=ast.parse(script);keep=[n for n in module.body if isinstance(n,ast.FunctionDef) and n.name in ['inside','legal5','fen5','term5']];exec(compile(ast.Module(body=keep,type_ignores=[]),'minihelper','exec'))
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

D=json.loads((R/'results/dev_aux/task1266/result.json').read_bytes());counts=collections.Counter()
def walk(node,b):
 assert node['fen']==b.fen();legal=literal(b);assert legal==legal5(b);counts['proof_frontiers']+=1
 if node['terminal']=='CHECKMATE':
  dd={s:(p.piece_type,p.color) for s,p in b.piece_map().items()};assert not legal and attacked(dd,b.king(b.turn),not b.turn) and node['value']==-1;counts['terminal_mate_witnesses']+=1;return
 assert node['depth']>0
 cc=node['children']
 if node['value']==1:assert len(cc)==1 and node['authority']=='onechosenwinningaction'
 else:assert node['value']==-1 and node['authority']=='ALLlegaldefenses' and [v['move'] for v in cc]==legal
 for c in cc:
  assert c['move'] in legal and c['child']['value']==-node['value'] and c['child']['depth']==node['depth']-1
  b.push_uci(c['move'])
  walk(c['child'],b)
  b.pop()
for row in D['rows']:
 assert row['status']=='COMPLETE_EXACT_FINITE_H4';b=chess.Board(row['root']['fen8']);assert sorted(row['scores'])==literal(b);counts['complete_roots']+=1
 assert row['best_value']==max(row['scores'].values())
 for p,u in row['cached_choices'].items():assert row['choice_values'][p]==row['scores'][u]
 for c in row['certificates']:
  assert c['first'] in literal(b) and c['value']==row['scores'][c['first']] and c['child']['value']==-c['value']
  b.push_uci(c['first']);walk(c['child'],b);b.pop();counts['verified_root_action_certificates']+=1
rootvalues=collections.Counter(row['best_value'] for row in D['rows'])
choices={p:dict(collections.Counter(row['choice_values'][p] for row in D['rows'])) for p in ['baseline','J_first','L_first']}
(O/'result.json').write_text(json.dumps(dict(status='PASS_INDEPENDENT_LITERAL_ALL_DEFENSE_MATE_CERTIFICATES',counts=dict(counts),root_values=dict(rootvalues),choice_values=choices,scope='H4value0=no forcedterminalbyH4 underfiniteobjective, NOTinfinitegame DRAW orunprovedmate. Root allactionscorecomputationfromboundedexactsolver; independentlycheckedPLUS/MINUScertificates only, noMSE/trainlabels added.',new_go=0),indent=2));print(dict(counts),dict(rootvalues),choices)
