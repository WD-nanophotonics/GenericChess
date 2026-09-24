"""Post-freeze descriptive transport/residual comparison (no fitting or inference)."""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]

FREEZE = ROOT / ".generic_chess_flow" / "static-material-transport-efficiency-freeze.json"
RAW = ROOT / ".generic_chess_flow" / "static-material-transport-efficiency-raw.json"
V2B = ROOT / ".generic_chess_flow" / "static-semantic-material-prior-v2b-validation.json"
FROZEN_FILES = {
    "scripts/static_material_transport_efficiency.py",
    "scripts/freeze_static_material_transport_efficiency.py",
    "scripts/validate_static_material_transport_efficiency.py",
    "tests/test_static_material_transport_efficiency.py",
    "docs/architecture/ADR-124-static-material-transport-efficiency.md",
    ".generic_chess_flow/static-material-transport-efficiency-raw.json",
}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _ranks(values: list[float]) -> list[float]:
    order = sorted(range(len(values)), key=values.__getitem__)
    ranks = [0.0] * len(values)
    start = 0
    while start < len(order):
        end = start + 1
        while end < len(order) and values[order[end]] == values[order[start]]:
            end += 1
        rank = ((start + 1) + end) / 2
        for i in range(start, end):
            ranks[order[i]] = rank
        start = end
    return ranks


def _pearson(x: list[float], y: list[float]) -> float:
    xm, ym = sum(x) / len(x), sum(y) / len(y)
    xc, yc = [v - xm for v in x], [v - ym for v in y]
    den = math.sqrt(sum(v * v for v in xc) * sum(v * v for v in yc))
    return sum(a * b for a, b in zip(xc, yc)) / den if den else 0.0


def _preflight() -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    if not FREEZE.is_file() or not RAW.is_file() or not V2B.is_file():
        raise RuntimeError("required transport freeze/raw output or already-frozen V2B validation is absent")
    freeze = json.loads(FREEZE.read_text(encoding="utf-8"))
    hashes = freeze.get("sha256", {})
    if set(hashes) != FROZEN_FILES:
        raise RuntimeError("transport freeze manifest file set is unexpected")
    for relative, expected in hashes.items():
        if _sha256(ROOT / relative) != expected:
            raise RuntimeError(f"frozen transport input changed: {relative}")
    if freeze.get("reference_data_read") is not False or freeze.get("v2b_residuals_read") is not False:
        raise RuntimeError("transport feature was not frozen before residual access")
    raw = json.loads(RAW.read_text(encoding="utf-8"))
    if raw.get("human_reference_imported") is not False or raw.get("v2b_residuals_imported") is not False:
        raise RuntimeError("raw transport feature includes validation data")
    v2b = json.loads(V2B.read_text(encoding="utf-8"))
    if v2b.get("classification") != "STATIC_MATERIAL_PRIOR_V2B_FULL_DENSITY_BOARD_NEEDS_GENERAL_REVISION":
        raise RuntimeError("the expected frozen V2B development residual report is unavailable")
    return freeze, raw, v2b


def validate() -> dict[str, Any]:
    freeze, raw, v2b = _preflight()
    chess = raw["rulesets"]["western_chess"]
    chess_v2b = v2b["rulesets"]["western_chess"]["v2b"]
    reference = v2b["rulesets"]["western_chess"]["human_reference"]
    scale = chess_v2b["metrics_vs_frozen_conventional_reference"]["best_single_global_scale"]
    chess_types = ["P", "N", "B", "R", "Q"]
    correction = {type_id: reference[type_id] - scale * chess_v2b["raw_board_values"][type_id] for type_id in chess_types}
    efficiency = {type_id: chess["types"][type_id]["metrics"]["global_transport_efficiency"] for type_id in chess_types}
    efficiency_rank = {
        type_id: rank for rank, type_id in enumerate(sorted(chess_types, key=efficiency.__getitem__), start=1)
    }
    under = [type_id for type_id in chess_types if correction[type_id] > 0]
    over = [type_id for type_id in chess_types if correction[type_id] < 0]
    pearson = _pearson([efficiency[t] for t in chess_types], [correction[t] for t in chess_types])
    spearman = _pearson(_ranks([efficiency[t] for t in chess_types]), _ranks([correction[t] for t in chess_types]))
    mean_under = sum(efficiency[t] for t in under) / len(under) if under else 0.0
    mean_over = sum(efficiency[t] for t in over) / len(over) if over else 0.0
    supported = pearson > 0 and mean_under > mean_over
    chess_report = {
        type_id: {
            "v2b_raw_material_value": chess_v2b["raw_board_values"][type_id],
            "best_global_scale": scale,
            "scaled_v2b_value": scale * chess_v2b["raw_board_values"][type_id],
            "required_correction_human_minus_scaled_v2b": correction[type_id],
            "transport_efficiency": efficiency[type_id],
            "reachable_fraction": chess["types"][type_id]["metrics"]["unweighted_reachable_fraction"],
            "mean_finite_transport_cost": chess["types"][type_id]["metrics"]["weighted_mean_finite_transport_cost"],
            "transport_efficiency_rank": efficiency_rank[type_id],
        }
        for type_id in chess_types
    }
    shogi = raw["rulesets"]["standard_shogi"]
    shogi_v2b = v2b["rulesets"]["standard_shogi"]["v2b"]
    shogi_scaled_residuals = shogi_v2b["metrics"]["piece_residuals_scaled_candidate_minus_reference"]
    shogi_report = {
        type_id: {
            "transport_efficiency": row["metrics"]["global_transport_efficiency"],
            "reachable_fraction": row["metrics"]["unweighted_reachable_fraction"],
            "mean_finite_transport_cost": row["metrics"]["weighted_mean_finite_transport_cost"],
            "v2b_scaled_residual_candidate_minus_reference": shogi_scaled_residuals[type_id],
        }
        for type_id, row in shogi["types"].items()
    }
    return {
        "schema_version": 1,
        "kind": "STATIC_MATERIAL_TRANSPORT_EFFICIENCY_POST_FREEZE_DEVELOPMENT_DIAGNOSTIC",
        "freeze_sha256": freeze["sha256"],
        "development_set_only": True,
        "independent_validation": False,
        "significance_claims": False,
        "v2b_material_values_modified": False,
        "western_chess": {
            "types": chess_report,
            "pearson_E_vs_required_correction": pearson,
            "spearman_E_vs_required_correction": spearman,
            "mean_E_underpredicted_types": mean_under,
            "mean_E_overpredicted_types": mean_over,
            "underpredicted_types": under,
            "overpredicted_types": over,
            "pearson_positive": pearson > 0,
            "underpredicted_mean_E_greater": mean_under > mean_over,
        },
        "standard_shogi": shogi_report,
        "classification": (
            "STATIC_MATERIAL_TRANSPORT_HYPOTHESIS_INCONCLUSIVE"
            if raw["classification"] == "STATIC_MATERIAL_TRANSPORT_FEATURE_INCONCLUSIVE"
            else "STATIC_MATERIAL_TRANSPORT_HYPOTHESIS_SUPPORTED" if supported
            else "STATIC_MATERIAL_TRANSPORT_HYPOTHESIS_NOT_SUPPORTED"
        ),
    }


def main() -> int:
    result = validate()
    output = ROOT / ".generic_chess_flow" / "static-material-transport-efficiency-validation.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(output), "classification": result["classification"],
                      "pearson": result["western_chess"]["pearson_E_vs_required_correction"],
                      "mean_E_under": result["western_chess"]["mean_E_underpredicted_types"],
                      "mean_E_over": result["western_chess"]["mean_E_overpredicted_types"]}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
