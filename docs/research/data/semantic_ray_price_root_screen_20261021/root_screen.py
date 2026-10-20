"""Fixed-root first-action sensitivity of static-v2 board prices on imported semantic rays."""
from __future__ import annotations
import json, random, sys
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT))
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/"semantic_generator_template_preflight_20261021"))
from ray_spread_setup import eligible_pairs, exposure_with_check, layout_for_seed
from generic_chess.ai.alphabeta import AlphaBetaPlayer, SearchTuning
from generic_chess.ai.evaluation import EvaluationConfig, Evaluator
from generic_chess.ai.evaluation.profile import build_ruleset_profile
from generic_chess.ai.limits import SearchLimits
from generic_chess.core.pieces import Piece
from generic_chess.generation.config import GeneratorConfig
from generic_chess.generation.generator import generate_game
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.schema import RuleActionEffect, RuleGeometrySpec, RuleInvariant, RuleSemanticAction, RuleSquareRef
from generic_chess.session.session import GameSession

SEEDS=tuple(range(202610501,202610509))
def run(seed):
    base=generate_game(GeneratorConfig(seed=seed,board_size=6,setup_preset="classic_like"))
    layout=layout_for_seed(base,seed)
    if layout.get("ruleset") is None:
        return {"seed":seed,"status":"layout_failure","rejections":layout.get("rejections")}
    rows=exposure_with_check(layout["ruleset"],eligible_pairs(base))
    exposed=[r for r in rows if r["type_present"] and r["matching_ray_action_count"]>0]
    if not exposed:
        return {"seed":seed,"status":"no_exposed_pair","layout_attempt":layout["attempt"],"opening_action_count":layout["opening_count"]}
    pair=random.Random(seed ^ 0x7A91).choice(exposed)
    type_id=pair["type_id"]; direction=tuple(pair["direction"])
    name=f"ray_price_root_screen_{seed}"
    action=RuleSemanticAction(name=name,type_ids=(type_id,),
        geometry=RuleGeometrySpec(kind="ray",direction=direction,min_steps=1,max_steps=3),
        target_relation="empty",composition="augment",
        effects=(RuleActionEffect("move",from_ref=RuleSquareRef("source"),to_ref=RuleSquareRef("target")),),
        invariants=(RuleInvariant("own_anchor_safe"),))
    ruleset=replace(layout["ruleset"],semantic_actions=(action,))
    compiled=compile_ruleset_for_execution(ruleset)
    cfg=EvaluationConfig()
    static=build_ruleset_profile(compiled,cfg)
    unit_board={pt.type_id:(0 if pt.is_anchor else 1000) for pt in compiled.piece_types}
    unit_hand={pt.type_id:(0 if pt.is_anchor else 900) for pt in compiled.piece_types}
    zero={pt.type_id:0 for pt in compiled.piece_types}
    control=replace(static,board_value_by_type=unit_board,hand_value_by_base_type=unit_hand,promotion_gain_by_type=zero)
    candidate=replace(static,hand_value_by_base_type=unit_hand,promotion_gain_by_type=zero)
    session=GameSession(compiled); before=session.to_record()
    legal=session.legal_actions()
    pattern=next(p.pattern_id for p in compiled.ir.patterns if p.pattern_id.endswith(name))
    ray_count=sum(a.pattern_id==pattern for a in legal)
    if ray_count<=0:
        return {"seed":seed,"status":"selected_pair_lost_exposure","pair":pair,"opening_action_count":len(legal)}
    limits=SearchLimits(max_depth=1,max_nodes=10000,quiescence_max_depth=0,quiescence_hard_max_depth=0,quiescence_max_nodes=0)
    results={}
    for label,profile in (("unit",control),("static_v2_board",candidate)):
        player=AlphaBetaPlayer(compiled,use_disk_cache=False,use_tt=False,use_ordering=False,
            use_native_semantic_legality=False,tuning=SearchTuning(use_root_tactical=False),
            evaluator_override=Evaluator(compiled,profile,cfg))
        d=player.choose_action(session,limits)
        results[label]={"action":None if d.action is None else str(d.action),"legal":d.action in legal,
            "score":d.score,"completed_depth":d.completed_depth,"nodes":d.nodes,"qnodes":d.qnodes,
            "termination_reason":d.termination_reason}
    if session.to_record()!=before: raise AssertionError("search mutated caller session")
    if not all(x["legal"] and x["completed_depth"]==1 and x["qnodes"]==0 for x in results.values()):
        raise AssertionError("paired search did not complete a legal D1/q0 result")
    return {"seed":seed,"status":"measured","layout_attempt":layout["attempt"],
        "type_id":type_id,"direction":list(direction),"root_legal_actions":len(legal),
        "root_ray_actions":ray_count,"price_delta":static.board_value_by_type[type_id]-unit_board[type_id],
        "unit":results["unit"],"static_v2_board":results["static_v2_board"],
        "action_changed":results["unit"]["action"]!=results["static_v2_board"]["action"],
        "caller_state_unchanged":True}
def main():
    roots=[run(seed) for seed in SEEDS]
    measured=[r for r in roots if r["status"]=="measured"]
    out={"observed_at":datetime.now(timezone.utc).isoformat(),"question":"Does static-v2 board price change a depth-1 root choice on fixed imported semantic-ray rules?",
      "seeds":list(SEEDS),"roots":roots,
      "summary":{"accepted":len(measured),"layout_or_exposure_failures":len(roots)-len(measured),
        "action_changed":sum(r["action_changed"] for r in measured),
        "candidate_actions_legal":all(r["unit"]["legal"] and r["static_v2_board"]["legal"] for r in measured),
        "games":0,"training_updates":0},
      "limitations":["synthetic three-rank fixtures","root D1/q0 only","action sensitivity is not utility","no generator/default claim"]}
    print(json.dumps(out,indent=2,sort_keys=True))
if __name__=="__main__": main()
