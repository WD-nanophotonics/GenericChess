"""Reconstruct frozen task2620 inputs without new search or outcome selection."""
from __future__ import annotations

import datetime
import hashlib
import json
import random
from pathlib import Path

from results.dev_aux.task2565.train import restore
from results.dev_aux.task2618.evaluate_learners import verify_training_result
from results.dev_aux.task2620 import protocol
from tools.local_agent.environment import require_identity

ROOT = Path(__file__).resolve().parents[3]
RUN = ROOT / "results/dev_aux/task2620/run-002"


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def verify():
    require_identity()
    output = RUN / "input-reconstruction.json"
    if output.exists():
        raise FileExistsError("input verification is write-once")
    raw = (RUN / "plan.json").read_bytes()
    plan = json.loads(raw)
    protocol.validate_plan(plan)
    for relative, digest in plan["source_sha256"].items():
        if sha((ROOT / relative).read_bytes()) != digest:
            raise ValueError("frozen source differs: " + relative)
    original_raw = (ROOT / plan["training_plan_path"]).read_bytes()
    if sha(original_raw) != plan["training_plan_sha256"]:
        raise ValueError("original training plan changed")
    original = json.loads(original_raw)
    training_raw = (RUN / "training-result.json").read_bytes()
    if sha(training_raw) != plan["training_result_sha256"]:
        raise ValueError("training result changed")
    training = json.loads(training_raw)
    arms = verify_training_result(original, training, sha(original_raw))
    if original["seeds"] != plan["seeds"] or original["methods"] != plan["methods"]:
        raise ValueError("seed/method panel changed")
    initial_by_seed = {}
    for (index, _method), arm in arms.items():
        seed = plan["seeds"][index]
        if arm["seed"] != seed:
            raise ValueError("training arm seed/index mismatch")
        if seed in initial_by_seed and initial_by_seed[seed] != arm["initial_weights"]:
            raise ValueError("methods did not share the registered initialization")
        initial_by_seed[seed] = arm["initial_weights"]
    roots_raw = (RUN / "evaluation-root-manifest.json").read_bytes()
    if sha(roots_raw) != plan["evaluation_root_manifest_sha256"]:
        raise ValueError("root manifest changed")
    manifest = json.loads(roots_raw)
    excluded, sources = protocol.exclusions()
    if sources != manifest["prior_source_pins"]:
        raise ValueError("exclusion source bytes or row accounting changed")
    if len(excluded) != manifest["excluded_exact_records"]:
        raise ValueError("reconstructed exclusion count changed")
    roots = protocol.select_roots(excluded)
    if roots != manifest["roots"]:
        raise ValueError("registered roots are not first eligible outcome-blind roots")
    for root in roots:
        env = restore(0, None, root["record"])
        if env.record() != root["record"] or env.terminal() is not None:
            raise ValueError("root is not a legal nonterminal full-history replay")
        if len(root["record"]["moves"]) != 8:
            raise ValueError("root prefix is not eight plies")
        if sha(protocol.canonical(root["record"]).encode()) != root["record_sha256"]:
            raise ValueError("root canonical digest mismatch")
    rng = random.Random(2620001)
    families = [root["family"] for root in roots]
    rng.shuffle(families)
    caps = {str(f): 20000 if i < len(families) // 2 else 40000
            for i, f in enumerate(families)}
    if families != plan["evaluation"]["cap_assignment_order"]:
        raise ValueError("cap randomization order changed")
    if caps != plan["evaluation"]["caps_by_family"]:
        raise ValueError("paired root budgets changed")
    blocks = [(i, seed, f, color) for i, seed in enumerate(plan["seeds"])
              for f in families for color in (0, 1)]
    rng.shuffle(blocks)
    slots = []
    for i, seed, family, color in blocks:
        order = ["initial", "TreeStrap", "TDLeaf", "WDL"]
        rng.shuffle(order)
        slots.extend([i, seed, family, color, endpoint] for endpoint in order)
    if slots != plan["evaluation"]["ordered_slots"]:
        raise ValueError("paired block or endpoint execution order changed")
    result = dict(status="PASS", at=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                  plan_sha256=sha(raw), roots=len(roots), full_history_replay=True,
                  exclusion_exact_records=len(excluded), exclusion_source_count=len(sources),
                  roots_exact_disjoint=True, deterministic_first_eligible_roots=True,
                  cap_and_slot_randomization_reconstructed=True, slots=len(slots),
                  same_initialization_per_seed=True, source_pins=len(plan["source_sha256"]),
                  training_paid_nodes=sum(arm["nodes_total"] for arm in arms.values()),
                  scope="Exact full-history start disjointness only; descendants/transpositions and population independence are not established.")
    with output.open("x", encoding="utf-8") as stream:
        stream.write(json.dumps(result, indent=2, sort_keys=True) + "\n")
    return result


if __name__ == "__main__":
    print(json.dumps(verify(), indent=2, sort_keys=True))
