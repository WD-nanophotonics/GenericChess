from pathlib import Path
import ast,json,chess,random
R=Path.cwd();O=R/'results/dev_aux/task1400';O.mkdir()
s=(R/'results/dev_aux/task1324/generate.py').read_text(encoding='utf-8-sig')
exec(compile(ast.Module(body=[n for n in ast.parse(s).body if isinstance(n,ast.FunctionDef) and n.name=='contactdraw'],type_ignores=[]),'sampler','exec'))
types=[6,4,4,2,3,6,4,4,2,3];colors=[1]*5+[0]*5;trace=[];roots=[]
for i,seed in enumerate(range(2026490000,2026492048)):
 sq=contactdraw(seed,types,colors);b=chess.Board(None)
 for pos,pt,c in zip(sq,types,colors):b.set_piece_at(pos,chess.Piece(pt,bool(c)))
 b.turn=not(i%2);legal=sorted(m.uci() for m in b.legal_moves);captures=[u for u in legal if b.is_capture(chess.Move.from_uci(u))];failure=None
 if not b.is_valid():failure='invalid'
 elif not legal or b.is_insufficient_material():failure='terminal'
 elif len(legal)<2:failure='too_few_legal'
 elif not captures:failure='no_capture'
 else:
  for u in legal:
   b.push_uci(u);mate=b.is_checkmate();b.pop()
   if mate:failure='immediate_win';break
 row=dict(seed=seed,index=i,squares=sq,types=types,colors=colors,variant='KR_R_N_B_contact',beneficiary=None,fen8=b.fen(),fen5=b.fen(),legal=legal,captures=captures,failure=failure)
 trace.append(row)
 if failure is None and len(roots)<32:roots.append(dict(row,ordinal=len(roots),phase='TRAIN' if len(roots)<16 else 'DEV'))
assert len(roots)==32
(O/'roots.json').write_text(json.dumps(dict(roots=roots,trace=trace),indent=2))
(O/'plan.json').write_text(json.dumps(dict(question='Add bishop without assuming a human price, interface feasibility only',types=types,colors=colors,split='first16TRAIN,next16DEV before any choices; feasibility search onlyTRAIN, all32nativelegal',selection='priceblind contact valid/capture/non-one-mate, noengine outcomes/D2criterion',profiles=[[720,720],[1728,720],[1728,360],[1728,1440],[4096,4096]],N=720,nativeR=720,nativeB=720,nodes=4096,max_seconds=90,expected_go=112,expected_perft=32,future='ActualW-L H48 training B only at fixed priorR1728, TRAIN16/DEV16; no training run yet, no ratioB fit/human labels',scope='KRRNBvKRRNB, noP/Q/promotion/drop/castling/ep; finite material upper26016 belowmate32000'),indent=2))
print('B_INPUT',len(roots))
