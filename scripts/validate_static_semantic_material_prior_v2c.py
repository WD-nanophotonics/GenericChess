"""Validate the frozen V2C candidate against human references after hash preflight."""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
FREEZE = ROOT / ".generic_chess_flow/static-semantic-material-prior-v2c-freeze.json"
CANDIDATE = ROOT / ".generic_chess_flow/static-semantic-material-prior-v2c-board.json"
WESTERN_REFERENCE = {"P": 100.0, "N": 320.0, "B": 330.0, "R": 500.0, "Q": 900.0}
WESTERN_BANDS = {"N": (2.5, 3.5), "B": (2.5, 3.75), "R": (4.0, 6.0), "Q": (7.5, 11.0)}
SHOGI_GATES = {"cosine": 0.95, "spearman": 0.90, "pairwise_ordering_accuracy": 0.90}
GENERATIONS = {
    "v2": "v2_fixed_occupancy_board_intrinsic",
    "v2a": "v2a_uniform_0_rho_max",
    "v2b": "v2b_fixed_rho_max",
    "v2c": "v2c_maxent_token_board_intrinsic",
}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _ranks(xs: list[float]) -> list[float]:
    order = sorted(range(len(xs)), key=xs.__getitem__)
    result = [0.0] * len(xs)
    i = 0
    while i < len(order):
        j = i + 1
        while j < len(order) and xs[order[j]] == xs[order[i]]:
            j += 1
        for k in range(i, j):
            result[order[k]] = (i + 1 + j) / 2
        i = j
    return result


def _correlation(x: list[float], y: list[float]) -> float:
    xm, ym = sum(x) / len(x), sum(y) / len(y)
    xx, yy = [v - xm for v in x], [v - ym for v in y]
    den = math.sqrt(sum(v * v for v in xx) * sum(v * v for v in yy))
    return sum(a * b for a, b in zip(xx, yy)) / den if den else 0.0


def _metrics(candidate: dict[str, float], reference: dict[str, float], types: list[str]) -> dict[str, Any]:
    x, y = [float(candidate[t]) for t in types], [float(reference[t]) for t in types]
    dot = sum(a * b for a, b in zip(x, y))
    xx = sum(a * a for a in x)
    scale = dot / xx if xx else 0.0
    norm = math.sqrt(xx * sum(v * v for v in y))
    matched = total = 0
    for i in range(len(types)):
        for j in range(i + 1, len(types)):
            matched += int((x[i] > x[j]) - (x[i] < x[j]) == (y[i] > y[j]) - (y[i] < y[j]))
            total += 1
    return {
        "type_order": types,
        "best_single_global_scale": scale,
        "cosine": dot / norm if norm else 0.0,
        "pearson": _correlation(x, y),
        "spearman": _correlation(_ranks(x), _ranks(y)),
        "pairwise_ordering_accuracy": matched / total if total else 1.0,
        "piece_residuals_scaled_candidate_minus_reference": {t: scale * candidate[t] - reference[t] for t in types},
        "piece_residuals_raw_candidate_minus_reference": {t: candidate[t] - reference[t] for t in types},
    }


