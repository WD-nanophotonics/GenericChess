"""Post-freeze validation of V2D against the unchanged Chess/Shogi references."""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
FLOW = ROOT / ".generic_chess_flow"
FREEZE = FLOW / "static-semantic-material-prior-v2d-freeze.json"
CANDIDATE = FLOW / "static-semantic-material-prior-v2d-capture-affordance.json"
V2C = FLOW / "static-semantic-material-prior-v2c-board.json"
CHESS_REF = {"P": 100.0, "N": 320.0, "B": 330.0, "R": 500.0, "Q": 900.0}
CHESS_BANDS = {"N": (2.5, 3.5), "B": (2.5, 3.75), "R": (4.0, 6.0), "Q": (7.5, 11.0)}
SHOGI_GATES = {"cosine": 0.95, "spearman": 0.90, "pairwise_ordering_accuracy": 0.90}
SHOGI_TYPES = ["P", "L", "N", "S", "G", "B", "R", "TP", "TL", "TN", "TS", "TB", "TR"]


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _ranks(values: list[float]) -> list[float]:
    order = sorted(range(len(values)), key=values.__getitem__)
    ranks = [0.0] * len(values)
    i = 0
    while i < len(order):
        j = i + 1
        while j < len(order) and values[order[j]] == values[order[i]]:
            j += 1
        for k in range(i, j):
            ranks[order[k]] = (i + 1 + j) / 2
        i = j
    return ranks


def _corr(x: list[float], y: list[float]) -> float:
    xm, ym = sum(x) / len(x), sum(y) / len(y)
    xc, yc = [v - xm for v in x], [v - ym for v in y]
    den = math.sqrt(sum(v * v for v in xc) * sum(v * v for v in yc))
    return sum(a * b for a, b in zip(xc, yc)) / den if den else 0.0


def _metrics(candidate: dict[str, float], reference: dict[str, float], types: list[str]) -> dict[str, Any]:
    x, y = [float(candidate[t]) for t in types], [float(reference[t]) for t in types]
    dot = sum(a * b for a, b in zip(x, y))
    xx = sum(a * a for a in x)
    scale = dot / xx if xx else 0.0
    norm = math.sqrt(xx * sum(v * v for v in y))
    matches = pairs = 0
    for i in range(len(types)):
        for j in range(i + 1, len(types)):
            matches += int(((x[i] > x[j]) - (x[i] < x[j])) == ((y[i] > y[j]) - (y[i] < y[j])))
            pairs += 1
    return {"type_order": types, "best_single_global_scale": scale,
        "cosine": dot / norm if norm else 0.0, "pearson": _corr(x, y),
        "spearman": _corr(_ranks(x), _ranks(y)), "pairwise_ordering_accuracy": matches / pairs if pairs else 1.0,
        "piece_residuals_scaled_candidate_minus_reference": {t: scale * candidate[t] - reference[t] for t in types},
        "piece_residuals_raw_candidate_minus_reference": {t: candidate[t] - reference[t] for t in types}}


