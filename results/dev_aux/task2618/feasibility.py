"""Recompute the task2618 Chess learner-comparison cost estimate.

This is a read-only feasibility audit. It does not register a protocol, select
roots/seeds, run a learner, search a position, or inspect outcome labels.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
SOURCES = {
    "trees": ("results/dev_aux/task2616/tree-training-result.json", (), ("nodes", "seconds")),
    "td_old": ("results/dev_aux/task2594/train/result.json", (), ("nodes", "seconds")),
    "td_current": ("results/dev_aux/task2568/summary.json", ("TRAIN_cost_by_method", "TD"), ("nodes", "seconds")),
    "wdl": ("results/dev_aux/task2568/summary.json", ("TRAIN_cost_by_method", "WDL"), ("nodes", "seconds")),
    "eval_2616": ("results/dev_aux/task2616/eval-result.json", (), ("nodes", "seconds", "expected", "actual")),
    "eval_2617": ("results/dev_aux/task2617/run-002/eval-result.json", (), ("nodes", "seconds", "expected", "actual")),
}
TRAIN_NODES_PER_METHOD = 4_000_000
EVAL_SLOTS = 1_024
RUNTIME_MARGIN = 0.25
SETUP_AUDIT_RESERVE_SECONDS = 900
TRAIN_PHASE_CAP_SECONDS = 2_100
EVAL_PHASE_CAP_SECONDS = 3_600
ALL_IN_CAP_SECONDS = 6_600
DOT_THRESHOLD_SECONDS = 7_200


def read_source(name: str) -> tuple[dict, dict]:
    relative, path, fields = SOURCES[name]
    file_path = ROOT / relative
    raw = file_path.read_bytes()
    value = json.loads(raw)
    for key in path:
        value = value[key]
    return {key: value[key] for key in fields}, {"path": relative, "sha256": hashlib.sha256(raw).hexdigest()}


def main() -> None:
    values, pins = {}, {}
    for name in SOURCES:
        values[name], pins[name] = read_source(name)

    # Use the slower of two historical 4M-node TD receipts and the slower of
    # the two complete 1,024-slot fixed-foe Chess evaluations.
    td_candidates = [values["td_old"], values["td_current"]]
    tree = values["trees"]
    wdl = values["wdl"]
    evaluations = [values["eval_2616"], values["eval_2617"]]
    for source in [tree, *td_candidates, wdl]:
        if source["nodes"] != TRAIN_NODES_PER_METHOD:
            raise SystemExit(f"unexpected training node count: {source}")
    for source in evaluations:
        if source["expected"] != EVAL_SLOTS or source.get("actual", EVAL_SLOTS) != EVAL_SLOTS:
            raise SystemExit(f"evaluation source is not a complete {EVAL_SLOTS}-slot panel: {source}")

    train_seconds = {
        "TreeStrap": tree["seconds"],
        "TDLeaf": max(item["seconds"] for item in td_candidates),
        "finite_WDL": wdl["seconds"],
    }
    evaluation = max(evaluations, key=lambda item: item["seconds"])
    base = sum(train_seconds.values()) + evaluation["seconds"]
    estimated = base * (1.0 + RUNTIME_MARGIN) + SETUP_AUDIT_RESERVE_SECONDS
    all_in_cap = TRAIN_PHASE_CAP_SECONDS + EVAL_PHASE_CAP_SECONDS + SETUP_AUDIT_RESERVE_SECONDS
    result = {
        "status": "FEASIBILITY_ONLY",
        "source_pins": pins,
        "assumptions": {
            "train_nodes_per_method": TRAIN_NODES_PER_METHOD,
            "evaluation_slots_total_across_endpoints": EVAL_SLOTS,
            "runtime_margin_fraction": RUNTIME_MARGIN,
            "setup_audit_reserve_seconds": SETUP_AUDIT_RESERVE_SECONDS,
            "proposed_stage_caps_seconds": {
                "training_all_methods": TRAIN_PHASE_CAP_SECONDS,
                "evaluation_all_endpoints": EVAL_PHASE_CAP_SECONDS,
            },
            "all_in_cap_seconds": all_in_cap,
            "dot_threshold_seconds": DOT_THRESHOLD_SECONDS,
        },
        "training_seconds_by_method": train_seconds,
        "evaluation_source": {
            "path": pins["eval_2617"]["path"],
            "nodes": evaluation["nodes"],
            "seconds": evaluation["seconds"],
            "slots": evaluation["expected"],
        },
        "base_observed_seconds": base,
        "estimate_with_margin_and_reserve_seconds": estimated,
        "estimate_minutes": estimated / 60,
        "all_in_cap_minutes": all_in_cap / 60,
        "threshold_assessment": "BELOW_120_MINUTES" if estimated < DOT_THRESHOLD_SECONDS else "DOT_ASSESSMENT_REQUIRED",
        "interpretation": (
            "Historical measurements are not guarantees: runner/search versions and node mix differ. "
            "The estimate uses the slowest observed TD receipt, the observed TreeStrap and WDL 4M-node "
            "receipts, and the slower complete 1,024-slot evaluation; adds 25% runtime margin plus "
            "15 minutes for setup/audit; and bounds the proposed all-in cap at 110 minutes. "
            "No roots, seeds, arms, outcomes or learner parameters are selected or executed here. "
            "Any later estimate reaching 120 minutes requires Dot assessment before registration/start."
        ),
    }
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
