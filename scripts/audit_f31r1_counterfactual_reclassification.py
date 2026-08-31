"""Evidence-only corrective reclassification of the frozen F31 results."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "tests" / "fixtures" / "f31_causal_manifest.json"
FIRST_PASS = ROOT / "tests" / "fixtures" / "f31_causal_diagnosis.json"
OUTPUT = ROOT / "tests" / "fixtures" / "f31r1_counterfactual_causal_reclassification.json"
PRODUCT_AUTHORITY = "a389adc50ed42096874ee38f818584978468c6ac"
F31_MANIFEST_SHA = "e08867b24fc268581b7853caf8e6bf2da0d2c25307c36120540313ea44f677dd"
F31_RESULT_SHA = "9eaaccf9ecea8717e6a2ffe198da9136cb1e7fee0ee9ac2edcb60d6f70d8b77e"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _rows(result: dict[str, Any], variant: str, seconds: str) -> dict[str, dict[str, Any]]:
    return result["timing_and_ablations"][variant][seconds]


def _effect_table(result: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    table: dict[str, list[dict[str, Any]]] = {}
    for seconds in ("0.5", "2.0"):
        baseline = _rows(result, "baseline", seconds)
        root_off = _rows(result, "root_tactical_off", seconds)
        q_off = _rows(result, "qsearch_off", seconds)
        table[seconds] = []
        for position_id in baseline:
            b = baseline[position_id]
            r = root_off[position_id]
            q = q_off[position_id]
            table[seconds].append(
                {
                    "position_id": position_id,
                    "baseline": {key: b[key] for key in ("selected_move", "completed_depth", "fallback", "elapsed_seconds", "total_nodes")},
                    "root_tactical_off": {key: r[key] for key in ("selected_move", "completed_depth", "fallback", "elapsed_seconds", "total_nodes")},
                    "qsearch_off": {key: q[key] for key in ("selected_move", "completed_depth", "fallback", "elapsed_seconds", "total_nodes")},
                    "alpha_sho_0.5_modal": b["reference_050"],
                    "alpha_sho_2.0_modal": b["reference_200"],
                    "root_tactical_effect": {"depth_delta": r["completed_depth"] - b["completed_depth"], "fallback_delta": int(r["fallback"]) - int(b["fallback"]), "reference_delta": int(r["reference_top1"]) - int(b["reference_top1"])},
                    "qsearch_effect": {"depth_delta": q["completed_depth"] - b["completed_depth"], "fallback_delta": int(q["fallback"]) - int(b["fallback"]), "reference_delta": int(q["reference_top1"]) - int(b["reference_top1"])},
                }
            )
    return table


def _aggregate(table: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for seconds, rows in table.items():
        result[seconds] = {}
        for name in ("root_tactical_effect", "qsearch_effect"):
            effects = [row[name] for row in rows]
            result[seconds][name] = {
                "roots_gaining_depth": sum(effect["depth_delta"] > 0 for effect in effects),
                "roots_losing_depth": sum(effect["depth_delta"] < 0 for effect in effects),
                "fallbacks_removed": sum(effect["fallback_delta"] < 0 for effect in effects),
                "fallbacks_added": sum(effect["fallback_delta"] > 0 for effect in effects),
                "reference_count_delta": sum(effect["reference_delta"] for effect in effects),
            }
    return result


def _forced_summary(result: dict[str, Any]) -> dict[str, Any]:
    categories = {"alpha_sho_candidate_remains_worse_through_depth_2": 0, "alpha_sho_candidate_catches_or_equalizes": 0, "alpha_sho_candidate_becomes_better": 0}
    details = {}
    for position_id, candidates in result["horizon_native_forced"]["forced_candidates"]["roots"].items():
        gc_move = result["causal_classification"]["per_root"][position_id]["generic_050"]
        as_move = result["causal_classification"]["per_root"][position_id]["alpha_sho_050"]
        if as_move not in candidates or gc_move not in candidates:
            continue
        as_score = candidates[as_move]["2"]["root_perspective_score"]
        gc_score = candidates[gc_move]["2"]["root_perspective_score"]
        if as_score > gc_score:
            category = "alpha_sho_candidate_becomes_better"
        elif as_score == gc_score:
            category = "alpha_sho_candidate_catches_or_equalizes"
        else:
            category = "alpha_sho_candidate_remains_worse_through_depth_2"
        categories[category] += 1
        details[position_id] = {"generic_chess_0.5_move": gc_move, "alphasho_0.5_move": as_move, "generic_chess_depth_2_score": gc_score, "alphasho_depth_2_score": as_score, "category": category}
    return {"counts": categories, "roots": details}


def reclassify() -> dict[str, Any]:
    manifest = load(MANIFEST)
    first_pass = load(FIRST_PASS)
    if manifest["manifest_sha256"] != F31_MANIFEST_SHA or sha(FIRST_PASS) != F31_RESULT_SHA:
        raise AssertionError("F31 first-pass evidence identity changed")
    table = _effect_table(first_pass)
    aggregate = _aggregate(table)
    baseline = first_pass["timing_and_ablations"]["baseline"]
    throughput = {
        seconds: {
            "average_nodes_per_second": sum(row["total_nodes"] / row["elapsed_seconds"] for row in rows.values()) / len(rows),
            "average_total_nodes": sum(row["total_nodes"] for row in rows.values()) / len(rows),
            "provider_modes": sorted({row["provider_mode"] for row in rows.values()}),
        }
        for seconds, rows in baseline.items()
    }
    causal_families = {
        "evaluator_value": {"label": "MATERIAL", "basis": "fresh AlphaSho modal moves are outside current evaluator-v1 static top-3 on 8/10 roots"},
        "accessible_horizon_depth_efficiency": {"label": "PRIMARY", "basis": "qsearch OFF gains one completed main-search ply on 10/10 roots at both controls"},
        "root_tactical_scan_computational_overhead": {"label": "NOT_SUPPORTED", "basis": "root-tactical OFF gains depth on 0/10 roots, removes 0/10 fallbacks at both controls"},
        "root_fallback_mechanism": {"label": "NOT_SUPPORTED", "basis": "fallback is an observed output; qsearch OFF removes 10/10 short-control fallbacks while root-tactical OFF removes none"},
        "qsearch_computational_cost": {"label": "PRIMARY", "basis": "qsearch OFF gains depth on 10/10 roots at 0.50 s and 2.00 s and removes all 10 short-control fallbacks"},
        "qsearch_decision_quality_contribution": {"label": "MATERIAL", "basis": "qsearch OFF loses one external-reference hit at each control, so qsearch quality benefit is not discarded"},
        "tt_order_pvs": {"label": "UNRESOLVED", "basis": "frozen fixed-node matrix has no consistent move/depth winner across TT, ordering, and PVS variants"},
        "python_semantic_runtime_throughput": {"label": "PRIMARY", "basis": "provider remains Python fallback and qsearch cost suppresses accessible depth under equal wall time"},
        "native_capability_gating": {"label": "UNRESOLVED", "status": "NATIVE_COUNTERFACTUAL_UNAVAILABLE", "basis": "live and stripped requested runs all report Python fallback"},
    }
    flags = {key: True for key in ("F30_EXTERNAL_BASELINE_CONSUMED", "STATIC_EVALUATOR_CAUSAL_AUDIT_COMPLETE", "SEARCH_HORIZON_CAUSAL_AUDIT_COMPLETE", "SEARCH_POLICY_ABLATION_COMPLETE", "RUNTIME_THROUGHPUT_CAUSAL_AUDIT_COMPLETE", "STANDARD_SHOGI_EXTERNAL_GAP_CAUSAL_DIAGNOSIS_COMPLETE")}
    return {
        "schema_version": 1,
        "status": "PASS",
        "kind": "F31R1_COUNTERFACTUAL_CAUSAL_RECLASSIFICATION",
        "production_changed": False,
        "input_identities": {"manifest_path": "tests/fixtures/f31_causal_manifest.json", "manifest_sha256": F31_MANIFEST_SHA, "diagnosis_path": "tests/fixtures/f31_causal_diagnosis.json", "diagnosis_file_sha256": F31_RESULT_SHA, "product_authority": PRODUCT_AUTHORITY},
        "rerun_policy": "No expensive F31 experiments rerun; reclassification consumes frozen measurements byte-identically.",
        "wall_time_effect_table": table,
        "aggregate_effects": aggregate,
        "throughput_context": throughput,
        "forced_candidate_summary": _forced_summary(first_pass),
        "stalemate_gate": first_pass["stalemate_audit"],
        "causal_families": causal_families,
        "first_pass_aggregate_labels": first_pass["causal_classification"]["aggregate_labels"],
        "corrected_next_boundary": "F32_SEARCH_HORIZON_AND_QUIESCENCE_DIAGNOSIS",
        "boundary_rationale": ["qsearch OFF gains one completed main-search ply on all ten roots at both controls", "qsearch OFF removes all ten 0.50 s fallbacks while retaining a quality contribution signal", "root-tactical OFF gains no depth and removes no fallback", "Native remains unavailable, so no Native boundary is selected"],
        "flags": flags,
    }


def main() -> int:
    result = reclassify()
    OUTPUT.write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": result["status"], "next": result["corrected_next_boundary"], "manifest_sha256": F31_MANIFEST_SHA, "diagnosis_sha256": F31_RESULT_SHA}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
