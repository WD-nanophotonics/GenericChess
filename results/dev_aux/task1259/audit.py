from pathlib import Path
import json,chess,random,collections,ast
from fractions import Fraction as F
R=Path.cwd();O=R/'results/dev_aux/task1271';O.mkdir(exist_ok=False);script=(R/'results/dev_aux/task1130/run.py').read_text(encoding='utf-8-sig');module=ast.parse(script);keep=[n for n in module.body if isinstance(n,ast.FunctionDef) and n.name in ['inside','legal5','fen5','term5']];exec(compile(ast.Module(body=keep,type_ignores=[]),'minihelper','exec'))
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
P=R/'results/dev_aux/task1269';games=list(map(json.loads,(P/'games.jsonl').read_text().splitlines()));raw=iter(map(json.loads,(P/'queries.jsonl').read_text().splitlines()));counts=collections.Counter();rows=[];seen=[]
for g in games:
 b=chess.Board(g['root']['fen8']);history=[b.board_fen()+str(b.turn)];qs=iter(g['queries']);randomturn=0;seen.append((g['arm'],g['price'],g['opponent'],g['root']['seed'],g['root']['variant'],g['color']))
 for ply,a in enumerate(g['actions']):
  assert term5(b) is None and a['before']==b.fen() and a['actor']==b.turn;assert literal(b)==legal5(b);counts['literal_frontiers']+=1
  if b.turn==g['color'] or g['opponent']!='uniform_random':
   q=next(qs);assert q==next(raw);assert q['move']==a['move'] and q['ply']==ply;expected=dict(P=1664,N=g['N'],B=1664,R=g['price'] if b.turn==g['color'] else g['N'],Q=1664,K=0);assert q['weights']==expected;native_expected=dict(expected,R=g['nativeR'] if b.turn==g['color'] else g['N']);assert q['native_weights']==native_expected;m=q['metadata'];assert m['root_fen5']==g['root']['fen5'] and m['root_fen8']==g['root']['fen8'] and m['full_history']==[x['move'] for x in g['actions'][:ply]] and m['command']=='go nodes 256'
   for line in m['uci_info']:
    fs=line.split()
    if 'tbhits' in fs:assert int(fs[fs.index('tbhits')+1])==0;counts['tbhits_zero']+=1
    if 'pv' in fs:
     v=b.copy()
     for text in fs[fs.index('pv')+1:]:assert text in literal(v);v.push_uci(text);counts['literal_PVmoves']+=1
   counts['go']+=1
  else:
   legal=literal(b);seed=(2026319000+2*g['root']['seed']+int(g['color']))*100+randomturn;idx=random.Random(seed).randrange(len(legal));assert a['draw']==dict(seed=seed,index=idx,legal=legal,opponent_turn=randomturn) and a['move']==legal[idx];randomturn+=1;counts['randomdraws']+=1
  assert a['move'] in literal(b);b.push_uci(a['move']);assert b.fen()==a['after'];history.append(b.board_fen()+str(b.turn));counts['actions']+=1
 assert next(qs,None) is None;legal=literal(b);d={s:(p.piece_type,p.color) for s,p in b.piece_map().items()};king=next(s for s,(pt,c) in d.items() if pt==6 and c==b.turn);checked=attacked(d,king,not b.turn);t=None
 if not legal:t=dict(kind='CHECKMATE' if checked else 'STALEMATE',winner=not b.turn if checked else None)
 elif b.is_insufficient_material():t=dict(kind='SUFFICIENT_MATERIAL_INSUFF_DRAW',winner=None)
 elif history.count(history[-1])>=3:t=dict(kind='THREEFOLD_AUTO',winner=None)
 elif b.halfmove_clock>=100:t=dict(kind='FIFTY_MOVE_AUTO',winner=None)
 assert t==term5(b);expected=t or dict(kind='cap24',winner=None);assert expected==g['termination'] and b.fen()==g['final_fen'];label='C' if t is None else 'D' if t['winner'] is None else 'W' if t['winner']==g['color'] else 'L';assert label==g['label'];assert len(g['actions'])==24 if t is None else len(g['actions'])<=24

assert next(raw,None) is None
plan=json.loads((R/'results/dev_aux/task1259/plan.json').read_bytes());roots=[r for r in json.loads((R/'results/dev_aux/task1238/roots.json').read_bytes())['roots'] if r['family_ordinal']<8]
assert seen==[(f'SCALE{n}',int(n*F(q)),opp,r['seed'],r['variant'],c) for n in plan['N_values'] for q in plan['ratios'] for opp in ['unit_search','uniform_random'] for r in roots for c in ([False,True] if r['beneficiary'] is None else [r['beneficiary']])]
old=[json.loads(v) for v in (R/'results/dev_aux/task1243/games.jsonl').read_text().splitlines()]
key=lambda g:(g['root']['seed'],g['root']['variant'],g['color'],g['opponent'])
oldmap={key(g):g for g in old if g['arm']=='J' and g['price']==720};controls=0
for g in games:
 if g['N']==720 and g['ratio']=='1':
  v=oldmap[key(g)];assert g['actions']==v['actions'] and g['final_fen']==v['final_fen'] and g['label']==v['label'] and g['termination']==v['termination'];controls+=1
(O/'result.json').write_text(json.dumps(dict(status='PASS_ALL864_MATERIAL_UNIT_SCALE_GAMES_LITERAL',counts=dict(counts),baseline_fulltrajectory_controls=controls,new_go=0,scope=plan),indent=2));print(dict(counts),'CONTROLS',controls)
