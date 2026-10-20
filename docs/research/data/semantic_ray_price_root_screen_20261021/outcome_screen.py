"""Bounded paired-colour utility screen for semantic-ray static board prices."""
from __future__ import annotations
import hashlib, json, random, sys
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))
sys.path.insert(0,str(HERE.parent/"semantic_generator_template_preflight_20261021"))
from ray_spread_setup import eligible_pairs, exposure_with_check, layout_for_seed
from generic_chess.ai.alphabeta import AlphaBetaPlayer, SearchTuning
from generic_chess.ai.evaluation import EvaluationConfig, Evaluator
from generic_chess.ai.evaluation.profile import build_ruleset_profile
from generic_chess.ai.limits import SearchLimits
from generic_chess.generation.config import GeneratorConfig
from generic_chess.generation.generator import generate_game
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.schema import RuleActionEffect, RuleGeometrySpec, RuleInvariant, RuleSemanticAction, RuleSquareRef
from generic_chess.session.result import SessionStatus
from generic_chess.session.session import GameSession
from generic_chess.ai.benchmark.runner import _adjudicate
SEEDS=tuple(range(202610501,202610509)); MAX_PLIES=48
LIMITS=SearchLimits(max_depth=2,max_nodes=20000,max_time_seconds=None,quiescence_max_depth=0,quiescence_hard_max_depth=0,quiescence_max_nodes=0)
TUNING=SearchTuning(use_root_tactical=False)
def make_rules(seed):
    base=generate_game(GeneratorConfig(seed=seed,board_size=6,setup_preset="classic_like"))
    layout=layout_for_seed(base,seed)
    if layout.get("ruleset") is None: return None,{"seed":seed,"status":"layout_failure","rejections":layout.get("rejections")}
    exposed=[r for r in exposure_with_check(layout["ruleset"],eligible_pairs(base)) if r["type_present"] and r["matching_ray_action_count"]>0]
    if not exposed: return None,{"seed":seed,"status":"no_exposed_pair"}
    pair=random.Random(seed ^ 0x7A91).choice(exposed); name=f"ray_price_root_screen_{seed}"
    action=RuleSemanticAction(name=name,type_ids=(pair["type_id"],),geometry=RuleGeometrySpec(kind="ray",direction=tuple(pair["direction"]),min_steps=1,max_steps=3),target_relation="empty",composition="augment",effects=(RuleActionEffect("move",from_ref=RuleSquareRef("source"),to_ref=RuleSquareRef("target")),),invariants=(RuleInvariant("own_anchor_safe"),))
    ruleset=replace(layout["ruleset"],semantic_actions=(action,))
    compiled=compile_ruleset_for_execution(ruleset); legal=GameSession(compiled).legal_actions()
    pattern=next(p.pattern_id for p in compiled.ir.patterns if p.pattern_id.endswith(name))
    ray_count=sum(a.pattern_id==pattern for a in legal)
    if not ray_count: return None,{"seed":seed,"status":"lost_exposure","root_legal_actions":len(legal)}
    cfg=EvaluationConfig(); static=build_ruleset_profile(compiled,cfg)
    board={p.type_id:(0 if p.is_anchor else 1000) for p in compiled.piece_types}
    hand={p.type_id:(0 if p.is_anchor else 900) for p in compiled.piece_types}
    zero={p.type_id:0 for p in compiled.piece_types}
    unit=replace(static,board_value_by_type=board,hand_value_by_base_type=hand,promotion_gain_by_type=zero)
    candidate=replace(static,hand_value_by_base_type=hand,promotion_gain_by_type=zero)
    digest=compiled.ruleset_fingerprint
    meta={"seed":seed,"status":"ready","ruleset_sha256":digest,"type_id":pair["type_id"],"direction":list(pair["direction"]),"root_legal_actions":len(legal),"root_ray_actions":ray_count,"static_minus_unit_board_value":static.board_value_by_type[pair["type_id"]]-board[pair["type_id"]]}
    return (compiled,cfg,candidate,unit,meta),None
