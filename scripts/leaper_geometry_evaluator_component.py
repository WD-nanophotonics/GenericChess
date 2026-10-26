"""Actual DEFAULT static evaluation of retained D4 inputs, no Player.

The static material/dynamic terms and cold ordering are distinct consumers.
No external/disk profile cache and no WDL labels are used.
"""
from dataclasses import asdict
from pathlib import Path
from datetime import datetime,timezone
import argparse,hashlib,json,time

from generic_chess.rules.schema import ruleset_from_dict
from generic_chess.rules.compiler import compile_legacy_ruleset_for_semantic_execution
from generic_chess.session.session import GameSession
from generic_chess.core.transition import legal_successors
from generic_chess.ai.evaluation.config import EvaluationConfig
from generic_chess.ai.evaluation.profile import build_ruleset_profile
from generic_chess.ai.evaluation.evaluator import Evaluator
from scripts.research_record import record_value
from scripts.leaper_geometry_order_consumer import projection
from tools.local_agent.common import write_json


def run(input_file,output):
    if output.exists():raise ValueError("no replacement/refill")
    data=json.loads(input_file.read_text());rows=[];cfg=EvaluationConfig()
    tick=time.perf_counter()
    for i,row in enumerate(data["rows"]):
        rr=ruleset_from_dict(row["ruleset"])
        compiled=compile_legacy_ruleset_for_semantic_execution(rr)
        ss=GameSession(compiled)
        # Direct builder: no disk cache; current config is recorded verbatim.
        profile=build_ruleset_profile(compiled,cfg);ev=Evaluator(compiled,profile,cfg)
        out={"matrix":row["matrix"],"record":record_value(ss.to_record()),
             "static_score_stm":ev.evaluate(ss.state),
             "board_values":dict(profile.board_value_by_type),"children":[]}
        if i==0:
            for action,child in legal_successors(ss.state,compiled):
                val=ev.evaluate(child)
                out["children"].append({"action":record_value(action),
                    "physical_action":projection(action),"child":record_value(child),
                    "score_child_stm":val,"score_parent_mover":-val})
        rows.append(out)
        if time.perf_counter()-tick>120:raise RuntimeError("frozen120s component cap; no refill")
    result={"at":datetime.now(timezone.utc).isoformat(),"rows":rows,
            "config":asdict(cfg),"root_evaluations":len(rows),
            "child_evaluations":sum(len(r["children"]) for r in rows),
            "root_scores_identical":len({r["static_score_stm"] for r in rows})==1,
            "source_sha256":hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            "input_sha256":hashlib.sha256(input_file.read_bytes()).hexdigest(),
            "claim":"staticcomponent control only, not Player/finalaction/WDL/strength; no disk cache",
            "Player":0,"solver":0,"games":0}
    write_json(output,result)
    print(json.dumps({"roots":result["root_evaluations"],"children":result["child_evaluations"],
                      "root_scores":[r["static_score_stm"] for r in rows],
                      "base_children":[(r["physical_action"],r["score_parent_mover"]) for r in rows[0]["children"]]}))
    return result


if __name__=="__main__":
    p=argparse.ArgumentParser(__doc__);p.add_argument("--input",type=Path,required=True)
    p.add_argument("--output",type=Path,required=True);a=p.parse_args();run(a.input,a.output)
