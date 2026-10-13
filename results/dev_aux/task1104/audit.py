from pathlib import Path
import json,chess,random,collections,ast
from fractions import Fraction as F
R=Path.cwd();O=R/'results/dev_aux/task1106';O.mkdir(exist_ok=False);script=(R/'results/dev_aux/task1016/qualify.py').read_text(encoding='utf-8-sig');module=ast.parse(script);keep=[n for n in module.body if isinstance(n,ast.FunctionDef) and n.name in ['inside','legal5','fen5','term5']];exec(compile(ast.Module(body=keep,type_ignores=[]),'minihelper','exec'))
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
  for rank in range(5):
   for file in range(5):
    t=rank*8+file
    if t in d and (d[t][1]==side or d[t][0]==6):continue
    if not reachable(d,s,t):continue
    q=dict(d);del q[s];q[t]=(p,c);king=next(sq for sq,(pt,col) in q.items() if pt==6 and col==side)
    if not attacked(q,king,not side):result.append(chess.square_name(s)+chess.square_name(t))
 return sorted(result)
P=R/'results/dev_aux/task1105';games=list(map(json.loads,(P/'games.jsonl').read_text().splitlines()));raw=iter(map(json.loads,(P/'queries.jsonl').read_text().splitlines()));counts=collections.Counter();rows=[];seen=[]
for g in games:
 b=chess.Board(g['root']['fen8']);history=[b.board_fen()+str(b.turn)];qs=iter(g['queries']);randomturn=0;seen.append((g['price'],g['leafR'],g['opponent'],g['root']['seed'],g['color']))
 for ply,a in enumerate(g['actions']):
  assert term5(b) is None and a['before']==b.fen() and a['actor']==b.turn;assert literal(b)==legal5(b);counts['literal_frontiers']+=1
  if b.turn==g['color'] or g['opponent']!='uniform_random':
   q=next(qs);assert q==next(raw);assert q['move']==a['move'] and q['ply']==ply;expected=dict(P=208,N=90,B=208,R=g['leafR'] if b.turn==g['color'] else (90 if g['opponent']=='unit_search' else 1718),Q=208,K=0);assert q['weights']==expected;m=q['metadata'];assert m['root_fen5']==g['root']['fen5'] and m['root_fen8']==g['root']['fen8'] and m['full_history']==[x['move'] for x in g['actions'][:ply]] and m['command']=='go nodes 64'
   for line in m['uci_info']:
    fs=line.split()
    if 'tbhits' in fs:assert int(fs[fs.index('tbhits')+1])==0;counts['tbhits_zero']+=1
    if 'pv' in fs:
     v=b.copy()
     for text in fs[fs.index('pv')+1:]:assert text in literal(v);v.push_uci(text);counts['literal_PVmoves']+=1
   counts['go']+=1
  else:
   legal=literal(b);seed=(2026185000+2*g['root']['seed']+int(g['color']))*100+randomturn;idx=random.Random(seed).randrange(len(legal));assert a['draw']==dict(seed=seed,index=idx,legal=legal,opponent_turn=randomturn) and a['move']==legal[idx];randomturn+=1;counts['randomdraws']+=1
  assert a['move'] in literal(b);b.push_uci(a['move']);assert b.fen()==a['after'];history.append(b.board_fen()+str(b.turn));counts['actions']+=1
 assert next(qs,None) is None;legal=literal(b);d={s:(p.piece_type,p.color) for s,p in b.piece_map().items()};king=next(s for s,(pt,c) in d.items() if pt==6 and c==b.turn);checked=attacked(d,king,not b.turn);t=None
 if not legal:t=dict(kind='CHECKMATE' if checked else 'STALEMATE',winner=not b.turn if checked else None)
 elif len(d)==2:t=dict(kind='KING_ONLY',winner=None)
 elif history.count(history[-1])>=3:t=dict(kind='THREEFOLD_AUTO',winner=None)
 elif b.halfmove_clock>=100:t=dict(kind='FIFTY_MOVE_AUTO',winner=None)
 assert t==term5(b);expected=t or dict(kind='cap24',winner=None);assert expected==g['termination'] and b.fen()==g['final_fen'];label='C' if t is None else 'D' if t['winner'] is None else 'W' if t['winner']==g['color'] else 'L';assert label==g['label'];assert len(g['actions'])==24 if t is None else len(g['actions'])<=24
assert next(raw,None) is None;roots=[r for r in json.loads((R/'results/dev_aux/task1098/roots.json').read_bytes())['roots']];assert seen==[(p,l,opp,r['seed'],c) for p,l in [(64,90),(90,64)] for opp in ['unit_search','uniform_random'] for r in roots for c in [False,True]]
for opp in ['unit_search','uniform_random']:
 for p in [64,90]:
  xx=[g for g in games if g['price']==p and g['opponent']==opp];cc=collections.Counter(g['label'] for g in xx);rows.append(dict(price=p,opponent=opp,N=len(xx),counts=dict(cc),J16=str(F(cc['W']-cc['L'],len(xx)))))
(O/'result.json').write_text(json.dumps(dict(status='PASS_ALL256_NATIVE_LEAF_FACTORIAL_GAMES_LITERAL_RULES',counts=dict(counts),rows=rows,new_go=0,scope='Mechanical5x5 K/R/N,mate/stalemate/3foldauto/50move/kingonly. NoChess8x8oracle applied,noPawn/promotion/drop/castling/EP,notfullgenericdomain; printedPVlegalnotforcemate'),indent=2),encoding='utf-8');print(rows);print(dict(counts))