def play(compiled,cfg,candidate_profile,unit_profile,seed,candidate_color):
    session=GameSession(compiled); players={}
    for color,profile,label in ((candidate_color,candidate_profile,"candidate"),(1-candidate_color,unit_profile,"unit_opponent")):
        players[color]=(label,AlphaBetaPlayer(compiled,evaluation_config=cfg,use_disk_cache=False,use_tt=False,use_ordering=False,use_native_semantic_legality=False,tuning=TUNING,evaluator_override=Evaluator(compiled,profile,cfg)))
    events=[]; censor=None
    while session.result.status is SessionStatus.ONGOING and session.state.ply_count<MAX_PLIES:
        side=session.state.position.side_to_move; label,player=players[side]; d=player.choose_action(session,LIMITS)
        e={"ply":session.state.ply_count,"side":side,"actor":label,"action":None if d.action is None else str(d.action),"choice_kind":d.choice_kind,"result_source":d.result_source,"completed_depth":d.completed_depth,"nodes":d.nodes,"qnodes":d.qnodes,"termination_reason":d.termination_reason}; events.append(e)
        if d.completed_depth!=2: censor={"status":"unknown","reason":"incomplete_depth","event":e}; break
        if d.action is None or d.result_source in {"fallback","legal_fallback","root_scan_fallback"}: censor={"status":"failed","reason":"fallback_or_no_action","event":e}; break
        try: session.submit(d.action)
        except ValueError as exc: censor={"status":"failed","reason":"illegal_action","detail":str(exc),"event":e}; break
    if censor: result=censor["status"]
    elif session.state.ply_count>=MAX_PLIES and session.result.status is SessionStatus.ONGOING: result="unknown"; censor={"status":"unknown","reason":"ply_cap"}
    else:
        result=_adjudicate(session,candidate_color)
        if result=="unresolved": result="unknown"; censor={"status":"unknown","reason":"unresolved_rule_terminal"}
    return {"seed":seed,"candidate_color":candidate_color,"result":result,"plies":session.state.ply_count,"terminal_status":session.result.status.name,"winner":session.result.winner,"censor_or_failure":censor,"events":events,"candidate_nodes":sum(e["nodes"]+e["qnodes"] for e in events if e["actor"]=="candidate"),"unit_opponent_nodes":sum(e["nodes"]+e["qnodes"] for e in events if e["actor"]=="unit_opponent")}
def main():
    games=[]; rules={}
    for seed in SEEDS:
        made,failure=make_rules(seed)
        if failure: games.append(failure); continue
        compiled,cfg,candidate,unit,meta=made; rules[str(seed)]=meta
        for color in (0,1):
            game=play(compiled,cfg,candidate,unit,seed,color); game["game_key"]=f"{seed}-c{color}"; games.append(game)
    resolved=[g for g in games if g["result"] in {"candidate_win","candidate_loss","rule_draw"}]
    pts=sum(1 if g["result"]=="candidate_win" else .5 if g["result"]=="rule_draw" else 0 for g in resolved)
    by_color={str(c):{"resolved":sum(g["candidate_color"]==c for g in resolved),"wins":sum(g["candidate_color"]==c and g["result"]=="candidate_win" for g in resolved),"losses":sum(g["candidate_color"]==c and g["result"]=="candidate_loss" for g in resolved),"draws":sum(g["candidate_color"]==c and g["result"]=="rule_draw" for g in resolved)} for c in (0,1)}
    by_seed={str(s):[g["result"] for g in sorted(resolved,key=lambda g:g["candidate_color"]) if g["seed"]==s] for s in SEEDS}
    cn=[e["nodes"]+e["qnodes"] for g in games for e in g.get("events",[]) if e["actor"]=="candidate"]
    un=[e["nodes"]+e["qnodes"] for g in games for e in g.get("events",[]) if e["actor"]=="unit_opponent"]
    median=lambda x: sorted(x)[len(x)//2] if x else None
    score=pts/len(resolved) if resolved else None
    follow=len(games)==16 and len(resolved)==16 and not any(g["result"]=="failed" for g in games) and score is not None and score>.5 and all(v!=["candidate_loss","candidate_loss"] for v in by_seed.values()) and median(cn)<=median(un)
    out={"schema_version":1,"observed_at":datetime.now(timezone.utc).isoformat(),"rulesets":rules,"games":games,"summary":{"planned_games":16,"accepted_rulesets":len(rules),"resolved_games":len(resolved),"unknown_games":sum(g["result"]=="unknown" for g in games),"failed_games":sum(g["result"]=="failed" for g in games),"candidate_wins":sum(g["result"]=="candidate_win" for g in resolved),"candidate_losses":sum(g["result"]=="candidate_loss" for g in resolved),"rule_draws":sum(g["result"]=="rule_draw" for g in resolved),"candidate_score":score,"by_candidate_color":by_color,"paired_ruleset_outcomes":by_seed,"candidate_move_nodes":{"count":len(cn),"median":median(cn),"total":sum(cn)},"unit_opponent_move_nodes":{"count":len(un),"median":median(un),"total":sum(un)},"followup_gate":follow,"games_with_results":len(games)},"search":{"max_depth":2,"max_nodes_per_move":20000,"qdepth":0,"tt":False,"ordering":False,"root_tactical":False,"max_plies":MAX_PLIES},"limitations":["fixed synthetic cohort only","small exploratory n=8 rules / 16 color-paired games","candidate-vs-fixed Unit outcomes do not estimate population strength","UNKNOWN and failures retained; no resampling/default change","uniform D2 setup is not an equal-cost utility proof"]}
    print(json.dumps(out,indent=2,sort_keys=True))
if __name__=="__main__": main()
