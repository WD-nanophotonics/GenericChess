from pathlib import Path
import json,ast
R=Path.cwd();O=R/'results/dev_aux/task1403';O.mkdir()
d=json.loads((R/'results/dev_aux/task1400/roots.json').read_bytes());s=(R/'results/dev_aux/task1324/generate.py').read_text(encoding='utf-8-sig');ns={}
import random,chess
ns.update(random=random,chess=chess);exec(compile(ast.Module(body=[n for n in ast.parse(s).body if isinstance(n,ast.FunctionDef) and n.name=='contactdraw'],type_ignores=[]),'sampler','exec'),ns)
spec=__import__('importlib.util',fromlist=['x']).spec_from_file_location('L',R/'results/dev_aux/task1387/literal_rb.py');L=__import__('importlib.util',fromlist=['x']).module_from_spec(spec);spec.loader.exec_module(L)
selected=[]
for f in d['trace']:
 assert ns['contactdraw'](f['seed'],f['types'],f['colors'])==f['squares'];b=chess.Board(f['fen8']);reason=None
 if not b.is_valid():reason='invalid'
 else:
  legal=L.literal(b);assert legal==f['legal'];caps=[u for u in legal if b.piece_at(chess.Move.from_uci(u).to_square)];assert caps==f['captures']
  if not legal or b.is_insufficient_material():reason='terminal'
  elif len(legal)<2:reason='too_few_legal'
  elif not caps:reason='no_capture'
  else:
   for u in legal:
    b.push_uci(u);ll=L.literal(b);dd={sq:(p.piece_type,p.color) for sq,p in b.piece_map().items()};mate=not ll and L.attacked(dd,b.king(b.turn),not b.turn);b.pop()
    if mate:reason='immediate_win';break
 assert reason==f['failure']
 if reason is None and len(selected)<32:selected.append(f['seed'])
assert selected==[v['seed'] for v in d['roots']]
(O/'result.json').write_text(json.dumps(dict(status='PASS_ALL2048_RB_PRICEBLIND_SAMPLER_REJECTS_AND_SPLIT',selected=len(selected),total=len(d['trace']),new_go=0),indent=2));print('B_ELIGIBILITY PASS')
