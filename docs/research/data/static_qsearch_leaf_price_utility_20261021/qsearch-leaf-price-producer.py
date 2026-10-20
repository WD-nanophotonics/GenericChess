"""Frozen static-v2 leaf-price utility panel; writes only into a unique ignored run folder."""
from __future__ import annotations
import hashlib, json, random, subprocess, sys, time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
HERE = Path(__file__).resolve().parent
RUN_DIR = HERE / "qsearch-leaf-price-run-20261021"
PLAN_PATH = HERE / "qsearch-leaf-price-plan.json"
PREFLIGHT_PATH = HERE / "qsearch-leaf-price-preflight.json"
sys.path.insert(0, str(ROOT))
from generic_chess.ai.alphabeta.player import AlphaBetaPlayer
from generic_chess.ai.evaluation.config import EvaluationConfig
from generic_chess.ai.evaluation.evaluator import Evaluator
from generic_chess.ai.evaluation.profile import build_ruleset_profile
from generic_chess.ai.alphabeta.tuning import SearchTuning
from generic_chess.ai.limits import SearchLimits
from generic_chess.core.actions import action_to_dict, action_promotion_target_id
from generic_chess.generation.config import GeneratorConfig
from generic_chess.generation.generator import generate_game
from generic_chess.rules.compiler import compile_legacy_ruleset_for_semantic_execution
from generic_chess.rules.serialization import ruleset_to_dict
from generic_chess.session.session import GameSession
from scripts.research_record import record_value

START_MONO = time.monotonic()
START_UTC = datetime.now(timezone.utc)
PLAN = json.loads(PLAN_PATH.read_text(encoding="utf-8"))
PREFLIGHT = json.loads(PREFLIGHT_PATH.read_text(encoding="utf-8")) if PREFLIGHT_PATH.exists() else {}
CAP = int(PLAN["cost"]["hard_cap_seconds"])
EXPECTED_SLOTS = 64
GAMES_PATH = RUN_DIR / "qsearch-leaf-price-games.jsonl"

def utcnow():
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")

