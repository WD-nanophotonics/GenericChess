"""Recompute task2618 learner-comparison feasibility from cost-only sources.

This read-only audit does not register a protocol, select roots/seeds, run a
learner, search a position, or inspect outcome labels.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
SOURCES = {
    "shared_chess_cost_scan": "results/dev_aux/task2612/attempt-4/result.json",
    "shared_wdl_cost_scan": "results/dev_aux/task2618/wdl-shared-cost/result.json",
    "eval_2616": "results/dev_aux/task2616/eval-result.json",
    "eval_2617": "results/dev_aux/task2617/run-002/eval-result.json",
}
TRAIN_NODES_PER_METHOD = 4_000_000
SHARED_SCAN_NODES_PER_METHOD = 400_000
EVAL_SLOTS = 1_024
RUNTIME_MARGIN = 0.25
SETUP_AUDIT_RESERVE_SECONDS = 900
TRAIN_PHASE_CAP_SECONDS = 2_100
EVAL_PHASE_CAP_SECONDS = 3_600
ALL_IN_CAP_SECONDS = 6_600
DOT_THRESHOLD_SECONDS = 7_200


def read_source(name: str) -> tuple[dict, dict]:
    relative = SOURCES[name]
    raw = (ROOT / relative).read_bytes()
    return json.loads(raw), {
        "path": relative,
        "sha256": hashlib.sha256(raw).hexdigest(),
    }


def main() -> None:
    values, pins = {}, {}
    for name in SOURCES:
        values[name], pins[name] = read_source(name)

    cost_scan_sources = {}
    for name in ("shared_chess_cost_scan", "shared_wdl_cost_scan"):
        embedded = values[name].get("source_sha256", {})
        if not embedded:
            raise SystemExit(f"cost scan has no pinned runner/source hashes: {name}")
        for relative, digest in embedded.items():
            actual = hashlib.sha256((ROOT / relative).read_bytes()).hexdigest()
            if actual != digest:
                raise SystemExit(f"cost scan source changed since measurement: {relative}")
        cost_scan_sources[name] = {
            relative: {"sha256": digest} for relative, digest in sorted(embedded.items())
        }

    chess_scan = values["shared_chess_cost_scan"]
    wdl_scan = values["shared_wdl_cost_scan"]
    if chess_scan.get("status") != "COMPLETE_COST_ONLY" or wdl_scan.get("status") != "COMPLETE_COST_ONLY":
        raise SystemExit("shared-path receipts must be complete cost-only scans")
    if any(arm.get("labels_or_weights_recorded") for arm in chess_scan.get("arms", [])):
        raise SystemExit("Chess cost scan unexpectedly persisted labels or weights")
    if any(arm.get("terminal_outcomes_or_coefficients_emitted") for arm in wdl_scan.get("arms", [])):
        raise SystemExit("WDL cost scan unexpectedly emitted outcomes or coefficients")

    train_seconds: dict[str, float] = {}
    for key, method in (
        ("TreeStrap", "TreeStrap(eta=.05)"),
        ("TDLeaf", "TDLeafEpisode(eta=.05,lambda=.95)"),
    ):
        arms = [arm for arm in chess_scan.get("arms", []) if arm.get("method") == method]
        nodes = sum(arm.get("total_nodes", 0) for arm in arms)
        seconds = sum(arm.get("wall_seconds", 0.0) for arm in arms)
        if nodes != SHARED_SCAN_NODES_PER_METHOD:
            raise SystemExit(f"unexpected shared Chess cost-scan nodes for {method}: {nodes}")
        train_seconds[key] = seconds * TRAIN_NODES_PER_METHOD / nodes

    wdl_nodes = sum(arm.get("total_nodes", 0) for arm in wdl_scan.get("arms", []))
    wdl_seconds = wdl_scan.get("wall_seconds")
    if wdl_nodes != SHARED_SCAN_NODES_PER_METHOD or wdl_seconds is None:
        raise SystemExit(f"unexpected shared WDL cost-scan totals: {wdl_nodes}, {wdl_seconds}")
    train_seconds["finite_WDL"] = wdl_seconds * TRAIN_NODES_PER_METHOD / wdl_nodes

    evaluations = [values["eval_2616"], values["eval_2617"]]
    for source in evaluations:
        if source["expected"] != EVAL_SLOTS or source.get("actual", EVAL_SLOTS) != EVAL_SLOTS:
            raise SystemExit(f"evaluation source is not a complete {EVAL_SLOTS}-slot panel: {source}")
    evaluation = max(evaluations, key=lambda item: item["seconds"])
    base = sum(train_seconds.values()) + evaluation["seconds"]
    estimated = base * (1.0 + RUNTIME_MARGIN) + SETUP_AUDIT_RESERVE_SECONDS
    all_in_cap = TRAIN_PHASE_CAP_SECONDS + EVAL_PHASE_CAP_SECONDS + SETUP_AUDIT_RESERVE_SECONDS
    result = {
        "status": "FEASIBILITY_ONLY",
        "source_pins": pins,
        "cost_scan_runner_source_pins": cost_scan_sources,
        "assumptions": {
            "train_nodes_per_method": TRAIN_NODES_PER_METHOD,
            "shared_scan_nodes_per_method": SHARED_SCAN_NODES_PER_METHOD,
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
            "Training cost scales each observed 400k-node shared AlphaBeta/Receipt cost-only scan "
            "(TreeStrap, TDLeaf, finite WDL) linearly to 4M paid candidate+foe nodes per method. "
            "Evaluation uses the slower complete 1,024-slot panel; the estimate adds a 25% runtime "
            "margin plus 15 minutes for setup/audit and bounds the hard all-in cap at 110 minutes. "
            "No outcomes, roots, seeds, arms or learner parameters are selected or executed here. "
            "Any later estimate reaching 120 minutes requires Dot assessment before registration/start."
        ),
    }
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
