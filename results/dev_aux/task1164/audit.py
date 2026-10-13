from pathlib import Path
import json,ast,chess,random,collections
R=Path.cwd()
# reconstruct all contact samples; independent royal movement/attacks
O=R/'results/dev_aux/task1166';O.mkdir()
src=(R/'results/dev_aux/task1016/audit_pilot.py').read_text(encoding='utf-8-sig')
defs=[n for n in ast.parse(src).body if isinstance(n,ast.FunctionDef) and n.name in ['reachable','attacked','literal']]
text=ast.unparse(ast.Module(body=defs,type_ignores=[])).replace('range(5)','range(8)')
inside=lambda s:0<=s<64
exec(text)
src=(R/'results/dev_aux/task1151/generate.py').read_text(encoding='utf-8-sig')
defs=[n for n in ast.parse(src).body if isinstance(n,ast.FunctionDef) and n.name=='contactdraw'];exec(compile(ast.Module(body=defs,type_ignores=[]),'sampling_replay','exec'))
d=json.loads((R/'results/dev_aux/task1165/roots.json').read_bytes());picked=[];counts=collections.Counter();valid=0;frontiers=0
for r in d['trace']:
 assert contactdraw(r['seed'],r['types'],r['colors'])==r['squares']
 b=chess.Board(None)
 for s,t,c in zip(r['squares'],r['types'],r['colors']):b.set_piece_at(s,chess.Piece(t,bool(c)))
 b.turn=not((r['index']//4)%2);assert b.fen()==r['fen8']
 failure=None
 if not b.is_valid():failure='invalid'
 else:
  valid+=1;legal=literal(b);assert legal==r['legal'];frontiers+=1
  cap=[u for u in legal if b.piece_at(chess.Move.from_uci(u).to_square)];assert cap==r['captures']
  if not legal or b.is_insufficient_material():failure='terminal'
  elif len(legal)<2:failure='too_few_legal'
  elif not cap:failure='no_capture'
  else:
   for u in legal:
    b.push_uci(u); ll=literal(b);frontiers+=1
    dd={s:(p.piece_type,p.color) for s,p in b.piece_map().items()};king=b.king(b.turn)
    win=not ll and attacked(dd,king,not b.turn);b.pop()
    if win:failure='immediate_win';break
 assert failure==r['failure']
 if failure is None and counts[r['composition']]<16:
  picked.append(r['seed']);counts[r['composition']]+=1
assert picked==[r['seed'] for r in d['roots']]
(O/'result.json').write_text(json.dumps(dict(status='PASS_ALL_CONTACT_SAMPLING_AND_LITERAL_FILTERS',attempts=len(d['trace']),valid=valid,literal_frontiers=frontiers,selected=len(picked),scope='Samplingfunction replay, independentliteralKRNroyalrulefilter. Invalidsamplespreserved; sufficientinsufficiency predicatepythonchess notcompleteFIDEdeadoracle.'),indent=2))
print('CONTACTPASS',valid,frontiers)
