from pathlib import Path
import json,chess,importlib.util,collections,hashlib
R=Path.cwd();O=R/'results/dev_aux/task1493';O.mkdir(exist_ok=False);P=R/'results/dev_aux/task1492'
sp=importlib.util.spec_from_file_location('L',R/'results/dev_aux/task1453/literal_pawn.py');L=importlib.util.module_from_spec(sp);sp.loader.exec_module(L)
# Certificate nodes are postorder; keep only minimal child conclusions/hashes, not complete trees twice.
seen={};counts=collections.Counter()
def hk(b):
 ep=b.ep_square;usable=ep is not None and any(chess.Move.from_uci(u).to_square==ep and b.piece_at(chess.Move.from_uci(u).from_square).piece_type==1 and b.piece_at(ep) is None for u in L.literal(b));return b.board_fen()+str(b.turn)+str(ep if usable else None)
roots=json.loads((R/'results/dev_aux/task1470/roots.json').read_bytes())['roots'];original={r['fen8'] for r in roots}
for line in (P/'certificate_nodes.jsonl').open(encoding='utf8'):
 x=json.loads(line);assert x['id'] not in seen;b=chess.Board(x['fen']);ll=L.literal(b);assert ll==x['legal'];d={s:(p.piece_type,p.color) for s,p in b.piece_map().items()};k=next(s for s,(pt,c) in d.items() if pt==6 and c==b.turn);checked=L.attacked(d,k,not b.turn);t=None
 # reconstruct original board from FEN after reverse? use history keyed root matched by replay, index available via path reversal impossible unique fen. For these H<=5 root clock0, threefold impossible until >=8, fifty impossible; assert that bound.
 assert len(x['history'])<=5 and b.halfmove_clock<=5
 if not ll:t={'kind':'CHECKMATE' if checked else 'STALEMATE','winner':not b.turn if checked else None}
 elif b.is_insufficient_material():t={'kind':'SUFFICIENT_MATERIAL_INSUFF_DRAW','winner':None}
 assert x['terminal']==t
 children=x['children'];own=b.turn==x['side']
 if t is not None:expected=t['winner']==x['side'];assert not children
 elif x['remaining']==0:expected=False;assert not children
 else:
  assert [u for u,_,_ in children]==ll[:len(children)] and children
  for u,cid,ans in children:
   assert cid in seen;child=seen[cid];v=b.copy();v.push_uci(u);assert child['fen']==v.fen() and child['history']==x['history']+[u] and child['remaining']==x['remaining']-1 and child['side']==x['side'] and child['win']==ans
  expected=any(a for _,_,a in children) if own else all(a for _,_,a in children)
  if len(children)<len(ll):assert children[-1][2]==own
 assert x['win_within_H']==expected
 seen[x['id']]={'fen':x['fen'],'history':x['history'],'remaining':x['remaining'],'side':x['side'],'win':expected};counts['literal_nodes']+=1;counts['edges']+=len(children);counts['terminal']+=t is not None
res=json.loads((P/'result.json').read_bytes());assert res['status']=='COMPLETE' and len(seen)==res['nodes'];wins=collections.Counter()
for r in res['rows']:
 root=roots[r['index']];assert root==r['root'] and [a['move'] for a in r['actions']]==root['legal'];b=chess.Board(root['fen8'])
 for a in r['actions']:
  v=b.copy();v.push_uci(a['move']);c=seen[a['certificate_id']];assert c['fen']==v.fen() and c['history']==[a['move']] and c['remaining']==r['H']-1 and c['side']==b.turn and c['win']==a['win_within_H']
 assert r['winning_actions']==[a['move'] for a in r['actions'] if a['win_within_H']];wins[f"H{r['H']}_"+('early' if r['index']<48 else 'late')]+=bool(r['winning_actions'])
out={'status':'PASS_INDEPENDENT_LITERAL_ALL_CERTIFICATE_NODES_EDGES_ROOTS','counts':dict(counts),'roots_with_forced_win':dict(wins),'scope':'H3 all96,H5 first8eachTRAIN; false=no forced win within horizon, not draw/loss. Clock/history draw impossible within5 from0. Geometry independent; insufficient draw uses same sufficient predicate.'};(O/'result.json').write_text(json.dumps(out,indent=2));print(out)
