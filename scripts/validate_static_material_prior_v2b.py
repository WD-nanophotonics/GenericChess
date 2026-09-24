"""Post-freeze validation of V2B against unchanged human-reference gates."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from generic_chess.rules.compiler import compile_semantic_ruleset
from generic_chess.rules.standard_shogi import build_standard_shogi_ruleset
from generic_chess.rules.western_chess import build_western_chess_ruleset
from scripts.audit_static_semantic_material_prior_v2 import audit_ruleset as audit_v2_ruleset
from scripts.audit_static_semantic_material_prior_v2a import audit_ruleset_v2a
from scripts.audit_static_semantic_material_prior_v2b import audit_ruleset_v2b
from scripts.validate_static_material_prior_v2a import (
    SHOGI_GATES,
    _full_semantic_ledger,
    _metrics,
    _western,
    _western_reference,
)

FREEZE = ROOT / ".generic_chess_flow" / "static-semantic-material-prior-v2b-freeze.json"
EXPECTED_FROZEN_FILES = {
    "scripts/audit_static_semantic_material_prior_v2a.py",
    "scripts/audit_static_semantic_material_prior_v2b.py",
    "scripts/freeze_static_semantic_material_prior_v2b.py",
    "scripts/validate_static_material_prior_v2b.py",
    "tests/test_static_semantic_material_prior_v2b.py",
    "docs/architecture/ADR-123-static-semantic-material-prior-v2b.md",
}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _freeze_preflight() -> dict[str, Any]:
    if not FREEZE.is_file():
        raise RuntimeError("V2B freeze manifest is absent; human references must remain unread")
    freeze = json.loads(FREEZE.read_text(encoding="utf-8"))
    files = freeze.get("sha256", {})
    if set(files) != EXPECTED_FROZEN_FILES | {".generic_chess_flow/static-semantic-material-prior-v2b-board.json"}:
        raise RuntimeError("V2B freeze manifest file set is incomplete or unexpected")
    for relative, expected in files.items():
        actual = _sha256(ROOT / relative)
        if actual != expected:
            raise RuntimeError(f"frozen V2B input changed: {relative}")
    if freeze.get("hypothesis") != "Evaluate the unchanged V2A semantic-event polynomial at rho_ref=rho_max, derived only from the executable initial conserved physical token inventory and board area.":
        raise RuntimeError("freeze manifest does not contain the preregistered inventory-density hypothesis")
    return freeze


def validate() -> dict[str, Any]:
    freeze = _freeze_preflight()
    rulesets = {
        "western_chess": compile_semantic_ruleset(build_western_chess_ruleset()),
        "standard_shogi": compile_semantic_ruleset(build_standard_shogi_ruleset()),
    }
    v2a_results = {name: audit_ruleset_v2a(compiled) for name, compiled in rulesets.items()}
    v2b_results = {name: audit_ruleset_v2b(compiled) for name, compiled in rulesets.items()}
    all_results = [*v2a_results.values(), *v2b_results.values()]
    if not all(result["coverage_complete"] for result in all_results):
        return {
            "schema_version": 1,
            "kind": "STATIC_MATERIAL_PRIOR_V2B_POST_FREEZE_HUMAN_VALIDATION",
            "classification": "STATIC_MATERIAL_PRIOR_V2B_FULL_DENSITY_BOARD_INCONCLUSIVE",
            "human_metrics_computed": False,
            "metrics_are_validation_only": True,
            "freeze_sha256": freeze["sha256"],
            "rulesets": {
                name: {
                    "v2a_coverage": v2a_results[name]["classification"],
                    "v2b_coverage": v2b_results[name]["classification"],
                    "v2a_coverage_complete": v2a_results[name]["coverage_complete"],
                    "v2b_coverage_complete": v2b_results[name]["coverage_complete"],
                    "human_metrics_computed": False,
                }
                for name in rulesets
            },
            "reason": "Fail closed before reading human references because frozen intrinsic coverage is incomplete.",
        }

    # Human-reference data is intentionally read only after freeze verification and coverage gates.
    fixture = json.loads((ROOT / "tests/fixtures/f40_material_prior_audit.json").read_text(encoding="utf-8"))
    shogi_reference = fixture["standard_shogi_human_validation"]["human_reference"]["board"]
    shogi_types = ["P", "L", "N", "S", "G", "B", "R", "TP", "TL", "TN", "TS", "TB", "TR"]
    western_reference = _western_reference()
    out: dict[str, Any] = {
        "schema_version": 1,
        "kind": "STATIC_MATERIAL_PRIOR_V2B_POST_FREEZE_HUMAN_VALIDATION",
        "candidate_definition": "ADR-123; unchanged V2A event construction, fixed at inventory-derived rho_max",
        "freeze_sha256": freeze["sha256"],
        "metrics_are_validation_only": True,
        "human_metrics_computed": True,
        "rulesets": {},
    }
    gates: dict[str, bool] = {}
    for name, compiled in rulesets.items():
        v2 = audit_v2_ruleset(compiled)
        v2a = v2a_results[name]
        v2b = v2b_results[name]
        rows = v2b["ledger"]
        v2_values = {type_id: row["board_intrinsic"] for type_id, row in v2["ledger"].items()}
        v2a_values = {type_id: row["v2a_phase_averaged_board_intrinsic"] for type_id, row in v2a["ledger"].items()}
        v2b_values = {type_id: row["v2b_fixed_rho_max_board_intrinsic"] for type_id, row in rows.items()}
        diagnostics = {
            type_id: {
                "v2_fixed_rho_2_3": v2_values[type_id],
                "v2a_uniform_0_rho_max": v2a_values[type_id],
                "v2b_fixed_rho_max": v2b_values[type_id],
                "v2b_exact": rows[type_id]["v2b_raw_exact"],
                "v2a_exact": v2a["ledger"][type_id]["v2a_raw_exact"],
                "v2b_components": rows[type_id]["components"],
                "v2b_components_exact": rows[type_id]["components_exact"],
                "v2a_components": v2a["ledger"][type_id]["components"],
                "v2a_components_exact": v2a["ledger"][type_id]["components_exact"],
                "dynamic_positional_legality_ledger_count": rows[type_id]["dynamic_positional_legality_ledger_count"],
                "held_drop_semantics_ledger_count": rows[type_id]["held_drop_semantics_ledger_count"],
                "drop_mask_allowed_outcomes_ledgered_not_scored": rows[type_id]["drop_mask_allowed_outcomes_ledgered_not_scored"],
                "source_destination_candidates": rows[type_id]["source_destination_candidates"],
                "source_restricted_candidate_count": rows[type_id]["source_restricted_candidate_count"],
                "distinct_geometric_source_destination_pairs": rows[type_id]["distinct_geometric_source_destination_pairs"],
                "promotion_transitions": rows[type_id]["promotion_transitions"],
                "complete_semantic_ledger": _full_semantic_ledger(compiled, type_id),
            }
            for type_id in v2_values
        }
        if name == "western_chess":
            metrics = _western(v2b_values)
            gates[name] = bool(
                v2b["coverage_complete"]
                and metrics["ratio_gate_pass"]
                and metrics["ordinal_ordering_sensible"]
                and metrics["pawn_positive_no_floor_fallback"]
            )
            out["rulesets"][name] = {
                "coverage": v2b["classification"],
                "rho_reference": v2b["inventory_bound"]["rho_max"],
                "human_reference": western_reference,
                "v2": {"raw_board_values": {t: v2_values[t] for t in western_reference}, **_western({t: v2_values[t] for t in western_reference})},
                "v2a": {"raw_board_values": {t: v2a_values[t] for t in western_reference}, **_western({t: v2a_values[t] for t in western_reference})},
                "v2b": {"raw_board_values": {t: v2b_values[t] for t in western_reference}, **metrics},
                "per_type_diagnostics": diagnostics,
                "classification_gate_pass": gates[name],
            }
        else:
            metrics_v2 = _metrics(v2_values, shogi_reference, shogi_types)
            metrics_v2a = _metrics(v2a_values, shogi_reference, shogi_types)
            metrics_v2b = _metrics(v2b_values, shogi_reference, shogi_types)
            gates[name] = bool(
                v2b["coverage_complete"]
                and metrics_v2b["cosine"] >= SHOGI_GATES["cosine"]
                and metrics_v2b["spearman"] >= SHOGI_GATES["spearman"]
                and metrics_v2b["pairwise_ordering_accuracy"] >= SHOGI_GATES["pairwise_ordering"]
            )
            out["rulesets"][name] = {
                "coverage": v2b["classification"],
                "rho_reference": v2b["inventory_bound"]["rho_max"],
                "human_reference_board": {t: shogi_reference[t] for t in shogi_types},
                "v2": {"raw_board_values": {t: v2_values[t] for t in shogi_types}, "metrics": metrics_v2},
                "v2a": {"raw_board_values": {t: v2a_values[t] for t in shogi_types}, "metrics": metrics_v2a},
                "v2b": {"raw_board_values": {t: v2b_values[t] for t in shogi_types}, "metrics": metrics_v2b},
                "per_type_diagnostics": diagnostics,
                "classification_gate_pass": gates[name],
                "thresholds": SHOGI_GATES,
            }
    out["gate_summary"] = gates
    out["classification"] = (
        "STATIC_MATERIAL_PRIOR_V2B_FULL_DENSITY_BOARD_PASS" if all(gates.values())
        else "STATIC_MATERIAL_PRIOR_V2B_FULL_DENSITY_BOARD_NEEDS_GENERAL_REVISION"
    )
    out["next_scope"] = (
        "If PASS: stop; Shogi held/drop value remains a separate Priority-1 question."
        if all(gates.values()) else
        "If FAIL: report residual pattern; do not density-scan, patch piece values, or begin another hypothesis."
    )
    return out


def main() -> int:
    result = validate()
    output = ROOT / ".generic_chess_flow" / "static-semantic-material-prior-v2b-validation.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(output), "classification": result["classification"], "gate_summary": result.get("gate_summary")}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
