"""Post-freeze human-reference comparison for the isolated V2A board prior."""

from __future__ import annotations

import json
import math
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

WESTERN_BANDS = {"N": (2.5, 3.5), "B": (2.5, 3.75), "R": (4.0, 6.0), "Q": (7.5, 11.0)}
SHOGI_GATES = {"cosine": 0.95, "spearman": 0.90, "pairwise_ordering": 0.90}


def _western_reference() -> dict[str, float]:
    # Evaluated only after both intrinsic semantic-coverage audits pass.
    return {"P": 100.0, "N": 320.0, "B": 330.0, "R": 500.0, "Q": 900.0}


def _pearson(left: list[float], right: list[float]) -> float:
    lm = sum(left) / len(left)
    rm = sum(right) / len(right)
    a = [x - lm for x in left]
    b = [y - rm for y in right]
    den = math.sqrt(sum(x * x for x in a) * sum(y * y for y in b))
    return sum(x * y for x, y in zip(a, b)) / den if den else 0.0


def _ranks(values: list[float]) -> list[float]:
    order = sorted(range(len(values)), key=values.__getitem__)
    ranks = [0.0] * len(values)
    i = 0
    while i < len(order):
        j = i + 1
        while j < len(order) and values[order[j]] == values[order[i]]:
            j += 1
        rank = ((i + 1) + j) / 2.0
        for k in range(i, j):
            ranks[order[k]] = rank
        i = j
    return ranks


def _pairwise(candidate: list[float], target: list[float]) -> float:
    matches = total = 0
    for i in range(len(target)):
        for j in range(i + 1, len(target)):
            total += 1
            candidate_sign = (candidate[i] > candidate[j]) - (candidate[i] < candidate[j])
            target_sign = (target[i] > target[j]) - (target[i] < target[j])
            matches += int(candidate_sign == target_sign)
    return matches / total if total else 1.0


def _metrics(candidate_by_type: dict[str, float], reference: dict[str, float], type_ids: list[str]) -> dict[str, Any]:
    x = [float(candidate_by_type[type_id]) for type_id in type_ids]
    y = [float(reference[type_id]) for type_id in type_ids]
    dot = sum(a * b for a, b in zip(x, y))
    norm = math.sqrt(sum(a * a for a in x) * sum(b * b for b in y))
    scale = dot / sum(a * a for a in x) if sum(a * a for a in x) else 0.0
    return {
        "type_order": type_ids,
        "best_single_global_scale": scale,
        "cosine": dot / norm if norm else 0.0,
        "pearson": _pearson(x, y),
        "spearman": _pearson(_ranks(x), _ranks(y)),
        "pairwise_ordering_accuracy": _pairwise(x, y),
        "piece_residuals_scaled_candidate_minus_reference": {
            type_id: scale * candidate_by_type[type_id] - reference[type_id]
            for type_id in type_ids
        },
        "piece_residuals_raw_candidate_minus_reference": {
            type_id: candidate_by_type[type_id] - reference[type_id]
            for type_id in type_ids
        },
    }


def _western(candidate: dict[str, float]) -> dict[str, Any]:
    ratios = {type_id: candidate[type_id] / candidate["P"] for type_id in ("N", "B", "R", "Q")}
    band_rows = {
        type_id: {
            "ratio": ratios[type_id],
            "band": list(WESTERN_BANDS[type_id]),
            "pass": WESTERN_BANDS[type_id][0] <= ratios[type_id] <= WESTERN_BANDS[type_id][1],
        }
        for type_id in WESTERN_BANDS
    }
    return {
        "metrics_vs_frozen_conventional_reference": _metrics(candidate, _western_reference(), ["P", "N", "B", "R", "Q"]),
        "pawn_normalized_ratios": {"P": 1.0, **ratios},
        "frozen_ratio_bands": band_rows,
        "pawn_positive_no_floor_fallback": candidate["P"] > 0,
        "ordinal_ordering_sensible": candidate["P"] < candidate["N"] < candidate["R"] < candidate["Q"] and candidate["P"] < candidate["B"] < candidate["Q"],
        "ratio_gate_pass": all(row["pass"] for row in band_rows.values()),
    }


