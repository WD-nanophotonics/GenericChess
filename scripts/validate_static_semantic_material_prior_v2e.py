"""Validate frozen V2E type-transition option values against unchanged references."""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
FLOW = ROOT / ".generic_chess_flow"
FREEZE = FLOW / "static-semantic-material-prior-v2e-freeze.json"
CANDIDATE = FLOW / "static-semantic-material-prior-v2e-type-transition.json"
V2D = FLOW / "static-semantic-material-prior-v2d-capture-affordance.json"
CHESS_REF = {"P": 100.0, "N": 320.0, "B": 330.0, "R": 500.0, "Q": 900.0}
CHESS_BANDS = {"N": (2.5, 3.5), "B": (2.5, 3.75), "R": (4.0, 6.0), "Q": (7.5, 11.0)}
SHOGI_GATES = {"cosine": 0.95, "spearman": 0.90, "pairwise_ordering_accuracy": 0.90}
SHOGI_TYPES = ["P", "L", "N", "S", "G", "B", "R", "TP", "TL", "TN", "TS", "TB", "TR"]


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _ranks(values: list[float]) -> list[float]:
    order = sorted(range(len(values)), key=values.__getitem__)
    result = [0.0] * len(values)
    i = 0
    while i < len(order):
        j = i + 1
        while j < len(order) and values[order[j]] == values[order[i]]:
            j += 1
        for k in range(i, j):
            result[order[k]] = (i + 1 + j) / 2
        i = j
    return result


def _corr(x: list[float], y: list[float]) -> float:
    xm, ym = sum(x) / len(x), sum(y) / len(y)
    xc, yc = [v - xm for v in x], [v - ym for v in y]
    denominator = math.sqrt(sum(v * v for v in xc) * sum(v * v for v in yc))
    return sum(a * b for a, b in zip(xc, yc)) / denominator if denominator else 0.0


def _metrics(candidate: dict[str, float], reference: dict[str, float], types: list[str]) -> dict[str, Any]:
    x, y = [float(candidate[t]) for t in types], [float(reference[t]) for t in types]
    dot = sum(a * b for a, b in zip(x, y))
    squares = sum(a * a for a in x)
    scale = dot / squares if squares else 0.0
    norm = math.sqrt(squares * sum(v * v for v in y))
    concordant = total = 0
    for i in range(len(types)):
        for j in range(i + 1, len(types)):
            concordant += int(((x[i] > x[j]) - (x[i] < x[j])) == ((y[i] > y[j]) - (y[i] < y[j])))
            total += 1
    return {"type_order": types, "best_single_global_scale": scale,
        "cosine": dot / norm if norm else 0.0, "pearson": _corr(x, y),
        "spearman": _corr(_ranks(x), _ranks(y)),
        "pairwise_ordering_accuracy": concordant / total if total else 1.0,
        "piece_residuals_scaled_candidate_minus_reference": {t: scale * candidate[t] - reference[t] for t in types},
        "piece_residuals_raw_candidate_minus_reference": {t: candidate[t] - reference[t] for t in types}}


