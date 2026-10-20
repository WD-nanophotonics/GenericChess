"""Outcome-blind material-feature excitation scan for task2633 rules."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import random
import sys
import time

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.serialization import deserialize_ruleset
from generic_chess.session.session import GameSession
from generic_chess.session.serialization import deserialize_game_record
from results.dev_aux.task2392.reader import SharedDeleteStopReader
from results.dev_aux.task2621.fixed_scale import FixedScaleSessionEnv
from tools.local_agent.environment import require_identity

TASK = ROOT / "results/dev_aux/task2635"
DEFAULT_PLAN = TASK / "plan.json"


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def write(path: Path, value: dict) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")


def check_cancel(stop_reader, started: float, plan: dict) -> None:
    stop_reader()
    if time.perf_counter() - started >= plan["hard_wall_cap_seconds"]:
        raise TimeoutError("task2635 reached its hard wall cap")


def run(plan_path: Path = DEFAULT_PLAN, output_path: Path | None = None) -> dict:
    require_identity()
    plan_path = plan_path.resolve()
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    out = output_path or (TASK / "run")
    if out.exists():
        raise FileExistsError("task2635 is write-once; no retry/top-up")
    expected_runner = plan.get("runner_sha256")
    if expected_runner and sha(Path(__file__).read_bytes()) != expected_runner:
        raise ValueError("runner source changed after plan freeze")
    candidate_index_path = ROOT / plan["candidate_index"]
    index_raw = candidate_index_path.read_bytes()
    if sha(index_raw) != plan["candidate_index_sha256"]:
        raise ValueError("candidate index changed after plan freeze")
    for rel, expected in plan["source_sha256"].items():
        if sha((ROOT / rel).read_bytes()) != expected:
            raise ValueError(f"pinned source changed: {rel}")
    out.mkdir(parents=True)
    started = time.perf_counter()
    stop_reader = SharedDeleteStopReader(ROOT)
    index = json.loads(index_raw)
    episodes = []
    aborted = None

    with (out / "episodes.jsonl").open("x", encoding="utf-8") as stream:
        for candidate_index, candidate in enumerate(index["rows"]):
            path = ROOT / candidate["source_file"]
            raw = path.read_bytes()
            if sha(raw) != candidate["ruleset_sha256"]:
                raise ValueError(f"candidate rules changed: {path}")
            compiled = compile_ruleset_for_execution(deserialize_ruleset(raw.decode("utf-8")))
            for replicate in range(plan["trajectories_per_candidate"]):
                try:
                    check_cancel(stop_reader, started, plan)
                    env = FixedScaleSessionEnv(GameSession(compiled), unit_type="P")
                    seed = plan["trajectory_seed_start"] + candidate_index * plan["trajectories_per_candidate"] + replicate
                    rng = random.Random(seed)
                    initial = tuple(env.features())
                    first_nonzero_ply = None
                    max_l1 = 0
                    ply = 0
                    ending = "PLY_CAP_UNKNOWN"
                    while ply < plan["max_plies"]:
                        check_cancel(stop_reader, started, plan)
                        legal = sorted((choice for choice in env.actions() if choice.kind == "ACTION"), key=repr)
                        if not legal:
                            ending = "NO_BOARD_ACTION_UNKNOWN"
                            break
                        env.push(rng.choice(legal))
                        ply += 1
                        features = tuple(env.features())
                        l1 = sum(abs(value) for value in features)
                        max_l1 = max(max_l1, l1)
                        if first_nonzero_ply is None and any(features):
                            first_nonzero_ply = ply
                    record = env.record()
                    replayed = GameSession.replay(compiled, deserialize_game_record(json.dumps(record)))
                    if replayed.to_record() != env.session.to_record() or replayed.state != env.session.state:
                        raise AssertionError("complete generated history did not replay exactly")
                    row = {
                        "candidate_index": candidate_index,
                        "seed": seed,
                        "ruleset_sha256": candidate["ruleset_sha256"],
                        "replicate": replicate,
                        "plies": ply,
                        "ending": ending,
                        "initial_features": list(initial),
                        "first_nonzero_feature_ply": first_nonzero_ply,
                        "max_material_feature_l1": max_l1,
                        "channels": [list(name) for name in env.names],
                        "full_history_record": record,
                        "full_history_replay": True,
                        "outcome_read": False,
                    }
                    stream.write(json.dumps(row, sort_keys=True, allow_nan=False) + "\n")
                    stream.flush()
                    episodes.append({key: value for key, value in row.items() if key != "full_history_record"})
                except (TimeoutError, RuntimeError) as exc:
                    aborted = type(exc).__name__ + ": " + str(exc)
                    break
            if aborted:
                break

    activations = [row["first_nonzero_feature_ply"] for row in episodes if row["first_nonzero_feature_ply"] is not None]
    result = {
        "status": "COMPLETE" if len(episodes) == PLAN["candidate_count"] * PLAN["trajectories_per_candidate"] else "PARTIAL_STOP_OR_CAP",
        "plan_sha256": sha(plan_path.read_bytes()),
        "candidate_index_sha256": sha(index_raw),
        "episodes_expected": plan["candidate_count"] * plan["trajectories_per_candidate"],
        "episodes_completed": len(episodes),
        "feature_activated_episodes": len(activations),
        "first_activation_ply_min": min(activations) if activations else None,
        "first_activation_ply_median": sorted(activations)[len(activations) // 2] if activations else None,
        "first_activation_ply_max": max(activations) if activations else None,
        "no_board_action_unknown": sum(row["ending"] == "NO_BOARD_ACTION_UNKNOWN" for row in episodes),
        "ply_cap_unknown": sum(row["ending"] == "PLY_CAP_UNKNOWN" for row in episodes),
        "full_history_replay_passed": all(row["full_history_replay"] for row in episodes),
        "outcome_reads": 0,
        "search_queries": 0,
        "seconds": time.perf_counter() - started,
        "abort_reason": aborted,
        "scope": "Outcome-blind uniform legal board-action feasibility only. No WDL, search, model/learner construction or update, training, evaluation, population-frequency claim, or root admission. All emitted histories are exposed and must be excluded from future pools.",
        "episodes": episodes,
    }
    write(out / "result.json", result)
    print(json.dumps({key: value for key, value in result.items() if key != "episodes"}, indent=2))
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--plan", type=Path, default=DEFAULT_PLAN)
    parser.add_argument("--output", type=Path, default=TASK / "run")
    args = parser.parse_args()
    run(args.plan, args.output)
