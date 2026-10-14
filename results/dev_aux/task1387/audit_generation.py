from pathlib import Path
import json,ast,chess
R=Path.cwd();O=R/'results/dev_aux/task1387';O.mkdir()
s=(R/'results/dev_aux/task1326/audit.py').read_text(encoding='utf-8-sig')
defs=[n for n in ast.parse(s).body if isinstance(n,ast.FunctionDef) and n.name in ['reachable','attacked','literal']]
text=ast.unparse(ast.Module(body=defs,type_ignores=[])).replace('p in [2, 4, 6]','p in [2, 3, 4, 6]').replace('assert p == 4',"if p == 3:\n        if abs(dx) != abs(dy) or dx == 0:\n            return False\n    else:\n        assert p == 4").replace('if dx and dy or not (dx or dy):','if p == 4 and (dx and dy or not (dx or dy)):')
inside=lambda sq:0<=sq<64;exec(text);(O/'literal_rb.py').write_text('import chess\ninside=lambda s:0<=s<64\n'+text)
d=json.loads((R/'results/dev_aux/task1386/roots.json').read_bytes());valid=front=0
for r in d['trace']:
 b=chess.Board(r['fen8'])
 if not b.is_valid():continue
 valid+=1;ll=literal(b);assert ll==r['legal'];front+=1
 for u in ll:
  b.push_uci(u);assert literal(b)==sorted(m.uci() for m in b.legal_moves);b.pop();front+=1
(O/'result.json').write_text(json.dumps(dict(status='PASS_ALL_VALID_KRRNB_LITERAL_FRONTIERS',valid=valid,frontiers=front,total_attempts=len(d['trace']),new_go=0),indent=2));print('B_LITERAL',valid,front)
