"""F38 corrective R1: replay frozen F37 R37C search parity.

This is an audit-only harness.  It preserves the first-pass F38 evidence and
compares the frozen F37 R37C rows against both a fresh F37 oracle replay and
the already-frozen production-shaped F38 prototype.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import audit_f23v_minimal_analytic_evaluator as f23v
from scripts import audit_f31_gap_causal as f31
from scripts import audit_f37_evaluator_reentry as f37
from scripts import audit_f38_activity_anchor_prototype as f38

FIXTURES = ROOT / "tests" / "fixtures"
OUT = FIXTURES / "f38r1_frozen_r37c_search_parity.json"
SHADOW = FIXTURES / "f37_evaluator_search_shadow.json"
F37_RANKS = FIXTURES / "f37_evaluator_representation_ranks.json"
F37_SELECTION = FIXTURES / "f37_evaluator_selection.json"
F37_R1 = FIXTURES / "f37r1_gate_recertification.json"
H38A_MANIFEST = FIXTURES / "f38_activity_anchor_manifest.json"
H38A_DESCRIPTOR = FIXTURES / "f38_external_holdout_descriptor.json"
F38_IDENTITY = FIXTURES / "f38_activity_anchor_prototype_identity.json"
F38_RANKS = FIXTURES / "f38_activity_anchor_holdout_ranks.json"
F38_SEARCH = FIXTURES / "f38_activity_anchor_holdout_search.json"
F38_COST = FIXTURES / "f38_activity_anchor_micro_cost.json"
F38_SELECTION = FIXTURES / "f38_activity_anchor_selection.json"

DETERMINISTIC_FIELDS = (
    "selected_move",
    "score",
    "pv_head",
    "completed_depth",
    "nodes",
    "qnodes",
    "termination_reason",
)
BUDGETS = (512, 2048)


def load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def sha_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def evidence_bindings() -> dict[str, dict[str, str]]:
    paths = {
        "f37_search_shadow": SHADOW,
        "f37_representation_ranks": F37_RANKS,
        "f37_selection": F37_SELECTION,
        "f37_r1_recertification": F37_R1,
        "h38a_manifest": H38A_MANIFEST,
        "h38a_descriptor": H38A_DESCRIPTOR,
        "f38_prototype_script": ROOT / "scripts/audit_f38_activity_anchor_prototype.py",
        "f38_prototype_identity": F38_IDENTITY,
        "f38_holdout_ranks": F38_RANKS,
        "f38_holdout_search": F38_SEARCH,
        "f38_micro_cost": F38_COST,
        "f38_first_pass_selection": F38_SELECTION,
    }
    return {name: {"path": str(path.relative_to(ROOT)).replace("\\", "/"), "sha256": sha_file(path)} for name, path in paths.items()}


def _search(compiled: Any, evaluator: Any, state: Any, budget: int) -> dict[str, Any]:
    return f31._direct(
        f31._imports(),
        compiled,
        evaluator,
        state,
        nodes=budget,
        max_depth=8,
        qmax=4,
        qhard=8,
        native_requested=True,
    )


def _comparison(expected: dict[str, Any], actual: dict[str, Any]) -> dict[str, Any]:
    mismatches = {
        field: {"expected": expected.get(field), "actual": actual.get(field)}
        for field in DETERMINISTIC_FIELDS
        if expected.get(field) != actual.get(field)
    }
    return {"equal": not mismatches, "mismatches": mismatches}


def _row(pid: str, budget: int, frozen: dict[str, Any], oracle: dict[str, Any], prototype: dict[str, Any]) -> dict[str, Any]:
    oracle_vs_frozen = _comparison(frozen, oracle)
    prototype_vs_frozen = _comparison(frozen, prototype)
    prototype_vs_oracle = _comparison(oracle, prototype)
    return {
        "position_id": pid,
        "budget": budget,
        "frozen_r37c": {field: frozen.get(field) for field in DETERMINISTIC_FIELDS},
        "fresh_f37_r37c_oracle": {field: oracle.get(field) for field in DETERMINISTIC_FIELDS},
        "fresh_production_shaped_prototype": {field: prototype.get(field) for field in DETERMINISTIC_FIELDS},
        "F37_ORACLE_REPLAY_PARITY": oracle_vs_frozen,
        "PROTOTYPE_VS_F37_FROZEN_PARITY": prototype_vs_frozen,
        "PROTOTYPE_VS_F37_ORACLE_REPLAY_PARITY": prototype_vs_oracle,
    }


def _summarize(rows: list[dict[str, Any]], key: str) -> dict[str, Any]:
    failures = [row for row in rows if not row[key]["equal"]]
    return {
        "run_count": len(rows),
        "exact_identity_count": len(rows) - len(failures),
        "passed": not failures,
        "first_divergent_row": failures[0] if failures else None,
    }


def _parity() -> dict[str, Any]:
    shadow = load(SHADOW)
    positions, _ = f31._frozen_roots()
    compiled, config, profile, production, prototype = f38._context()
    oracle = f37.CandidateEvaluator(production, "R37C")
    by_budget: dict[str, Any] = {}
    all_rows: list[dict[str, Any]] = []
    for budget in BUDGETS:
        rows = []
        for item in positions:
            pid = item["position_id"]
            state = f31._imports()["sfen_to_gc_state"](compiled, item["sfen"])
            fresh_oracle = _search(compiled, oracle, state, budget)
            fresh_prototype = _search(compiled, prototype, state, budget)
            frozen = shadow["fixed_node_results"][str(budget)][pid]["R37C"]
            rows.append(_row(pid, budget, frozen, fresh_oracle, fresh_prototype))
        all_rows.extend(rows)
        by_budget[str(budget)] = {
            "rows": rows,
            "F37_ORACLE_REPLAY_PARITY": _summarize(rows, "F37_ORACLE_REPLAY_PARITY"),
            "PROTOTYPE_VS_F37_FROZEN_PARITY": _summarize(rows, "PROTOTYPE_VS_F37_FROZEN_PARITY"),
            "PROTOTYPE_VS_F37_ORACLE_REPLAY_PARITY": _summarize(rows, "PROTOTYPE_VS_F37_ORACLE_REPLAY_PARITY"),
        }
    return {
        "protocol": {
            "roots": len(positions),
            "budgets": list(BUDGETS),
            "max_depth": 8,
            "qsearch": "4/8",
            "fresh_tt_per_run": True,
            "native_requested": True,
            "timing_fields_excluded": True,
            "deterministic_fields": list(DETERMINISTIC_FIELDS),
        },
        "by_budget": by_budget,
        "all_runs": {
            "F37_ORACLE_REPLAY_PARITY": _summarize(all_rows, "F37_ORACLE_REPLAY_PARITY"),
            "PROTOTYPE_VS_F37_FROZEN_PARITY": _summarize(all_rows, "PROTOTYPE_VS_F37_FROZEN_PARITY"),
            "PROTOTYPE_VS_F37_ORACLE_REPLAY_PARITY": _summarize(all_rows, "PROTOTYPE_VS_F37_ORACLE_REPLAY_PARITY"),
        },
    }


def _reclassification(parity: dict[str, Any], bindings: dict[str, Any]) -> dict[str, Any]:
    first_pass_selection = load(F38_SELECTION)
    holdout_descriptor = load(H38A_DESCRIPTOR)
    holdout_ranks = load(F38_RANKS)
    holdout_search = load(F38_SEARCH)
    holdout_cost = load(F38_COST)
    original_search_identity = all(
        parity["all_runs"][name]["passed"]
        for name in (
            "F37_ORACLE_REPLAY_PARITY",
            "PROTOTYPE_VS_F37_FROZEN_PARITY",
            "PROTOTYPE_VS_F37_ORACLE_REPLAY_PARITY",
        )
    )
    gates = {
        "exact_static_identity": load(F38_IDENTITY)["score_identity"],
        "original_ten_root_r37c_search_identity": original_search_identity,
        "generic_transfer": load(F38_IDENTITY)["generic_transfer_contract"]["passed"],
        "holdout_corpus": len(holdout_descriptor["positions"]) >= 16,
        "holdout_static_signal": holdout_ranks["status"] == "PASS",
        "micro_cost": holdout_cost["gate"],
        "independent_search_cost": first_pass_selection["gates"]["search_cost"],
        "independent_search_signal": first_pass_selection["gates"]["search_signal"],
        "runtime_2s_safety": holdout_search["runtime_2s"]["runtime_safety_gate"],
    }
    all_parity = original_search_identity
    boundary = "F39_EVALUATOR_REENTRY_GENERALIZATION_CORRECTIVE" if all_parity and not gates["holdout_static_signal"] else "F38A_F37_SEARCH_REPRODUCIBILITY_DIAGNOSIS" if not parity["all_runs"]["F37_ORACLE_REPLAY_PARITY"]["passed"] else "F38A_R37C_PROTOTYPE_PARITY_DIAGNOSIS"
    return {
        "first_pass_defect": "WRONG_ORIGINAL_SEARCH_PARITY_ORACLE",
        "first_pass_mechanically_compared": "ProductionShapedR37CPrototype == V1 production evaluator",
        "required_comparison": "ProductionShapedR37CPrototype == frozen F37 R37C",
        "first_pass_boundary_invalidated": first_pass_selection["selected_boundary"] == "F38A_R37C_PROTOTYPE_PARITY_DIAGNOSIS",
        "gates": gates,
        "F39_IMPLEMENTATION_ELIGIBLE": False,
        "selected_boundary": boundary,
        "flags": {
            "F38_FIRST_PASS_EVIDENCE_PRESERVED": bool(bindings),
            "F38_WRONG_PARITY_ORACLE_IDENTIFIED": True,
            "F37_FROZEN_SEARCH_REPLAY_CERTIFIED": parity["all_runs"]["F37_ORACLE_REPLAY_PARITY"]["passed"],
            "R37C_PRODUCTION_SHAPE_SEARCH_IDENTITY_CERTIFIED": parity["all_runs"]["PROTOTYPE_VS_F37_FROZEN_PARITY"]["passed"],
            "F38_HOLDOUT_NEGATIVE_SIGNAL_PRESERVED": not gates["holdout_static_signal"] and gates["holdout_corpus"],
            "F38_FINAL_BOUNDARY_RECLASSIFIED": boundary == "F39_EVALUATOR_REENTRY_GENERALIZATION_CORRECTIVE",
        },
    }


def run() -> dict[str, Any]:
    bindings = evidence_bindings()
    parity = _parity()
    reclassification = _reclassification(parity, bindings)
    production_diff_zero = subprocess.run(["git", "diff", "--quiet", "--", "generic_chess"], cwd=ROOT).returncode == 0
    result = {
        "schema_version": 1,
        "status": "PASS" if production_diff_zero and reclassification["flags"]["F38_FINAL_BOUNDARY_RECLASSIFIED"] else "FAIL",
        "work_order": "GENERICCHESS-F38-CORRECTIVE-R1-FROZEN-R37C-SEARCH-PARITY-AND-BOUNDARY-RECLASSIFICATION",
        "production_diff_zero": production_diff_zero,
        "evidence_bindings": bindings,
        "parity": parity,
        "reclassification": reclassification,
        "no_rerun": {"alphasho": True, "paired_benchmark": True, "holdout_reselection": True, "candidate_formula_change": True, "production_change": True},
    }
    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run", action="store_true")
    args = parser.parse_args(argv)
    if not args.run:
        parser.error("use --run")
    result = run()
    print(json.dumps({"status": result["status"], "parity": result["parity"]["all_runs"], "selected_boundary": result["reclassification"]["selected_boundary"]}, sort_keys=True))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
