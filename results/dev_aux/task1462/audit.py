from pathlib import Path
import json,chess,random,collections,ast
from fractions import Fraction as F
R=Path.cwd();O=R/'results/dev_aux/task1466';O.mkdir(exist_ok=False);script=(R/'results/dev_aux/task1130/run.py').read_text(encoding='utf-8-sig');module=ast.parse(script);keep=[n for n in module.body if isinstance(n,ast.FunctionDef) and n.name in ['inside','legal5','fen5','term5']];exec(compile(ast.Module(body=keep,type_ignores=[]),'minihelper','exec'))
import importlib.util
sp=importlib.util.spec_from_file_location('literalRB',R/'results/dev_aux/task1453/literal_pawn.py');L=importlib.util.module_from_spec(sp);sp.loader.exec_module(L);literal=L.literal;attacked=L.attacked
def history_key(b):
 dd=b.board_fen()+str(b.turn);ep=b.ep_square;usable=ep is not None and any(chess.Move.from_uci(u).to_square==ep and b.piece_at(chess.Move.from_uci(u).from_square).piece_type==1 and b.piece_at(ep) is None for u in literal(b))
 return dd+str(ep if usable else None)
P=R/'results/dev_aux/task1461';games=list(map(json.loads,(P/'games.jsonl').read_text().splitlines()));raw=iter(map(json.loads,(P/'queries.jsonl').read_text().splitlines()));counts=collections.Counter();rows=[];seen=[]
for g in games:
 b=chess.Board(g['root']['fen8']);history=[history_key(b)];qs=iter(g['queries']);randomturn=0;seen.append((g['arm'],g['price'],g['opponent'],g['root']['seed'],g['root']['variant'],g['color']))
 for ply,a in enumerate(g['actions']):
  assert term5(b) is None and a['before']==b.fen() and a['actor']==b.turn;assert literal(b)==legal5(b);counts['literal_frontiers']+=1
  if b.turn==g['color'] or g['opponent']!='uniform_random':
   q=next(qs);assert q==next(raw);assert q['move']==a['move'] and q['ply']==ply;expected=dict(P=g['leafP'] if b.turn==g['color'] else 720,N=720,B=g['leafB'] if b.turn==g['color'] else 720,R=g['leafR'] if b.turn==g['color'] else 720,Q=1664,K=0);assert q['weights']==expected;native_expected=dict(expected,R=720,B=720,P=720);assert q['native_weights']==native_expected;m=q['metadata'];assert m['root_fen5']==g['root']['fen5'] and m['root_fen8']==g['root']['fen8'] and m['full_history']==[x['move'] for x in g['actions'][:ply]] and m['command']=='go nodes 1024'
   for line in m['uci_info']:
    fs=line.split()
    if 'tbhits' in fs:assert int(fs[fs.index('tbhits')+1])==0;counts['tbhits_zero']+=1
    if 'pv' in fs:
     v=b.copy()
     for text in fs[fs.index('pv')+1:]:assert text in literal(v);v.push_uci(text);counts['literal_PVmoves']+=1
   counts['go']+=1
  else:
   legal=literal(b);seed=(2026559000+2*g['root']['seed']+int(g['color']))*100+randomturn;idx=random.Random(seed).randrange(len(legal));assert a['draw']==dict(seed=seed,index=idx,legal=legal,opponent_turn=randomturn) and a['move']==legal[idx];randomturn+=1;counts['randomdraws']+=1
  assert a['move'] in literal(b);b.push_uci(a['move']);assert b.fen()==a['after'];history.append(history_key(b));counts['actions']+=1
 assert next(qs,None) is None;legal=literal(b);d={s:(p.piece_type,p.color) for s,p in b.piece_map().items()};king=next(s for s,(pt,c) in d.items() if pt==6 and c==b.turn);checked=attacked(d,king,not b.turn);t=None
 if not legal:t=dict(kind='CHECKMATE' if checked else 'STALEMATE',winner=not b.turn if checked else None)
 elif b.is_insufficient_material():t=dict(kind='SUFFICIENT_MATERIAL_INSUFF_DRAW',winner=None)
 elif history.count(history[-1])>=3:t=dict(kind='THREEFOLD_AUTO',winner=None)
 elif b.halfmove_clock>=100:t=dict(kind='FIFTY_MOVE_AUTO',winner=None)
 assert t==term5(b);expected=t or dict(kind='cap48',winner=None);assert expected==g['termination'] and b.fen()==g['final_fen'];label='C' if t is None else 'D' if t['winner'] is None else 'W' if t['winner']==g['color'] else 'L';assert label==g['label'];assert len(g['actions'])==48 if t is None else len(g['actions'])<=48
assert next(raw,None) is None
roots=json.loads((R/'results/dev_aux/task1455/roots.json').read_bytes())['roots'][:16]
plan=json.loads((R/'results/dev_aux/task1460/manifest.json').read_bytes())
assert len(roots)==16 and len(games)==256
assert seen==[(arm,p['leafP'],opp,r['seed'],r['variant'],c) for arm,p in plan['profiles'].items() for opp in ['unit_search','uniform_random'] for r in roots for c in [False,True]]
for g in games:
 assert g['profile']==g['arm'] and g['nativeR']==720 and g['leafR']==plan['profiles'][g['arm']]['leafR'] and g['leafB']==plan['profiles'][g['arm']]['leafB'] and g['parameter_price']==g['leafP'] and g['leafP']==plan['profiles'][g['arm']]['leafP']
for arm in plan['profiles']:
 for opp in ['unit_search','uniform_random']:
  xx=[g for g in games if g['arm']==arm and g['opponent']==opp];cc=collections.Counter(g['label'] for g in xx);rows.append(dict(arm=arm,opponent=opp,N=len(xx),counts=dict(cc),J48=str(F(cc['W']-cc['L'],len(xx)))))
(O/'result.json').write_text(json.dumps(dict(status='PASS_256_PAWN_TRAIN_PROMOTION_EP_LITERAL_PV_HISTORY_RNG_TERMINAL_LITERAL_PV_HISTORY_RNG_TERMINAL',counts=dict(counts),rows=rows,new_go=0),indent=2));print(rows);print(dict(counts))


