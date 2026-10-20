from __future__ import annotations

import hashlib
import json
import random
import subprocess
import sys
import time
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
HERE = Path(__file__).resolve().parent
PLAN_PATH = HERE / "promotion-utility-plan.json"
PLAN = json.loads(PLAN_PATH.read_text(encoding="utf-8"))
PLAN_SHA = hashlib.sha256(PLAN_PATH.read_bytes()).hexdigest().upper()
RUN = HERE / "promotion-utility-run"
START = time.monotonic()

sys.path.insert(0, str(ROOT))
from generic_chess.ai.alphabeta.player import AlphaBetaPlayer
from generic_chess.ai.alphabeta.tuning import SearchTuning
from generic_chess.ai.evaluation.config import EvaluationConfig
from generic_chess.ai.evaluation.evaluator import Evaluator
from generic_chess.ai.evaluation.profile import build_ruleset_profile
from generic_chess.ai.limits import SearchLimits
from generic_chess.core.actions import action_to_dict, action_is_drop
from generic_chess.generation.config import GeneratorConfig
from generic_chess.generation.generator import generate_game
from generic_chess.rules.compiler import compile_legacy_ruleset_for_semantic_execution
from generic_chess.rules.serialization import ruleset_to_dict
from generic_chess.session.session import GameSession
from scripts.research_record import record_value


def utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


def digest(value) -> str:
    payload = json.dumps(record_value(value), sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode()).hexdigest().upper()


def write(path: Path, value) -> None:
    path.write_text(json.dumps(record_value(value), sort_keys=True, indent=2) + "\n", encoding="utf-8")


def poll() -> None:
    if time.monotonic() - START >= 3600:
        raise TimeoutError("FROZEN_3600S_CAP")
    for name in ("rollout", "advisor", "slack"):
        flag = json.loads((ROOT / ".local_agent" / f"{name}.json").read_text(encoding="utf-8"))
        if flag.get("stopped") or flag.get("user_paused"):
            raise InterruptedError(f"STOP_{name.upper()}")


def opening(compiled, plies: int, seed: int):
    session = GameSession(compiled)
    rng = random.Random(seed)
    actions = []
    for _ in range(plies):
        if session.result.status.value != "ongoing":
            break
        legal = sorted(session.legal_actions(), key=lambda a: json.dumps(action_to_dict(a), sort_keys=True))
        if not legal:
            raise RuntimeError("ONGOING_WITHOUT_LEGAL_ACTION")
        action = legal[rng.randrange(len(legal))]
        actions.append(action)
        session.submit(action)
    return actions, session


class PromotionValueOnly:
    def __init__(self, unit: Evaluator, static_values: dict[str, int]):
        self.unit = unit
        self.static_values = static_values

    def evaluate(self, state):
        return self.unit.evaluate(state)

    def capture_order_value(self, moving, captured):
        return self.unit.capture_order_value(moving, captured)

    def type_value(self, type_id: str):
        return self.static_values[type_id]


