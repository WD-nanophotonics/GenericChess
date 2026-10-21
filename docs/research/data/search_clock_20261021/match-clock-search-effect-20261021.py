import json, sys, time
from pathlib import Path
sys.path.insert(0, str(Path.cwd() / "tests"))
from ai_fixtures import build_4x4_rooks
from generic_chess.ai.alphabeta.player import AlphaBetaPlayer
from generic_chess.ai.limits import SearchLimits
from generic_chess.ai.alphabeta.tuning import SearchTuning
from generic_chess.core.movegen import legal_actions
from generic_chess.session.session import GameSession
compiled=build_4x4_rooks()
rows=[]
for rep in range(4):
    order=(0.044,0.060) if rep%2==0 else (0.060,0.044)
    for seconds in order:
        session=GameSession(compiled)
        player=AlphaBetaPlayer(compiled,use_disk_cache=False,tt_max_entries=10000,use_tt=False,use_ordering=False,tuning=SearchTuning(use_root_tactical=False))
        start=time.perf_counter()
        d=player.choose_action(session,SearchLimits(max_depth=64,max_time_seconds=seconds,max_nodes=None,quiescence_max_depth=0))
        elapsed=(time.perf_counter()-start)*1000
        rows.append({"rep":rep,"budget_ms":seconds*1000,"elapsed_ms":elapsed,"nodes":d.nodes,"qnodes":d.qnodes,"completed_depth":d.completed_depth,"termination_reason":d.termination_reason,"action":repr(d.action),"legal":d.action in legal_actions(session.state,compiled)})
result={"question":"Does the measured 44ms-vs-60ms UI budget quantization change paid search work on a fixed representative root?","scope":"Four alternating pairs, same 4x4-rooks authored root, cold player each run, no TT/ordering/root tactical/qsearch, QPC deadlines. This isolates budget effect, not strength or generated-domain coverage.","runs":rows}
out=Path('.local_agent/match-clock-search-effect-20261021.json'); out.write_text(json.dumps(result,indent=2),encoding='utf-8'); print(json.dumps(result,indent=2))
