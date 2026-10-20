"""Verify the timing of task2618's existing TreeStrap weight telemetry.

No trainer/endpoint is modified. Re-execute at most the first changed candidate
query per seed, selected by telemetry change alone, to distinguish the actual
pre-search model from a field serialized after TreeStrap.update.
"""
from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path

from results.dev_aux.task2492.learning import AlphaBeta, Model, TreeStrap
from results.dev_aux.task2565.train import restore
from tools.local_agent.environment import require_identity

ROOT = Path(__file__).resolve().parents[3]
TRAIN = ROOT / "results/dev_aux/task2618/learner-comparison-v4"
OUT = ROOT / "results/dev_aux/task2620/training-telemetry-audit.json"


def diagnose():
    require_identity()
    if OUT.exists():
        raise FileExistsError("telemetry diagnosis is write-once")
    plan_raw = (TRAIN / "plan.json").read_bytes()
    plan = json.loads(plan_raw)
    for relative, digest in plan["source_sha256"].items():
        if hashlib.sha256((ROOT / relative).read_bytes()).hexdigest() != digest:
            raise ValueError("frozen training source changed: " + relative)
    before = {int(seed): list(weights) for seed, weights
              in plan["candidate_initial_weights_by_seed"].items()}
    selected = {}
    rows_scanned = 0
    with (TRAIN / "queries.jsonl").open(encoding="utf-8") as stream:
        for number, line in enumerate(stream, 1):
            row = json.loads(line)
            rows_scanned += 1
            if row["method"] != "TreeStrap" or not row["candidate_turn"]:
                continue
            seed = row["seed"]
            logged = row["weights_before_search"]
            if seed not in selected and logged != before[seed]:
                selected[seed] = dict(source_line=number, before=before[seed], row=row)
            before[seed] = logged
    if set(selected) != set(plan["seeds"]):
        raise ValueError("not every seed has a changed TreeStrap query; preserve unresolved scope")
    observations = []
    began = time.perf_counter()
    paid_nodes = 0
    for seed in plan["seeds"]:
        sample = selected[seed]
        row = sample["row"]
        env = restore(0, None, row["record_before"])
        model = Model(sample["before"])
        receipt = AlphaBeta(plan["search"]["depth"], plan["search"]["qdepth"]).search(
            env, model, nodes=row["effective_nodes"], seconds=row["effective_seconds"],
            seed=row["ordering_seed"])
        paid_nodes += receipt.nodes
        if not receipt.complete:
            raise ValueError("bounded diagnostic search did not complete; do not retry")
        TreeStrap(plan["learner_parameters"]["TreeStrap"]["eta"]).update(model, receipt)
        if (receipt.action.uci() != row["action"] or receipt.nodes != row["nodes"]
                or receipt.value != row["value"] or model.weights != row["weights_before_search"]):
            raise ValueError("first-change replay does not explain logged after-update weights")
        observations.append(dict(seed=seed, source_line=sample["source_line"],
                                 game_index=row["game_index"], ply=row["ply"],
                                 actual_before=sample["before"], logged_field=row["weights_before_search"],
                                 reproduced_after=list(model.weights), nodes=receipt.nodes,
                                 action_value_nodes_and_post_update_match=True))
    result = dict(status="CONFIRMED_TELEMETRY_NAME_DEFECT", observations=observations,
                  selected_rule="First TreeStrap candidate query with changed logged weights per seed; no outcome selection",
                  source_plan_sha256=hashlib.sha256(plan_raw).hexdigest(),
                  rows_scanned=rows_scanned, verifier_paid_nodes=paid_nodes,
                  verifier_seconds=time.perf_counter()-began,
                  finding="TreeStrap weights_before_search is serialized after TreeStrap.update, so it contains post-update weights on changed candidate queries.",
                  consequence="Do not use that field as actual pre-search weights. This diagnostic validates four first-change cases, not all training updates or endpoint provenance.",
                  frozen_training_or_endpoint_changed=False, evaluation_labels_added=0,
                  future_fix="In a separately registered future trainer, snapshot actor weights before search/update; retain historical raw logs and this interpretation correction.")
    with OUT.open("x", encoding="utf-8") as stream:
        stream.write(json.dumps(result, indent=2, sort_keys=True) + "\n")
    return result


if __name__ == "__main__":
    result = diagnose()
    print(json.dumps({key: value for key, value in result.items() if key != "observations"}, indent=2))
