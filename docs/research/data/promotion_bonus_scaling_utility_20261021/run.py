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
sys.path.insert(0, str(ROOT))
BASE = Path(__file__).resolve().parent
PLAN_PATH = BASE / "plan.json"
PLAN = json.loads(PLAN_PATH.read_text(encoding="utf-8"))
RUN = BASE / "run"
START = time.monotonic()

from generic_chess.ai.alphabeta.player import AlphaBetaPlayer
from generic_chess.ai.alphabeta.search import SearchLimits, SearchTuning
from generic_chess.ai.evaluation.config import EvaluationConfig
from generic_chess.ai.evaluation.evaluator import Evaluator
from generic_chess.ai.evaluation.profile import build_ruleset_profile
from generic_chess.core.actions import action_to_dict
from generic_chess.generation.config import GeneratorConfig
from generic_chess.generation.generator import generate_game
from generic_chess.rules.compiler import compile_legacy_ruleset_for_semantic_execution
from generic_chess.rules.serialization import ruleset_to_dict
from generic_chess.session.session import GameSession
from scripts.research_record import record_value


def utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def write(path: Path, value) -> None:
    path.write_text(json.dumps(value, sort_keys=True, indent=2) + "\n", encoding="utf-8")


def digest(value) -> str:
    payload = json.dumps(record_value(value), sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode()).hexdigest().upper()


def stop_requested() -> None:
    if time.monotonic() - START > PLAN["controls"]["hard_cap_seconds"]:
        raise TimeoutError("FROZEN_RUN_CAP_SECONDS")
    for name in ("rollout", "advisor", "slack"):
        flag = json.loads((ROOT / ".local_agent" / f"{name}.json").read_text(encoding="utf-8"))
        if flag.get("stopped") or flag.get("user_paused"):
            raise InterruptedError(f"STOP_{name.upper()}")


class GainScaledEvaluator(Evaluator):
    """Diagnostic-only alternate mapping; no product code or default changes."""

    def _promotion_bonus(self, piece, idx: int) -> int:
        base = piece.base_type_id
        if piece.promoted or base not in self._profile.promotion_gain_by_type:
            return 0
        gain = self._profile.promotion_gain_by_type[base]
        if gain <= 0:
            return 0
        owner = piece.owner
        zone = self._zones.get((base, owner))
        if zone is None:
            return 0
        scaled_zone_bonus = (self._config.promotion_potential_weight * gain + 500) // 1000
        if idx in zone:
            bonus = scaled_zone_bonus
        else:
            forward = self._promotion_forward[(base, owner)][idx]
            bonus = scaled_zone_bonus // 2 if any(t in zone for t in forward) else 0
        return bonus if owner == 0 else -bonus


def make_opening(compiled, plies: int, seed: int):
    session = GameSession(compiled)
    rng = random.Random(seed)
    actions = []
    for _ in range(plies):
        stop_requested()
        if session.result.status.value != "ongoing":
            break
        legal = sorted(session.legal_actions(), key=lambda a: json.dumps(action_to_dict(a), sort_keys=True))
        if not legal:
            raise RuntimeError("ONGOING_WITHOUT_LEGAL_ACTION")
        action = legal[rng.randrange(len(legal))]
        actions.append(action)
        session.submit(action)
    return actions, session


def play(compiled, evaluators, opening, variant: str, candidate_owner: int, root_id: str, game_id: str, limits):
    session = GameSession(compiled)
    for action in opening:
        session.submit(action)
    root_hash = digest({"state": session.state, "history": session.history,
                        "witnesses": session._search_witnesses, "result": session.result})
    players = {
        side: AlphaBetaPlayer(
            compiled,
            evaluator_override=(evaluators[variant] if side == candidate_owner else evaluators["fixed_foe"]),
            use_tt=False, use_ordering=True, use_native_semantic_legality=True,
            tuning=SearchTuning(use_root_tactical=False),
        ) for side in (0, 1)
    }
    moves = []
    candidate_plies = 0
    reason = "ACTUAL_TERMINAL" if session.result.status.value != "ongoing" else None
    while session.result.status.value == "ongoing" and candidate_plies < PLAN["controls"]["candidate_ply_horizon"]:
        stop_requested()
        side = session.state.position.side_to_move
        role = "candidate" if side == candidate_owner else "fixed_foe"
        before = digest({"state": session.state, "history": session.history,
                         "witnesses": session._search_witnesses, "result": session.result})
        decision = players[side].choose_action(session, limits)
        action = decision.action
        legal = action is not None and action in session.legal_actions()
        row = {
            "ply": len(moves), "side": side, "role": role, "state_before": before,
            "action": None if action is None else record_value(action), "action_valid": legal,
            "score": decision.score, "completed_depth": decision.completed_depth,
            "selective_depth": decision.selective_depth, "nodes": decision.nodes,
            "qnodes": decision.qnodes, "fallback": decision.result_source not in ("main_iteration", "verified_root_child"),
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
                    and replay._search_witnesses == session._search_witnesses
                    and replay.result == session.result)
    if not replay_equal:
        raise RuntimeError(f"FULL_HISTORY_REPLAY_MISMATCH:{game_id}")
    unknown = "UNKNOWN" in reason or session.result.status.value == "no_contest"
    winner = session.result.winner
    reward = None if unknown else (0 if winner is None else (1 if winner == candidate_owner else -1))
    return {
        "game_id": game_id, "root_id": root_id, "variant": variant,
        "candidate_owner": candidate_owner, "root_state_sha256": root_hash,
        "moves": moves, "move_count": len(moves), "candidate_plies": candidate_plies,
        "terminal_status": session.result.status.value, "terminal_reason": reason,
        "winner": winner, "reward": reward, "full_record": json.loads(
            __import__("generic_chess.session.serialization", fromlist=["serialize_game_record"])
            .serialize_game_record(session.to_record())),
        "final_state_sha256": digest({"state": session.state, "history": session.history,
                                      "witnesses": session._search_witnesses, "result": session.result}),
        "full_history_replay_equal": replay_equal,
        "nodes": sum(m["nodes"] for m in moves),
        "candidate_nodes": sum(m["nodes"] for m in moves if m["role"] == "candidate"),
        "foe_nodes": sum(m["nodes"] for m in moves if m["role"] == "fixed_foe"),
        "caller_seconds": sum(m["elapsed_seconds"] for m in moves),
        "action_invalid_count": sum(not m["action_valid"] for m in moves if m["action"] is not None),
    }


