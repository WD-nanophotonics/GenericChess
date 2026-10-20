"""Frozen static-v2 StagedMovePicker capture-order utility panel; writes once into its unique evidence folder."""
from __future__ import annotations
import hashlib, json, random, subprocess, sys, time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
HERE = Path(__file__).resolve().parent
RUN_DIR = HERE / "staged-capture-order-run-20261021"
PLAN_PATH = HERE / "staged-capture-order-plan.json"
PREFLIGHT_PATH = HERE / "staged-capture-order-preflight.json"
PLAN_SHA = "dea4c277271cbcfde1e2601e9e8701881d9025189907fbe139914c410f50f968"
PREFLIGHT_SHA = "b8e253314db2019d743a67cb83f85636f6a52654d7136a2700c65f697728495f"
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
PREFLIGHT = json.loads(PREFLIGHT_PATH.read_text(encoding="utf-8"))
CAP = int(PLAN["cost"]["hard_cap_seconds"])
EXPECTED_SLOTS = 64
GAMES_PATH = RUN_DIR / "capture-order-games.jsonl"

def utcnow():
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")

def digest(value):
    raw = json.dumps(record_value(value), sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(raw).hexdigest()

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

class ControlledEvaluator:
    """Identical Unit leaf/type values; candidate arm changes capture ordering only."""
    def __init__(self, compiled, profile, kind):
        self._delegate = Evaluator(compiled, profile, EvaluationConfig())
        self._compiled = compiled
        self._kind = kind
        self.capture_calls = []
        self.type_ids = []
    def evaluate(self, state):
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
    def capture_order_value(self, moving, captured):
        if self._kind == "static_v2_capture_order":
            value = self._delegate.capture_order_value(moving, captured)
        else:
            moving_value = 0 if self._compiled.types_by_id[moving.current_type_id].is_anchor else 100
            captured_value = 0 if self._compiled.types_by_id[captured.current_type_id].is_anchor else 100
            value = captured_value * 10 - moving_value // 10
        self.capture_calls.append({
            "moving": moving.current_type_id,
            "captured": captured.current_type_id,
            "value": value,
        })
        return value
    def type_value(self, type_id):
        self.type_ids.append(type_id)
        return 0 if self._compiled.types_by_id[type_id].is_anchor else 100

def make_player(compiled, profile, kind):
    evaluator = ControlledEvaluator(compiled, profile, kind)
    player = AlphaBetaPlayer(
        compiled, evaluator_override=evaluator, use_tt=False, use_ordering=True,
        use_native_semantic_legality=True, tuning=SearchTuning(use_staged_move_picker=True),
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
        kind = variant if side == owner else "unit_capture_order"
        players[side], evaluators[side] = make_player(compiled, profile, kind)
    search = PLAN["arms"]["search"]
    limits = SearchLimits(
        max_depth=search["max_depth"], max_nodes=search["max_nodes"],
        max_time_seconds=search["max_time_seconds"],
        quiescence_max_depth=search["quiescence_max_depth"],
        quiescence_hard_max_depth=search["quiescence_hard_max_depth"],
    )
    moves = []
    candidate_plies = 0
    reason = "ACTUAL_TERMINAL" if initial_result.status.value != "ongoing" else None
    while session.result.status.value == "ongoing" and candidate_plies < search["max_candidate_plies"]:
        poll()
        side = session.state.position.side_to_move
        role = "candidate" if side == owner else "foe"
        state_before = digest(session.state)
        capture_before = len(evaluators[side].capture_calls)
        types_before = len(evaluators[side].type_ids)
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
            "capture_order_calls_delta": len(evaluators[side].capture_calls) - capture_before,
            "capture_order_trace": evaluators[side].capture_calls[capture_before:],
            "type_value_calls_delta": len(evaluators[side].type_ids) - types_before,
            "type_ids_consulted": evaluators[side].type_ids[types_before:],
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
        "capture_order_calls": sum(int(m["capture_order_calls_delta"]) for m in moves),
        "type_value_calls": sum(int(m["type_value_calls_delta"]) for m in moves),
        "action_invalid_count": sum(not m["action_valid"] for m in moves if m["action"] is not None),
    }

def main():
    if Path.cwd().resolve() != ROOT:
        raise RuntimeError(f"RUN_FROM_REPOSITORY_ROOT:{ROOT}")
    if hashlib.sha256(PLAN_PATH.read_bytes()).hexdigest() != PLAN_SHA:
        raise RuntimeError("FROZEN_CAPTURE_ORDER_PLAN_HASH_MISMATCH")
    if hashlib.sha256(PREFLIGHT_PATH.read_bytes()).hexdigest() != PREFLIGHT_SHA:
        raise RuntimeError("CAPTURE_ORDER_PREFLIGHT_HASH_MISMATCH")
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    if head != PLAN["source_head"]:
        raise RuntimeError(f"SOURCE_HEAD_MISMATCH:{head}")
    if PREFLIGHT.get("outcomes_collected") != 0:
        raise RuntimeError("PREFLIGHT_ALREADY_HAS_OUTCOMES")
    if RUN_DIR.exists():
        raise RuntimeError("RUN_DIRECTORY_ALREADY_EXISTS_NO_RERUN")
    RUN_DIR.mkdir(parents=False, exist_ok=False)
    start_record = {
        "schema": PLAN["schema"], "session_id": PLAN["session_id"],
        "plan_sha256": PLAN_SHA, "preflight_sha256": PREFLIGHT_SHA,
        "source_head": head, "producer_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
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
            if actual != expected["state_digest"]:
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
                for variant in PLAN["arms"]["candidate_arms"]:
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
        "capture_order_calls": sum(g["capture_order_calls"] for g in games),
        "type_value_calls": sum(g["type_value_calls"] for g in games),
        "caller_seconds": sum(g["caller_seconds"] for g in games),
        "elapsed_seconds": elapsed, "limits": "D3/8192/0.5s/q0; optional StagedMovePicker; TT0",
    }
    write_json(RUN_DIR / "result.json", summary)
    start_record.update({"ended_at_utc": utcnow(), "elapsed_seconds": elapsed,
                         "completed_slots": completed, "status": "COMPLETE"})
    write_json(RUN_DIR / "execution-start.json", start_record)
    print(json.dumps(summary, sort_keys=True))

if __name__ == "__main__":
    try:
        main()
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
