from pathlib import Path
import json,ast,chess,random,collections
R=Path.cwd();O=R/'results/dev_aux/task1304';O.mkdir(exist_ok=False)
src=(R/'results/dev_aux/task1016/audit_pilot.py').read_text(encoding='utf-8-sig');defs=[n for n in ast.parse(src).body if isinstance(n,ast.FunctionDef) and n.name in ['reachable','attacked','literal']];text=ast.unparse(ast.Module(body=defs,type_ignores=[])).replace('range(5)','range(8)');inside=lambda s:0<=s<64;exec(text)
src=(R/'results/dev_aux/task1301/generate.py').read_text(encoding='utf-8-sig');defs=[n for n in ast.parse(src).body if isinstance(n,ast.FunctionDef) and n.name=='contactdraw'];exec(compile(ast.Module(body=defs,type_ignores=[]),'sampler','exec'))
d=json.loads((R/'results/dev_aux/task1302/roots.json').read_bytes());selected=[];counts=collections.Counter()
types=[6,4,4,2,2,6,4,4,2,2];colors=[1]*5+[0]*5
for f in d['trace']:
 expected=contactdraw(f['seed'],types,colors);assert expected==f['squares']
 assert f['types']==types and f['colors']==colors and f['variant']=='exchange_conflict'
 b=chess.Board(None)
 for sq,typ,col in zip(expected,types,colors):b.set_piece_at(sq,chess.Piece(typ,bool(col)))
 b.turn=not(f['index']%2);assert b.fen()==f['fen8'];failure=None
 if not b.is_valid():failure='invalid'
 else:
  counts['valid_profiles']+=1;legal=literal(b);assert legal==f['legal'];counts['literal_frontiers']+=1
  capture=[u for u in legal if b.piece_at(chess.Move.from_uci(u).to_square)];assert capture==f['captures']
  if not legal or b.is_insufficient_material():failure='terminal'
  elif len(legal)<2:failure='too_few_legal'
  elif {b.piece_at(chess.Move.from_uci(u).to_square).piece_type for u in capture}!={2,4}:failure='missing_both_R_N_capture_targets'
  else:
   for u in legal:
    b.push_uci(u);ll=literal(b);counts['literal_frontiers']+=1;dd={sq:(p.piece_type,p.color) for sq,p in b.piece_map().items()};win=not ll and attacked(dd,b.king(b.turn),not b.turn);b.pop()
    if win:failure='immediate_win';break
 if failure is None:
  sym=f['symbolic'];assert sym is not None;assert sorted(sym['tree'])==literal(b);color=b.turn
  for u in literal(b):
   b.push_uci(u);ll=literal(b);assert ll==legal5(b) if 'legal5' in globals() else ll==sorted(x.uci() for x in b.legal_moves);cached=sym['tree'][u];values=[]
   if not ll or b.is_insufficient_material():values=[dict(terminal=(-1 if b.turn==color else 1) if not ll and b.is_check() else 0)]
   else:
    for v in ll:
     b.push_uci(v);qq=literal(b);counts['symbolic_literal_leaf']+=1
     if not qq:values.append(dict(terminal=(-1 if b.turn==color else 1) if b.is_check() else 0))
     elif b.is_insufficient_material():values.append(dict(terminal=0))
     else:values.append(dict(R=len(b.pieces(4,color))-len(b.pieces(4,not color)),N=len(b.pieces(2,color))-len(b.pieces(2,not color))))
     b.pop()
   b.pop();assert values==cached
  intersection=set(sym['tree'])
  for cell in sym['cells']:intersection &= set(cell['opt'])
  assert sorted(intersection)==sym['universal_optimal_actions'] and sym['has_tradeoff']==(not intersection)
  if intersection:failure='no_D2_symbolic_exchange_conflict'
 assert failure==f['failure']
 if failure is None and len(selected)<32:selected.append(f['seed'])
assert selected==d['families'] and [r['seed'] for r in d['roots']]==selected
(O/'result.json').write_text(json.dumps(dict(status='PASS_ALL2048_PRICEBLIND_SYMBOLIC_EXCHANGE_GENERATION_LITERAL',counts=dict(counts),selected=len(selected),new_go=0),indent=2));print(dict(counts))