def main() -> None:
    if Path.cwd().resolve() != ROOT:
        raise RuntimeError("WRONG_CWD")
    expected_plan_sha = ""
    source = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    if source != PLAN["source_head"]:
        raise RuntimeError(f"SOURCE_HEAD_MISMATCH:{source}")
    if RUN.exists():
        raise RuntimeError("NO_OVERWRITE")
    RUN.mkdir()
    expected_plan_sha = hashlib.sha256(PLAN_PATH.read_bytes()).hexdigest().upper()
    write(RUN / "execution-start.json", {
        "status": "ACTIVE", "source_head": source, "plan_sha256": expected_plan_sha,
        "started_at_utc": utc(), "expected_slots": 64,
    })
    setup = PLAN["rules"]["setup_schedule"]
    symmetry = PLAN["rules"]["symmetry_schedule"]
    compiled_by_seed = {}
    evaluators_by_seed = {}
    rules = []
    profiles = []
    for index, seed in enumerate(PLAN["rules"]["seeds"]):
        stop_requested()
        generated = generate_game(GeneratorConfig(
            seed=seed, board_size=PLAN["rules"]["board_size"],
            setup_preset=setup[index % len(setup)],
            movement_symmetry=symmetry[index % len(symmetry)],
            allow_hybrid=PLAN["rules"]["allow_hybrid"],
            require_promotable_type=PLAN["rules"]["require_promotable_type"],
            require_nonpromotable_type=PLAN["rules"]["require_nonpromotable_type"],
            max_generation_attempts=PLAN["rules"]["max_generation_attempts"],
            require_no_opening_win_in_one=PLAN["rules"]["require_no_opening_win_in_one"],
        ))
        compiled = compile_legacy_ruleset_for_semantic_execution(generated.ruleset)
        static_profile = build_ruleset_profile(compiled, EvaluationConfig())
        unit_hand = {pt.type_id: (0 if pt.is_anchor else 900) for pt in compiled.piece_types}
        profile = replace(static_profile, hand_value_by_base_type=unit_hand)
        default_cfg = EvaluationConfig()
        off_cfg = replace(default_cfg, promotion_potential_weight=0)
        scaled_cfg = replace(default_cfg, promotion_potential_weight=3)
        evaluators = {
            "candidate_current": Evaluator(compiled, profile, default_cfg),
            "candidate_gain_scaled": GainScaledEvaluator(compiled, profile, scaled_cfg),
            "fixed_foe": Evaluator(compiled, profile, off_cfg),
        }
        gain_by_type = dict(profile.promotion_gain_by_type)
        scaled_values = {tid: (3 * gain + 500) // 1000 for tid, gain in gain_by_type.items() if gain > 0}
        current_values = {tid: 3 * max(1, gain // 1000) for tid, gain in gain_by_type.items() if gain > 0}
        rules.append({"seed": seed, "ruleset": ruleset_to_dict(generated.ruleset)})
        profiles.append({"seed": seed, "board_values": dict(profile.board_value_by_type),
                         "unit_hand_values": unit_hand, "promotion_gain_by_type": gain_by_type,
                         "current_zone_bonus": current_values, "scaled_zone_bonus": scaled_values})
        compiled_by_seed[seed] = compiled
        evaluators_by_seed[seed] = evaluators
        write(RUN / f"rule-{seed}.json", ruleset_to_dict(generated.ruleset))
        write(RUN / f"profile-{seed}.json", profiles[-1])
    exposure_types = [(item["seed"], tid, gain) for item in profiles
                      for tid, gain in item["promotion_gain_by_type"].items() if gain > 0
                      and item["current_zone_bonus"][tid] != item["scaled_zone_bonus"][tid]]
    positive_rule_count = sum(any(g > 0 for g in item["promotion_gain_by_type"].values()) for item in profiles)
    if positive_rule_count < 4 or len(exposure_types) < 4:
        write(RUN / "preflight-closure.json", {
            "status": "CLOSED_INSUFFICIENT_FORMULA_EXPOSURE", "source_head": source,
            "plan_sha256": expected_plan_sha, "rules_generated": len(rules),
            "rules_with_positive_gain": positive_rule_count,
            "types_with_different_scaled_zone_bonus": exposure_types,
            "games_started": 0, "closed_at_utc": utc(),
        })
        print(json.dumps({"status": "CLOSED_INSUFFICIENT_FORMULA_EXPOSURE",
                          "rules_with_positive_gain": positive_rule_count,
                          "types_with_different_scaled_zone_bonus": exposure_types}, sort_keys=True))
        return
    write(RUN / "preflight.json", {
        "status": "PASS", "rules": rules, "profiles": profiles,
        "rules_with_positive_gain": positive_rule_count,
        "types_with_different_scaled_zone_bonus": exposure_types,
        "preflight_at_utc": utc(),
    })
    roots = []
    openings_by_root = {}
    for seed in PLAN["rules"]["seeds"]:
        compiled = compiled_by_seed[seed]
        for family, plies in enumerate(PLAN["controls"]["prefix_plies"]):
            opening, session = make_opening(compiled, plies, seed * 1_000_000 + family)
            root_id = f"{seed}-{family}"
            openings_by_root[root_id] = tuple(opening)
            evaluators = evaluators_by_seed[seed]
            roots.append({"root_id": root_id, "seed": seed, "family": family,
                          "prefix_plies": plies, "opening": [record_value(a) for a in opening],
                          "root_state_sha256": digest({"state": session.state, "history": session.history,
                                                       "witnesses": session._search_witnesses, "result": session.result}),
                          "current_bonus_delta": evaluators["candidate_current"].evaluate(session.state)
                              - evaluators["fixed_foe"].evaluate(session.state)})
    write(RUN / "roots.json", roots)
    limits = SearchLimits(max_depth=3, max_nodes=8192, max_time_seconds=0.5,
                          quiescence_max_depth=0, quiescence_hard_max_depth=8)
    games = []
    with (RUN / "games.jsonl").open("x", encoding="utf-8") as stream:
        for root in roots:
            seed = root["seed"]
            opening = openings_by_root[root["root_id"]]
            for owner in PLAN["controls"]["candidate_owners"]:
                for variant in ("candidate_current", "candidate_gain_scaled"):
                    stop_requested()
                    game_id = f"{root['root_id']}-o{owner}-{variant}"
                    game = play(compiled_by_seed[seed], evaluators_by_seed[seed], opening,
                                variant, owner, root["root_id"], game_id, limits)
                    if game["root_state_sha256"] != root["root_state_sha256"]:
                        raise RuntimeError(f"ROOT_REPLAY_MISMATCH:{game_id}")
                    stream.write(json.dumps(record_value(game), sort_keys=True) + "\n")
                    stream.flush()
                    games.append(game)
                    write(RUN / "progress.json", {"completed_slots": len(games), "expected_slots": 64,
                          "last_game_id": game_id, "observed_at_utc": utc(),
                          "elapsed_seconds": time.monotonic() - START})
    result = {
        "status": "COMPLETE", "planned_physical_games": 64, "returned_physical_games": len(games),
        "actual_terminals": sum(g["reward"] is not None for g in games),
        "unknown": sum(g["reward"] is None for g in games),
        "invalid_actions": sum(g["action_invalid_count"] for g in games),
        "replay_mismatches": sum(not g["full_history_replay_equal"] for g in games),
        "unstarted_slots": 64 - len(games),
        "elapsed_seconds": time.monotonic() - START, "plan_sha256": expected_plan_sha,
        "source_head": source, "started_at_utc": json.loads((RUN / "execution-start.json").read_text())["started_at_utc"],
        "ended_at_utc": utc(),
    }
    write(RUN / "result.json", result)
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    try:
        main()
    except BaseException as error:
        if RUN.exists():
            games_file = RUN / "games.jsonl"
            completed = sum(1 for line in games_file.read_text(encoding="utf-8").splitlines() if line) if games_file.exists() else 0
            write(RUN / "failure.json", {"status": "INTERRUPTED", "type": type(error).__name__,
                  "message": str(error), "observed_at_utc": utc(), "elapsed_seconds": time.monotonic() - START,
                  "completed_slots": completed, "expected_slots": 64})
        raise