def _full_semantic_ledger(compiled: Any, type_id: str) -> dict[str, Any]:
    held_patterns = []
    dynamic_patterns = []
    for pattern in compiled.ir.patterns:
        if type_id not in pattern.type_ids:
            continue
        for geometry_id in pattern.geometry_ids:
            geometry = compiled.ir.geometry[geometry_id]
            if geometry.kind == "drop":
                held_patterns.append({
                    "pattern": pattern.name,
                    "geometry": geometry.kind,
                    "target": pattern.target.kind,
                    "guards": [{
                        "aggregation": g.aggregation,
                        "owner": g.owner,
                        "type_ref": repr(g.type_ref),
                        "compare_field": g.compare_field,
                        "promoted": g.promoted,
                        "location": g.location,
                        "spatial_kind": g.spatial.kind,
                        "spatial_refs": [repr(ref) for ref in g.spatial.refs],
                        "comparison": g.comparison,
                        "value": g.value,
                        "subject_ref": repr(g.subject_ref),
                    } for g in pattern.guards],
                    "invariants": [inv.kind for inv in pattern.invariants],
                    "postconditions": [{"kind": post.kind, "max_stratum": post.max_stratum} for post in pattern.postconditions],
                    "effects": [{"kind": effect.kind, "disposition": effect.disposition,
                                 "piece_type_ref": repr(effect.piece_type_ref)} for effect in pattern.effects],
                })
            for invariant in pattern.invariants:
                if invariant.kind in {"own_anchor_safe", "squares_not_attacked"}:
                    dynamic_patterns.append({"pattern": pattern.name, "geometry": geometry.kind,
                                             "invariant": invariant.kind,
                                             "reason": "global positional legality; excluded from intrinsic piece-type material prior"})
    masks = compiled.support.drop_allowed.get(type_id, ())
    return {
        "held_drop_patterns": held_patterns,
        "drop_allowed_square_indices_by_owner": [
            [index for index, allowed in enumerate(mask) if allowed] for mask in masks[:2]
        ],
        "dynamic_positional_legality_patterns": dynamic_patterns,
    }


