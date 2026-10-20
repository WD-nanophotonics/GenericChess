"""One-shot matched actual-terminal evaluation of initialization vs TDLeaf."""
from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.schema import ruleset_from_dict
from generic_chess.session.serialization import deserialize_game_record
from generic_chess.session.session import GameSession
from results.dev_aux.task2392.reader import SharedDeleteStopReader
from results.dev_aux.task2492.learning import AlphaBeta
from results.dev_aux.task2511.generic import NonScoringTerminal
from results.dev_aux.task2621.fixed_scale import FixedScaleSessionEnv, unchanged_model
from tools.local_agent.environment import require_identity

RUN = ROOT / "results/dev_aux/task2623/run"
RULES = (271001, 271002, 271003, 271004)
SEEDS = (1977, 8173, 27182, 31415)
ENDPOINTS = ("initial", "TDLeaf")


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def write_once(path: Path, value: dict) -> None:
    with path.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False)
        stream.write("\n")


def validate_plan_contract(plan: dict) -> None:
    evaluation = plan["evaluation"]
    search = plan["search"]
    required_evaluation = {"slots", "H", "hard_seconds", "node_cap_by_rule_family"}
    if not required_evaluation.issubset(evaluation):
        raise ValueError(f"registered evaluation plan is missing fields: {sorted(required_evaluation - set(evaluation))}")
    if evaluation["slots"] != len(RULES) * len(SEEDS) * 16 * 2 * len(ENDPOINTS):
        raise ValueError("registered evaluation slot count is invalid")
    if evaluation["H"] <= 0 or evaluation["hard_seconds"] <= 0:
        raise ValueError("registered evaluation traversal/time budget is invalid")
    if len(evaluation["node_cap_by_rule_family"]) != len(RULES) * 16:
        raise ValueError("registered evaluation family caps are incomplete")
    if search["nodes_per_query"] <= 0 or search["depth"] <= 0:
        raise ValueError("registered search budget is invalid")


