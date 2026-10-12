"""Freeze all actual first-divergence states from quantity objective heldout pairs."""
import json,hashlib,chess
from pathlib import Path
R=Path.cwd();O=R/'results/dev_aux/task183';O.mkdir(exist_ok=True)
if (O/'declaration.json').exists():raise FileExistsError('frozen')
P=R/'results/dev_aux/task175/controller.json';C=json.loads(P.read_bytes());assert C['completed'];lookup={c['context']['name']:c for c in C['calls']};cases=[];identical=[]
for seed in (503,504,505):
 for oi in range(8):
  for color in (True,False):
   pair=[lookup[f's{seed}-unit2ply-heldout-g0-k0-a{arm}-o{oi}-c{int(color)}'] for arm in ('initial','final')];a,b=[p['result']['actions'] for p in pair];prefix=0
   while prefix<min(len(a),len(b)) and a[prefix]==b[prefix]:prefix+=1
   if prefix==len(a)==len(b):identical.append(dict(seed=seed,opening=oi,color=color));continue
   assert prefix<len(a) and prefix<len(b)
   r=pair[0]['result'];board=chess.Board(r['root_fen'])
   history=r['opening_history']+a[:prefix]
   for move in history:board.push_uci(move)
   assert board.turn==color and not board.is_game_over(claim_draw=False)
   assert chess.Move.from_uci(a[prefix]) in board.legal_moves and chess.Move.from_uci(b[prefix]) in board.legal_moves
   cases.append(dict(seed=seed,opening=oi,color=color,initial_fen=r['root_fen'],history=history,expected_fen=board.fen(),played_prefix=prefix,initial_move=a[prefix],final_move=b[prefix],initial_weights=pair[0]['weights'],final_weights=pair[1]['weights'],heldout_quantity_delta=pair[1]['result']['reward']-pair[0]['result']['reward'],heldout_original_delta=pair[1]['result']['score']['reward']-pair[0]['result']['score']['reward']))
D=dict(task_id='183',question='Do actual heldout materialpolicy branch changes expose a finite quantity-versus-mate goal difference?',source_controller_sha256=hashlib.sha256(P.read_bytes()).hexdigest(),cases=cases,identical_pairs=identical,all_pairs=48,case_selection='Allinitial/final heldoutpairs/firstdifferentactor move, noreward/humanfilter; identicaltraces retained. Exactcompleteprelude+sharedprefix.',depth=3,per_case_node_cap=50000,deadline_seconds=240,goals=['unitquantity_including_terminal','terminal_priority_then_unitquantity'],oracle='Onefulllegaldepth3tree produces both goals in vectorutility, standardmax/min fromactorperspective, terminalstops; unitgoal integer PNBRQdifference, WDLgoal terminal±1000000/draw0 elseunitdifference. Allrootmaxsets andinitial/final child scores retained. Node counts include internal nodes andleaves.',failure='Per-case50000node cap preservespartialunproven rootmembers; no increase/retry/resample. Total240sfuse; true userstop alwayswins. Incomplete isnotfailure oflearner itself.',cost='Atmost48bounded depth3 roots, expected<120s/240sfuse frompriorlegalopponent compute, atmost2.4Mnodes; noengine/newgames/workers/fees. Reusealreadyactualgames, notnewphysicalgameevidence.',decision='Ifgoalmaxsets disjoint orobservedactions haveoppositefiniteutility ranking, target/searchalignment deservesnextcheck; ifnot, donotextrapolatesynthetic180mismatch ascurrentfailurecause. Finite3plynot16plyoptimality/WDLcertification orpolicygainevidence.',scope='Exposedheldoutposthoc attribution, fullStandardChess history; notCore/Native/primarycomparison, nohumantuning.')
(O/'declaration.json').write_text(json.dumps(D,indent=2),encoding='utf-8');print(json.dumps(dict(frozen=True,cases=len(cases),identical=len(identical))))