def validate() -> dict[str, Any]:
    if not FREEZE.is_file() or not CANDIDATE.is_file() or not V2D.is_file():
        return {"classification": "STATIC_MATERIAL_PRIOR_V2E_TYPE_TRANSITION_INCONCLUSIVE",
                "human_metrics_computed": False, "reason": "Frozen candidate/input is missing."}
    freeze = json.loads(FREEZE.read_text(encoding="utf-8"))
    mismatches = {}
    for relative, expected in freeze.get("sha256", {}).items():
        path = ROOT / relative
        actual = _sha(path) if path.is_file() else None
        if actual != expected:
            mismatches[relative] = {"expected": expected, "actual": actual}
    if mismatches:
        return {"classification": "STATIC_MATERIAL_PRIOR_V2E_TYPE_TRANSITION_INCONCLUSIVE",
                "human_metrics_computed": False, "hash_mismatches": mismatches,
                "reason": "Frozen input changed; reference files were not read."}
    candidate = json.loads(CANDIDATE.read_text(encoding="utf-8"))
    v2d = json.loads(V2D.read_text(encoding="utf-8"))
    incomplete = {name: row.get("classification") for name, row in candidate["rulesets"].items()
        if not row.get("coverage_complete") or not row.get("transition_graph_acyclic")}
    base_mismatches = {}
    for name, row in candidate["rulesets"].items():
        for type_id, values in row["ledger"].items():
            baseline = v2d["rulesets"][name]["ledger"][type_id]
            for field, expected in (("b0_v2d_exact", baseline["v2d_m_exact"]),
                                    ("v2c_u_exact", baseline["v2c_u_exact"]),
                                    ("v2d_c_exact", baseline["capture_affordance_exact"])):
                if values[field] != expected:
                    base_mismatches[f"{name}:{type_id}:{field}"] = {"candidate": values[field], "frozen": expected}
    if incomplete or base_mismatches:
        return {"classification": "STATIC_MATERIAL_PRIOR_V2E_TYPE_TRANSITION_INCONCLUSIVE",
                "human_metrics_computed": False, "incomplete_rulesets": incomplete,
                "base_v2d_reproduction_mismatches": base_mismatches,
                "reason": "Transition graph/coverage or unchanged V2D base check failed; references were not read."}

    # First human-reference access for this V2E order, after hash and model preflight.
    fixture = json.loads((ROOT / "tests/fixtures/f40_material_prior_audit.json").read_text(encoding="utf-8"))
    shogi_ref = {t: float(fixture["standard_shogi_human_validation"]["human_reference"]["board"][t]) for t in SHOGI_TYPES}
    result: dict[str, Any] = {"schema_version": 1, "kind": "STATIC_MATERIAL_PRIOR_V2E_POST_FREEZE_HUMAN_VALIDATION",
        "human_metrics_computed": True, "metrics_are_validation_only": True,
        "base_v2d_reproduced": True, "freeze_sha256": freeze["sha256"], "rulesets": {}}
    chess_candidate = candidate["rulesets"]["western_chess"]["ledger"]
    chess_values = {g: {t: float(chess_candidate[t][field]) for t in CHESS_REF}
        for g, field in (("v2c", "v2c_u"), ("v2d", "b0_v2d"), ("v2e", "b1"))}
    chess_passes = {}
    for generation, values in chess_values.items():
        ratios = {t: values[t] / values["P"] for t in CHESS_BANDS}
        bands = {t: {"ratio": ratios[t], "band": list(CHESS_BANDS[t]),
                     "pass": CHESS_BANDS[t][0] <= ratios[t] <= CHESS_BANDS[t][1]} for t in CHESS_BANDS}
        ordering = values["P"] > 0 and values["P"] < values["N"] and values["P"] < values["B"] and values["N"] < values["R"] and values["B"] < values["R"] < values["Q"]
        passed = all(row["pass"] for row in bands.values()) and ordering
        chess_passes[generation] = passed
        result["rulesets"].setdefault("western_chess", {})[generation] = {"raw_values": values,
            "pawn_normalized_ratios": {"P": 1.0, **ratios}, "ratio_bands": bands,
            "sensible_ordering_positive_nonfloor_pawn": ordering,
            "metrics_vs_reference": _metrics(values, CHESS_REF, list(CHESS_REF)), "gate_pass": passed}
    result["rulesets"]["western_chess"]["raw_U_C_B0_T_B1_by_piece"] = {
        t: {"U": chess_candidate[t]["v2c_u"], "C": chess_candidate[t]["v2d_c"],
            "B0": chess_candidate[t]["b0_v2d"], "T": chess_candidate[t]["transition_premium_t"],
            "B1": chess_candidate[t]["b1"]} for t in CHESS_REF}
    result["rulesets"]["western_chess"]["gate_pass_by_generation"] = chess_passes
    result["rulesets"]["western_chess"]["human_reference"] = CHESS_REF
    shogi_candidate = candidate["rulesets"]["standard_shogi"]["ledger"]
    shogi_values = {g: {t: float(shogi_candidate[t][field]) for t in SHOGI_TYPES}
        for g, field in (("v2c", "v2c_u"), ("v2d", "b0_v2d"), ("v2e", "b1"))}
    shogi_metrics = {g: _metrics(values, shogi_ref, SHOGI_TYPES) for g, values in shogi_values.items()}
    shogi_pass = all(shogi_metrics["v2e"][key] >= threshold for key, threshold in SHOGI_GATES.items())
    result["rulesets"]["standard_shogi"] = {"validation_scope": "board_plus_type_transition_only",
        "human_reference_board": shogi_ref, "raw_values_by_generation": shogi_values,
        "raw_U_C_B0_T_B1_by_piece": {t: {"U": shogi_candidate[t]["v2c_u"], "C": shogi_candidate[t]["v2d_c"],
            "B0": shogi_candidate[t]["b0_v2d"], "T": shogi_candidate[t]["transition_premium_t"],
            "B1": shogi_candidate[t]["b1"]} for t in SHOGI_TYPES},
        "metrics_by_generation": shogi_metrics, "frozen_gates": SHOGI_GATES, "v2e_gate_pass": shogi_pass}
    chess_pass = chess_passes["v2e"]
    result["gate_summary"] = {"western_chess_v2e": chess_pass, "standard_shogi_v2e": shogi_pass}
    result["classification"] = ("STATIC_MATERIAL_PRIOR_V2E_TYPE_TRANSITION_PASS" if chess_pass and shogi_pass
        else "STATIC_MATERIAL_PRIOR_V2E_TYPE_TRANSITION_NEEDS_GENERAL_REVISION")
    return result


if __name__ == "__main__":
    output = validate()
    (FLOW / "static-semantic-material-prior-v2e-human-validation.json").write_text(
        json.dumps(output, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"classification": output["classification"], "gate_summary": output.get("gate_summary"),
        "human_metrics_computed": output["human_metrics_computed"],
        "output": ".generic_chess_flow/static-semantic-material-prior-v2e-human-validation.json"}, indent=2, sort_keys=True))
