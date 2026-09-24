"""Fail-closed pre-reference freeze and arithmetic audit for the domain diagnostic."""

from __future__ import annotations

from fractions import Fraction
import hashlib
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / ".generic_chess_flow/static-material-domain-conditional-capability.json"
FREEZE = ROOT / ".generic_chess_flow/static-material-domain-conditional-capability-freeze.json"
V2C_FREEZE = ROOT / ".generic_chess_flow/static-semantic-material-prior-v2c-freeze.json"
V2C_RAW = ROOT / ".generic_chess_flow/static-semantic-material-prior-v2c-board.json"
V2D_FREEZE = ROOT / ".generic_chess_flow/static-semantic-material-prior-v2d-freeze.json"
V2D_RAW = ROOT / ".generic_chess_flow/static-semantic-material-prior-v2d-capture-affordance.json"
TOPOLOGY_FREEZE = ROOT / ".generic_chess_flow/static-material-domain-fragmentation-freeze.json"
TOPOLOGY_RAW = ROOT / ".generic_chess_flow/static-material-domain-fragmentation-topology.json"
FILES = (
    "docs/architecture/ADR-129-static-material-domain-conditional-capability-diagnostic.md",
    "scripts/audit_static_material_domain_conditional_capability.py",
    "scripts/freeze_static_material_domain_conditional_capability.py",
    "tests/test_static_material_domain_conditional_capability.py",
    ".generic_chess_flow/static-semantic-material-prior-v2c-freeze.json",
    ".generic_chess_flow/static-semantic-material-prior-v2c-board.json",
    ".generic_chess_flow/static-semantic-material-prior-v2d-freeze.json",
    ".generic_chess_flow/static-semantic-material-prior-v2d-capture-affordance.json",
    ".generic_chess_flow/static-material-domain-fragmentation-freeze.json",
    ".generic_chess_flow/static-material-domain-fragmentation-topology.json",
)


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _fraction(value: str) -> Fraction:
    numerator, denominator = value.split("/", 1)
    return Fraction(int(numerator), int(denominator))


def _canonical_sha(value: Any) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _verify_baseline_freeze(path: Path) -> dict[str, Any]:
    freeze = json.loads(path.read_text(encoding="utf-8"))
    if freeze.get("human_metrics_computed") is not False:
        raise RuntimeError(f"Baseline is not a pre-reference freeze: {path.name}")
    if freeze.get("reference_data_read") not in (None, False):
        raise RuntimeError(f"Baseline reference data was read: {path.name}")
    for relative, expected in freeze.get("sha256", {}).items():
        source = ROOT / relative
        if not source.is_file() or _sha(source) != expected:
            raise RuntimeError(f"Frozen baseline hash mismatch: {relative}")
    return freeze


