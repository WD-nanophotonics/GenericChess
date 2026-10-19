"""One frozen, single-process static-vs-Unit 5x5 utility panel."""
from __future__ import annotations

from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import random
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[5]
if Path.cwd().resolve() != ROOT:
    raise RuntimeError(f"RUN_FROM_REPOSITORY_ROOT:{ROOT}")
sys.path.insert(0, str(ROOT))

from generic_chess.ai.evaluation.config import EvaluationConfig
from generic_chess.ai.evaluation.profile import build_ruleset_profile
from generic_chess.ai.limits import SearchLimits
from generic_chess.core.actions import action_to_dict
from generic_chess.generation.config import GeneratorConfig
from generic_chess.generation.generator import generate_game
from generic_chess.learning.material import LearnableMaterialCheckpoint
from generic_chess.native.compiler import compile_native_semantic_rules
from generic_chess.native.semantic_engine import SemanticSearchEngine
from generic_chess.rules.compiler import compile_legacy_ruleset_for_semantic_execution
from generic_chess.rules.serialization import ruleset_to_dict
from generic_chess.session.session import GameSession
from generic_chess.session.serialization import serialize_game_record
from scripts.research_record import record_value

HERE = Path(__file__).resolve().parent
PLAN = json.loads((HERE / "plan.json").read_text(encoding="utf-8"))
STARTED = time.monotonic()
CAP = float(PLAN["cost"]["hard_cap_seconds"])


def write_json(path: Path, value) -> None:
    path.write_text(json.dumps(record_value(value), indent=2, sort_keys=True) + "\n", encoding="utf-8")


def poll() -> None:
    if time.monotonic() - STARTED >= CAP:
        raise TimeoutError("FROZEN_GLOBAL_2400S_CAP")
    for name in ("rollout", "advisor", "slack"):
        state = json.loads((ROOT / ".local_agent" / f"{name}.json").read_text(encoding="utf-8"))
        if state.get("stopped") or state.get("user_paused"):
            raise InterruptedError(f"EXPLICIT_{name.upper()}_STOP")