def run() -> dict:
    require_identity()
    plan_path, reg_path = RUN / "plan.json", RUN / "registration.json"
    plan, reg = json.loads(plan_path.read_text(encoding="utf-8")), json.loads(reg_path.read_text(encoding="utf-8"))
    validate_plan_contract(plan)
    eval_reg_path = RUN / "evaluation-registration.json"
    eval_reg = json.loads(eval_reg_path.read_text(encoding="utf-8"))
    training_path = RUN / "training-result.json"
    training = json.loads(training_path.read_text(encoding="utf-8"))
    if training.get("status") != "COMPLETE" or len(training.get("arms", [])) != 16:
        raise ValueError("evaluation requires all 16 registered training arms at their node caps")
    if sha(plan_path.read_bytes()) != reg["plan_sha256"]:
        raise ValueError("study plan changed")
    if sha(training_path.read_bytes()) != eval_reg.get("training_result_sha256"):
        raise ValueError("training result hash differs from evaluation registration")
    if eval_reg.get("state") != "EVALUATION_BOUND_BEFORE_FIRST_SLOT" or eval_reg.get("plan_sha256") != reg["plan_sha256"]:
        raise ValueError("evaluation was not bound before the first slot")
    for path, expected in reg["source_pins"].items():
        if sha((ROOT / path).read_bytes()) != expected:
            raise ValueError(f"registered source changed: {path}")
    if (RUN / "eval-started.json").exists() or (RUN / "eval-games.jsonl").exists() or (RUN / "eval-queries.jsonl").exists():
        raise FileExistsError("one-shot evaluation output exists; no retry/top-up")
    arm_index = {(a["rule"], a["seed"]): a for a in training["arms"]}
    if len(arm_index) != 16 or set(arm_index) != {(r, s) for r in RULES for s in SEEDS}:
        raise ValueError("unexpected training arm set")
    for (rule, seed), arm in arm_index.items():
        if arm["initial_weights"] != plan["initialization"]["weights_by_rule_seed"][f"{rule}:{seed}"]:
            raise ValueError("training initialization differs from frozen plan")

    pool = json.loads((ROOT / "results/dev_aux/task2622/root-pools-v2.json").read_text(encoding="utf-8"))
    roots = {r: [row for row in pool["evaluation_roots"] if row["rule"] == r] for r in RULES}
    if any(len(rows) != 16 for rows in roots.values()):
        raise ValueError("evaluation root pool mismatch")
    caps = plan["evaluation"]["node_cap_by_rule_family"]
    slots = []
    for rule in RULES:
        for seed in SEEDS:
            for row in roots[rule]:
                for color in (0, 1):
                    for endpoint in ENDPOINTS:
                        slots.append([rule, seed, row["family"], color, endpoint])
    if len(slots) != plan["evaluation"]["slots"] or len(set(tuple(s) for s in slots)) != len(slots):
        raise ValueError("evaluation slot plan is inconsistent")

    compilers = {}
    for rule in RULES:
        raw = (ROOT / f"results/dev_aux/task2525/rules-{rule}.json").read_bytes()
        if sha(raw) != reg["source_pins"][f"results/dev_aux/task2525/rules-{rule}.json"]:
            raise ValueError(f"rule source changed: {rule}")
        compilers[rule] = compile_ruleset_for_execution(ruleset_from_dict(json.loads(raw)))
    stop = SharedDeleteStopReader(ROOT)
    stop()
    began = time.perf_counter()
    start_receipt = {"started_utc": __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat(),
                     "plan_sha256": reg["plan_sha256"], "training_result_sha256": eval_reg["training_result_sha256"],
                     "root_pools_sha256": reg["root_pools_sha256"], "expected_slots": len(slots)}
    write_once(RUN / "eval-started.json", start_receipt)
    rows = []
    status = "COMPLETE"
    with (RUN / "eval-games.jsonl").open("x", encoding="utf-8") as gout, \
         (RUN / "eval-queries.jsonl").open("x", encoding="utf-8") as qout:
        for slot in slots:
            rule, seed, family, learner_color, endpoint = slot
            if time.perf_counter() - began >= plan["evaluation"]["hard_seconds"]:
                status = "PARTIAL_GLOBAL_TIME_CAP"
                break
            arm = arm_index[(rule, seed)]
            weights = arm["initial_weights"] if endpoint == "initial" else arm["final_weights"]
            dimension = len(weights)
            learner = unchanged_model(weights)
            foe = unchanged_model([1.0] * dimension)
            root = next(r for r in roots[rule] if r["family"] == family)
            env = FixedScaleSessionEnv(GameSession.replay(compilers[rule],
                deserialize_game_record(json.dumps(root["record"]))))
            if env.record() != root["record"]:
                raise ValueError("evaluation root failed full-history replay")
            initial_record = env.record()
            slot_cap = caps[f"{rule}:{family}"]
            nodes = queries = 0
            ending = "HORIZON_UNKNOWN"
            try:
                for ply in range(plan["evaluation"]["H"]):
                    stop()
                    try:
                        terminal = env.terminal()
                    except NonScoringTerminal:
                        ending = "NON_SCORING_UNKNOWN"
                        break
                    if terminal is not None:
                        ending = "ACTUAL_TERMINAL"
                        break
                    remaining = slot_cap - nodes
                    if remaining <= 0:
                        ending = "NODE_CAP_UNKNOWN"
                        break
                    actor = env.player()
                    current = learner if actor == learner_color else foe
                    before = env.record()
                    state = env.session.state
                    request = min(plan["search"]["nodes_per_query"], remaining)
                    receipt = AlphaBeta(plan["search"]["depth"], 0).search(
                        env, current, nodes=request, seconds=plan["search"]["seconds_per_query"],
                        seed=plan["search"]["ordering_seed_base"] + rule * 1_000_000 + seed * 1000 + family * 10 + learner_color * 2 + (endpoint == "TDLeaf") + ply,
                        cancel=stop)
                    if env.record() != before or env.session.state != state:
                        raise AssertionError("evaluation search mutated full history")
                    nodes += receipt.nodes
                    queries += 1
                    if receipt.complete:
                        env.push(receipt.action)
                    qrow = {"slot": slot, "ply": ply, "actor": actor,
                            "weights": list(current.weights), "record_before": before,
                            "record_after": env.record(), "complete": receipt.complete,
                            "value": receipt.value, "pv_phi": receipt.pv_phi,
                            "pv_terminal": receipt.pv_terminal, "nodes": receipt.nodes,
                            "requested_nodes": request, "seconds": receipt.seconds,
                            "search_reason": receipt.reason}
                    qout.write(json.dumps(qrow, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n")
                    qout.flush()
                    if not receipt.complete:
                        ending = "SEARCH_RESOURCE_UNKNOWN"
                        break
                    env.replay()
                try:
                    actual = env.terminal()
                except NonScoringTerminal:
                    actual, ending = None, "NON_SCORING_UNKNOWN"
                if actual is not None:
                    ending = "ACTUAL_TERMINAL"
                reward = None if actual is None else actual * (1 if learner_color == 0 else -1)
                row = {"slot": slot, "weights": list(weights), "initial_record": initial_record,
                       "final_record": env.record(), "actual_outcome": actual, "reward": reward,
                       "ending": ending, "nodes": nodes, "queries": queries,
                       "node_cap": slot_cap}
                rows.append(row)
                gout.write(json.dumps(row, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n")
                gout.flush()
                if nodes > slot_cap:
                    raise AssertionError("evaluation slot exceeded its combined two-side node cap")
            except BaseException:
                raise
            if len(rows) % 64 == 0:
                print(json.dumps({"completed_slots": len(rows), "expected_slots": len(slots),
                                  "seconds": time.perf_counter() - began}), flush=True)

    seen = {tuple(row["slot"]) for row in rows}
    missing = [slot for slot in slots if tuple(slot) not in seen]
    result = {"status": status, "expected_slots": len(slots), "completed_slots": len(rows),
              "missing_slots": missing, "missing": len(missing),
              "actual_terminal": sum(row["actual_outcome"] is not None for row in rows),
              "UNKNOWN": sum(row["actual_outcome"] is None for row in rows),
              "nodes": sum(row["nodes"] for row in rows),
              "queries": sum(row["queries"] for row in rows),
              "seconds": time.perf_counter() - began,
              "training_result_sha256": eval_reg["training_result_sha256"],
              "plan_sha256": reg["plan_sha256"], "scope": plan["scope"]}
    write_once(RUN / "eval-result.json", result)
    print(json.dumps({k: v for k, v in result.items() if k != "missing_slots"}, indent=2, sort_keys=True))
    return result


if __name__ == "__main__":
    run()