def validate() -> dict[str, Any]:
    if not FREEZE.is_file() or not CANDIDATE.is_file():
        return {"classification": "STATIC_MATERIAL_PRIOR_V2D_CAPTURE_AFFORDANCE_INCONCLUSIVE",
                "human_metrics_computed": False, "reason": "Freeze or candidate file is missing."}
    freeze = json.loads(FREEZE.read_text(encoding="utf-8"))
    mismatches = {}
    for relative, expected in freeze.get("sha256", {}).items():
        path = ROOT / relative
        actual = _sha(path) if path.is_file() else None
        if actual != expected:
            mismatches[relative] = {"expected": expected, "actual": actual}
    if mismatches:
        return {"classification": "STATIC_MATERIAL_PRIOR_V2D_CAPTURE_AFFORDANCE_INCONCLUSIVE",
                "human_metrics_computed": False, "hash_mismatches": mismatches,
                "reason": "Frozen input changed; reference files were not read."}
    candidate = json.loads(CANDIDATE.read_text(encoding="utf-8"))
    v2c = json.loads(V2C.read_text(encoding="utf-8"))
    incomplete = {name: row.get("classification") for name, row in candidate["rulesets"].items()
        if not row.get("coverage_complete") or not row.get("ledger")}
    mismatched_u = {}
    for name, row in candidate["rulesets"].items():
        for type_id, values in row["ledger"].items():
            if values["v2c_u_exact"] != v2c["rulesets"][name]["ledger"][type_id]["v2c_exact"]:
                mismatched_u[f"{name}:{type_id}"] = {"V2D_U": values["v2c_u_exact"],
                                                       "frozen_V2C": v2c["rulesets"][name]["ledger"][type_id]["v2c_exact"]}
    if incomplete or mismatched_u:
        return {"classification": "STATIC_MATERIAL_PRIOR_V2D_CAPTURE_AFFORDANCE_INCONCLUSIVE",
                "human_metrics_computed": False, "incomplete_rulesets": incomplete,
                "V2C_U_baseline_mismatches": mismatched_u,
                "reason": "Capture coverage or unchanged V2C baseline check failed; references were not read."}

    # The first human-reference read for this V2D order occurs only after hash and coverage preflight.
    fixture = json.loads((ROOT / "tests/fixtures/f40_material_prior_audit.json").read_text(encoding="utf-8"))
    shogi_ref = {t: float(fixture["standard_shogi_human_validation"]["human_reference"]["board"][t]) for t in SHOGI_TYPES}
    result: dict[str, Any] = {"schema_version": 1, "kind": "STATIC_MATERIAL_PRIOR_V2D_POST_FREEZE_HUMAN_VALIDATION",
        "human_metrics_computed": True, "metrics_are_validation_only": True,
        "freeze_sha256": freeze["sha256"], "v2c_u_reproduced_exactly": True, "rulesets": {}}
    chess_row = candidate["rulesets"]["western_chess"]["ledger"]
    chess_generations = {"v2c": {t: float(chess_row[t]["v2c_u"]) for t in CHESS_REF},
                         "v2d": {t: float(chess_row[t]["v2d_m"]) for t in CHESS_REF}}
    chess_gates = {}
    for generation, vals in chess_generations.items():
        ratios = {t: vals[t] / vals["P"] for t in CHESS_BANDS}
        bands = {t: {"ratio": ratios[t], "band": list(CHESS_BANDS[t]),
                     "pass": CHESS_BANDS[t][0] <= ratios[t] <= CHESS_BANDS[t][1]} for t in CHESS_BANDS}
        ordering = vals["P"] > 0 and vals["P"] < vals["N"] and vals["P"] < vals["B"] and vals["N"] < vals["R"] and vals["B"] < vals["R"] < vals["Q"]
        passed = all(v["pass"] for v in bands.values()) and ordering
        chess_gates[generation] = passed
        result["rulesets"].setdefault("western_chess", {})[generation] = {
            "raw_values": vals, "pawn_normalized_ratios": {"P": 1.0, **ratios}, "ratio_bands": bands,
            "sensible_ordering_positive_pawn_no_floor_fallback": ordering,
            "metrics_vs_reference": _metrics(vals, CHESS_REF, list(CHESS_REF)), "gate_pass": passed}
    result["rulesets"]["western_chess"]["human_reference"] = CHESS_REF
    result["rulesets"]["western_chess"]["gate_pass_by_generation"] = chess_gates
    result["rulesets"]["western_chess"]["raw_U_C_M_by_piece"] = {
        t: {"U": chess_row[t]["v2c_u"], "C": chess_row[t]["capture_affordance"], "M": chess_row[t]["v2d_m"]}
        for t in CHESS_REF}
    shogi_row = candidate["rulesets"]["standard_shogi"]["ledger"]
    shogi_generations = {g: {t: float(shogi_row[t][field]) for t in SHOGI_TYPES}
        for g, field in (("v2c", "v2c_u"), ("v2d", "v2d_m"))}
    shogi_metrics = {g: _metrics(vals, shogi_ref, SHOGI_TYPES) for g, vals in shogi_generations.items()}
    shogi_pass = all(shogi_metrics["v2d"][key] >= threshold for key, threshold in SHOGI_GATES.items())
    result["rulesets"]["standard_shogi"] = {"validation_scope": "board_capture_affordance_only",
        "capture_to_hand_future_hand_value_included": False, "human_reference_board": shogi_ref,
        "raw_values_by_generation": shogi_generations, "metrics_by_generation": shogi_metrics,
        "raw_U_C_M_by_piece": {t: {"U": shogi_row[t]["v2c_u"], "C": shogi_row[t]["capture_affordance"],
                                    "M": shogi_row[t]["v2d_m"]} for t in SHOGI_TYPES},
        "frozen_gates": SHOGI_GATES, "v2d_gate_pass": shogi_pass}
    chess_pass = chess_gates["v2d"]
    result["gate_summary"] = {"western_chess_v2d": chess_pass, "standard_shogi_v2d": shogi_pass}
    result["classification"] = ("STATIC_MATERIAL_PRIOR_V2D_CAPTURE_AFFORDANCE_PASS" if chess_pass and shogi_pass
        else "STATIC_MATERIAL_PRIOR_V2D_CAPTURE_AFFORDANCE_NEEDS_GENERAL_REVISION")
    return result


if __name__ == "__main__":
    output = validate()
    (FLOW / "static-semantic-material-prior-v2d-human-validation.json").write_text(
        json.dumps(output, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"classification": output["classification"], "gate_summary": output.get("gate_summary"),
        "human_metrics_computed": output["human_metrics_computed"],
        "output": ".generic_chess_flow/static-semantic-material-prior-v2d-human-validation.json"}, indent=2, sort_keys=True))
