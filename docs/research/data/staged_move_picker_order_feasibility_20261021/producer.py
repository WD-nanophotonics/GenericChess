"""Outcome-free, full-history StagedMovePicker price feasibility probe."""
from __future__ import annotations
import hashlib, json, random, subprocess, sys, time
from pathlib import Path
ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
from generic_chess.ai.alphabeta import search as search_module
from generic_chess.ai.alphabeta.player import AlphaBetaPlayer
from generic_chess.ai.alphabeta.tuning import SearchTuning
from generic_chess.ai.evaluation.config import EvaluationConfig
from generic_chess.ai.evaluation.evaluator import Evaluator
from generic_chess.ai.evaluation.profile import build_ruleset_profile
from generic_chess.ai.limits import SearchLimits
from generic_chess.core.actions import action_to_dict, action_promotion_target_id
from generic_chess.generation.config import GeneratorConfig
from generic_chess.generation.generator import generate_game
from generic_chess.rules.compiler import compile_legacy_ruleset_for_semantic_execution
from generic_chess.rules.serialization import ruleset_to_dict
from generic_chess.session.session import GameSession
from scripts.research_record import record_value

HERE = Path(__file__).resolve().parent
PLAN_PATH = HERE / "plan.json"
OUT_PATH = HERE / "preflight.json"
PLAN = json.loads(PLAN_PATH.read_text(encoding="utf-8"))
START = time.monotonic()
UNIT_EVAL_CALLS = 0

def sha(v):
    return hashlib.sha256(json.dumps(record_value(v),sort_keys=True,separators=(",",":")).encode()).hexdigest()

