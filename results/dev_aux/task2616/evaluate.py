"""Task2616 fixed-slot Chess deployment, enforcing the registered per-slot cap."""
from pathlib import Path
from collections import Counter
import datetime, hashlib, json, sys, time

from results.dev_aux.task2504.search import TrainingSearch
from results.dev_aux.task2565.train import model, compiled, environment, prefix, restore
from results.dev_aux.task2392.reader import SharedDeleteStopReader

TASK = Path(__file__).resolve().parent
ROOT = Path.cwd()
def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def run(directory=None):
    d = TASK if directory is None else Path(directory)
    p = json.loads((d / "eval-plan.json").read_text(encoding="utf-8"))
    plan = json.loads((d / "plan.json").read_text(encoding="utf-8"))
    reg = json.loads((d / "registration.json").read_text(encoding="utf-8"))
    runreg = json.loads((d / "runner-registration.json").read_text(encoding="utf-8"))
    result = json.loads((d / "result.json").read_text(encoding="utf-8"))
    model_binding = json.loads((d / "model-binding.json").read_text(encoding="utf-8"))
    if sha(d / "plan.json") != reg["plan_sha256"] or sha(d / "eval-plan.json") != reg["eval_plan_sha256"]:
        raise RuntimeError("registered task/evaluation plan hash mismatch")
    if model_binding["assembled_result_sha256"] != sha(d / "result.json"):
        raise RuntimeError("assembled model binding mismatch")
    if model_binding["eval_plan_sha256"] != sha(d / "eval-plan.json") or model_binding["plan_sha256"] != sha(d / "plan.json"):
        raise RuntimeError("model binding is for different frozen inputs")
    if model_binding["tree_training_result_sha256"] != sha(d / "tree-training-result.json"):
        raise RuntimeError("TreeStrap training result changed after assembly")
    if model_binding["frozen_task2568_result_sha256"] != sha(ROOT / "results/dev_aux/task2568/result.json"):
        raise RuntimeError("frozen TD/WDL model source changed after assembly")
    if sha(d / "runner-registration.json") != reg["runner_registration_sha256"]:
        raise RuntimeError("runner registration changed")
    if sha(d / "root-manifest.json") != reg["root_manifest_sha256"]:
        raise RuntimeError("root manifest changed")
    for name, expected in runreg["runtime_pins"].items():
        if sha(ROOT / name) != expected:
            raise RuntimeError(f"runtime source changed: {name}")
    if (d / "eval-started.json").exists() or (d / "eval-games.jsonl").exists() or (d / "eval-queries.jsonl").exists():
        raise FileExistsError("refusing to overwrite evaluation evidence")

    arms = {(a["generator_seed"], a["seed"], a["method"]): a for a in result["arms"]}
    roots = {row["family"]: row["record"] for row in json.loads((d / "root-manifest.json").read_text(encoding="utf-8"))["roots"]}
    ccs = {gs: compiled(gs) for gs in p["rules"]}
    stop = SharedDeleteStopReader(ROOT)
    stop()
    began = time.perf_counter()
    binding = {
        "plan_sha256": sha(d / "eval-plan.json"), "task_plan_sha256": sha(d / "plan.json"),
        "assembled_result_sha256": sha(d / "result.json"),
        "runtime_pins": runreg["runtime_pins"],
        "slots_sha256": hashlib.sha256(json.dumps(p["slots"], separators=(",", ":")).encode()).hexdigest(),
        "started_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    }
    (d / "eval-binding.json").write_text(json.dumps(binding, indent=2) + "\n", encoding="utf-8")
    (d / "eval-started.json").write_text(json.dumps(binding, indent=2) + "\n", encoding="utf-8")
    rows, missing = [], []
    counters = Counter()
    status = "COMPLETE"
    with (d / "eval-games.jsonl").open("x", encoding="utf-8") as gf, (d / "eval-queries.jsonl").open("x", encoding="utf-8") as qf:
        for slot in p["slots"]:
            stop()
            gs, seed, family, color, endpoint, foe_name = slot
            key = (gs, seed, "TD" if endpoint == "initial" else endpoint)
            if key not in arms:
                missing.append(slot)
                continue
            if time.perf_counter() - began >= p["cap_seconds"]:
                status = "PARTIAL_CAP"
                break
            arm = arms[key]
            weights = arm["initial"] if endpoint == "initial" else arm["weights"]
            learner = model(p["domain"], weights)
            opponent = model(p["domain"], p["foes"][foe_name])
            env = environment(gs, ccs[gs])
            prefix(env, gs, family, p["prefix_plies"])
            initial_record = env.record()
            if initial_record != roots[family]:
                raise AssertionError("evaluation root differs from frozen exact-history manifest")
            nqueries = nodes = 0
            ending = "HORIZON_UNKNOWN"
            for ply in range(p["H"]):
                stop()
                if env.terminal() is not None:
                    ending = "ACTUAL_TERMINAL"
                    break
                global_left = p["cap_seconds"] - (time.perf_counter() - began)
                slot_left = p["node_budget_per_slot_both_actors"] - nodes
                if global_left <= 0:
                    ending, status = "GLOBAL_CAP_UNKNOWN", "PARTIAL_CAP"
                    break
                if slot_left <= 0:
                    ending = "SLOT_NODE_CAP_UNKNOWN"
                    break
                actor = env.player()
                current = learner if actor == color else opponent
                record_before = env.record()
                effective_nodes = min(p["nodes_per_query"], slot_left)
                effective_seconds = min(p["seconds_per_query"], global_left)
                ordering_seed = gs * 100000000 + family * 1000 + ply + p["ordering_seed_offset"]
                receipt = TrainingSearch(p["depth"], quiet=False, q_limit=p["q_limit"]).search(
                    env, current, nodes=effective_nodes, seconds=effective_seconds,
                    seed=ordering_seed, cancel=stop,
                )
                if env.record() != record_before:
                    raise AssertionError("evaluation search mutated full Chess history")
                nodes += receipt.nodes
                nqueries += 1
                if receipt.complete:
                    env.push(receipt.action)
                query = {
                    "slot": slot, "ply": ply, "actor": actor, "weights": list(current.weights),
                    "record_before": record_before, "record_after": env.record(),
                    "complete": receipt.complete,
                    "action": None if not receipt.complete else receipt.action.uci(),
                    "value": receipt.value,
                    "pv_phi": receipt.pv_phi, "pv_terminal": receipt.pv_terminal,
                    "nodes": receipt.nodes, "seconds": receipt.seconds,
                    "effective_nodes": effective_nodes, "effective_seconds": effective_seconds,
                    "ordering_seed": ordering_seed, "reason": receipt.reason,
                }
                qf.write(json.dumps(query, separators=(",", ":"), allow_nan=False) + "\n")
                qf.flush()
                if not receipt.complete:
                    ending = "SEARCH_RESOURCE_UNKNOWN"
                    break
            outcome = env.terminal()
            if outcome is not None:
                ending = "ACTUAL_TERMINAL"
            replay = restore(gs, ccs[gs], env.record())
            if replay.record() != env.record() or replay.terminal() != outcome:
                raise AssertionError("evaluation game replay mismatch")
            row = {
                "slot": slot, "weights": list(weights), "initial_record": initial_record,
                "record": env.record(), "outcome": outcome,
                "reward": None if outcome is None else outcome * (1 if color == 0 else -1),
                "ending": ending, "nodes": nodes, "queries": nqueries,
            }
            rows.append(row)
            gf.write(json.dumps(row, separators=(",", ":"), allow_nan=False) + "\n")
            gf.flush()
            counters.update(games=1, actual_terminal=outcome is not None, unknown=outcome is None,
                            nodes=nodes, queries=nqueries)
            if status != "COMPLETE":
                break
    seen = {tuple(row["slot"]) for row in rows}
    missing = [slot for slot in p["slots"] if tuple(slot) not in seen]
    summary = {
        "status": status, "expected": len(p["slots"]), "actual": len(rows),
        "missing": len(missing), "missing_slots": missing,
        "actual_terminal": counters["actual_terminal"], "unknown": counters["unknown"],
        "nodes": counters["nodes"], "queries": counters["queries"],
        "seconds": time.perf_counter() - began,
        "all_endpoints_and_unknowns_preserved": True,
    }
    (d / "eval-result.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    return summary

if __name__ == "__main__": print(json.dumps(run(), indent=2))
