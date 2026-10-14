from pathlib import Path
import json,chess,random,ast,time,importlib.util
R=Path.cwd();O=R/'results/dev_aux/task1455';O.mkdir(exist_ok=False)
plan=dict(question='Does addingpawnandpromotion preservecheap trueWL pricelearning?',stock='KRNBPvKRNBP8x8, 2originalN/2P, norights/EP atroot; EP and allqrbnpromotions preservedatcontinuation; KINGroyal, matestalemate+insuff sufficient+3foldauto+50auto, no materialproxy',seed_start=2026550000,attempts=2048,split='first16TRAIN,next16DEV beforechoices',selection='contactpriceblindvalid,capture>=1,pawnlegal>=1,non1plymate; noprice/engineoutcomes',R=1728,N=720,B=720,nativeRNBP=720,leafQ=1664,P_grid=[180,360,720,1440],H=48,nodes=1024,max_seconds=180,expected_seconds=60,expected_train_cases=256,future='NoTRAINyet; qualifyall32nativelegal, allPprobes+promotions/EP plus independentliteralfirst. PrimaryTRAINmixedglobalP vsbaselineP720 fixedR1728,N/B720; freezeDEVunionbeforeplay. PromotionP->R/N/B/Q valueexclusions described, no humanprices.',scope='Fixedoriginal2N remain, atmost6othernonkingactors each<=4096=>27456below31754. WithfixedR1728,N/B720,P<=1440,Q1664 actualbound<=9792. Not Chessstartingreachability orfullGeneric target.')
(O/'study.json').write_text(json.dumps(plan,indent=2))
s=(R/'results/dev_aux/task1324/generate.py').read_text(encoding='utf-8-sig');exec(compile(ast.Module(body=[n for n in ast.parse(s).body if isinstance(n,ast.FunctionDef) and n.name=='contactdraw'],type_ignores=[]),'contact','exec'))
sp=importlib.util.spec_from_file_location('L',R/'results/dev_aux/task1453/literal_pawn.py');L=importlib.util.module_from_spec(sp);sp.loader.exec_module(L)
types=[6,4,2,3,1,6,4,2,3,1];colors=[1]*5+[0]*5;roots=[];trace=[]
for i,seed in enumerate(range(plan['seed_start'],plan['seed_start']+plan['attempts'])):
 sq=contactdraw(seed,types,colors);b=chess.Board(None)
 for pos,pt,c in zip(sq,types,colors):b.set_piece_at(pos,chess.Piece(pt,bool(c)))
 b.turn=not(i%2);legal=sorted(m.uci() for m in b.legal_moves);caps=[u for u in legal if b.is_capture(chess.Move.from_uci(u))];pawn=[u for u in legal if b.piece_at(chess.Move.from_uci(u).from_square).piece_type==1];failure=None
 if not b.is_valid():failure='invalid'
 elif not legal or b.is_insufficient_material():failure='terminal'
 elif len(legal)<2:failure='too_few_legal'
 elif not caps:failure='no_capture'
 elif not pawn:failure='no_pawn_action'
 else:
  assert legal==L.literal(b)
  for u in legal:
   b.push_uci(u);mate=b.is_checkmate();b.pop()
   if mate:failure='immediate_win';break
 row=dict(seed=seed,index=i,squares=sq,types=types,colors=colors,variant='KRNBP_contact',fen8=b.fen(),fen5=b.fen(),legal=legal,captures=caps,pawn_actions=pawn,failure=failure)
 trace.append(row)
 if failure is None and len(roots)<32:roots.append(dict(row,ordinal=len(roots),phase='TRAIN' if len(roots)<16 else 'DEV'))
assert len(roots)==32
(O/'roots.json').write_text(json.dumps(dict(roots=roots,trace=trace),indent=2));print('PAWN_PRICEBLIND32_FROZEN',sum(x['failure'] is None for x in trace))