def freeze() -> dict[str, Any]:
    _verify_baseline_freeze(V2C_FREEZE)
    _verify_baseline_freeze(V2D_FREEZE)
    topology_freeze = json.loads(TOPOLOGY_FREEZE.read_text(encoding="utf-8"))
    if (topology_freeze.get("human_reference_read") is not False
            or topology_freeze.get("v2d_validation_residuals_read") is not False):
        raise RuntimeError("ADR-128 topology is not proven pre-reference")
    for relative, expected in topology_freeze["sha256"].items():
        source = ROOT / relative
        if not source.is_file() or _sha(source) != expected:
            raise RuntimeError(f"Frozen topology hash mismatch: {relative}")
    if _sha(TOPOLOGY_RAW) != topology_freeze["topology_candidate_sha256"]:
        raise RuntimeError("ADR-128 raw topology hash mismatch")

    raw = json.loads(RAW.read_text(encoding="utf-8"))
    false_flags = (
        "human_reference_imported", "v2d_residuals_imported", "material_formula_modified",
        "score_validation_performed", "v2e_transition_value_used", "transport_efficiency_used",
        "transition_bearing_domain_payoff_assigned", "piece_specific_logic", "game_specific_logic",
    )
    if any(raw.get(key) is not False for key in false_flags):
        raise RuntimeError("Raw candidate violates no-score/no-reference diagnostic boundary")
    if raw.get("factorization_scope") != "same_weak_domain_random_target_diagnostic_only_not_directed_reachability_or_game_deployment":
        raise RuntimeError("Random-target diagnostic scope is not correctly qualified")
    if not raw.get("coverage_complete") or not raw.get("reconstruction_complete"):
        raise RuntimeError("Candidate coverage or frozen baseline reconstruction is incomplete")

    v2d = json.loads(V2D_RAW.read_text(encoding="utf-8"))
    source_hashes = {
        "v2c_freeze": _sha(V2C_FREEZE), "v2c_candidate": _sha(V2C_RAW),
        "v2d_freeze": _sha(V2D_FREEZE), "v2d_candidate": _sha(V2D_RAW),
        "topology_freeze": _sha(TOPOLOGY_FREEZE), "topology_candidate": _sha(TOPOLOGY_RAW),
    }
    if source_hashes != raw.get("input_sha256"):
        raise RuntimeError("Candidate input digest manifest mismatch")

    type_manifest: dict[str, Any] = {}
    terminal_count = 0
    transition_count = 0
    for ruleset, ruleset_row in sorted(raw["rulesets"].items()):
        area = int(ruleset_row["board_area"])
        baseline_types = v2d["rulesets"][ruleset]["ledger"]
        if set(ruleset_row["types"]) != set(baseline_types):
            raise RuntimeError(f"Candidate type set differs from frozen V2D: {ruleset}")
        type_manifest[ruleset] = {}
        for type_id, row in sorted(ruleset_row["types"].items()):
            if not all(row["semantic_coverage"].values()):
                raise RuntimeError(f"Semantic coverage incomplete: {ruleset}/{type_id}")
            baseline = baseline_types[type_id]
            expected_u = _fraction(baseline["v2c_u_exact"])
            expected_c = _fraction(baseline["capture_affordance_exact"])
            expected_b = _fraction(baseline["v2d_m_exact"])
            if (_fraction(row["u_exact"]) != expected_u
                    or _fraction(row["c_exact"]) != expected_c
                    or _fraction(row["b0_exact"]) != expected_b
                    or expected_u + expected_c != expected_b):
                raise RuntimeError(f"Global V2D reconstruction mismatch: {ruleset}/{type_id}")
            source_hashes_for_type = {}
            for owner in ("0", "1"):
                owner_row = row["owner_graphs"][owner]
                sources = owner_row["source_rows"]
                if len(sources) != area or [item["source_square"] for item in sources] != list(range(area)):
                    raise RuntimeError(f"Source table is incomplete: {ruleset}/{type_id}/{owner}")
                local_u = sum((_fraction(item["u_exact"]) for item in sources), Fraction(0)) / area
                local_c = sum((_fraction(item["c_exact"]) for item in sources), Fraction(0)) / area
                local_b = sum((_fraction(item["b_exact"]) for item in sources), Fraction(0)) / area
                if (local_u != _fraction(owner_row["u_owner_average_exact"])
                        or local_c != _fraction(owner_row["c_owner_average_exact"])
                        or local_b != _fraction(owner_row["b0_owner_average_exact"])):
                    raise RuntimeError(f"Owner/source reconstruction mismatch: {ruleset}/{type_id}/{owner}")
                if any(_fraction(item["b_exact"]) != _fraction(item["u_exact"]) + _fraction(item["c_exact"])
                       for item in sources):
                    raise RuntimeError(f"Source-local b != u+c: {ruleset}/{type_id}/{owner}")
                source_hashes_for_type[owner] = _canonical_sha(sources)

                domains = owner_row["domain_conditioned"]["domains"]
                if row["terminal_current_type"]:
                    weighted_u = sum((_fraction(domain["w_exact"]) * _fraction(domain["u_bar_exact"])
                                      for domain in domains), Fraction(0))
                    weighted_c = sum((_fraction(domain["w_exact"]) * _fraction(domain["c_bar_exact"])
                                      for domain in domains), Fraction(0))
                    weighted_b = sum((_fraction(domain["w_exact"]) * _fraction(domain["b_bar_exact"])
                                      for domain in domains), Fraction(0))
                    if (weighted_u != local_u or weighted_c != local_c or weighted_b != local_b):
                        raise RuntimeError(f"Domain-conditioned reconstruction mismatch: {ruleset}/{type_id}/{owner}")
                    if any(_fraction(domain["b_bar_exact"]) != _fraction(domain["u_bar_exact"])
                           + _fraction(domain["c_bar_exact"]) for domain in domains):
                        raise RuntimeError(f"Domain conditional Bbar != Ubar+Cbar: {ruleset}/{type_id}/{owner}")
                    d = sum((_fraction(domain["w_exact"]) ** 2 for domain in domains), Fraction(0))
                    j = sum((_fraction(domain["w_exact"]) ** 2 * _fraction(domain["b_bar_exact"])
                             for domain in domains), Fraction(0))
                    b0_owner = _fraction(owner_row["b0_owner_average_exact"])
                    if _fraction(owner_row["domain_conditioned"]["d_exact"]) != d:
                        raise RuntimeError(f"D identity mismatch: {ruleset}/{type_id}/{owner}")
                    if (_fraction(owner_row["domain_conditioned"]["j_exact"]) != j
                            or _fraction(owner_row["domain_conditioned"]["fct_exact"]) != b0_owner * d
                            or _fraction(owner_row["domain_conditioned"]["factorization_error_exact"]) != b0_owner * d - j):
                        raise RuntimeError(f"Owner joint/FCT identity mismatch: {ruleset}/{type_id}/{owner}")
                else:
                    transition_count += 1 if owner == "0" else 0
                    if set(owner_row["domain_conditioned"]) != {"domains", "same_type_d_exact", "joint_measure_status"}:
                        raise RuntimeError(f"Transition type has an assigned joint diagnostic: {ruleset}/{type_id}/{owner}")
                    if owner_row["domain_conditioned"]["joint_measure_status"] != "NOT_APPLICABLE_TRANSITION_BEARING_TYPE":
                        raise RuntimeError(f"Transition type lacks N/A joint status: {ruleset}/{type_id}/{owner}")

            terminal = not row["outgoing_type_transition_types"]
            if terminal != row["terminal_current_type"]:
                raise RuntimeError(f"Terminal classification mismatch: {ruleset}/{type_id}")
            if terminal:
                terminal_count += 1
                j = _fraction(row["j_exact"])
                fct = _fraction(row["fct_owner_consistent_exact"])
                error = fct - j
                if _fraction(row["factorization_error_exact"]) != error:
                    raise RuntimeError(f"Terminal factorization identity mismatch: {ruleset}/{type_id}")
                if row["joint_measure_status"] != "APPLICABLE_TERMINAL_TYPE_SAME_WEAK_DOMAIN_RANDOM_TARGET_DIAGNOSTIC_ONLY":
                    raise RuntimeError(f"Terminal joint diagnostic scope missing: {ruleset}/{type_id}")
                if row["r_joint_exact"] is not None and _fraction(row["r_joint_exact"]) != j / expected_b:
                    raise RuntimeError(f"R_joint mismatch: {ruleset}/{type_id}")
            else:
                if any(row.get(key) is not None for key in (
                        "j_exact", "fct_owner_consistent_exact", "factorization_error_exact",
                        "relative_factorization_error_exact", "r_joint_exact")):
                    raise RuntimeError(f"Transition type has terminal joint values: {ruleset}/{type_id}")
            type_manifest[ruleset][type_id] = {
                "terminal_current_type": terminal,
                "source_u_c_b_sha256_by_owner": source_hashes_for_type,
                "domain_table_sha256_by_owner": {owner: _canonical_sha(row["owner_graphs"][owner]["domain_conditioned"])
                                                  for owner in ("0", "1")},
                "reconstructed_u_exact": row["u_exact"],
                "reconstructed_c_exact": row["c_exact"],
                "reconstructed_b0_exact": row["b0_exact"],
                "j_exact": row["j_exact"],
                "fct_owner_consistent_exact": row["fct_owner_consistent_exact"],
                "factorization_error_exact": row["factorization_error_exact"],
            }

    if terminal_count == 0 or transition_count == 0:
        raise RuntimeError("Expected terminal and transition-bearing benchmark types")
    errors = [row["factorization_error_exact"] for ruleset in raw["rulesets"].values()
              for row in ruleset["types"].values() if row["terminal_current_type"]]
    expected_classification = ("STATIC_MATERIAL_DOMAIN_CONDITIONAL_CAPABILITY_FACTORABLE"
                               if all(_fraction(value) == 0 for value in errors)
                               else "STATIC_MATERIAL_DOMAIN_CONDITIONAL_CAPABILITY_NONFACTORABLE")
    if raw["classification"] != expected_classification:
        raise RuntimeError("Classification does not match exact terminal factorization errors")

    output = {
        "schema_version": 1,
        "kind": "STATIC_MATERIAL_DOMAIN_CONDITIONAL_CAPABILITY_PRE_REFERENCE_FREEZE",
        "classification": raw["classification"],
        "candidate_sha256": _sha(RAW),
        "reference_data_read": False,
        "human_validation_performed": False,
        "material_score_modified": False,
        "factorization_scope": raw["factorization_scope"],
        "terminal_type_count": terminal_count,
        "transition_bearing_type_count": transition_count,
        "all_source_and_domain_reconstructions_exact": True,
        "sha256": {relative: _sha(ROOT / relative) for relative in FILES},
        "inputs": raw["input_sha256"],
        "types": type_manifest,
    }
    FREEZE.write_text(json.dumps(output, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return output


def main() -> int:
    result = freeze()
    print(json.dumps({"freeze": str(FREEZE), "candidate_sha256": result["candidate_sha256"],
        "classification": result["classification"], "terminal_type_count": result["terminal_type_count"],
        "transition_bearing_type_count": result["transition_bearing_type_count"],
        "reference_data_read": result["reference_data_read"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