def validate() -> dict[str, Any]:
    rulesets = {
        "western_chess": compile_semantic_ruleset(build_western_chess_ruleset()),
        "standard_shogi": compile_semantic_ruleset(build_standard_shogi_ruleset()),
    }
    candidates = {name: audit_ruleset_v2a(compiled) for name, compiled in rulesets.items()}
    if not all(result["coverage_complete"] for result in candidates.values()):
        return {
            "schema_version": 1,
            "kind": "STATIC_MATERIAL_PRIOR_V2A_POST_FREEZE_HUMAN_VALIDATION",
            "classification": "STATIC_MATERIAL_PRIOR_V2A_BOARD_INCONCLUSIVE",
            "human_metrics_computed": False,
            "metrics_are_validation_only": True,
            "rulesets": {
                name: {
                    "coverage": result["classification"],
                    "coverage_complete": result["coverage_complete"],
                    "intrinsic_unsupported_semantics": result["unsupported_intrinsic_semantics"],
                    "human_metrics_computed": False,
                }
                for name, result in candidates.items()
            },
            "reason": "Fail closed before reading human-reference data because intrinsic board semantics are incomplete.",
        }

    # Human references are opened only after both coverage audits pass.
    fixture = json.loads((ROOT / "tests/fixtures/f40_material_prior_audit.json").read_text(encoding="utf-8"))
    shogi_reference = fixture["standard_shogi_human_validation"]["human_reference"]["board"]
    shogi_types = ["P", "L", "N", "S", "G", "B", "R", "TP", "TL", "TN", "TS", "TB", "TR"]
    western_reference = _western_reference()
    out: dict[str, Any] = {
        "schema_version": 1,
        "kind": "STATIC_MATERIAL_PRIOR_V2A_POST_FREEZE_HUMAN_VALIDATION",
        "candidate_definition": "ADR-122; values computed without reference imports by audit_static_semantic_material_prior_v2a.py",
        "metric_sources": {
            "western_chess": "scripts/gate1_known_game_backend_equivalence.py CHESS_MATERIAL; band gates from current Chat work order and AGENTS.md",
            "standard_shogi": "tests/fixtures/f40_material_prior_audit.json standard_shogi_human_validation.human_reference.board",
        },
        "metrics_are_validation_only": True,
        "human_metrics_computed": True,
        "rulesets": {},
    }
    for name, compiled in rulesets.items():
        result = candidates[name]
        old = audit_v2_ruleset(compiled)
        candidate_v2 = {tid: row["board_intrinsic"] for tid, row in old["ledger"].items()}
        candidate_v2a = {tid: row["v2a_phase_averaged_board_intrinsic"] for tid, row in result["ledger"].items()}
        diagnostics = {
            tid: {
                "v2_raw_board_value": candidate_v2[tid],
                "v2_components": old["ledger"][tid]["components"],
                "v2a_raw_board_value": candidate_v2a[tid],
                "v2a_components": result["ledger"][tid]["components"],
                "ray_path_attenuation": result["ledger"][tid]["components"]["ray_path_attenuation"],
                "source_restriction_excluded_raw": result["ledger"][tid]["components"]["source_restriction_excluded_raw"],
                "immediate_promotion_branch_mass": result["ledger"][tid]["components"]["immediate_promotion_branch_mass"],
                "dynamic_positional_legality_ledger_count": result["ledger"][tid]["dynamic_positional_legality_ledger_count"],
                "held_drop_semantics_ledger_count": result["ledger"][tid]["held_drop_semantics_ledger_count"],
                "drop_mask_allowed_outcomes_ledgered_not_scored": result["ledger"][tid]["drop_mask_allowed_outcomes_ledgered_not_scored"],
                "source_destination_candidates": result["ledger"][tid]["source_destination_candidates"],
                "source_restricted_candidate_count": result["ledger"][tid]["source_restricted_candidate_count"],
                "distinct_geometric_source_destination_pairs": result["ledger"][tid]["distinct_geometric_source_destination_pairs"],
                "promotion_transitions": result["ledger"][tid]["promotion_transitions"],
                "complete_semantic_ledger": _full_semantic_ledger(compiled, tid),
            }
            for tid in candidate_v2
        }
        if name == "western_chess":
            out["rulesets"][name] = {
                "coverage": result["classification"],
                "human_reference": western_reference,
                "v2": {"raw_board_values": {t: candidate_v2[t] for t in western_reference}, **_western({t: candidate_v2[t] for t in western_reference})},
                "v2a": {"raw_board_values": {t: candidate_v2a[t] for t in western_reference}, **_western({t: candidate_v2a[t] for t in western_reference})},
                "components": {t: result["ledger"][t]["components"] for t in western_reference},
                "per_type_diagnostics": diagnostics,
                "classification_gate_pass": all(_western({t: candidate_v2a[t] for t in western_reference})["frozen_ratio_bands"][t]["pass"] for t in WESTERN_BANDS),
            }
        else:
            out["rulesets"][name] = {
                "coverage": result["classification"],
                "human_reference_board": {t: shogi_reference[t] for t in shogi_types},
                "v2": {"raw_board_values": {t: candidate_v2[t] for t in shogi_types}, "metrics": _metrics(candidate_v2, shogi_reference, shogi_types)},
                "v2a": {"raw_board_values": {t: candidate_v2a[t] for t in shogi_types}, "metrics": _metrics(candidate_v2a, shogi_reference, shogi_types),
                        "components": {t: result["ledger"][t]["components"] for t in shogi_types}},
                "per_type_diagnostics": diagnostics,
            }
            shogi_metrics = out["rulesets"][name]["v2a"]["metrics"]
            out["rulesets"][name]["classification_gate_pass"] = bool(
                result["coverage_complete"]
                and shogi_metrics["cosine"] >= SHOGI_GATES["cosine"]
                and shogi_metrics["spearman"] >= SHOGI_GATES["spearman"]
                and shogi_metrics["pairwise_ordering_accuracy"] >= SHOGI_GATES["pairwise_ordering"]
            )
            out["rulesets"][name]["thresholds"] = SHOGI_GATES

    chess_pass = out["rulesets"]["western_chess"]["classification_gate_pass"]
    shogi_pass = out["rulesets"]["standard_shogi"]["classification_gate_pass"]
    out["classification"] = (
        "STATIC_MATERIAL_PRIOR_V2A_BOARD_CHESS_SHOGI_PASS" if chess_pass and shogi_pass
        else "STATIC_MATERIAL_PRIOR_V2A_BOARD_NEEDS_GENERAL_REVISION"
    )
    out["gate_summary"] = {"western_chess": chess_pass, "standard_shogi": shogi_pass}
    out["next_scope"] = "Board-only milestone; Shogi held/drop theory remains unresolved; Xiangqi is not authorized by this result."
    return out


def main() -> int:
    result = validate()
    output = ROOT / ".generic_chess_flow" / "static-semantic-material-prior-v2a-validation.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "output": str(output),
        "classification": result["classification"],
        "gate_summary": result["gate_summary"],
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
