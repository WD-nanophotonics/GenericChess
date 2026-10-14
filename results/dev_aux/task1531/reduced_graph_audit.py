from pathlib import Path
import json,chess,importlib.util,collections
R=Path.cwd();O=R/'results/dev_aux/task1542';O.mkdir(exist_ok=False)
sp=importlib.util.spec_from_file_location('T',R/'results/dev_aux/task1531/rules.py');T=importlib.util.module_from_spec(sp);sp.loader.exec_module(T)
sp=importlib.util.spec_from_file_location('L',R/'results/dev_aux/task1453/literal_pawn.py');L=importlib.util.module_from_spec(sp);sp.loader.exec_module(L)
P=R/'results/dev_aux/task1538';states=list(map(tuple,json.loads((P/'states.json').read_bytes())));index={s:i for i,s in enumerate(states)};v=json.loads((P/'values.json').read_bytes());values=v['value'];ranks=v['rank'];counts=collections.Counter()
for line in (P/'edges.jsonl').open():
 e=json.loads(line);i=e['id'];s=states[i];b=chess.Board(T.fen(s,8,8));legal=sorted(u for u in L.literal(b) if chess.square_file(chess.Move.from_uci(u).to_square)<3 and chess.square_rank(chess.Move.from_uci(u).to_square)<4);assert legal==[u for u,j in e['moves']]
 d={sq:(p.piece_type,p.color) for sq,p in b.piece_map().items()};k=b.king(b.turn);assert e['checked']==L.attacked(d,k,not b.turn)
 for u,j in e['moves']:
  after=b.copy();after.push_uci(u);p=[12]*6
  for sq,actor in after.piece_map().items():
   ix=T.KINDS.index(actor.symbol());p[ix]=chess.square_rank(sq)*3+chess.square_file(sq)
  t=tuple(p+[0 if after.turn else 1]);assert t==states[j] and index[t]==j;counts['edges']+=1
 if not legal:assert values[i]==(-1 if e['checked'] else 0)
 else:
  child=[values[j] for u,j in e['moves']];assert values[i]==max(-x for x in child)
  if values[i]==1:assert any(values[j]==-1 and ranks[j]<ranks[i] for u,j in e['moves'])
  elif values[i]==-1:assert all(values[j]==1 and ranks[j]<ranks[i] for u,j in e['moves'])
  else:assert all(values[j]!=-1 for u,j in e['moves']) and any(values[j]==0 for u,j in e['moves'])
 counts['states']+=1
out={'status':'PASS_ALL_LITERAL_GEOMETRY_TRANSITIONS_BELLMAN_AND_MATE_RANKS','counts':dict(counts),'scope':'Independent 8-board literal geometry restricted to3x4; every graph state/edge and exactWLD proof. Infinite cycles draw; no standard8board insufficient shortcut.'};(O/'result.json').write_text(json.dumps(out,indent=2));print(out)
