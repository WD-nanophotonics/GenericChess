from pathlib import Path
import json,ast,chess,random,collections
R=Path.cwd();O=R/'results/dev_aux/task1377';O.mkdir(exist_ok=False)
src=(R/'results/dev_aux/task1016/audit_pilot.py').read_text(encoding='utf-8-sig');defs=[n for n in ast.parse(src).body if isinstance(n,ast.FunctionDef) and n.name in ['reachable','attacked','literal']];text=ast.unparse(ast.Module(body=defs,type_ignores=[])).replace('range(5)','range(8)');inside=lambda s:0<=s<64;exec(text)
src=(R/'results/dev_aux/task1375/generate.py').read_text(encoding='utf-8-sig');defs=[n for n in ast.parse(src).body if isinstance(n,ast.FunctionDef) and n.name=='contactdraw'];exec(compile(ast.Module(body=defs,type_ignores=[]),'sampler','exec'))
d=json.loads((R/'results/dev_aux/task1376/roots.json').read_bytes());selected=[];counts=collections.Counter()
types=[6,4,4,2,2,6,4,4,2,2];colors=[1]*5+[0]*5
for f in d['trace']:
 expected=contactdraw(f['seed'],types,colors);assert expected==f['squares']
 assert f['types']==types and f['colors']==colors and f['variant']=='contact_unfiltered'
 b=chess.Board(None)
 for sq,typ,col in zip(expected,types,colors):b.set_piece_at(sq,chess.Piece(typ,bool(col)))
 b.turn=not(f['index']%2);assert b.fen()==f['fen8'];failure=None
 if not b.is_valid():failure='invalid'
 else:
  counts['valid_profiles']+=1;legal=literal(b);assert legal==f['legal'];counts['literal_frontiers']+=1
  capture=[u for u in legal if b.piece_at(chess.Move.from_uci(u).to_square)];assert capture==f['captures']
  if not legal or b.is_insufficient_material():failure='terminal'
  elif len(legal)<2:failure='too_few_legal'
  elif not capture:failure='no_capture'
  else:
   for u in legal:
    b.push_uci(u);ll=literal(b);counts['literal_frontiers']+=1;dd={sq:(p.piece_type,p.color) for sq,p in b.piece_map().items()};win=not ll and attacked(dd,b.king(b.turn),not b.turn);b.pop()
    if win:failure='immediate_win';break
 assert f['symbolic'] is None
 assert failure==f['failure']
 if failure is None and len(selected)<64:selected.append(f['seed'])
assert selected==d['families'] and [r['seed'] for r in d['roots']]==selected
(O/'result.json').write_text(json.dumps(dict(status='PASS_ALL4096_PRICEBLIND_SYMBOLIC_EXCHANGE_GENERATION_LITERAL',counts=dict(counts),selected=len(selected),new_go=0),indent=2));print(dict(counts))