def sha(value) -> str:
    raw = json.dumps(record_value(value), sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def checkpoint(compiled, profile, kind: str) -> LearnableMaterialCheckpoint:
    ids = [pt.type_id for pt in compiled.piece_types]
    anchors = {pt.type_id for pt in compiled.piece_types if pt.is_anchor}
    if kind == "unit":
        board = {type_id: (0.0 if type_id in anchors else 1.0) for type_id in ids}
        hand = dict(board)
    else:
        board = {t: v / 1000.0 for t, v in profile.board_value_by_type.items()}
        hand = {t: v / 1000.0 for t, v in profile.hand_value_by_base_type.items()}
    return LearnableMaterialCheckpoint(
        ruleset_fingerprint=compiled.ruleset_fingerprint,
        evaluation_profile_version=f"primary-static-5x5-{kind}",
        board_weights=board,
        hand_weights=hand,
        material_scale=256,
        value_scale=10.0,
        reference_median=1.0,
    )


def search_limits(role: str) -> SearchLimits:
    spec = PLAN["arms"][f"{role}_budget"]
    return SearchLimits(
        max_depth=spec["max_depth"],
        max_nodes=spec["max_nodes"],
        max_time_seconds=spec["max_time_seconds"],
        quiescence_max_depth=spec["quiescence_max_depth"],
    )


def make_opening(compiled, seed: int):
    session = GameSession(compiled)
    rng = random.Random(seed)
    actions = []
    for _ in range(PLAN["roots"]["prefix_plies"]):
        if session.result.status.value != "ongoing":
            break
        legal = sorted(session.legal_actions(), key=lambda a: json.dumps(action_to_dict(a), sort_keys=True))
        if not legal:
            raise RuntimeError("CORE_ONGOING_WITHOUT_LEGAL_ACTION_DURING_PREFIX")
        action = legal[rng.randrange(len(legal))]
        actions.append(action)
        session.submit(action)
    return actions


def play_one(compiled, native, checkpoints, opening, candidate: str, foe: str, owner: int, game_id: str):
    session = GameSession(compiled)
    for action in opening:
        session.submit(action)
    root_sha = sha(session.state)
    root_result = session.result
    engines = {
        0: SemanticSearchEngine(compiled, native, checkpoint=checkpoints["candidate" if owner == 0 else "foe"], tt_megabytes=0),
        1: SemanticSearchEngine(compiled, native, checkpoint=checkpoints["candidate" if owner == 1 else "foe"], tt_megabytes=0),
    }
    moves = []
    candidate_plies = 0
    reason = "ACTUAL_TERMINAL" if root_result.status.value != "ongoing" else None
    while session.result.status.value == "ongoing" and candidate_plies < 96:
        poll()
        side = session.state.position.side_to_move
        role = "candidate" if side == owner else "foe"
        before = sha(session.state)
        start = time.perf_counter()
        result = engines[side].search(
            session,
            search_limits(role),
            root_window_pruning=PLAN["arms"]["root_window_pruning"],
        )
        caller_seconds = time.perf_counter() - start
        row = {
            "ply": len(moves), "side": side, "role": role, "state_before": before,
            "candidate_ply": candidate_plies + 1 if role == "candidate" else None,
            "action": None if result.action is None else record_value(result.action),
            "declaration_id": result.declaration_id,
            "score": result.score, "depth": result.completed_depth,
            "nodes": result.nodes, "qnodes": result.qnodes,
            "fallback": result.used_fallback, "cause": result.termination_reason,
            "kernel_seconds": result.elapsed_seconds, "caller_seconds": caller_seconds,
        }
        if result.declaration_id is not None:
            session.declare(result.declaration_id)
        elif result.action is not None and result.action in session.legal_actions():
            session.submit(result.action)
        else:
            reason = "NO_EXECUTABLE_RETURN_UNKNOWN"
            moves.append(row)
            break
        row["state_after"] = sha(session.state)
        moves.append(row)
        if role == "candidate":
            candidate_plies += 1
        if session.result.status.value != "ongoing":
            reason = "ACTUAL_TERMINAL"
    if session.result.status.value == "ongoing" and reason is None:
        reason = "HORIZON_96_CANDIDATE_UNKNOWN"
    replay = GameSession.replay(compiled, session.to_record())
    replay_equal = (
        replay.state == session.state
        and replay.history == session.history
        and replay._search_witnesses == session._search_witnesses
        and replay.result == session.result
    )
    if not replay_equal:
        raise RuntimeError(f"FULL_REPLAY_MISMATCH:{game_id}")
    winner = session.result.winner
    reward = None if reason.endswith("UNKNOWN") else (0 if winner is None else (1 if winner == owner else -1))
    return {
        "game_id": game_id, "candidate": candidate, "foe": foe, "candidate_owner": owner,
        "opening_actions": [record_value(a) for a in opening], "root_state_sha256": root_sha,
        "moves": moves, "move_count": len(moves), "terminal_reason": reason,
        "candidate_plies": candidate_plies,
        "winner": winner, "reward": reward,
        "final_record": json.loads(serialize_game_record(session.to_record())),
        "final_state_sha256": sha(session.state), "full_history_replay_equal": replay_equal,
        "queries": len(moves), "nodes": sum(int(r["nodes"]) for r in moves),
        "caller_seconds": sum(float(r["caller_seconds"]) for r in moves),
    }


def main():
    rules = {}
    roots = []
    for index, seed in enumerate(PLAN["rules"]["seeds"]):
        poll()
        cfg = GeneratorConfig(
            seed=seed,
            board_size=5,
            setup_preset=PLAN["rules"]["setups_by_seed_order"][index % 3],
            movement_symmetry=PLAN["rules"]["movement_symmetry_by_seed_order"][index % 2],
            allow_hybrid=True,
            require_promotable_type=True,
            require_nonpromotable_type=True,
            max_generation_attempts=16,
            require_no_opening_win_in_one=False,
        )
        generated = generate_game(cfg)
        compiled = compile_legacy_ruleset_for_semantic_execution(generated.ruleset)
        native = compile_native_semantic_rules(compiled)
        profile = build_ruleset_profile(compiled, EvaluationConfig())
        cps = {label: checkpoint(compiled, profile, label) for label in ("unit", "static_v2")}
        rule_id = str(seed)
        rules[rule_id] = {"config": asdict(cfg), "compiled": compiled, "native": native, "profile": profile, "checkpoints": cps, "ruleset": generated.ruleset}
        write_json(HERE / f"rule-{rule_id}.json", ruleset_to_dict(generated.ruleset))
        write_json(HERE / f"profile-{rule_id}.json", {"fingerprint": compiled.ruleset_fingerprint, "piece_profiles": profile.piece_profiles, "board": profile.board_value_by_type, "hand": profile.hand_value_by_base_type})
        for family in range(PLAN["roots"]["prefix_families_per_rule"]):
            prefix_seed = seed * 1_000_000 + family
            opening = make_opening(compiled, prefix_seed)
            roots.append({
                "root_id": f"{rule_id}-{family}",
                "rule_id": rule_id,
                "family": family,
                "prefix_seed": prefix_seed,
                "opening": opening,
                "root_sha256": sha(_opening_state(compiled, opening)),
            })
    write_json(HERE / "roots.json", [{k: v for k, v in r.items() if k != "opening"} | {"opening": [record_value(a) for a in r["opening"]]} for r in roots])
    source = {
        "schema": PLAN["schema"],
        "head": subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
        "plan_sha256": hashlib.sha256((HERE / "plan.json").read_bytes()).hexdigest(),
        "producer_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "started_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "rule_count": len(rules), "root_count": len(roots),
        "planned_physical_games": PLAN["arms"]["physical_games"],
    }
    write_json(HERE / "producer-source.json", source)
    games_path = HERE / "games.jsonl"
    queries_path = HERE / "queries.jsonl"
    returned = 0
    status, stop_reason = "COMPLETE", None
    with games_path.open("w", encoding="utf-8", newline="\n") as games_out, queries_path.open("w", encoding="utf-8", newline="\n") as queries_out:
        try:
            for root in roots:
                data = rules[root["rule_id"]]
                for foe in PLAN["arms"]["fixed_foes"]:
                    for candidate in PLAN["arms"]["candidates"]:
                        cps = {"candidate": data["checkpoints"][candidate], "foe": data["checkpoints"][foe]}
                        for owner in (0, 1):
                            poll()
                            game_id = f"{root['root_id']}|foe={foe}|candidate={candidate}|owner={owner}"
                            row = play_one(data["compiled"], data["native"], cps, root["opening"], candidate, foe, owner, game_id)
                            games_out.write(json.dumps(row, separators=(",", ":"), sort_keys=True) + "\n")
                            games_out.flush()
                            for q in row["moves"]:
                                queries_out.write(json.dumps({"game_id": game_id, **q}, separators=(",", ":"), sort_keys=True) + "\n")
                            queries_out.flush()
                            returned += 1
                            if returned % 16 == 0:
                                print(f"CLOSED_GAMES {returned}/{PLAN['arms']['physical_games']} seconds={time.monotonic()-STARTED:.1f}", flush=True)
        except (TimeoutError, InterruptedError) as exc:
            status, stop_reason = "INTERRUPTED", str(exc)
    rows = [json.loads(line) for line in games_path.read_text(encoding="utf-8").splitlines() if line]
    result = {
        "status": status, "stop_reason": stop_reason,
        "planned_physical_games": PLAN["arms"]["physical_games"],
        "returned_physical_games": returned,
        "unstarted_slots": PLAN["arms"]["physical_games"] - returned,
        "actual_terminals": sum(r["terminal_reason"] == "ACTUAL_TERMINAL" for r in rows),
        "unknown": sum(r["reward"] is None for r in rows),
        "queries": sum(r["queries"] for r in rows),
        "nodes": sum(r["nodes"] for r in rows),
        "caller_seconds": sum(r["caller_seconds"] for r in rows),
        "full_history_replay_mismatches": sum(not r["full_history_replay_equal"] for r in rows),
        "elapsed_seconds": time.monotonic() - STARTED,
        "scope": "Finite new 5x5 fixed-budget comparison only; no training, population claim, global price winner or default activation.",
    }
    write_json(HERE / "result.json", result)
    print(json.dumps(result, sort_keys=True), flush=True)


def _opening_state(compiled, opening):
    session = GameSession(compiled)
    for action in opening:
        session.submit(action)
    return session.state


if __name__ == "__main__":
    main()
