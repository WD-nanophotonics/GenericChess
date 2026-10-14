from pathlib import Path
import json,ast,random,chess,importlib.util,collections
R=Path.cwd();O=R/'results/dev_aux/task1459';O.mkdir(exist_ok=False);d=json.loads((R/'results/dev_aux/task1455/roots.json').read_bytes())
sp=importlib.util.spec_from_file_location('L',R/'results/dev_aux/task1453/literal_pawn.py');L=importlib.util.module_from_spec(sp);sp.loader.exec_module(L)
s=(R/'results/dev_aux/task1324/generate.py').read_text(encoding='utf-8-sig');exec(compile(ast.Module(body=[n for n in ast.parse(s).body if isinstance(n,ast.FunctionDef) and n.name=='contactdraw'],type_ignores=[]),'contact','exec'))
selected=[];cc=collections.Counter()
for x in d['trace']:
 assert contactdraw(x['seed'],x['types'],x['colors'])==x['squares'];b=chess.Board(None)
 for sq,pt,col in zip(x['squares'],x['types'],x['colors']):b.set_piece_at(sq,chess.Piece(pt,bool(col)))
 b.turn=not(x['index']%2);assert b.fen()==x['fen8'];failure=None
 if not b.is_valid():failure='invalid'
 else:
  ll=L.literal(b);assert ll==x['legal'];caps=[u for u in ll if b.piece_at(chess.Move.from_uci(u).to_square) is not None];pawn=[u for u in ll if b.piece_at(chess.Move.from_uci(u).from_square).piece_type==1];assert caps==x['captures'] and pawn==x['pawn_actions']
  if not ll or b.is_insufficient_material():failure='terminal'
  elif len(ll)<2:failure='too_few_legal'
  elif not caps:failure='no_capture'
  elif not pawn:failure='no_pawn_action'
  else:
   for u in ll:
    b.push_uci(u);dd={sq:(pc.piece_type,pc.color) for sq,pc in b.piece_map().items()};mate=not L.literal(b) and L.attacked(dd,b.king(b.turn),not b.turn);b.pop()
    if mate:failure='immediate_win';break
 assert failure==x['failure'];cc[str(failure)]+=1
 if failure is None and len(selected)<32:selected.append(x['seed'])
assert selected==[x['seed'] for x in d['roots']]
distance=[]
for r in d['roots']:
 b=chess.Board(r['fen8']);distance.append(dict(seed=r['seed'],phase=r['phase'],promotion_distances={chess.square_name(sq):7-chess.square_rank(sq) if pc.color else chess.square_rank(sq) for sq,pc in b.piece_map().items() if pc.piece_type==1},immediate_promotion_choices=[u for u in r['pawn_actions'] if len(u)==5]))
out=dict(status='PASS_ALL2048_PAWN_SAMPLER_REJECTS_FULL_LEGAL_AND_SPLIT',counts=dict(cc),selected=32,pawn_distance_records=distance,roots_with_immediate_promotion=sum(bool(x['immediate_promotion_choices']) for x in distance),new_go=0,scope='Postfreeze distributiondescription only, neverexcludeafterpricefit. ContactrootPpositions are not startingstandardChessrank distribution; promotiondistance mayexplain usefulconditionalprice ratherthanordinaryhumanpawn table.')
(O/'result.json').write_text(json.dumps(out,indent=2));print({k:v for k,v in out.items() if k!='pawn_distance_records'})
