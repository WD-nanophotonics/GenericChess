"""Family-cap randomized Chess evaluation for task2617.

The runner is inert until a separate run directory has a valid pre-run
registration. It preserves actual W/D/L, censors UNKNOWN, and pays the same
pre-assigned per-slot cap from both players' combined search nodes.
"""
from __future__ import annotations

from collections import Counter
from itertools import product
import datetime
import hashlib
from importlib.metadata import version
import json
from pathlib import Path
import sys
import time
import platform

from results.dev_aux.task2504.search import TrainingSearch
from results.dev_aux.task2565.train import compiled, environment, model, prefix, restore
from results.dev_aux.task2392.reader import SharedDeleteStopReader


TASK = Path(__file__).resolve().parent
ROOT = Path.cwd()


def sha(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def slot_key(slot: list) -> tuple:
    return tuple(slot)


def family_cap(plan: dict, family: int) -> int:
    """Resolve the frozen both-actor cap for a registered family."""
    try:
        cap = plan["caps_by_family"][str(family)]
    except KeyError as exc:
        raise ValueError(f"family has no registered cap: {family}") from exc
    allowed = set(plan["cap_values_nodes_both_sides"])
    if cap not in allowed:
        raise ValueError(f"unregistered node cap {cap} for family {family}")
    return cap


def terminal_reward(outcome: int | None, learner_color: int) -> int | None:
    """Return actual terminal W/D/L from learner perspective; censor UNKNOWN."""
    if learner_color not in (0, 1):
        raise ValueError("learner color must be 0 or 1")
    if outcome is None:
        return None
    if outcome not in (-1, 0, 1):
        raise ValueError(f"invalid terminal outcome: {outcome}")
    return outcome if learner_color == 0 else -outcome


def validate_slots(slots: list, plan: dict, eval_plan: dict) -> None:
    """Require the exact frozen cross product and balanced family assignments."""
    families = set(map(int, plan["caps_by_family"]))
    expected = {
        (rule, seed, family, color, endpoint, foe)
        for rule, seed, family, color, endpoint, foe in product(
            eval_plan["rules"], eval_plan["seeds"], families, (0, 1),
            eval_plan["endpoints"], eval_plan["foes"],
        )
    }
    actual = {slot_key(s) for s in slots if isinstance(s, list) and len(s) == 6}
    if len(slots) != len(expected) or actual != expected:
        raise ValueError("execution order is not the exact frozen rule/seed/family/color/endpoint/foe cross product")
    cap_map = plan["caps_by_family"]
    counts = Counter(cap_map.values())
    if counts != Counter({20000: 16, 40000: 16}):
        raise ValueError("frozen cap assignment must be balanced 16/16")
    per_family = Counter(s[2] for s in slots)
    if set(per_family.values()) != {32}:
        raise ValueError("every family must retain all 32 endpoint/seed/color slots")


def run(directory: str | Path | None = None) -> dict:
    d = TASK / "run-001" if directory is None else Path(directory)
    if not d.is_absolute():
        d = ROOT / d
    plan_path = d / "plan.json"
    eval_path = d / "eval-plan.json"
    registration_path = d / "registration.json"
    runner_registration_path = d / "runner-registration.json"
    model_binding_path = d / "model-binding.json"
    required = (plan_path, eval_path, registration_path, runner_registration_path, model_binding_path)
    if not all(p.exists() for p in required):
        raise FileNotFoundError("task2617 run-001 is not registered; refusing to search")
    p = json.loads(plan_path.read_text(encoding="utf-8"))
    ep = json.loads(eval_path.read_text(encoding="utf-8"))
    reg = json.loads(registration_path.read_text(encoding="utf-8"))
    runreg = json.loads(runner_registration_path.read_text(encoding="utf-8"))
    model_binding = json.loads(model_binding_path.read_text(encoding="utf-8"))
    if runreg.get("python_version") != platform.python_version() or runreg.get("python_chess_version") != version("chess"):
        raise RuntimeError("registered Python/python-chess runtime differs from execution environment")
    if reg.get("status") != "REGISTERED_PRE_RUN" or not reg.get("no_evaluation_yet"):
        raise RuntimeError("registration is not valid pre-run state")
    if sha(plan_path) != reg["plan_sha256"] or sha(eval_path) != reg["eval_plan_sha256"]:
        raise RuntimeError("registered plan hash mismatch")
    if sha(d / "root-manifest.json") != reg["root_manifest_sha256"]:
        raise RuntimeError("registered roots changed")
    if sha(runner_registration_path) != reg["runner_registration_sha256"]:
        raise RuntimeError("runner source registration changed")
    if sha(model_binding_path) != reg["model_binding_sha256"]:
        raise RuntimeError("model binding changed after preregistration")
    if model_binding["task2616_result_sha256"] != sha(ROOT / "results/dev_aux/task2616/result.json"):
        raise RuntimeError("frozen task2616 endpoint models changed")
    if model_binding["tree_training_result_sha256"] != sha(ROOT / "results/dev_aux/task2616/tree-training-result.json"):
        raise RuntimeError("frozen task2616 TreeStrap model changed")
    for name, expected in runreg["runtime_pins"].items():
        if sha(ROOT / name) != expected:
            raise RuntimeError(f"runtime source changed: {name}")
    if ep["slots"] != [
        [0, item[1], item[0], item[2], item[3], "uniform"]
        for item in json.loads((d / "execution-order.json").read_text(encoding="utf-8"))["slots"]
    ]:
        raise RuntimeError("slot order no longer matches its frozen source")
    caps = p["caps_by_family"]
    validate_slots(ep["slots"], p, ep)
    roots_doc = json.loads((d / "root-manifest.json").read_text(encoding="utf-8"))
    root_families = {str(row["family"]) for row in roots_doc["roots"]}
    if len(caps) != 32 or p["slots"] != 1024 or root_families != set(caps):
        raise RuntimeError("registered family/root/slot counts do not match the frozen 32-family design")
    if (
        ep["cap_seconds"] != 5400
        or ep["global_cap_seconds"] != 5400
        or ep["cap_seconds"] != ep["global_cap_seconds"]
        or ep["prefix_plies"] != 8
        or ep["nodes_per_query"] != 8192
        or ep["seconds_per_query"] != 2.0
        or ep["depth"] != 2
        or ep["q_limit"] != 2
        or ep["H"] != 1024
    ):
        raise RuntimeError("run cap or root prefix differs from the frozen protocol")
    if sum(map(int, caps.values())) * 32 != p["max_paid_nodes"]:
        raise RuntimeError("registered total node ceiling differs from family assignments")
    if p["hard_cap_plus_reserve_seconds"] != 6300 or p["evaluation_hard_cap_seconds"] != 5400:
        raise RuntimeError("registered all-in run ceiling differs from the frozen feasibility assessment")
    if any((d / name).exists() for name in ("eval-started.json", "eval-games.jsonl", "eval-queries.jsonl", "eval-result.json")):
        raise FileExistsError("refusing to overwrite existing run evidence")

    result_path = ROOT / "results/dev_aux/task2616/result.json"
    result = json.loads(result_path.read_text(encoding="utf-8"))
    arms = {(a["generator_seed"], a["seed"], a["method"]): a for a in result["arms"]}
    roots = {row["family"]: row["record"] for row in roots_doc["roots"]}
    ccs = {gs: compiled(gs) for gs in ep["rules"]}
    stop = SharedDeleteStopReader(ROOT)
    stop()
    began = time.perf_counter()
    binding = {
        "task": "DEV_AUX2617",
        "plan_sha256": sha(eval_path),
        "registration_sha256": sha(registration_path),
        "root_manifest_sha256": sha(d / "root-manifest.json"),
        "runner_registration_sha256": sha(runner_registration_path),
        "model_binding_sha256": sha(model_binding_path),
        "runtime_pins": runreg["runtime_pins"],
        "ordered_slots_sha256": hashlib.sha256(
            json.dumps(ep["slots"], separators=(",", ":")).encode()
        ).hexdigest(),
        "started_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    }
    (d / "eval-binding.json").write_text(json.dumps(binding, indent=2) + "\n", encoding="utf-8")
    (d / "eval-started.json").write_text(json.dumps(binding, indent=2) + "\n", encoding="utf-8")
    rows: list[dict] = []
    counters = Counter()
    status = "COMPLETE"
    with (d / "eval-games.jsonl").open("x", encoding="utf-8") as gf, (d / "eval-queries.jsonl").open(
        "x", encoding="utf-8"
    ) as qf:
        for slot in ep["slots"]:
            stop()
            gs, seed, family, color, endpoint, foe_name = slot
            key = (gs, seed, "TD" if endpoint == "initial" else endpoint)
            if key not in arms:
                raise KeyError(f"frozen endpoint arm absent: {key}")
            if time.perf_counter() - began >= ep["cap_seconds"]:
                status = "PARTIAL_CAP"
                break
            arm = arms[key]
            weights = arm["initial"] if endpoint == "initial" else arm["weights"]
            learner = model(ep["domain"], weights)
            opponent = model(ep["domain"], ep["foes"][foe_name])
            env = environment(gs, ccs[gs])
            prefix(env, gs, family, ep["prefix_plies"])
            initial_record = env.record()
            if initial_record != roots[family]:
                raise AssertionError("actual full Chess history differs from frozen root")
            nqueries = nodes = 0
            slot_cap = family_cap(p, family)
            ending = "HORIZON_UNKNOWN"
            for ply in range(ep["H"]):
                stop()
                if env.terminal() is not None:
                    ending = "ACTUAL_TERMINAL"
                    break
                global_left = ep["cap_seconds"] - (time.perf_counter() - began)
                slot_left = slot_cap - nodes
                if global_left <= 0:
                    ending, status = "GLOBAL_CAP_UNKNOWN", "PARTIAL_CAP"
                    break
                if slot_left <= 0:
                    ending = "SLOT_NODE_CAP_UNKNOWN"
                    break
                actor = env.player()
                current = learner if actor == color else opponent
                record_before = env.record()
                effective_nodes = min(ep["nodes_per_query"], slot_left)
                effective_seconds = min(ep["seconds_per_query"], global_left)
                ordering_seed = gs * 100000000 + family * 1000 + ply + ep["ordering_seed_offset"]
                receipt = TrainingSearch(ep["depth"], quiet=False, q_limit=ep["q_limit"]).search(
                    env,
                    current,
                    nodes=effective_nodes,
                    seconds=effective_seconds,
                    seed=ordering_seed,
                    cancel=stop,
                )
                if env.record() != record_before:
                    raise AssertionError("evaluation search mutated full Chess history")
                if receipt.nodes < 0 or receipt.nodes > effective_nodes:
                    raise AssertionError("search receipt violated requested node limit")
                nodes += receipt.nodes
                if nodes > slot_cap:
                    raise AssertionError("both-actor paid node count exceeded family cap")
                nqueries += 1
                if receipt.complete:
                    env.push(receipt.action)
                query = {
                    "slot": slot,
                    "family_cap_nodes_both_sides": slot_cap,
                    "ply": ply,
                    "actor": actor,
                    "weights": list(current.weights),
                    "record_before": record_before,
                    "record_after": env.record(),
                    "complete": receipt.complete,
                    "action": None if not receipt.complete else receipt.action.uci(),
                    "value": receipt.value,
                    "pv_phi": receipt.pv_phi,
                    "pv_terminal": receipt.pv_terminal,
                    "nodes": receipt.nodes,
                    "seconds": receipt.seconds,
                    "effective_nodes": effective_nodes,
                    "effective_seconds": effective_seconds,
                    "ordering_seed": ordering_seed,
                    "reason": receipt.reason,
                }
                qf.write(json.dumps(query, separators=(",", ":"), allow_nan=False) + "\n")
                qf.flush()
                if not receipt.complete:
                    ending = "SEARCH_RESOURCE_UNKNOWN"
                    if time.perf_counter() - began >= ep["cap_seconds"]:
                        ending, status = "GLOBAL_CAP_UNKNOWN", "PARTIAL_CAP"
                    break
            outcome = env.terminal()
            if outcome is not None:
                ending = "ACTUAL_TERMINAL"
            replay = restore(gs, ccs[gs], env.record())
            if replay.record() != env.record() or replay.terminal() != outcome:
                raise AssertionError("evaluation game full-history replay mismatch")
            row = {
                "slot": slot,
                "family_cap_nodes_both_sides": slot_cap,
                "weights": list(weights),
                "initial_record": initial_record,
                "record": env.record(),
                "outcome": outcome,
                "reward": terminal_reward(outcome, color),
                "ending": ending,
                "nodes": nodes,
                "queries": nqueries,
            }
            rows.append(row)
            gf.write(json.dumps(row, separators=(",", ":"), allow_nan=False) + "\n")
            gf.flush()
            counters.update(
                games=1,
                actual_terminal=outcome is not None,
                unknown=outcome is None,
                nodes=nodes,
                queries=nqueries,
                cap_slots_20000=slot_cap == 20000,
                cap_slots_40000=slot_cap == 40000,
            )
            if status != "COMPLETE":
                break

    seen = {slot_key(row["slot"]) for row in rows}
    missing = [slot for slot in ep["slots"] if slot_key(slot) not in seen]
    summary = {
        "task": "DEV_AUX2617",
        "status": status,
        "expected": len(ep["slots"]),
        "actual": len(rows),
        "missing": len(missing),
        "missing_slots": missing,
        "actual_terminal": counters["actual_terminal"],
        "unknown": counters["unknown"],
        "nodes": counters["nodes"],
        "queries": counters["queries"],
        "slots_20000": counters["cap_slots_20000"],
        "slots_40000": counters["cap_slots_40000"],
        "seconds": time.perf_counter() - began,
        "unknown_is_draw": False,
        "all_slots_recorded_or_explicitly_missing": len(rows) + len(missing) == len(ep["slots"]),
    }
    (d / "eval-result.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    return summary


if __name__ == "__main__":
    print(json.dumps(run(), indent=2))