def write(path, value):
    tmp=path.with_suffix(path.suffix+".tmp")
    tmp.write_text(json.dumps(value,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    tmp.replace(path)

def limits():
    s=PLAN["settings"]["limits"]
    return SearchLimits(max_depth=s["max_depth"],max_nodes=s["max_nodes"],max_time_seconds=s["max_time_seconds"],quiescence_max_depth=s["quiescence_max_depth"],quiescence_hard_max_depth=s["quiescence_hard_max_depth"],quiescence_max_nodes=s["quiescence_max_nodes"])

class OrderEvaluator:
    def __init__(self, compiled, profile, kind):
        self.compiled=compiled
        self.delegate=Evaluator(compiled,profile,EvaluationConfig())
        self.kind=kind
        self.eval_calls=0
        self.capture_trace=[]
        self.type_trace=[]
    def evaluate(self,state):
        self.eval_calls+=1
        score=0
        for piece in state.position.board:
            if piece is not None and not self.compiled.types_by_id[piece.current_type_id].is_anchor:
                score += 100 if piece.owner==0 else -100
        for owner,hand in enumerate(state.position.hands):
            sign=100 if owner==0 else -100
            for type_id,count in hand.counts:
                if not self.compiled.types_by_id[type_id].is_anchor:
                    score += sign*count
        return score if state.position.side_to_move==0 else -score
    def capture_order_value(self,moving,captured):
        if self.kind=="static_v2": value=self.delegate.capture_order_value(moving,captured)
        else:
            mv=0 if self.compiled.types_by_id[moving.current_type_id].is_anchor else 100
            cv=0 if self.compiled.types_by_id[captured.current_type_id].is_anchor else 100
            value=cv*10-mv//10
        self.capture_trace.append({"moving":moving.current_type_id,"captured":captured.current_type_id,"value":value})
        return value
    def type_value(self,type_id):
        value=(self.delegate.type_value(type_id) if self.kind=="static_v2" else
               0 if self.compiled.types_by_id[type_id].is_anchor else 100)
        self.type_trace.append({"type_id":type_id,"value":value})
        return value

def make_player(compiled,profile,kind):
    ev=OrderEvaluator(compiled,profile,kind)
    tuning=SearchTuning(use_staged_move_picker=True,use_ordered_qsearch=False)
    return AlphaBetaPlayer(compiled,evaluator_override=ev,use_tt=False,use_ordering=True,use_native_semantic_legality=True,tuning=tuning),ev

def generate(seed,index):
    r=PLAN["rules"]
    g=generate_game(GeneratorConfig(seed=seed,board_size=r["board_size"],setup_preset=r["setup_schedule"][index%len(r["setup_schedule"])],movement_symmetry=r["symmetry_schedule"][index%len(r["symmetry_schedule"])],allow_hybrid=r["allow_hybrid"],require_promotable_type=r["require_promotable_type"],require_nonpromotable_type=r["require_nonpromotable_type"],max_generation_attempts=r["max_generation_attempts"],require_no_opening_win_in_one=False))
    c=compile_legacy_ruleset_for_semantic_execution(g.ruleset)
    return g,c,build_ruleset_profile(c,EvaluationConfig())

def snapshot(session):
    return {"state":sha(session.state),"history":record_value(session.history),"result":record_value(session.result),"witnesses":record_value(session._search_witnesses)}

def run_one(session,compiled,profile,kind):
    global UNIT_EVAL_CALLS
    before=snapshot(session)
    player,evaluator=make_player(compiled,profile,kind)
    target=sha(session.state)
    root_orders=[]
    original=search_module.StagedMovePicker
    def tracked(*args,**kwargs):
        picker=original(*args,**kwargs)
        # run_root_search's first StagedMovePicker invocation is the root:
        # iterative deepening enters negamax(root, depth) before descending.
        # SearchPathRuntime views intentionally contain a non-serializable
        # runtime object, so identify root by source-defined call order.
        if root_orders: return picker
        order=[]
        root_orders.append(order)
        def values():
            for action in picker:
                order.append(action_to_dict(action))
                yield action
        return values()
    search_module.StagedMovePicker=tracked
    try:
        decision=player.choose_action(session,limits())
    finally:
        search_module.StagedMovePicker=original
    after=snapshot(session)
    if before!=after: raise RuntimeError("SEARCH_MUTATED_COMPLETE_SESSION")
    legal=decision.action is not None and decision.action in session.legal_actions()
    return {"kind":kind,"root_state_sha256":target,"action":None if decision.action is None else action_to_dict(decision.action),"action_legal":legal,"score":decision.score,"result_source":decision.result_source,"termination_reason":decision.termination_reason,"completed_depth":decision.completed_depth,"nodes":decision.nodes,"qnodes":decision.qnodes,"evaluation_calls":decision.evaluation_calls,"unit_evaluation_calls":evaluator.eval_calls,"evaluation_count_matches":decision.evaluation_calls==evaluator.eval_calls,"root_order_calls":len(root_orders),"first_root_order":root_orders[0] if root_orders else [],"root_orders":root_orders,"capture_trace":evaluator.capture_trace,"type_trace":evaluator.type_trace,"session_unchanged":True}

def preflight():
    if Path.cwd().resolve()!=ROOT: raise RuntimeError(f"RUN_FROM_REPOSITORY_ROOT:{ROOT}")
    if OUT_PATH.exists(): raise RuntimeError("PREFLIGHT_EXISTS_NO_OVERWRITE")
    head=subprocess.check_output(["git","rev-parse","HEAD"],cwd=ROOT,text=True).strip()
    producer_sha=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    plan_sha=hashlib.sha256(PLAN_PATH.read_bytes()).hexdigest()
    if head!=PLAN["source_head"]: raise RuntimeError(f"SOURCE_HEAD_MISMATCH:{head}")
    if producer_sha!=PLAN["producer_sha256"]: raise RuntimeError("PRODUCER_HASH_MISMATCH")
    roots=[]; exposures=[]
    for si,seed in enumerate(PLAN["rules"]["seeds"]):
        if time.monotonic()-START>=600: raise TimeoutError("PREFLIGHT_600S_CAP")
        generated,compiled,profile=generate(seed,si)
        for family,plies in enumerate(PLAN["roots"]["prefix_plies"]):
            seed_open=seed*1_000_000+family
            base=GameSession(compiled); rng=random.Random(seed_open)
            for _ in range(plies):
                if base.result.status.value!="ongoing": break
                actions=sorted(base.legal_actions(),key=lambda a:json.dumps(action_to_dict(a),sort_keys=True))
                if not actions: raise RuntimeError("ONGOING_WITHOUT_LEGAL_ACTION_IN_PREFIX")
                base.submit(actions[rng.randrange(len(actions))])
            prefix_actions=[record_value(x.action) for x in base.history]
            root_id=f"{seed}-{family}"
            roots.append({"root_id":root_id,"seed":seed,"family":family,"requested_prefix_plies":plies,"actual_prefix_plies":len(base.history),"root_digest":sha(base.state),"opening":prefix_actions,"ruleset_fingerprint":compiled.ruleset_fingerprint,"ruleset":ruleset_to_dict(generated.ruleset)})
            for owner in PLAN["roots"]["candidate_owners"]:
                session=GameSession.replay(compiled,base.to_record())
                prep=None
                if session.state.position.side_to_move!=owner and session.result.status.value=="ongoing":
                    foe,_=make_player(compiled,profile,"unit")
                    d=foe.choose_action(session,limits())
                    if d.action is not None and d.action in session.legal_actions():
                        prep=action_to_dict(d.action); session.submit(d.action)
                    elif d.declaration is not None:
                        session.declare(d.declaration.declaration_id)
                context={"root_id":root_id,"owner":owner,"preparation_action":prep,"history_length":len(session.history),"state_sha256":sha(session.state),"history_sha256":sha(session.history),"status":session.result.status.value}
                arms={}
                if session.result.status.value=="ongoing" and session.state.position.side_to_move==owner:
                    for kind in PLAN["arms"]:
                        clone=GameSession.replay(compiled,session.to_record())
                        arms[kind]=run_one(clone,compiled,profile,kind)
                exposures.append({**context,"arms":arms,"candidate_search_pair":len(arms)==2,"outcome_submitted":False})
    pairs=[x for x in exposures if x["candidate_search_pair"]]
    changed=[]
    for x in pairs:
        u=x["arms"]["unit_order"]; s=x["arms"]["static_v2_order"]
        cap_u={(a["moving"],a["captured"]):a["value"] for a in u["capture_trace"]}
        cap_s={(a["moving"],a["captured"]):a["value"] for a in s["capture_trace"]}
        typ_u={a["type_id"]:a["value"] for a in u["type_trace"]}; typ_s={a["type_id"]:a["value"] for a in s["type_trace"]}
        value_diff=any(cap_u.get(k)!=cap_s.get(k) for k in cap_u.keys()|cap_s.keys()) or any(typ_u.get(k)!=typ_s.get(k) for k in typ_u.keys()|typ_s.keys())
        order_diff=u["first_root_order"]!=s["first_root_order"]
        action_diff=u["action"]!=s["action"]
        x["price_values_differ"]=value_diff; x["root_order_differs"]=order_diff; x["candidate_action_differs"]=action_diff
        if value_diff and order_diff and action_diff: changed.append(x["root_id"]+f"-o{x['owner']}")
    result={"schema":"primary-staged-order-feasibility-v1","status":"NO_OUTCOME_PREFLIGHT","source_head":head,"plan_sha256":plan_sha,"producer_sha256":producer_sha,"source_sha256":hashlib.sha256((ROOT/"generic_chess/ai/alphabeta/search.py").read_bytes()).hexdigest(),"outcomes_collected":0,"candidate_actions_submitted_after_search":0,"roots_count":len(roots),"contexts_count":len(exposures),"paired_candidate_searches":len(pairs),"roots":roots,"exposures":exposures,"changed_action_contexts":changed,"preflight_gate":{"minimum_distinct_contexts":PLAN["preflight_gate"]["minimum_distinct_contexts"],"qualified_contexts":len(changed),"passed":len(changed)>=PLAN["preflight_gate"]["minimum_distinct_contexts"]}}
    write(OUT_PATH,result)
    print(json.dumps({k:result[k] for k in ("status","outcomes_collected","candidate_actions_submitted_after_search","roots_count","contexts_count","paired_candidate_searches","changed_action_contexts","preflight_gate")},sort_keys=True))

if __name__=="__main__": preflight()
