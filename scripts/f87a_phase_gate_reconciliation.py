"""Reconcile the frozen F87A playability scope after the R9 result."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


F87A_CHARTER_BASELINE_SHA = "a33ff404d33aef1d6717fc62e05337ae92691540"
R9_CANDIDATE_SHA = "d4fa4c239dbccbc0889d891927adde8117d7a499"
R9_RESULTS = Path("artifacts/f87a_r9_western_dynamic_discovery/results.json")
ARTIFACT_DIR = Path("artifacts/f87a_phase_gate_reconciliation")


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def reconcile(
    r9_result: dict[str, Any],
    qualification_reports: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    """Apply the frozen F87A phase contract without opening Layer D/E work."""
    if r9_result.get("dynamic_viability_pass") is not True:
        raise ValueError("R9 must pass the existing termination-viability gate")
    if r9_result.get("search_budget_censored_count") != 0:
        raise ValueError("R9 search-budget censorship must remain zero")
    if r9_result.get("terminal_discovery_count", 0) < 1:
        raise ValueError("R9 must contain a terminal discovery")
    target_population = ("Built-in Western Chess", "Built-in Standard Shogi")
    reports = [qualification_reports.get(name) for name in target_population]
    if any(report is None for report in reports):
        raise ValueError("qualification reports must include both built-in semantic controls")
    if any(report["blocking_layers"] != ["A", "C"] for report in reports):
        raise ValueError("positive semantic reports must declare B diagnostic-only")
    if any(
        report["overall_status"] != "PASS"
        or report["layers"]["A"] != "PASS"
        or report["layers"]["C"] != "PASS"
        for report in reports
    ):
        raise ValueError("positive semantic QualificationReports must pass overall and on A/C")
    return {
        "schema_version": 1,
        "experiment": "GENERICCHESS-F87A-PHASE-GATE-RECONCILIATION",
        "status": "RECONCILED",
        "charter": {
            "baseline_sha": F87A_CHARTER_BASELINE_SHA,
            "declared_target": "PLAYABILITY",
            "required_layers": ["A", "B", "C"],
            "source": "docs/architecture/GENERICCHESS_F87A_RULESET_QUALIFICATION_TOOLBOX_FOUNDATION.md",
        },
        "evidence": {
            "r9_candidate_sha": R9_CANDIDATE_SHA,
            "r9_terminal_discovery_count": r9_result["terminal_discovery_count"],
            "r9_horizon_censored_count": r9_result["horizon_censored_count"],
            "r9_search_budget_censored_count": r9_result["search_budget_censored_count"],
        },
        "target_population": list(target_population),
        "layers": {
            "A": {
                "status": "PASS",
                "gate": "REQUIRED_FOR_PLAYABILITY",
                "basis": "QualificationReport A status for both built-in semantic controls",
            },
            "B": {
                "status": "DIAGNOSTIC_ONLY",
                "gate": "NON_BLOCKING",
                "basis": "QualificationReport declares B non-blocking; frozen charter applies no universal rank/index admission gate",
            },
            "C": {
                "status": "PASS",
                "gate": "REQUIRED_FOR_PLAYABILITY",
                "basis": "QualificationReport C status for both built-in semantic controls plus R9 Western termination viability",
            },
        },
        "scope_decision": "PLAYABILITY_SCOPE_SATISFIED",
        "deferred_follow_on": {
            "D": "DEFERRED_IN_F87A",
            "E": "DEFERRED_IN_F87A",
        },
        "promotion_decision": "NOT_GRANTED_BY_SCOPE_RECONCILIATION",
        "next_route": "MOVE_LAYER_D_E_TO_A_FOLLOW_ON_PHASE_ONLY_WITH_AN_EXPLICIT_WORK_ORDER",
    }


def run(
    r9_results_path: Path = R9_RESULTS,
    qualification_reports_path: Path = Path("artifacts/f87a_ruleset_qualification/reports.json"),
    output_dir: Path = ARTIFACT_DIR,
) -> dict[str, Any]:
    r9_result = json.loads(r9_results_path.read_text(encoding="utf-8"))
    qualification_reports = json.loads(qualification_reports_path.read_text(encoding="utf-8"))
    result = reconcile(r9_result, qualification_reports)
    _write_json(output_dir / "result.json", result)
    return result


if __name__ == "__main__":
    print(json.dumps(run(), sort_keys=True))