def digest(value):
    raw = json.dumps(record_value(value), sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(raw).hexdigest()

def q_state_digest(state):
    runtime=getattr(state,"_runtime",None)
    if runtime is None:
        return digest(state)
    def identity_value(identity):
        position=getattr(identity,"position",None)
        if position is not None:
            return {"position":record_value(position)}
        external=getattr(identity,"external_key",None)
        if external is not None:
            return {"external_key":str(external)}
        return {"identity_repr":repr(identity)}
    history=[]
    for item in runtime._history:
        rh=item.runtime_hash
        history.append({"identity":identity_value(item.identity),"actor":item.actor,"action_signature":item.action_signature,"gave_check":item.gave_check,"runtime_hash":None if rh is None else [rh.lo,rh.hi],"external_key":None if item.external_key is None else str(item.external_key)})
    counts=[{"identity":identity_value(key),"count":count} for key,count in runtime._snapshot.items()]
    no_progress=record_value(runtime._no_progress_context) if runtime._no_progress_context is not None else None
    rh=runtime.runtime_hash
    return digest({"position":record_value(runtime.position),"ply_count":runtime.ply_count,"terminal_status":record_value(runtime.terminal_status),"runtime_hash":[rh.lo,rh.hi],"history":history,"repetition_counts":counts,"no_progress_context":no_progress})

def write_json(path, value):
    path = Path(path)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(record_value(value), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    tmp.replace(path)

def poll():
    if time.monotonic() - START_MONO >= CAP:
        raise TimeoutError("FROZEN_3600S_HARD_CAP")
    for name in ("rollout", "advisor", "slack"):
        state = json.loads((ROOT / ".local_agent" / f"{name}.json").read_text(encoding="utf-8"))
        if state.get("stopped") or state.get("user_paused"):
            raise InterruptedError(f"EXPLICIT_{name.upper()}_STOP")

def gen_opening(compiled, plies, seed):
    session = GameSession(compiled)
    rng = random.Random(seed)
    actions = []
    for _ in range(plies):
        if session.result.status.value != "ongoing":
            break
        legal = sorted(session.legal_actions(), key=lambda a: json.dumps(action_to_dict(a), sort_keys=True))
        if not legal:
            raise RuntimeError("ONGOING_WITHOUT_LEGAL_ACTION_IN_ROOT_PREFIX")
        action = legal[rng.randrange(len(legal))]
        actions.append(action)
        session.submit(action)
    return actions, session

PAIRED_PREFLIGHT = False

class ControlledEvaluator:
    """Unit material for main-search leaves; q-leaf proxy is scoped separately."""
    def __init__(self, compiled, profile, q_kind):
        self._delegate = Evaluator(compiled, profile, EvaluationConfig())
        self._compiled = compiled
        self.main_eval_calls = 0
        self.normal_capture_calls = []
        self.normal_type_ids = []
        self.q_leaf_proxy = QLeafProxy(self, q_kind, PAIRED_PREFLIGHT)
    def _unit_material_score(self, state):
        score = 0
        for piece in state.position.board:
            if piece is not None and not self._compiled.types_by_id[piece.current_type_id].is_anchor:
                score += 100 if piece.owner == 0 else -100
        for owner, hand in enumerate(state.position.hands):
            sign = 100 if owner == 0 else -100
            for type_id, count in hand.counts:
                if not self._compiled.types_by_id[type_id].is_anchor:
                    score += sign * count
        return score if state.position.side_to_move == 0 else -score
    def evaluate(self, state):
        self.main_eval_calls += 1
        return self._unit_material_score(state)
    def _unit_capture_order_value(self, moving, captured):
        moving_value = 0 if self._compiled.types_by_id[moving.current_type_id].is_anchor else 100
        captured_value = 0 if self._compiled.types_by_id[captured.current_type_id].is_anchor else 100
        return captured_value * 10 - moving_value // 10
    def capture_order_value(self, moving, captured):
        value = self._unit_capture_order_value(moving, captured)
        self.normal_capture_calls.append({"moving":moving.current_type_id,"captured":captured.current_type_id,"value":value})
        return value
    def type_value(self, type_id):
        self.normal_type_ids.append(type_id)
        return 0 if self._compiled.types_by_id[type_id].is_anchor else 100

class QLeafProxy:
    """Swap only evaluator.evaluate during qsearch; ordering delegates to Unit."""
    def __init__(self, base, q_kind, paired_values=False):
        self.base=base
        self.q_kind=q_kind
        self.paired_values=paired_values
        self.call_count=0
        self.score_sum=0
        self.score_min=None
        self.score_max=None
        self.trace=[]
    def reset(self):
        self.call_count=0; self.score_sum=0; self.score_min=None; self.score_max=None; self.trace=[]
    def snapshot(self):
        return {"calls":self.call_count,"score_sum":self.score_sum,"score_min":self.score_min,"score_max":self.score_max}
    def evaluate(self,state):
        unit=self.base._unit_material_score(state) if self.paired_values or self.q_kind=="unit_q_leaf" else None
        static=self.base._delegate.evaluate(state) if self.paired_values or self.q_kind=="static_v2_q_leaf" else None
        score=unit if self.q_kind=="unit_q_leaf" else static
        self.call_count+=1; self.score_sum+=score
        self.score_min=score if self.score_min is None else min(self.score_min,score)
        self.score_max=score if self.score_max is None else max(self.score_max,score)
        if self.paired_values:
            self.trace.append({"state_sha256":q_state_digest(state),"unit_score":unit,"static_v2_score":static,"difference":static-unit})
        return score
    def capture_order_value(self,moving,captured):
        return self.base.capture_order_value(moving,captured)
    def type_value(self,type_id):
        return self.base.type_value(type_id)

# Public quiescence entry is the single transition into the recursive runtime
# qsearch. Keep the q-only evaluator installed through that recursion, then
# restore Unit before the caller resumes main search.
from generic_chess.ai.alphabeta import search as search_module
_original_quiescence=search_module.quiescence
def _q_leaf_only_quiescence(state,alpha,beta,ply,qdepth,ctx):
    original=ctx.evaluator
    proxy=getattr(original,"q_leaf_proxy",None)
    if proxy is None:
        return _original_quiescence(state,alpha,beta,ply,qdepth,ctx)
    ctx.evaluator=proxy
    try:
        return _original_quiescence(state,alpha,beta,ply,qdepth,ctx)
    finally:
        ctx.evaluator=original
search_module.quiescence=_q_leaf_only_quiescence

def make_player(compiled, profile, kind):
    evaluator = ControlledEvaluator(compiled, profile, kind)
    player = AlphaBetaPlayer(
        compiled, evaluator_override=evaluator, use_tt=False, use_ordering=True,
        use_native_semantic_legality=True, tuning=SearchTuning(use_ordered_qsearch=False),
    )
    return player, evaluator

def play_one(compiled, profile, opening, variant, owner, root_id, game_id):
    session = GameSession(compiled)
    for action in opening:
        session.submit(action)
    root_sha = digest(session.state)
    initial_result = session.result
    players, evaluators = {}, {}
    for side in (0, 1):
        kind = variant if side == owner else "unit_q_leaf"
        players[side], evaluators[side] = make_player(compiled, profile, kind)
    search = PLAN["search"]
    limits = SearchLimits(
        max_depth=search["max_depth"], max_nodes=search["max_nodes"],
        max_time_seconds=search["max_time_seconds"],
        quiescence_max_depth=search["quiescence_max_depth"],
        quiescence_hard_max_depth=search["quiescence_hard_max_depth"],
        quiescence_max_nodes=search["quiescence_max_nodes"],
    )
    moves = []
    candidate_plies = 0
    reason = "ACTUAL_TERMINAL" if initial_result.status.value != "ongoing" else None
    while session.result.status.value == "ongoing" and candidate_plies < search["max_candidate_plies"]:
        poll()
        side = session.state.position.side_to_move
        role = "candidate" if side == owner else "foe"
        state_before = digest(session.state)
        normal_capture_before = len(evaluators[side].normal_capture_calls)
        normal_type_before = len(evaluators[side].normal_type_ids)
        q_leaf_before = evaluators[side].q_leaf_proxy.snapshot()
        main_eval_before = evaluators[side].main_eval_calls
        decision = players[side].choose_action(session, limits)
        action = decision.action
        legal = action is not None and action in session.legal_actions()
        row = {
            "ply": len(moves), "side": side, "role": role, "state_before": state_before,
            "action": None if action is None else record_value(action),
            "action_valid": legal, "score": decision.score,
            "completed_depth": decision.completed_depth, "selective_depth": decision.selective_depth,
            "nodes": decision.nodes, "qnodes": decision.qnodes,
            "fallback": decision.result_source not in ("main_iteration", "verified_root_child"),
            "result_source": decision.result_source, "termination_reason": decision.termination_reason,
            "elapsed_seconds": decision.elapsed_seconds,
            "normal_capture_order_calls_delta": len(evaluators[side].normal_capture_calls) - normal_capture_before,
            "normal_capture_order_trace": evaluators[side].normal_capture_calls[normal_capture_before:],
            "q_leaf_evaluations_delta": evaluators[side].q_leaf_proxy.call_count - q_leaf_before["calls"],
            "q_leaf_score_sum_delta": evaluators[side].q_leaf_proxy.score_sum - q_leaf_before["score_sum"],
            "q_leaf_score_min": evaluators[side].q_leaf_proxy.score_min,
            "q_leaf_score_max": evaluators[side].q_leaf_proxy.score_max,
            "main_leaf_evaluations_delta": evaluators[side].main_eval_calls - main_eval_before,
            "decision_evaluation_calls": decision.evaluation_calls,
            "normal_type_value_calls_delta": len(evaluators[side].normal_type_ids) - normal_type_before,
            "q_type_value_calls_delta": 0,
        }
        if decision.declaration is not None:
            session.declare(decision.declaration.declaration_id)
        elif legal:
            session.submit(action)
        else:
            reason = "NO_EXECUTABLE_RETURN_UNKNOWN"
            moves.append(row)
            break
        row["state_after"] = digest(session.state)
        moves.append(row)
        if role == "candidate":
            candidate_plies += 1
        if session.result.status.value != "ongoing":
            reason = "ACTUAL_TERMINAL"
    if session.result.status.value == "ongoing" and reason is None:
        reason = "HORIZON_48_CANDIDATE_UNKNOWN"
    replay = GameSession.replay(compiled, session.to_record())
    replay_equal = (
        replay.state == session.state and replay.history == session.history
        and replay._search_witnesses == session._search_witnesses and replay.result == session.result
    )
    if not replay_equal:
        raise RuntimeError(f"FULL_HISTORY_REPLAY_MISMATCH:{game_id}")
    status = session.result.status.value
    winner = session.result.winner
    reward = None if "UNKNOWN" in reason or status == "no_contest" else (
        0 if winner is None else (1 if winner == owner else -1)
    )
    return {
        "game_id": game_id, "root_id": root_id, "variant": variant,
        "candidate_owner": owner, "opening_actions": [record_value(a) for a in opening],
        "root_state_sha256": root_sha, "moves": moves, "move_count": len(moves),
        "terminal_status": status, "terminal_reason": reason,
        "candidate_plies": candidate_plies, "winner": winner, "reward": reward,
        "full_record": json.loads(__import__("generic_chess.session.serialization", fromlist=["serialize_game_record"]).serialize_game_record(session.to_record())),
        "final_state_sha256": digest(session.state), "full_history_replay_equal": replay_equal,
        "queries": len(moves), "nodes": sum(int(m["nodes"]) for m in moves),
        "qnodes": sum(int(m["qnodes"]) for m in moves),
        "caller_seconds": sum(float(m["elapsed_seconds"]) for m in moves),
        "normal_capture_order_calls": sum(int(m["normal_capture_order_calls_delta"]) for m in moves),
        "q_leaf_evaluations": sum(int(m["q_leaf_evaluations_delta"]) for m in moves),
        "normal_type_value_calls": sum(int(m["normal_type_value_calls_delta"]) for m in moves),
        "q_type_value_calls": sum(int(m["q_type_value_calls_delta"]) for m in moves),
        "action_invalid_count": sum(not m["action_valid"] for m in moves if m["action"] is not None),
    }

def run_limits():
    s=PLAN["search"]
    return SearchLimits(max_depth=s["max_depth"],max_nodes=s["max_nodes"],max_time_seconds=s["max_time_seconds"],quiescence_max_depth=s["quiescence_max_depth"],quiescence_hard_max_depth=s["quiescence_hard_max_depth"],quiescence_max_nodes=s["quiescence_max_nodes"])

def generate_rule(seed,index):
    setup=PLAN["rules"]["setup_schedule"]; symmetry=PLAN["rules"]["symmetry_schedule"]
    generated=generate_game(GeneratorConfig(seed=seed,board_size=PLAN["rules"]["board_size"],setup_preset=setup[index%len(setup)],movement_symmetry=symmetry[index%len(symmetry)],allow_hybrid=PLAN["rules"]["allow_hybrid"],require_promotable_type=PLAN["rules"]["require_promotable_type"],require_nonpromotable_type=PLAN["rules"]["require_nonpromotable_type"],max_generation_attempts=PLAN["rules"]["max_generation_attempts"],require_no_opening_win_in_one=False))
    compiled=compile_legacy_ruleset_for_semantic_execution(generated.ruleset)
    return generated,compiled,build_ruleset_profile(compiled,EvaluationConfig())

def preflight():
    global PAIRED_PREFLIGHT
    if Path.cwd().resolve()!=ROOT: raise RuntimeError(f"RUN_FROM_REPOSITORY_ROOT:{ROOT}")
    if PREFLIGHT_PATH.exists(): raise RuntimeError("PREFLIGHT_EXISTS_NO_OVERWRITE")
    head=subprocess.check_output(["git","rev-parse","HEAD"],cwd=ROOT,text=True).strip()
    producer_sha=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    plan_sha=hashlib.sha256(PLAN_PATH.read_bytes()).hexdigest()
    if head!=PLAN["source_head"]: raise RuntimeError(f"SOURCE_HEAD_MISMATCH:{head}")
    if producer_sha!=PLAN["producer_sha256"]: raise RuntimeError("FROZEN_PRODUCER_HASH_MISMATCH")
    PAIRED_PREFLIGHT=True
    roots=[]; exposures=[]; root_count=0
    seeds=PLAN["rules"]["seeds"]
    for i,seed in enumerate(seeds):
        generated,compiled,profile=generate_rule(seed,i)
        for family,plies in enumerate(PLAN["roots"]["prefix_plies"]):
            actions,root_session=gen_opening(compiled,plies,seed*1_000_000+family)
            root_sha=digest(root_session.state)
            rid=f"{seed}-{family}"
            roots.append({"root_id":rid,"seed":seed,"family":family,"prefix_plies":plies,"root_digest":root_sha,"opening":[record_value(a) for a in actions]})
            arms={}
            for kind in PLAN["arms"]["candidate"]:
                session=GameSession(compiled)
                for action in actions: session.submit(action)
                before=digest(session.state); history_before=tuple(session.history); result_before=session.result
                player,evaluator=make_player(compiled,profile,kind)
                decision=player.choose_action(session,run_limits())
                proxy=evaluator.q_leaf_proxy
                changed={"state":digest(session.state)!=before,"history":tuple(session.history)!=history_before,"result":session.result!=result_before}
                if any(changed.values()):
                    raise RuntimeError(f"PREFLIGHT_SEARCH_MUTATED_ROOT:{rid}:{kind}:{json.dumps(changed,sort_keys=True)}")
                arms[kind]={"q_calls":proxy.call_count,"q_trace":proxy.trace,"main_unit_evaluations":evaluator.main_eval_calls,"decision_evaluations":decision.evaluation_calls,"counts_match":decision.evaluation_calls==proxy.call_count+evaluator.main_eval_calls,"selected_action":None if decision.action is None else record_value(decision.action),"completed_depth":decision.completed_depth,"result_source":decision.result_source,"nodes":decision.nodes,"qnodes":decision.qnodes,"normal_capture_order_calls":len(evaluator.normal_capture_calls)}
            unit_trace={x["state_sha256"]:x for x in arms["unit_q_leaf"]["q_trace"]}
            paired_differences=sum(1 for x in unit_trace.values() if x["difference"]!=0)
            exposures.append({"root_id":rid,"seed":seed,"family":family,"root_digest":root_sha,"arms":{k:{"q_calls":v["q_calls"],"main_unit_evaluations":v["main_unit_evaluations"],"decision_evaluations":v["decision_evaluations"],"counts_match":v["counts_match"],"completed_depth":v["completed_depth"],"result_source":v["result_source"],"nodes":v["nodes"],"qnodes":v["qnodes"]} for k,v in arms.items()},"paired_states":len(unit_trace),"paired_different_values":paired_differences,"paired_value_examples":[x for x in unit_trace.values() if x["difference"]!=0][:8],"selected_actions":{k:v["selected_action"] for k,v in arms.items()},"outcome_submitted":False})
            root_count+=1
    value=any(e["paired_different_values"]>0 for e in exposures)
    summary={"schema":"primary-static-qsearch-leaf-price-preflight-v1","status":"NO_OUTCOME_PREFLIGHT","session_id":PLAN["session_id"],"source_head":head,"producer_sha256":producer_sha,"plan_sha256":plan_sha,"source_sha256":hashlib.sha256((ROOT/"generic_chess/ai/alphabeta/search.py").read_bytes()).hexdigest(),"outcomes_collected":0,"actions_submitted_after_search":0,"roots_count":root_count,"roots":roots,"exposures":exposures,"distinct_q_leaf_values_observed":value,"exposure_gate":{"minimum_roots":PLAN["preflight"]["minimum_exposed_roots"],"exposed_roots":sum(e["arms"]["unit_q_leaf"]["q_calls"]>0 and e["arms"]["static_v2_q_leaf"]["q_calls"]>0 and e["paired_different_values"]>0 for e in exposures),"passed":sum(e["arms"]["unit_q_leaf"]["q_calls"]>0 and e["arms"]["static_v2_q_leaf"]["q_calls"]>0 and e["paired_different_values"]>0 for e in exposures)>=PLAN["preflight"]["minimum_exposed_roots"]}}
    write_json(PREFLIGHT_PATH,summary)
    print(json.dumps({k:summary[k] for k in ("status","outcomes_collected","actions_submitted_after_search","roots_count","distinct_q_leaf_values_observed","exposure_gate")},sort_keys=True))

def main():
    if Path.cwd().resolve() != ROOT:
        raise RuntimeError(f"RUN_FROM_REPOSITORY_ROOT:{ROOT}")
    plan_sha = hashlib.sha256(PLAN_PATH.read_bytes()).hexdigest()
    producer_sha = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    preflight_sha = hashlib.sha256(PREFLIGHT_PATH.read_bytes()).hexdigest()
    if producer_sha != PLAN["producer_sha256"]:
        raise RuntimeError("FROZEN_PRODUCER_HASH_MISMATCH")
    if PREFLIGHT.get("plan_sha256") != plan_sha or PREFLIGHT.get("producer_sha256") != producer_sha:
        raise RuntimeError("PREFLIGHT_NOT_BOUND_TO_FROZEN_PLAN_AND_PRODUCER")
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    if head != PLAN["source_head"]:
        raise RuntimeError(f"SOURCE_HEAD_MISMATCH:{head}")
    if PREFLIGHT.get("outcomes_collected") != 0:
        raise RuntimeError("PREFLIGHT_ALREADY_HAS_OUTCOMES")
    exposed = [e for e in PREFLIGHT["exposures"] if e["arms"]["unit_q_leaf"]["q_calls"] > 0 and e["arms"]["static_v2_q_leaf"]["q_calls"] > 0 and e["paired_different_values"] > 0]
    if len(exposed) < int(PLAN["preflight"]["minimum_exposed_roots"]):
        print(json.dumps({"status":"CLOSED_UNTESTED","reason":"PREFLIGHT_EXPOSURE_GATE","exposed_roots":len(exposed),"minimum":PLAN["preflight"]["minimum_exposed_roots"],"outcomes_collected":0}))
        return
    if RUN_DIR.exists():
        raise RuntimeError("RUN_DIRECTORY_ALREADY_EXISTS_NO_RERUN")
    RUN_DIR.mkdir(parents=False, exist_ok=False)
    start_record = {
        "schema": PLAN["schema"], "session_id": PLAN["session_id"],
        "plan_sha256": plan_sha, "preflight_sha256": preflight_sha,
        "source_head": head, "producer_sha256": producer_sha,
        "started_at_utc": START_UTC.isoformat(), "hard_cap_seconds": CAP,
        "expected_slots": EXPECTED_SLOTS, "outcomes_collected": 0,
    }
    write_json(RUN_DIR / "execution-start.json", start_record)
    profiles, compiled_rules, roots_by_id = {}, {}, {}
    setup_schedule = PLAN["rules"]["setup_schedule"]
    symmetry_schedule = PLAN["rules"]["symmetry_schedule"]
    expected_roots = {(r["seed"], r["family"]): r for r in PREFLIGHT["roots"]}
    for i, seed in enumerate(PLAN["rules"]["seeds"]):
        poll()
        generated = generate_game(GeneratorConfig(
            seed=seed, board_size=PLAN["rules"]["board_size"],
            setup_preset=setup_schedule[i % len(setup_schedule)],
            movement_symmetry=symmetry_schedule[i % len(symmetry_schedule)],
            allow_hybrid=PLAN["rules"]["allow_hybrid"],
            require_promotable_type=PLAN["rules"]["require_promotable_type"],
            require_nonpromotable_type=PLAN["rules"]["require_nonpromotable_type"],
            max_generation_attempts=PLAN["rules"]["max_generation_attempts"],
            require_no_opening_win_in_one=False,
        ))
        compiled = compile_legacy_ruleset_for_semantic_execution(generated.ruleset)
        profile = build_ruleset_profile(compiled, EvaluationConfig())
        rule_id = str(seed)
        compiled_rules[rule_id] = compiled
        profiles[rule_id] = profile
        write_json(RUN_DIR / f"rule-{rule_id}.json", ruleset_to_dict(generated.ruleset))
        write_json(RUN_DIR / f"profile-{rule_id}.json", {
            "fingerprint": compiled.ruleset_fingerprint,
            "board": profile.board_value_by_type, "hand": profile.hand_value_by_base_type,
        })
        for family, plies in enumerate(PLAN["roots"]["prefix_plies"]):
            expected = expected_roots[(seed, family)]
            actions, root_session = gen_opening(
                compiled, plies, seed * 1_000_000 + family
            )
            actual = digest(root_session.state)
            if actual != expected["root_digest"]:
                raise RuntimeError(f"PREFLIGHT_ROOT_REGEN_MISMATCH:{seed}:{family}:{actual}")
            rid = f"{rule_id}-{family}"
            roots_by_id[rid] = {
                "root_id": rid, "rule_id": rule_id, "seed": seed, "family": family,
                "prefix_plies": plies, "opening": actions, "root_sha256": actual,
            }
    write_json(RUN_DIR / "roots.json", [
        {**{k:v for k,v in root.items() if k != "opening"},
         "opening": [record_value(a) for a in root["opening"]]}
        for root in roots_by_id.values()
    ])
    with GAMES_PATH.open("x", encoding="utf-8") as f:
        completed = 0
        for root_id, root in roots_by_id.items():
            compiled = compiled_rules[root["rule_id"]]
            profile = profiles[root["rule_id"]]
            for owner in PLAN["roots"]["candidate_owners"]:
                for variant in PLAN["arms"]["candidate"]:
                    poll()
                    game_id = f"{root_id}-o{owner}-{variant}"
                    row = play_one(compiled, profile, root["opening"], variant, owner, root_id, game_id)
                    f.write(json.dumps(record_value(row), sort_keys=True) + "\n")
                    f.flush()
                    completed += 1
                    write_json(RUN_DIR / "progress.json", {
                        "completed_slots": completed, "expected_slots": EXPECTED_SLOTS,
                        "last_game_id": game_id, "observed_at_utc": utcnow(),
                        "elapsed_seconds": time.monotonic() - START_MONO,
                    })
    elapsed = time.monotonic() - START_MONO
    if completed != EXPECTED_SLOTS:
        raise RuntimeError(f"INCOMPLETE_SLOTS:{completed}:{EXPECTED_SLOTS}")
    games = [json.loads(line) for line in GAMES_PATH.read_text(encoding="utf-8").splitlines() if line]
    summary = {
        "status": "COMPLETE", "planned_physical_games": EXPECTED_SLOTS,
        "returned_physical_games": len(games),
        "actual_terminals": sum(g["terminal_status"] != "ongoing" and "UNKNOWN" not in g["terminal_reason"] for g in games),
        "unknown": sum(g["reward"] is None for g in games),
        "invalid_actions": sum(g["action_invalid_count"] for g in games),
        "replay_mismatches": sum(not g["full_history_replay_equal"] for g in games),
        "unstarted_slots": EXPECTED_SLOTS - len(games),
        "nodes": sum(g["nodes"] for g in games), "qnodes": sum(g["qnodes"] for g in games),
        "normal_capture_order_calls": sum(g["normal_capture_order_calls"] for g in games),
        "q_leaf_evaluations": sum(g["q_leaf_evaluations"] for g in games),
        "normal_type_value_calls": sum(g["normal_type_value_calls"] for g in games),
        "q_type_value_calls": sum(g["q_type_value_calls"] for g in games),
        "caller_seconds": sum(g["caller_seconds"] for g in games),
        "elapsed_seconds": elapsed, "limits": "D3/8192/0.5s/q2/qhard2/qnodes128; Unit leaves and normal ordering; candidate q leaf price only; TT0",
    }
    write_json(RUN_DIR / "result.json", summary)
    start_record.update({"ended_at_utc": utcnow(), "elapsed_seconds": elapsed,
                         "completed_slots": completed, "status": "COMPLETE"})
    write_json(RUN_DIR / "execution-start.json", start_record)
    print(json.dumps(summary, sort_keys=True))

if __name__ == "__main__":
    try:
        if len(sys.argv)>1 and sys.argv[1]=="--preflight":
            preflight()
        elif len(sys.argv)>1 and sys.argv[1]=="--run":
            main()
        else:
            raise SystemExit("use --preflight or --run")
    except BaseException as exc:
        if RUN_DIR.exists():
            write_json(RUN_DIR / "failure.json", {
                "status": "INTERRUPTED", "type": type(exc).__name__,
                "message": str(exc), "observed_at_utc": utcnow(),
                "elapsed_seconds": time.monotonic() - START_MONO,
                "completed_slots": sum(1 for line in GAMES_PATH.read_text(encoding="utf-8").splitlines() if line) if GAMES_PATH.exists() else 0,
                "expected_slots": EXPECTED_SLOTS,
            })
        raise
