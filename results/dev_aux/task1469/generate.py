from pathlib import Path
import json,chess,random,ast,importlib.util
R=Path.cwd();O=R/'results/dev_aux/task1470';O.mkdir(exist_ok=False)
plan=dict(question='Do trueWL learnedP prices depend on frozenpawnadvancement μ?',seed_starts=dict(early=2026570000,late=2026590000),attempts_per_group=2048,split='first16TRAINnext32DEV eachgroup,48pergroupbeforechoices',P_grid=[180,360,720,1440],fixed=dict(R=1728,N=720,B=720,Q=1664,nativePNBR=720),H=48,nodes=1024,random_seed_base=2026579000,TRAIN_expected_pergroup=256,TRAIN_max_seconds_pergroup=180,DEV='AfterTRAIN eachgroupfreeze ownθ+othergroupθ+P720dedup; eachfresh32DEVgroup compare ownminusbaselineprimary and ownminusother directtransfersecondary; noDEVfit/extension/humanfit',scope='Changedμ premise only, preservesoldP/N2 boundary+negativeuncertainty. KRNBPvKRNBP fullpromotionqrbn/EP/history; finiteW-L Cunknown. earlywhiteP rank2/black7, latewhite6or7/black2or3; other8contactactors priceblind. Notinitialreachability/commonhumanvalue proof.')
(O/'study.json').write_text(json.dumps(plan,indent=2));s=(R/'results/dev_aux/task1324/generate.py').read_text(encoding='utf-8-sig');exec(compile(ast.Module(body=[n for n in ast.parse(s).body if isinstance(n,ast.FunctionDef) and n.name=='contactdraw'],type_ignores=[]),'contact','exec'))
types8=[6,4,2,3]*2;colors8=[1]*4+[0]*4;allroots=[];trace=[]
for group,base in plan['seed_starts'].items():
 selected=[]
 for i,seed in enumerate(range(base,base+2048)):
  sq=contactdraw(seed,types8,colors8);rng=random.Random(seed+970000);wp=[s for s in range(64) if s//8 in ([1] if group=='early' else [5,6]) and s not in sq];ws=rng.choice(wp);bp=[s for s in range(64) if s//8 in ([6] if group=='early' else [1,2]) and s not in sq+[ws]];bs=rng.choice(bp);b=chess.Board(None)
  for pos,pt,c in zip(sq+[ws,bs],types8+[1,1],colors8+[1,0]):b.set_piece_at(pos,chess.Piece(pt,bool(c)))
  b.turn=not(i%2);legal=sorted(m.uci() for m in b.legal_moves);caps=[u for u in legal if b.is_capture(chess.Move.from_uci(u))];pawn=[u for u in legal if b.piece_at(chess.Move.from_uci(u).from_square).piece_type==1];fail=None
  if not b.is_valid():fail='invalid'
  elif not legal or b.is_insufficient_material():fail='terminal'
  elif len(legal)<2:fail='too_few_legal'
  elif not caps:fail='no_capture'
  elif not pawn:fail='no_pawn_action'
  else:
   for u in legal:
    b.push_uci(u);mate=b.is_checkmate();b.pop()
    if mate:fail='immediate_win';break
  row=dict(seed=seed,index=i,group=group,squares=sq+[ws,bs],types=types8+[1,1],colors=colors8+[1,0],variant='KRNBP_'+group,fen8=b.fen(),fen5=b.fen(),legal=legal,captures=caps,pawn_actions=pawn,failure=fail)
  trace.append(row)
  if fail is None and len(selected)<48:selected.append(dict(row,ordinal=len(selected),phase='TRAIN' if len(selected)<16 else 'DEV'))
 assert len(selected)==48;allroots.extend(selected)
(O/'roots.json').write_text(json.dumps(dict(roots=allroots,trace=trace),indent=2));print('FUTURE_ADVANCEMENT96_FROZEN_NOGAMES')
