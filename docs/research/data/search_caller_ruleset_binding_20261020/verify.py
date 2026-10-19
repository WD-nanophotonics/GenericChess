from __future__ import annotations
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[4]
sys.path.insert(0,str(ROOT))
from generic_chess.ai.alphabeta.player import AlphaBetaPlayer
from generic_chess.ai.limits import SearchLimits
from generic_chess.core.errors import RuleSetMismatchError
from generic_chess.generation.config import GeneratorConfig
from generic_chess.generation.generator import generate_game
from generic_chess.rules.compiler import compile_legacy_ruleset_for_semantic_execution
from generic_chess.session.session import GameSession
from scripts.research_record import write_record
def main():
    configs=[GeneratorConfig(seed=s,board_size=5,setup_preset="bilateral_random",allow_hybrid=True) for s in (20261020,20261021)]
    compiled=[compile_legacy_ruleset_for_semantic_execution(generate_game(c).ruleset) for c in configs]
    assert compiled[0].ruleset_fingerprint != compiled[1].ruleset_fingerprint
    player=AlphaBetaPlayer(compiled[0],use_disk_cache=False,use_native_semantic_legality=False)
    session=GameSession(compiled[1])
    outcome="UNEXPECTED_ACCEPT"
    error=None
    exception=None
    try:
        player.choose_action(session,SearchLimits(max_depth=1,max_nodes=256,quiescence_max_depth=0))
    except RuleSetMismatchError as exc:
        outcome="EXPECTED_RULESET_MISMATCH"
        error=str(exc)
        exception=type(exc).__name__
    result={"schema":"primary-alphabeta-public-ruleset-binding-v1","rule_seeds":[20261020,20261021],"board_size":5,"mode":"ongoing session; Core legality path; D1/node256 cap (search must reject before entering search)","fingerprints":[c.ruleset_fingerprint for c in compiled],"fingerprints_distinct":True,"outcome":outcome,"exception":exception,"message":error,"search_started":False if outcome=="EXPECTED_RULESET_MISMATCH" else None,"status":"COMPLETE" if outcome=="EXPECTED_RULESET_MISMATCH" else "FAIL"}
    write_record(Path(__file__).with_name("result.json"),result)
    print(json.dumps(result,separators=(",",":")))
    if result["status"]!="COMPLETE":raise SystemExit(1)
if __name__=="__main__":main()