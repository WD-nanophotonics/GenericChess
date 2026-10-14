from pathlib import Path
import json,chess,importlib.util,collections
R=Path.cwd();O=R/'results/dev_aux/task1429';O.mkdir(exist_ok=False)
sp=importlib.util.spec_from_file_location('L',R/'results/dev_aux/task1387/literal_rb.py');L=importlib.util.module_from_spec(sp);sp.loader.exec_module(L)
cert=json.loads((R/'results/dev_aux/task1424/certificate.json').read_bytes());D=json.loads((R/'results/dev_aux/task1415/study.json').read_bytes());counts=collections.Counter()
expected=json.loads((R/'results/dev_aux/task1416/roots.json').read_bytes())['roots'][:16];assert [x['root'] for x in cert['rows']]==expected
for row in cert['rows']:
 b=chess.Board(row['root']['fen8']);side=b.turn;assert sorted(row['tree'])==L.literal(b)
 values={name:{} for name in D['profiles']}
 for u,ls in row['tree'].items():
  b.push_uci(u);legal=L.literal(b)
  assert [x['reply'] for x in ls]==(legal if legal and not b.is_insufficient_material() else [None])
  for leaf in ls:
   if leaf['reply']:b.push_uci(leaf['reply'])
   assert b.fen()==leaf['fen'];legal=L.literal(b);dd={sq:(p.piece_type,p.color) for sq,p in b.piece_map().items()};check=L.attacked(dd,b.king(b.turn),not b.turn);term=None
   if not legal:term=dict(kind='CHECKMATE' if check else 'STALEMATE',winner=not b.turn if check else None)
   elif b.is_insufficient_material():term=dict(kind='INSUFFICIENT',winner=None)
   elif b.is_repetition(3):term=dict(kind='THREEFOLD_AUTO',winner=None)
   elif b.halfmove_clock>=100:term=dict(kind='FIFTY_AUTO',winner=None)
   assert term==leaf['termination'];coef={p:sum((1 if c==side else -1) for pt,c in dd.values() if pt==typ) for p,typ in [('R',4),('N',2),('B',3)]};assert coef==leaf['coefficients']
   for name,pr in D['profiles'].items():
    val=(0 if term['winner'] is None else (1 if term['winner']==side else -1)*(32000-leaf['ply'])) if term else sum(coef[p]*pr['leaf'+p] for p in 'RNB')
    values[name].setdefault(u,[]).append(val)
   counts['complete_literal_leafs']+=1;counts['terminal_leafs']+=term is not None
   if leaf['reply']:b.pop()
  b.pop()
 for name,sc in values.items():
  vv={u:min(x) for u,x in sc.items()};mx=max(vv.values());assert row['profiles'][name]==dict(value=mx,opt=sorted(u for u,v in vv.items() if v==mx),action_values=vv)
 for role in ['V','U']:assert len({tuple(row['profiles'][role+'_S'+s]['opt']) for s in ['half','one','two']})==1
counts['root_count']=len(expected)
out=dict(status='PASS_INDEPENDENT_LITERAL_COMPLETE_D2_REPLAY_ALL_OPTSETS',counts=dict(counts),new_go=0,scope='Alllegalroot/reply/leafstates/terminalauthority/coefficients/fullties independently reconstructed; D2notWDL/longterm/maturedepth.')
(O/'result.json').write_text(json.dumps(out,indent=2));print(out)