def play(compiled, profiles, open_actions, variant, owner, root_id, game_id, limits):
    session = GameSession(compiled)
    for action in open_actions:
        session.submit(action)
    root_state = digest({"state": session.state, "history": session.history,
                         "witnesses": session._search_witnesses, "result": session.result})
    hand_stock = sum(n for hand in session.state.position.hands for _, n in hand.counts)
    drops = sum(action_is_drop(a) for a in session.legal_actions())
    tuning = SearchTuning(use_staged_move_picker=True, use_root_tactical=False)
    players = {
        side: AlphaBetaPlayer(compiled, evaluator_override=(profiles[variant] if side == owner else profiles["unit_foe"]),
                              use_tt=False, use_ordering=True, use_native_semantic_legality=True, tuning=tuning)
        for side in (0, 1)
    }
    moves = []
    candidate_plies = 0
    reason = "ACTUAL_TERMINAL" if session.result.status.value != "ongoing" else None
    while session.result.status.value == "ongoing" and candidate_plies < 48:
        poll()
        side = session.state.position.side_to_move
        role = "candidate" if side == owner else "fixed_foe"
        before = digest({"state": session.state, "history": session.history,
                         "witnesses": session._search_witnesses, "result": session.result})
        decision = players[side].choose_action(session, limits)
        action = decision.action
        legal = action is not None and action in session.legal_actions()
        row = {
            "ply": len(moves), "side": side, "role": role,
            "state_before": before, "action": None if action is None else record_value(action),
            "action_valid": legal, "score": decision.score,
            "completed_depth": decision.completed_depth, "selective_depth": decision.selective_depth,
            "nodes": decision.nodes, "qnodes": decision.qnodes,
            "fallback": decision.result_source not in ("main_iteration", "verified_root_child"),
            "result_source": decision.result_source, "termination_reason": decision.termination_reason,
            "elapsed_seconds": decision.elapsed_seconds,
        }
        if action is None or not legal:
            reason = "NO_ACTION_UNKNOWN" if action is None else "ILLEGAL_RETURN_UNKNOWN"
            moves.append(row)
            break
        session.submit(action)
        row["state_after"] = digest({"state": session.state, "history": session.history,
                                     "witnesses": session._search_witnesses, "result": session.result})
        moves.append(row)
        if role == "candidate":
            candidate_plies += 1
        if session.result.status.value != "ongoing":
            reason = "ACTUAL_TERMINAL"
    if session.result.status.value == "ongoing" and reason is None:
        reason = "HORIZON_48_CANDIDATE_UNKNOWN"
    replay = GameSession.replay(compiled, session.to_record())
    replay_equal = (replay.state == session.state and replay.history == session.history
                    and replay._search_witnesses == session._search_witnesses and replay.result == session.result)
    if not replay_equal:
        raise RuntimeError(f"FULL_HISTORY_REPLAY_MISMATCH:{game_id}")
    unknown = "UNKNOWN" in reason or session.result.status.value == "no_contest"
    winner = session.result.winner
    reward = None if unknown else (0 if winner is None else (1 if winner == owner else -1))
    return {
        "game_id": game_id, "root_id": root_id, "variant": variant, "candidate_owner": owner,
        "opening_actions": [record_value(a) for a in open_actions], "root_state_sha256": root_state,
        "root_hand_stock_total": hand_stock, "root_legal_drop_count": drops,
        "moves": moves, "move_count": len(moves), "terminal_status": session.result.status.value,
        "terminal_reason": reason, "candidate_plies": candidate_plies, "winner": winner, "reward": reward,
        "full_record": json.loads(__import__("generic_chess.session.serialization", fromlist=["serialize_game_record"]).serialize_game_record(session.to_record())),
        "final_state_sha256": digest({"state": session.state, "history": session.history,
                                       "witnesses": session._search_witnesses, "result": session.result}),
        "full_history_replay_equal": replay_equal,
        "nodes": sum(m["nodes"] for m in moves), "qnodes": sum(m["qnodes"] for m in moves),
        "caller_seconds": sum(m["elapsed_seconds"] for m in moves),
        "candidate_nodes": sum(m["nodes"] for m in moves if m["role"] == "candidate"),
        "foe_nodes": sum(m["nodes"] for m in moves if m["role"] == "fixed_foe"),
        "action_invalid_count": sum(not m["action_valid"] for m in moves if m["action"] is not None),
    }


