"""Validate the already-frozen V2G candidate; reference reads occur after preflight."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
FLOW = ROOT / ".generic_chess_flow"
FREEZE = FLOW / "static-material-v2g-redeployment-throughput-freeze.json"
CANDIDATE = FLOW / "static-material-v2g-redeployment-throughput.json"
V2C = FLOW / "static-semantic-material-prior-v2c-board.json"
CAPABILITY = FLOW / "static-material-domain-conditional-capability.json"
FIXTURE = ROOT / "tests/fixtures/f40_material_prior_audit.json"
OUTPUT = FLOW / "static-material-v2g-redeployment-throughput-human-validation.json"

from scripts.validate_static_semantic_material_prior_v2d import (
    CHESS_BANDS,
    CHESS_REF,
    SHOGI_GATES,
    SHOGI_TYPES,
    _metrics,
)
from scripts.static_material_v2g_validator_provenance import check_validator_version


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _f(value: str) -> float:
    numerator, denominator = value.split("/", 1)
    return int(numerator) / int(denominator)


def _preflight() -> tuple[dict[str, Any] | None, dict[str, Any] | None, dict[str, Any] | None]:
    """Return freeze/candidate/baselines only if every frozen input still matches."""
    if not FREEZE.is_file() or not CANDIDATE.is_file():
        return None, None, None
    freeze = json.loads(FREEZE.read_text(encoding="utf-8"))
    own_relative = Path(__file__).resolve().relative_to(ROOT).as_posix()
    mismatches = {}
    validator_provenance = check_validator_version(freeze, Path(__file__).resolve())
    if not validator_provenance["approved"]:
        mismatches["validator_provenance"] = validator_provenance
    for relative, expected in freeze.get("sha256", {}).items():
        # Its hash is checked against the exact frozen/current pair above.
        if relative == own_relative:
            continue
        path = ROOT / relative
        actual = _sha(path) if path.is_file() else None
        if actual != expected:
            mismatches[relative] = {"expected": expected, "actual": actual}
    candidate = json.loads(CANDIDATE.read_text(encoding="utf-8"))
    if _sha(CANDIDATE) != freeze.get("candidate_sha256"):
        mismatches["candidate"] = {"expected": freeze.get("candidate_sha256"), "actual": _sha(CANDIDATE)}
    if candidate.get("input_sha256") != freeze.get("input_sha256"):
        mismatches["candidate_input_manifest"] = {"expected": freeze.get("input_sha256"),
                                                   "actual": candidate.get("input_sha256")}
    if freeze.get("reference_data_read") is not False or freeze.get("human_validation_performed") is not False:
        mismatches["pre_reference_freeze"] = {"expected": False, "actual": True}
    if mismatches:
        return freeze, None, {"hash_mismatches": mismatches}
    if any(candidate.get(key) is not False for key in (
        "human_reference_imported", "human_validation_performed", "free_material_coefficient",
        "context_weight_used", "v2e_transition_value_used", "adr124_transport_cost_used",
        "density_scan_used", "piece_specific_logic", "game_specific_logic",
        "production_evaluator_modified", "score_validation_performed",
    )):
        return freeze, None, {"reason": "Candidate flags violate pre-reference frozen boundary."}

    # Baseline files are frozen inputs; loading them here does not load human values.
    v2c = json.loads(V2C.read_text(encoding="utf-8"))
    capability = json.loads(CAPABILITY.read_text(encoding="utf-8"))
    for ruleset, ruleset_row in candidate["rulesets"].items():
        expected_types = set(ruleset_row["types"])
        if expected_types != set(v2c["rulesets"][ruleset]["ledger"]) - set(ruleset_row["anchor_types_excluded"]):
            return freeze, None, {"reason": f"V2C type coverage differs for {ruleset}."}
        if expected_types != set(capability["rulesets"][ruleset]["types"]) - set(ruleset_row["anchor_types_excluded"]):
            return freeze, None, {"reason": f"V2D/ADR-129 type coverage differs for {ruleset}."}
        for type_id in expected_types:
            cap = capability["rulesets"][ruleset]["types"][type_id]
            if cap["b0_exact"] != candidate["rulesets"][ruleset]["types"][type_id]["frozen_v2d_b0_exact"]:
                return freeze, None, {"reason": f"Frozen V2D B0 differs for {ruleset}/{type_id}."}
    return freeze, candidate, {
        "v2c": v2c,
        "capability": capability,
        "validation_code_provenance": validator_provenance,
    }


def validate() -> dict[str, Any]:
    freeze, candidate, prepared = _preflight()
    if candidate is None or prepared is None or "hash_mismatches" in prepared or "reason" in prepared:
        return {
            "schema_version": 1,
            "kind": "STATIC_MATERIAL_PRIOR_V2G_POST_FREEZE_HUMAN_VALIDATION",
            "classification": "STATIC_MATERIAL_PRIOR_V2G_REDEPLOYMENT_THROUGHPUT_INCONCLUSIVE",
            "human_metrics_computed": False,
            "reason": prepared or "Candidate preflight failed; reference file was not opened.",
        }

    # This is the first human-reference read in the V2G pipeline, after full freeze preflight.
    fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
    shogi_reference = {
        type_id: float(fixture["standard_shogi_human_validation"]["human_reference"]["board"][type_id])
        for type_id in SHOGI_TYPES
    }
    chess_candidate_by_version: dict[str, dict[str, float]] = {}
    chess_row = candidate["rulesets"]["western_chess"]["types"]
    v2c_chess = prepared["v2c"]["rulesets"]["western_chess"]["ledger"]
    v2d_chess = prepared["capability"]["rulesets"]["western_chess"]["types"]
    chess_candidate_by_version["v2c"] = {
        t: float(v2c_chess[t]["v2c_maxent_token_board_intrinsic"]) for t in CHESS_REF
    }
    chess_candidate_by_version["v2d"] = {t: _f(v2d_chess[t]["b0_exact"]) for t in CHESS_REF}
    chess_candidate_by_version["v2g"] = {t: _f(chess_row[t]["M_exact"]) for t in CHESS_REF}

    result: dict[str, Any] = {
        "schema_version": 1,
        "kind": "STATIC_MATERIAL_PRIOR_V2G_POST_FREEZE_HUMAN_VALIDATION",
        "classification": "",
        "human_metrics_computed": True,
        "metrics_are_validation_only": True,
        "candidate_sha256": freeze["candidate_sha256"],
        "freeze_sha256": _sha(FREEZE),
        "candidate_freeze_preceded_reference_read": True,
        "validation_code_provenance": prepared["validation_code_provenance"],
        "human_reference_sources": {
            "western_chess": "unchanged conventional reference targets used by frozen V2C/V2D validation",
            "standard_shogi": "tests/fixtures/f40_material_prior_audit.json standard_shogi_human_validation.human_reference.board",
        },
        "rulesets": {},
    }
    chess_gate_by_version = {}
    for version, values in chess_candidate_by_version.items():
        ratios = {type_id: values[type_id] / values["P"] for type_id in CHESS_BANDS}
        bands = {
            type_id: {
                "ratio": ratios[type_id],
                "frozen_band": list(CHESS_BANDS[type_id]),
                "pass": CHESS_BANDS[type_id][0] <= ratios[type_id] <= CHESS_BANDS[type_id][1],
            }
            for type_id in CHESS_BANDS
        }
        ordering = (
            values["P"] > 0
            and values["P"] < values["N"]
            and values["P"] < values["B"]
            and values["N"] < values["R"]
            and values["B"] < values["R"] < values["Q"]
        )
        passed = all(row["pass"] for row in bands.values()) and ordering
        chess_gate_by_version[version] = passed
        result["rulesets"].setdefault("western_chess", {})[version] = {
            "raw_values": values,
            "pawn_normalized_ratios": {"P": 1.0, **ratios},
            "frozen_ratio_bands": bands,
            "positive_nonfloor_pawn_and_sensible_ordering": ordering,
            "gate_pass": passed,
            "metrics_vs_reference": _metrics(values, CHESS_REF, list(CHESS_REF)),
        }
    result["rulesets"]["western_chess"]["human_reference"] = CHESS_REF
    result["rulesets"]["western_chess"]["gate_pass_by_version"] = chess_gate_by_version

    shogi_row = candidate["rulesets"]["standard_shogi"]["types"]
    shogi_v2c = prepared["v2c"]["rulesets"]["standard_shogi"]["ledger"]
    shogi_v2d = prepared["capability"]["rulesets"]["standard_shogi"]["types"]
    shogi_candidate_by_version = {
        "v2c": {
            type_id: float(shogi_v2c[type_id]["v2c_maxent_token_board_intrinsic"])
            for type_id in SHOGI_TYPES
        },
        "v2d": {type_id: _f(shogi_v2d[type_id]["b0_exact"]) for type_id in SHOGI_TYPES},
        "v2g": {type_id: _f(shogi_row[type_id]["M_exact"]) for type_id in SHOGI_TYPES},
    }
    shogi_metrics = {
        version: _metrics(values, shogi_reference, SHOGI_TYPES)
        for version, values in shogi_candidate_by_version.items()
    }
    v2g_shogi_pass = all(shogi_metrics["v2g"][gate] >= threshold
                         for gate, threshold in SHOGI_GATES.items())
    result["rulesets"]["standard_shogi"] = {
        "validation_scope": "board_capture_plus_semantic_redeployment_throughput_only",
        "held_drop_reentry_value_included": False,
        "human_reference_board": shogi_reference,
        "raw_values_by_version": shogi_candidate_by_version,
        "pawn_normalized_ratios_by_version": {
            version: {type_id: values[type_id] / values["P"] for type_id in SHOGI_TYPES}
            for version, values in shogi_candidate_by_version.items()
        },
        "metrics_by_version": shogi_metrics,
        "frozen_gates": SHOGI_GATES,
        "v2g_gate_pass": v2g_shogi_pass,
    }
    chess_pass = chess_gate_by_version["v2g"]
    result["gate_summary"] = {
        "western_chess_v2g": chess_pass,
        "standard_shogi_v2g": v2g_shogi_pass,
    }
    result["classification"] = (
        "STATIC_MATERIAL_PRIOR_V2G_REDEPLOYMENT_THROUGHPUT_PASS"
        if chess_pass and v2g_shogi_pass
        else "STATIC_MATERIAL_PRIOR_V2G_REDEPLOYMENT_THROUGHPUT_NEEDS_GENERAL_REVISION"
    )
    return result


if __name__ == "__main__":
    validation = validate()
    OUTPUT.write_text(json.dumps(validation, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "classification": validation["classification"],
        "gate_summary": validation.get("gate_summary"),
        "human_metrics_computed": validation["human_metrics_computed"],
        "output": str(OUTPUT),
    }, indent=2, sort_keys=True))
