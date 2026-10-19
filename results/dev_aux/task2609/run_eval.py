"""Bounded actual-terminal evaluation of frozen task2606 models."""
from pathlib import Path
import datetime, hashlib, json, sys, time
from results.dev_aux.task2606.train import compiled, environment, model, prefix, restore
from results.dev_aux.task2504.search import TrainingSearch
from results.dev_aux.task2392.reader import SharedDeleteStopReader


def run(directory):
    d = Path(directory)
    plan = json.loads((d / "eval-plan.json").read_text(encoding="utf-8"))
    reg = json.loads((d / "registration.json").read_text(encoding="utf-8"))
    manifest = json.loads((d / "root-manifest.json").read_text(encoding="utf-8"))
    train_path = Path("results/dev_aux/task2606/result.json")
    train = json.loads(train_path.read_text(encoding="utf-8"))
    assert reg["state"] == "REGISTERED_BEFORE_EVALUATION" and train["status"] == "COMPLETE"
    assert hashlib.sha256((d / "eval-plan.json").read_bytes()).hexdigest() == reg["eval_plan_sha256"]
    assert hashlib.sha256((d / "root-manifest.json").read_bytes()).hexdigest() == reg["root_manifest_sha256"]
    assert hashlib.sha256(train_path.read_bytes()).hexdigest() == reg["model_result_sha256"]
    for name, digest in reg["source_pins"].items():
        assert hashlib.sha256(Path(name).read_bytes()).hexdigest() == digest, name
    arms = {(arm["generator_seed"], arm["seed"], arm["method"]): arm for arm in train["arms"]}
    assert len(arms) == 32 and len(plan["slots"]) == reg["expected_slots"] == 1536
    assert plan["prefix_plies"] == manifest["prefix_plies"] == 4 and len(manifest["roots"]) == 64
    assert not (d / "eval-started.json").exists()

    # Preflight every frozen root before writing eval-started or any outcomes.
    compilers = {rule: compiled(rule) for rule in plan["rules"]}
    for rule in plan["rules"]:
        for family in manifest["selected_families"][str(rule)]:
            env = environment(rule, compilers[rule])
            prefix(env, rule, family, plan["prefix_plies"])
            assert env.record() == manifest["roots"][f"{rule}:{family}"] and env.terminal() is None

    binding = {"models_sha256": reg["model_result_sha256"], "plan_sha256": reg["eval_plan_sha256"],
               "root_manifest_sha256": reg["root_manifest_sha256"], "models": len(arms),
               "preflight_roots": len(manifest["roots"]), "prefix_plies": plan["prefix_plies"]}
    (d / "eval-binding.json").write_text(json.dumps(binding, indent=2), encoding="utf-8")
    stop = SharedDeleteStopReader(Path.cwd())
    stop()
    (d / "eval-started.json").write_text(json.dumps({"utc": datetime.datetime.now(datetime.timezone.utc).isoformat()}), encoding="utf-8")
    began, games, status = time.perf_counter(), [], "COMPLETE"
    with (d / "eval-games.jsonl").open("x", encoding="utf-8") as game_file, (d / "eval-queries.jsonl").open("x", encoding="utf-8") as query_file:
        for slot in plan["slots"]:
            rule, seed, family, color, endpoint, foe_name = slot
            td_arm = arms[(rule, seed, "TD95")]
            weights = td_arm["initial"] if endpoint == "initial" else arms[(rule, seed, endpoint)]["weights"]
            learner, foe = model("generic", weights), model("generic", plan["foes"][foe_name])
            env = environment(rule, compilers[rule])
            prefix(env, rule, family, plan["prefix_plies"])
            initial, nodes, queries, ending = env.record(), 0, 0, "HORIZON_UNKNOWN"
            assert initial == manifest["roots"][f"{rule}:{family}"]
            if time.perf_counter() - began >= plan["cap_seconds"]:
                status = "PARTIAL_CAP"
                break
            for ply in range(plan["H"]):
                stop()
                if env.terminal() is not None:
                    ending = "ACTUAL_TERMINAL"
                    break
                wall = plan["cap_seconds"] - (time.perf_counter() - began)
                if wall <= 0:
                    ending, status = "GLOBAL_CAP_UNKNOWN", "PARTIAL_CAP"
                    break
                actor, before = env.player(), env.record()
                current = learner if actor == color else foe
                order = rule * 100000000 + family * 1000 + ply + 972609000
                result = TrainingSearch(plan["depth"], quiet=False).search(
                    env, current, nodes=plan["nodes_per_query"],
                    seconds=min(wall, plan["seconds_per_query"]), seed=order, cancel=stop)
                assert env.record() == before
                nodes += result.nodes
                queries += 1
                if result.complete:
                    env.push(result.action)
                query_file.write(json.dumps({
                    "slot": slot, "ply": ply, "actor": actor, "weights": list(current.weights),
                    "record_before": before, "record_after": env.record(), "complete": result.complete,
                    "value": result.value, "pv_phi": result.pv_phi, "pv_terminal": result.pv_terminal,
                    "nodes": result.nodes, "seconds": result.seconds, "ordering_seed": order,
                    "reason": result.reason,
                }, separators=(",", ":")) + "\n")
                query_file.flush()
                if not result.complete:
                    ending = "SEARCH_RESOURCE_UNKNOWN"
                    break
            actual = env.terminal()
            if actual is not None:
                ending = "ACTUAL_TERMINAL"
            replay = restore(rule, compilers[rule], env.record())
            assert replay.record() == env.record() and replay.terminal() == actual
            row = {"slot": slot, "weights": weights, "initial_record": initial, "record": env.record(),
                   "outcome": actual, "reward": None if actual is None else actual * (1 if color == 0 else -1),
                   "ending": ending, "nodes": nodes, "queries": queries}
            games.append(row)
            game_file.write(json.dumps(row, separators=(",", ":")) + "\n")
            game_file.flush()
            if len(games) % 16 == 0:
                print(json.dumps({"games": len(games), "seconds": time.perf_counter() - began}), flush=True)
            if status != "COMPLETE":
                break

    completed = {tuple(game["slot"]) for game in games}
    missing = [slot for slot in plan["slots"] if tuple(slot) not in completed]
    result = {"status": status, "expected": len(plan["slots"]), "actual": len(games),
              "missing": len(missing), "missing_slots": missing,
              "actual_terminal": sum(game["outcome"] is not None for game in games),
              "unknown": sum(game["outcome"] is None for game in games),
              "nodes": sum(game["nodes"] for game in games),
              "queries": sum(game["queries"] for game in games), "seconds": time.perf_counter() - began}
    (d / "eval-result.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps({key: value for key, value in result.items() if key != "missing_slots"}))


if __name__ == "__main__":
    run(sys.argv[1])