def validate() -> dict[str, Any]:
    if not FREEZE.is_file() or not CANDIDATE.is_file():
        return {"classification": "STATIC_MATERIAL_PRIOR_V2C_INCONCLUSIVE", "human_metrics_computed": False,
                "reason": "Pre-reference freeze or candidate file is missing."}
    frozen = json.loads(FREEZE.read_text(encoding="utf-8"))
    mismatches = {}
    for relative, expected in frozen.get("sha256", {}).items():
        path = ROOT / relative
        actual = _sha256(path) if path.is_file() else None
        if actual != expected:
            mismatches[relative] = {"expected": expected, "actual": actual}
    if mismatches:
        return {"classification": "STATIC_MATERIAL_PRIOR_V2C_INCONCLUSIVE", "human_metrics_computed": False,
                "hash_mismatches": mismatches, "reason": "Frozen inputs changed; references were not read."}

    candidate = json.loads(CANDIDATE.read_text(encoding="utf-8"))
    incomplete = {
        name: row.get("classification") for name, row in candidate.get("rulesets", {}).items()
        if not row.get("coverage_complete") or row.get("human_reference_imported") or row.get("human_metrics_computed")
        or not row.get("token_state_ledger", {}).get("complete")
    }
    if incomplete:
        return {"classification": "STATIC_MATERIAL_PRIOR_V2C_INCONCLUSIVE", "human_metrics_computed": False,
                "incomplete_rulesets": incomplete, "reason": "Coverage/ledger incomplete; references were not read."}

    # This is intentionally the first reference-data read in the V2C pipeline.
    fixture = json.loads((ROOT / "tests/fixtures/f40_material_prior_audit.json").read_text(encoding="utf-8"))
    shogi_ref = fixture["standard_shogi_human_validation"]["human_reference"]["board"]
    shogi_types = ["P", "L", "N", "S", "G", "B", "R", "TP", "TL", "TN", "TS", "TB", "TR"]
    out: dict[str, Any] = {"schema_version": 1, "kind": "STATIC_MATERIAL_PRIOR_V2C_POST_FREEZE_HUMAN_VALIDATION",
                           "classification": "", "human_metrics_computed": True, "metrics_are_validation_only": True,
                           "freeze_sha256": frozen["sha256"], "rulesets": {}}
    chess_ledger = candidate["rulesets"]["western_chess"]["ledger"]
    chess_passes = {}
    for generation, field in GENERATIONS.items():
        vals = {t: float(chess_ledger[t][field]) for t in WESTERN_REFERENCE}
        ratios = {t: vals[t] / vals["P"] for t in WESTERN_BANDS}
        bands = {t: {"ratio": ratios[t], "band": list(WESTERN_BANDS[t]),
                     "pass": WESTERN_BANDS[t][0] <= ratios[t] <= WESTERN_BANDS[t][1]} for t in WESTERN_BANDS}
        passed = all(row["pass"] for row in bands.values()) and vals["P"] > 0 and vals["P"] < vals["N"] < vals["R"] < vals["Q"] and vals["P"] < vals["B"] < vals["Q"]
        chess_passes[generation] = passed
        out["rulesets"].setdefault("western_chess", {})[generation] = {"raw_board_values": vals,
            "pawn_normalized_ratios": {"P": 1.0, **ratios}, "frozen_ratio_bands": bands,
            "sensible_ordering_and_positive_pawn": vals["P"] > 0 and vals["P"] < vals["N"] < vals["R"] < vals["Q"] and vals["P"] < vals["B"] < vals["Q"],
            "gate_pass": passed, "metrics_vs_reference": _metrics(vals, WESTERN_REFERENCE, list(WESTERN_REFERENCE))}
    shogi_ledger = candidate["rulesets"]["standard_shogi"]["ledger"]
    shogi_values = {g: {t: float(shogi_ledger[t][field]) for t in shogi_types} for g, field in GENERATIONS.items()}
    shogi_metrics = {g: _metrics(vals, shogi_ref, shogi_types) for g, vals in shogi_values.items()}
    shogi_pass = all(shogi_metrics["v2c"][key] >= threshold for key, threshold in SHOGI_GATES.items())
    out["rulesets"]["standard_shogi"] = {"human_reference_board": {t: shogi_ref[t] for t in shogi_types},
        "raw_board_values_by_generation": shogi_values, "metrics_by_generation": shogi_metrics,
        "frozen_gates": SHOGI_GATES, "v2c_gate_pass": shogi_pass,
        "per_piece_v2c_components": {t: shogi_ledger[t]["components_v2c"] for t in shogi_types}}
    out["rulesets"]["western_chess"]["human_reference"] = WESTERN_REFERENCE
    out["rulesets"]["western_chess"]["gate_pass_by_generation"] = chess_passes
    out["gate_summary"] = {"western_chess_v2c": chess_passes["v2c"], "standard_shogi_v2c": shogi_pass}
    out["classification"] = ("STATIC_MATERIAL_PRIOR_V2C_MAXENT_TOKEN_ENSEMBLE_PASS"
                              if chess_passes["v2c"] and shogi_pass
                              else "STATIC_MATERIAL_PRIOR_V2C_NEEDS_GENERAL_REVISION")
    out["human_reference_sources"] = {"western_chess": "frozen conventional material targets in ADR-125",
                                      "standard_shogi": "tests/fixtures/f40_material_prior_audit.json"}
    return out


if __name__ == "__main__":
    result = validate()
    (ROOT / ".generic_chess_flow/static-semantic-material-prior-v2c-human-validation.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps({"classification": result["classification"], "gate_summary": result.get("gate_summary"),
                      "validation_path": ".generic_chess_flow/static-semantic-material-prior-v2c-human-validation.json",
                      "human_metrics_computed": result["human_metrics_computed"]}, indent=2, sort_keys=True))