def main() -> None:
    if Path.cwd().resolve() != ROOT:
        raise RuntimeError("WRONG_CWD")
    if hashlib.sha256(PLAN_PATH.read_bytes()).hexdigest().upper() != PLAN_SHA:
        raise RuntimeError("PLAN_CHANGED")
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    if head != PLAN["source_head"]:
        raise RuntimeError(f"SOURCE_HEAD_MISMATCH:{head}")
    if RUN.exists():
        raise RuntimeError("NO_OVERWRITE")
    RUN.mkdir()
    write(RUN / "execution-start.json", {"plan_sha256": PLAN_SHA, "source_head": head,
                                         "started_at_utc": utc(), "expected_slots": 64, "status": "ACTIVE"})
    compiled_by_seed = {}
    profiles_by_seed = {}
    roots = []
    for i, seed in enumerate(PLAN["rules"]["seeds"]):
        poll()
        generated = generate_game(GeneratorConfig(
            seed=seed, board_size=5,
            setup_preset=PLAN["rules"]["setup_schedule"][i % 3],
            movement_symmetry=PLAN["rules"]["symmetry_schedule"][i % 2],
            allow_hybrid=True, require_promotable_type=True, require_nonpromotable_type=True,
            max_generation_attempts=16, require_no_opening_win_in_one=False,
        ))
        compiled = compile_legacy_ruleset_for_semantic_execution(generated.ruleset)
        cfg = EvaluationConfig(promotion_potential_weight=0)
        static_profile = build_ruleset_profile(compiled, EvaluationConfig())
        unit_board = {pt.type_id: (0 if pt.is_anchor else 1000) for pt in compiled.piece_types}
        unit_profile = replace(static_profile, board_value_by_type=unit_board,
                                hand_value_by_base_type={pt.type_id: (0 if pt.is_anchor else 900) for pt in compiled.piece_types},
                                promotion_gain_by_type={})
        unit = Evaluator(compiled, unit_profile, cfg)
        static_order = PromotionValueOnly(unit, static_profile.board_value_by_type)
        if any(unit.evaluate(GameSession(compiled).state) != static_order.evaluate(GameSession(compiled).state)
               or unit.capture_order_value(type("Piece", (), {"current_type_id": t})(), type("Piece", (), {"current_type_id": t})())
                  != static_order.capture_order_value(type("Piece", (), {"current_type_id": t})(), type("Piece", (), {"current_type_id": t})())
               for t in unit_board):
            raise AssertionError("NON_PROMOTION_CHANNEL_CHANGED")
        profiles_by_seed[seed] = {"unit_promotion_order": unit,
                                  "static_promotion_order": static_order, "unit_foe": unit}
        compiled_by_seed[seed] = compiled
        write(RUN / f"rule-{seed}.json", ruleset_to_dict(generated.ruleset))
        write(RUN / f"profile-{seed}.json", {
            "static_board_values": static_profile.board_value_by_type,
            "unit_board_values": unit_board, "unit_hand_values": unit_profile.hand_value_by_base_type,
            "promotion_potential_disabled": True, "candidate_type_value_only_differs": True,
        })
        for family, plies in enumerate(PLAN["roots"]["prefix_plies"]):
            opening_actions, session = opening(compiled, plies, seed * 1_000_000 + family)
            root_id = f"{seed}-{family}"
            roots.append({"root_id": root_id, "seed": seed, "family": family,
                          "prefix_plies": plies, "opening_actions": opening_actions,
                          "root_state_sha256": digest({"state": session.state, "history": session.history,
                                                        "witnesses": session._search_witnesses, "result": session.result})})
    write(RUN / "roots.json", [{"root_id": r["root_id"], "seed": r["seed"],
                                "prefix_plies": r["prefix_plies"],
                                "root_state_sha256": r["root_state_sha256"],
                                "opening": [record_value(a) for a in r["opening_actions"]]} for r in roots])
    limits = SearchLimits(max_depth=3, max_nodes=8192, max_time_seconds=0.5,
                          quiescence_max_depth=0, quiescence_hard_max_depth=8)
    games = []
    with (RUN / "games.jsonl").open("x", encoding="utf-8") as stream:
        for root in roots:
            for owner in (0, 1):
                for variant in ("unit_promotion_order", "static_promotion_order"):
                    poll()
                    game_id = f"{root['root_id']}-o{owner}-{variant}"
                    game = play(compiled_by_seed[root["seed"]], profiles_by_seed[root["seed"]],
                                root["opening_actions"], variant, owner, root["root_id"], game_id, limits)
                    stream.write(json.dumps(record_value(game), sort_keys=True) + "\n")
                    stream.flush()
                    games.append(game)
                    write(RUN / "progress.json", {"completed_slots": len(games), "expected_slots": 64,
                                                   "last_game_id": game_id, "observed_at_utc": utc(),
                                                   "elapsed_seconds": time.monotonic() - START})
    if len(games) != 64:
        raise RuntimeError("SLOT_COUNT_MISMATCH")
    result = {
        "status": "COMPLETE", "planned_physical_games": 64, "returned_physical_games": len(games),
        "actual_terminals": sum(g["reward"] is not None for g in games),
        "unknown": sum(g["reward"] is None for g in games),
        "invalid_actions": sum(g["action_invalid_count"] for g in games),
        "replay_mismatches": sum(not g["full_history_replay_equal"] for g in games),
        "unstarted_slots": 0, "candidate_nodes": sum(g["candidate_nodes"] for g in games),
        "foe_nodes": sum(g["foe_nodes"] for g in games),
        "caller_seconds": sum(g["caller_seconds"] for g in games),
        "elapsed_seconds": time.monotonic() - START, "plan_sha256": PLAN_SHA,
        "source_head": head, "started_at_utc": json.loads((RUN / "execution-start.json").read_text())["started_at_utc"],
        "ended_at_utc": utc(),
    }
    write(RUN / "result.json", result)
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    try:
        main()
    except BaseException as error:
        if RUN.exists():
            completed = sum(1 for x in (RUN / "games.jsonl").read_text(encoding="utf-8").splitlines() if x) if (RUN / "games.jsonl").exists() else 0
            write(RUN / "failure.json", {"status": "INTERRUPTED", "type": type(error).__name__,
                                         "message": str(error), "observed_at_utc": utc(),
                                         "elapsed_seconds": time.monotonic() - START,
                                         "completed_slots": completed, "expected_slots": 64})
        raise
