"""Bound actual price/search-source scope and coordinate reachability, no games."""
import hashlib,json,re,math,itertools,importlib.util,statistics,time
from pathlib import Path
R=Path.cwd();O=R/'results/dev_aux/task132';O.mkdir(exist_ok=True);PIN='9f778da667f6e07dae1e85d3e2ea204fc6dee94d'
files={'evaluate.cpp':R/'.local_agent/material-selfplay/evaluate.cpp','psqt.cpp':R/'.local_agent/material-selfplay/psqt.cpp','movepick.cpp':R/'.local_agent/material-selfplay/movepick.cpp','position.cpp':R/'.local_agent/material-selfplay/position.cpp','search.cpp':R/'.local_agent/material-selfplay/source-review/search.cpp','thread.cpp':R/'.local_agent/material-selfplay/source-review/thread.cpp','types.h':R/'.local_agent/material-selfplay/source-review/types.h'}
needles={'evaluate.cpp':['GENERICCHESS_MATERIAL_DEVELOPMENT','material += EvalPieceValue[MG][pt]','return Value(std::clamp(material'], 'psqt.cpp':['if (is_custom(pt))','PieceValue[MG][make_piece(WHITE, pt)]','if (v->pieceValue[MG][pt])','CapturePieceValue[MG][pc]','EvalPieceValue[MG][pc]'], 'movepick.cpp':['PieceValue[MG][pos.piece_on(to_sq(m))]'],'position.cpp':['st->nonPawnMaterial[them] -= PieceValue[MG][captured]','int swap = PieceValue[MG][piece_on(to)] - threshold','PieceValue[MG][moved_piece(m)] - swap'], 'search.cpp':['TT.clear();','Threads.clear();','futilityBase = bestValue + 155','futilityValue = futilityBase + PieceValue[EG][pos.piece_on(to_sq(move))]'], 'thread.cpp':['counterMoves.fill(MOVE_NONE)','mainHistory.fill(0)','captureHistory.fill(0)','main()->bestPreviousScore = VALUE_INFINITE'], 'types.h':['PawnValueMg   = 126','KnightValueMg = 781','BishopValueMg = 825','RookValueMg   = 1276','QueenValueMg  = 2538']}
old=json.loads((R/'results/dev_aux/task091/declaration.json').read_bytes());bindings={}
for name,p in files.items():
 raw=p.read_bytes();text=raw.decode('utf-8');sha=hashlib.sha256(raw).hexdigest()
 if name in old['files']:assert sha==old['files'][name]
 loc={}
 for needle in needles[name]:
  hits=[i+1 for i,line in enumerate(text.splitlines()) if needle in line];assert hits,(name,needle);loc[needle]=hits
 bindings[name]=dict(sha256=sha,url=f'https://github.com/fairy-stockfish/Fairy-Stockfish/blob/{PIN}/src/{name}',source_note='evaluate.cpp includes retainedTask091patch; other retainedfiles matchdeclaredhash where available',witness_lines=loc)
s=importlib.util.spec_from_file_location('e132',R/'results/dev_aux/task108/evolution.py');E=importlib.util.module_from_spec(s);s.loader.exec_module(E);ref=dict(N=3,B=3,R=5,Q=9);steps=[(E.HIGH-E.LOW)/2**(i+1) for i in range(6)];started=time.monotonic();bounds=[]
for seed in (103,104,105):
 initial=E.starts(seed);mins={}
 for k in range(4):
  best=float('inf')
  for path in itertools.product((0,1,2),repeat=6):
   assert time.monotonic()-started<10
   theta=initial[k]
   for choice,step in zip(path,steps):
    if choice:theta=max(E.LOW,min(E.HIGH,theta+(1 if choice==1 else -1)*step))
   price=round(208*math.exp(theta));best=min(best,abs(math.log(price/208/ref[E.TYPES[k]])))
  mins[E.TYPES[k]]=best
 bounds.append(dict(seed=seed,per_coordinate_min_distance=mins,best_attainable_mean_log_distance=statistics.mean(mins.values()),no_best_price_vectors_exported=True))
out=dict(complete=True,source_pin=PIN,source_bindings=bindings,standard_search_prices_MG=dict(P=126,N=781,B=825,R=1276,Q=2538),standard_search_prices_EG=dict(P=208,N=854,B=915,R=1380,Q=2682),candidate_leaf='EvalPieceValueMGcustomPNBRQlinearcounts; kingexcluded; side-to-move sign; TBclamp',remaining_priors='StandardPieceValue remains in SEE/movepick/nonpawnmaterial/qfutility, plus fixedcentipawn pruning margins. CapturePieceValue is separately overridden; not all capture logic uses the same table.',scope_limit='This explains a possible alignment issue, not an executed prior-ablation cause of learning failure. Binaryprovenance remains retainedbuildrecord+hash+actualprobes, not independentsource-to-binaryattestation.',coordinate_reachability=bounds,reachability_scope='Exactindependentcoordinate paths3^6each over6sweeps. Assumes all choices reachable under any reward; bound only, no convergence/feedbackproof, no humanfit or deployment.',coordinate_bound_seconds=time.monotonic()-started)
(O/'audit.json').write_text(json.dumps(out,indent=2),encoding='utf-8');print(json.dumps({'complete':True,'source_files':len(bindings),'coordinate_reachability':bounds,'seconds':out['coordinate_bound_seconds']},indent=2))