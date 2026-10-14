from pathlib import Path
import json,ast,chess,random,collections
R=Path.cwd();O=R/'results/dev_aux/task1287';O.mkdir(exist_ok=False)
src=(R/'results/dev_aux/task1016/audit_pilot.py').read_text(encoding='utf-8-sig');defs=[n for n in ast.parse(src).body if isinstance(n,ast.FunctionDef) and n.name in ['reachable','attacked','literal']];text=ast.unparse(ast.Module(body=defs,type_ignores=[])).replace('range(5)','range(8)');inside=lambda s:0<=s<64;exec(text)
src=(R/'results/dev_aux/task1285/generate.py').read_text(encoding='utf-8-sig');defs=[n for n in ast.parse(src).body if isinstance(n,ast.FunctionDef) and n.name=='contactdraw'];exec(compile(ast.Module(body=defs,type_ignores=[]),'sampler','exec'))
d=json.loads((R/'results/dev_aux/task1286/roots.json').read_bytes());selected=[];counts=collections.Counter()
for f in d['trace']:
 expected=contactdraw(f['seed'],[6,4,2,6,4,2,2],[1,1,1,0,0,0,1]);assert expected==f['squares'];flags=[]
 assert [r['variant'] for r in f['profiles']]==['none','whiteR','whiteN','blackR','blackN']
 for r in f['profiles']:
  base=[6,4,2,6,4,2];cols=[1,1,1,0,0,0];add=r['variant']!='none';side=r['variant'].startswith('white') if add else None;t=4 if r['variant'].endswith('R') else 2
  assert r['types']==base+([t] if add else []) and r['colors']==cols+([int(side)] if add else []) and r['beneficiary']==side and r['squares']==expected[:6]+([expected[6]] if add else [])
  b=chess.Board(None)
  for sq,typ,col in zip(r['squares'],r['types'],r['colors']):b.set_piece_at(sq,chess.Piece(typ,bool(col)))
  b.turn=not(f['index']%2);assert b.fen()==r['fen8'];failure=None
  if not b.is_valid():failure='invalid'
  else:
   counts['valid_profiles']+=1;legal=literal(b);assert legal==r['legal'];counts['literal_frontiers']+=1;capture=[u for u in legal if b.piece_at(chess.Move.from_uci(u).to_square)];assert capture==r['captures']
   if not legal or b.is_insufficient_material():failure='terminal'
   elif len(legal)<2:failure='too_few_legal'
   elif not capture:failure='no_capture'
   else:
    for u in legal:
     b.push_uci(u);ll=literal(b);counts['literal_frontiers']+=1;dd={sq:(p.piece_type,p.color) for sq,p in b.piece_map().items()};win=not ll and attacked(dd,b.king(b.turn),not b.turn);b.pop()
     if win:failure='immediate_win';break
  assert failure==r['failure'];flags.append(failure is None)
 assert f['eligible']==all(flags)
 if all(flags) and len(selected)<64:selected.append(f['seed'])
assert selected==d['families'] and [r['seed'] for r in d['roots']]==[s for s in selected for _ in range(5)]
(O/'result.json').write_text(json.dumps(dict(status='PASS_ALL8192_MATCHED_COMMON_SUPPORT_FAMILIES_LITERAL',counts=dict(counts),selected=len(selected),roots=len(d['roots']),new_go=0,scope='Samplingreplay plus independentliteralroyalfilters; allfiveprofiles/beneficiaries/extrasquares checked; common-supportμ notallpossiblepositions.'),indent=2));print(dict(counts))
