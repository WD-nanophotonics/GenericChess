"""Task2616: capped Chess TreeStrap fit using the registered fixed-foe recipe."""
from pathlib import Path
from collections import Counter
import datetime, hashlib, json, math, sys, time

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from results.dev_aux.task2492.adapters import ChessEnv
from results.dev_aux.task2492.learning import Model, TreeStrap
from results.dev_aux.task2504.search import TrainingSearch
from results.dev_aux.task2565.train import prefix, restore
from results.dev_aux.task2392.reader import SharedDeleteStopReader

TASK = Path(__file__).resolve().parent
ROOT = Path.cwd()

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def encode_bound(x):
    if math.isinf(x):
        return "+inf" if x > 0 else "-inf"
    return x

def initial(seed):
    import random
    r = random.Random(seed)
    return [1.0] + [r.uniform(0.5, 1.5) for _ in range(4)]

def candidate_update(learner, model, actor, candidate_color, receipt):
    """Only complete candidate-color receipts contribute internal tree samples."""
    if actor != candidate_color or not receipt.complete:
        return None
    return learner.update(model, receipt)

def run(directory=None):
    d = TASK if directory is None else Path(directory)
    plan = json.loads((d / "plan.json").read_text(encoding="utf-8"))
    training = plan["conditions"]["training"]
    reg = json.loads((d / "registration.json").read_text(encoding="utf-8"))
    runreg = json.loads((d / "runner-registration.json").read_text(encoding="utf-8"))
    session = json.loads(Path(".local_agent/session.json").read_text(encoding="utf-8"))
    if session.get("state") != "active":
        raise RuntimeError("own research session is not active")
    if reg.get("status") != "REGISTERED_PRE_RUN" or runreg.get("status") != "READY_PRE_RUN":
        raise RuntimeError("task2616 is not registered and source-pinned for first execution")
    if sha(d / "plan.json") != reg["plan_sha256"]:
        raise RuntimeError("registered experiment plan hash mismatch")
    if sha(d / "eval-plan.json") != reg["eval_plan_sha256"]:
        raise RuntimeError("registered evaluation plan hash mismatch")
    if sha(d / "root-manifest.json") != reg["root_manifest_sha256"]:
        raise RuntimeError("registered root manifest hash mismatch")
    if sha(d / "runner-registration.json") != reg["runner_registration_sha256"]:
        raise RuntimeError("runner registration hash mismatch")
    if runreg.get("plan_sha256") != reg["plan_sha256"] or runreg.get("eval_plan_sha256") != reg["eval_plan_sha256"]:
        raise RuntimeError("runner registration is for a different frozen plan")
    for name, expected in runreg["runtime_pins"].items():
        if sha(ROOT / name) != expected:
            raise RuntimeError(f"runtime source changed: {name}")
    for output in ("tree-started.json", "tree-queries.jsonl", "tree-games.jsonl", "tree-training-result.json"):
        if (d / output).exists():
            raise RuntimeError(f"refusing to overwrite existing evidence: {output}")

    stop = SharedDeleteStopReader(ROOT)
    stop()
    began = time.perf_counter()
    started = {
        "utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "plan_sha256": sha(d / "plan.json"),
        "eval_plan_sha256": sha(d / "eval-plan.json"),
        "runner_registration_sha256": sha(d / "runner-registration.json"),
        "session_id": session["id"],
        "runtime_pins": runreg["runtime_pins"],
        "caps": {"training_global_seconds": training["global_hard_cap_seconds"], "nodes_per_seed_both_actors": training["node_budget_per_seed_both_actors"]},
    }
    (d / "tree-started.json").write_text(json.dumps(started, indent=2) + "\n", encoding="utf-8")
    counts = Counter()
    arms = []
    status = "COMPLETE"
    with (d / "tree-queries.jsonl").open("x", encoding="utf-8") as qf, (d / "tree-games.jsonl").open("x", encoding="utf-8") as gf:
        for seed in plan["conditions"]["seeds"]:
            stop()
            weights0 = initial(seed)
            model = Model(weights0)
            learner = TreeStrap(eta=0.05)
            foe = Model(training["fixed_foe"])
            used = games = updates = observations = sample_count = active_count = 0
            weighted_loss = 0.0
            snapshots = []
            arm_began = time.perf_counter()
            max_games = training["max_games_per_seed"]
            node_budget = training["node_budget_per_seed_both_actors"]
            global_cap = training["global_hard_cap_seconds"]
            for index in range(max_games):
                if used >= node_budget or time.perf_counter() - began >= global_cap:
                    break
                stop()
                color = index % 2
                family = training["training_family_offset"] + index // 2
                env = ChessEnv()
                prefix(env, 0, family, 8)
                first = env.record()
                before = list(model.weights)
                game_nodes = used
                nq = candidate_receipts = 0
                ending = "HORIZON_UNKNOWN"
                for ply in range(training["H"]):
                    stop()
                    terminal = env.terminal()
                    if terminal is not None:
                        ending = "ACTUAL_TERMINAL"
                        break
                    remaining = min(node_budget - used, training["nodes_per_game"] - (used - game_nodes))
                    wall = global_cap - (time.perf_counter() - began)
                    if remaining <= 0 or wall <= 0:
                        ending = "AGGREGATE_CAP_UNKNOWN"
                        break
                    actor = env.player()
                    current = model if actor == color else foe
                    played_weights = list(current.weights)
                    record_before = env.record()
                    effective_nodes = min(remaining, training["nodes_per_query"])
                    effective_seconds = min(wall, training["seconds_per_query"])
                    ordering_seed = family * 1000 + ply + training["ordering_seed_offset"]
                    receipt = TrainingSearch(training["depth"], quiet=False, q_limit=training["q_limit"]).search(
                        env, current, nodes=effective_nodes, seconds=effective_seconds,
                        seed=ordering_seed, cancel=stop,
                    )
                    if env.record() != record_before:
                        raise AssertionError("search mutated the Chess history")
                    used += receipt.nodes
                    nq += 1
                    update = candidate_update(learner, model, actor, color, receipt)
                    observed = update is not None
                    sample_rows = []
                    if observed:
                        candidate_receipts += 1
                        observations += 1
                        sample_count += update["samples"]
                        active_count += update["active"]
                        if update["loss"] is not None:
                            weighted_loss += update["loss"] * update["samples"]
                        updates += int(update["changed"])
                        for sample in receipt.samples:
                            sample_rows.append({
                                "phi": sample.phi,
                                "lower": encode_bound(sample.lower),
                                "upper": encode_bound(sample.upper),
                                "depth": sample.depth,
                            })
                    if receipt.complete:
                        env.push(receipt.action)
                    q = {
                        "seed": seed, "game_index": index, "family": family, "color": color,
                        "ply": ply, "actor": actor, "observed": observed,
                        "weights_used": played_weights, "record_before": record_before,
                        "record_after": env.record(), "complete": receipt.complete,
                        "action": None if not receipt.complete else receipt.action.uci(),
                        "value": receipt.value, "pv_phi": receipt.pv_phi,
                        "pv_terminal": receipt.pv_terminal, "nodes": receipt.nodes,
                        "total_nodes": used, "seconds": receipt.seconds,
                        "effective_nodes": effective_nodes, "effective_seconds": effective_seconds,
                        "ordering_seed": ordering_seed, "reason": receipt.reason,
                        "update": update, "samples": sample_rows,
                    }
                    qf.write(json.dumps(q, separators=(",", ":"), allow_nan=False) + "\n")
                    qf.flush()
                    if not receipt.complete:
                        ending = "SEARCH_RESOURCE_UNKNOWN"
                        break
                outcome = env.terminal()
                if outcome is not None:
                    ending = "ACTUAL_TERMINAL"
                replay = restore(0, None, env.record())
                if replay.record() != env.record() or replay.terminal() != outcome:
                    raise AssertionError("Chess game replay mismatch")
                games += 1
                game = {
                    "seed": seed, "index": index, "family": family, "color": color,
                    "initial_weights": before, "weights": list(model.weights),
                    "initial_record": first, "record": env.record(), "outcome": outcome,
                    "ending": ending, "nodes": used - game_nodes, "total_nodes": used,
                    "queries": nq, "candidate_complete_receipts": candidate_receipts,
                }
                gf.write(json.dumps(game, separators=(",", ":"), allow_nan=False) + "\n")
                gf.flush()
                counts.update(games=1, actual_terminal=outcome is not None, unknown=outcome is None,
                              queries=nq, nodes=game["nodes"], candidate_complete_receipts=candidate_receipts)
                for boundary in (250000, 500000, 750000):
                    if used >= boundary and not any(row["boundary"] == boundary for row in snapshots):
                        snapshots.append({"boundary": boundary, "nodes": used, "game_index": index,
                                          "weights": list(model.weights)})
                if ending == "AGGREGATE_CAP_UNKNOWN" or time.perf_counter() - began >= global_cap:
                    break
            arm = {
                "generator_seed": 0, "seed": seed, "method": "TreeStrap",
                "initial": weights0, "weights": list(model.weights), "nodes": used,
                "games": games, "updates": updates, "observations": observations,
                "samples": sample_count, "active_samples": active_count,
                "mean_one_sided_loss": weighted_loss / sample_count if sample_count else None,
                "snapshots": snapshots, "seconds": time.perf_counter() - arm_began,
                "cause": "TOTAL_NODES" if used == training["node_budget_per_seed_both_actors"] else
                         "GLOBAL_CAP" if time.perf_counter() - began >= global_cap else "MAX_GAMES",
            }
            arms.append(arm)
            print(json.dumps(arm, allow_nan=False), flush=True)
            if time.perf_counter() - began >= global_cap:
                status = "PARTIAL_CAP"
                break
    result = {
        "status": status if len(arms) == len(plan["conditions"]["seeds"]) else "PARTIAL_CAP",
        "expected_arms": len(plan["conditions"]["seeds"]), "arms": arms,
        "nodes": sum(arm["nodes"] for arm in arms), "seconds": time.perf_counter() - began,
        "counts": dict(counts), "training_loss_is_diagnostic_not_selection": True,
        "actual_outcomes_are_recorded_not_used_for_tree_updates": True,
        "unknown": "Incomplete search receipts do not update; nonterminal game endings are censored, never draws.",
    }
    (d / "tree-training-result.json").write_text(json.dumps(result, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in result.items() if k != "arms"}, allow_nan=False), flush=True)
    return result

if __name__ == "__main__":
    run(sys.argv[1] if len(sys.argv) > 1 else None)

