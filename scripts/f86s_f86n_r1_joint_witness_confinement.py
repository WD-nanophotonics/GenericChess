"""F86S joint-witness confinement diagnosis for the frozen F86N-R1 cohort."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any

from generic_chess.core.attacks import anchor_square, pseudo_attacks, is_in_check
from generic_chess.core.movegen import has_legal_action
from generic_chess.core.coordinates import square_to_index
from generic_chess.rules.compiler import compile_ruleset
from generic_chess.rules.schema import ruleset_from_dict

try:
    from scripts.f86n_transport_aware_signed_sampler import (
        _bounded_census,
        _build_position,
    )
    from scripts.f86r_escapable_check_defense_mode import (
        _anchor_neighbors,
        _exact_checkers,
    )
except ModuleNotFoundError:
    from f86n_transport_aware_signed_sampler import _bounded_census, _build_position
    from f86r_escapable_check_defense_mode import _anchor_neighbors, _exact_checkers


BASELINE = "453dac15fc5b0568d285615c142f572a0dc6a233"
F86N_PREP_BLOB = "adba41fa02a6e44459d3692ba232bf564c4450c7"
F86N_RESULT_BLOB = "d7f7e7648255e009a1544908a75e7d49ee4a8e72"
F86R_RESULT_BLOB = "c0de094522a8660750221d9fa948cfd79a5c00cf"
F86N_FINGERPRINTS = {
    "V4-3": "856a810d3a21eec779f9ba8300ce602cd24d3e8850ba895e39579603fd4ff3e2",
    "V5-3": "e8528688a64bce3f39231d9e4f38d5d200ade57c6f517ae33ce9b71b9f75ebe5",
}
SAMPLES = ("V4-3", "V5-3")
STATIC_CAP_PER_CELL = 2048
STATIC_CAP_TOTAL = 4096


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")


def _load(root: Path, relative: str) -> dict[str, Any]:
    return json.loads((root / relative).read_text(encoding="utf-8"))


def _square_index(square: list[int], n: int) -> int:
    return square[1] * n + square[0]


def _distribution(rows: list[dict[str, Any]], key: str) -> dict[str, int]:
    return dict(sorted(Counter(str(row[key]) for row in rows).items(), key=lambda item: int(item[0])))


def _load_frozen_inputs(root: Path) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    f86n_prep = _load(root, "artifacts/f86n_r1_transport_aware_signed_sampler/manifest.json")
    f86n_result = _load(root, "artifacts/f86n_r1_transport_aware_signed_sampler/results.json")
    f86r_result = _load(root, "artifacts/f86r_escapable_check_defense_mode/summary.json")
    if f86n_prep.get("status") != "PRE_REGISTERED_STATIC_FROZEN_CANDIDATES":
        raise RuntimeError("F86N-R1 PREP status drift")
    if f86n_result.get("status") != "F86N_R1_STATIC_PREFLIGHT_ZERO_DYNAMIC_COMPUTE":
        raise RuntimeError("F86N-R1 RESULT status drift")
    if f86r_result.get("baseline_commit") != "35d9dfcbf76a5e51dc72f49722389e8dc1b60076":
        raise RuntimeError("F86R RESULT baseline drift")
    return f86n_prep, f86n_result, f86r_result


def build_prep(root: Path, output: Path) -> dict[str, Any]:
    f86n_prep, f86n_result, f86r_result = _load_frozen_inputs(root)
    targeted = {
        row["sample_id"]: row
        for row in f86n_result["targeted_static_mate_capacity"]
        if row["sample_id"] in SAMPLES
    }
    if set(targeted) != set(SAMPLES):
        raise RuntimeError("F86N-R1 targeted cohort drift")
    for sample_id, fingerprint in F86N_FINGERPRINTS.items():
        if targeted[sample_id]["candidate_ruleset_fingerprint"] != fingerprint:
            raise RuntimeError(f"F86N-R1 fingerprint drift:{sample_id}")
    payload = {
        "schema_version": 1,
        "status": "PRE_REGISTERED_F86S_F86N_R1_JOINT_WITNESS_CONFINEMENT",
        "baseline_commit": BASELINE,
        "f86n_r1_manifest_blob": F86N_PREP_BLOB,
        "f86n_r1_result_blob": F86N_RESULT_BLOB,
        "f86r_result_blob": F86R_RESULT_BLOB,
        "source_artifacts": {
            "f86n_r1_manifest": "artifacts/f86n_r1_transport_aware_signed_sampler/manifest.json",
            "f86n_r1_result": "artifacts/f86n_r1_transport_aware_signed_sampler/results.json",
            "f86r_result": "artifacts/f86r_escapable_check_defense_mode/summary.json",
        },
        "targeted_samples": list(SAMPLES),
        "frozen_candidate_fingerprints": dict(F86N_FINGERPRINTS),
        "frozen_census_expectations": {
            sample_id: {
                key: targeted[sample_id][key]
                for key in (
                    "candidate_position_count",
                    "validated_position_count",
                    "validated_template_count",
                    "truncation",
                    "ordinary_assignment_reachable_count",
                    "joint_kinematically_reachable_count",
                    "minimum_optimistic_ply_lower_bound",
                )
            }
            for sample_id in SAMPLES
        },
        "census_ordering": {
            "defender_anchor": "ascending row-major square index",
            "ordinary_placement": "recursive type-sorted placement, ascending square index, duplicate types canonicalized",
            "attacker_anchor": "ascending row-major square index, after ordinary placement",
            "template_rows": "sorted by (defender_anchor, sorted ordinary (type_id, square_index))",
            "attacker_targets": "ascending row-major square index",
        },
        "witness_serialization_schema": {
            "required": [
                "source_template_id",
                "defender_anchor",
                "attacker_anchor_admissible_target_square",
                "ordinary",
                "opening_piece_assignment",
                "optimistic_assignment_path_lengths",
                "joint_optimistic_ply_lower_bound",
                "candidate_ruleset_fingerprint",
                "exact_checkmate_confinement",
            ],
            "assignment_identity": "compiled opening owner-0 piece type and row-major source square to target square",
            "confinement_checker": "F86R exact piece-level Leap/Ray checker geometry with child occupancy and ray blocking",
        },
        "static_budget": {
            "candidate_checks_per_cell": STATIC_CAP_PER_CELL,
            "candidate_checks_total_cap": STATIC_CAP_TOTAL,
            "new_games": 0,
            "new_movement_candidates": 0,
        },
        "prohibited_compute": {
            "dynamic_beyond_f86r": 0,
            "alphabeta": 0,
            "bfs": 0,
            "training": 0,
            "teacher": 0,
            "c2": 0,
            "f85": 0,
            "heavy": 0,
        },
        "result_driven_replacement_forbidden": True,
        "default_generator_changed": False,
    }
    _write_json(output, payload)
    return payload


def _load_prep(root: Path) -> dict[str, Any]:
    prep = _load(root, "artifacts/f86s_f86n_r1_joint_witness_confinement/manifest.json")
    if prep.get("status") != "PRE_REGISTERED_F86S_F86N_R1_JOINT_WITNESS_CONFINEMENT":
        raise RuntimeError("F86S PREP status drift")
    if prep.get("baseline_commit") != BASELINE:
        raise RuntimeError("F86S baseline drift")
    if prep.get("f86n_r1_manifest_blob") != F86N_PREP_BLOB or prep.get("f86n_r1_result_blob") != F86N_RESULT_BLOB:
        raise RuntimeError("F86S F86N authority drift")
    if prep.get("f86r_result_blob") != F86R_RESULT_BLOB:
        raise RuntimeError("F86S F86R authority drift")
    if prep.get("static_budget", {}).get("candidate_checks_per_cell") != STATIC_CAP_PER_CELL:
        raise RuntimeError("F86S per-cell cap drift")
    return prep


def _profile_position(position, compiled) -> dict[str, Any]:
    n = compiled.board_size
    anchor = anchor_square(position, 1, compiled)
    if anchor is None:
        raise RuntimeError("static witness has no defender Anchor")
    neighbors = _anchor_neighbors(anchor, n)
    attacked = pseudo_attacks(position, 0, compiled)
    neighbor_indices = {square_to_index(square, n) for square in neighbors}
    friendly = sum(position.board[index] is not None and position.board[index].owner == 1 for index in neighbor_indices)
    enemy = sum(position.board[index] is not None and position.board[index].owner == 0 for index in neighbor_indices)
    checkers = _exact_checkers(position, 0, 1, compiled)
    legal_replies = int(has_legal_action(position, compiled))
    if is_in_check(position, 0, compiled) or not is_in_check(position, 1, compiled) or legal_replies != 0:
        raise RuntimeError("static witness is not an exact checkmate")
    return {
        "checker_squares": [item["square"] for item in checkers],
        "checker_types": sorted({item["type_id"] for item in checkers}),
        "checker_multiplicity": len(checkers),
        "anchor_neighbor_in_board_count": len(neighbors),
        "attacker_pseudo_attacked_neighbor_count": len(neighbors & attacked),
        "friendly_occupied_neighbor_count": friendly,
        "enemy_occupied_neighbor_count": enemy,
        "legal_defender_reply_count": legal_replies,
        "legal_anchor_flight_reply_count": 0,
        "checker_capture_reply_count": 0,
        "interposition_screen_reply_count": 0,
        "validated_exact_checkmate": True,
    }


def _witness_rows(sample_id: str, compiled, census_result: dict[str, Any]) -> list[dict[str, Any]]:
    n = compiled.board_size
    kinematic = census_result["kinematic"]
    rows = []
    for template in kinematic["template_results"]:
        target = template.get("best_joint_target")
        if not target:
            continue
        defender_anchor = template["defender_anchor"]
        attacker_target = target["attacker_anchor_target"]
        ordinary = template["ordinary"]
        placement = tuple((item["type_id"], _square_index(item["square"], n)) for item in ordinary)
        position = _build_position(compiled, _square_index(defender_anchor, n), _square_index(attacker_target, n), placement)
        assignment = template["ordinary_assignment"]
        rows.append({
            "source_template_id": template["template_id"],
            "sample_id": sample_id,
            "defender_anchor": defender_anchor,
            "attacker_anchor_admissible_target_square": attacker_target,
            "attacker_anchor_frozen_target_square": attacker_target,
            "ordinary": ordinary,
            "opening_piece_assignment": assignment,
            "optimistic_assignment_path_lengths": {
                "ordinary_piece_move_count": template["ordinary_assignment_move_count"],
                "attacker_anchor_move_count": target["attacker_anchor_distance"],
                "defender_anchor_move_count": target["defender_anchor_distance"],
            },
            "joint_optimistic_ply_lower_bound": target["optimistic_ply_lower_bound"],
            "candidate_ruleset_fingerprint": compiled.ruleset_fingerprint,
            "exact_checkmate_confinement": _profile_position(position, compiled),
        })
    return rows


def _static_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    profiles = [row["exact_checkmate_confinement"] for row in rows]
    return {
        "witness_count": len(rows),
        "checker_multiplicity_distribution": _distribution(profiles, "checker_multiplicity"),
        "anchor_neighborhood_coverage_distribution": _distribution(profiles, "attacker_pseudo_attacked_neighbor_count"),
        "friendly_occupied_neighbor_distribution": _distribution(profiles, "friendly_occupied_neighbor_count"),
        "enemy_occupied_neighbor_distribution": _distribution(profiles, "enemy_occupied_neighbor_count"),
        "legal_defender_reply_distribution": _distribution(profiles, "legal_defender_reply_count"),
        "all_validated_exact_checkmate": all(profile["validated_exact_checkmate"] for profile in profiles),
    }


def _dynamic_control(f86r: dict[str, Any], sample_id: str) -> dict[str, Any]:
    row = f86r["by_arm_sample"]["N"][sample_id]
    return {
        "checking_actions": row["checking_actions"],
        "breaking_replies": row["breaking_replies"],
        "checker_multiplicity_distribution": row["checker_multiplicity_distribution"],
        "anchor_neighborhood_coverage_distribution": row["anchor_neighborhood_coverage_distribution"],
        "breaking_reply_mechanism_counts": row["breaking_reply_mechanism_counts"],
        "route": row["route"],
        "occupancy_distributions": "NOT_SERIALIZED_BY_F86R_RESULT",
    }


def _route(static: dict[str, Any], dynamic: dict[str, Any]) -> str:
    static_coverage = [int(key) for key in static["anchor_neighborhood_coverage_distribution"] for _ in range(static["anchor_neighborhood_coverage_distribution"][key])]
    dynamic_coverage = [int(key) for key in dynamic["anchor_neighborhood_coverage_distribution"] for _ in range(dynamic["anchor_neighborhood_coverage_distribution"][key])]
    if not static_coverage or not dynamic_coverage:
        return "STATIC_VS_DYNAMIC_CONFINEMENT_DIFFERENCE_IS_MULTI_FACTOR"
    if min(static_coverage) > max(dynamic_coverage):
        return "STATIC_MATE_WITNESSES_HAVE_STRICTLY_STRONGER_NEIGHBOR_ATTACK_COVERAGE"
    overlap = min(static_coverage) <= max(dynamic_coverage) and min(dynamic_coverage) <= max(static_coverage)
    occupancy_blocking = (
        overlap
        and (sum(int(key) * value for key, value in static["friendly_occupied_neighbor_distribution"].items()) > 0
             or sum(int(key) * value for key, value in static["enemy_occupied_neighbor_distribution"].items()) > 0)
        and int(dynamic["breaking_reply_mechanism_counts"].get("ANCHOR_FLIGHT", 0)) > 0
    )
    if occupancy_blocking:
        return "STATIC_MATE_CONFINEMENT_DEPENDS_ON_OCCUPANCY_STRUCTURE"
    static_checker = [int(key) for key in static["checker_multiplicity_distribution"] for _ in range(static["checker_multiplicity_distribution"][key])]
    dynamic_checker = [int(key) for key in dynamic["checker_multiplicity_distribution"] for _ in range(dynamic["checker_multiplicity_distribution"][key])]
    if static_checker and dynamic_checker and min(static_checker) > max(dynamic_checker):
        return "STATIC_MATE_CONFINEMENT_DEPENDS_ON_MULTI_CHECKER_SUPPORT"
    return "STATIC_VS_DYNAMIC_CONFINEMENT_DIFFERENCE_IS_MULTI_FACTOR"


def run(root: Path, output_dir: Path) -> dict[str, Any]:
    prep = _load_prep(root)
    _f86n_prep, _f86n_result, f86r_result = _load_frozen_inputs(root)
    compiled_by_sample = {}
    for entry in _f86n_prep["entries"]:
        if entry["sample_id"] in SAMPLES:
            compiled = compile_ruleset(ruleset_from_dict(entry["candidate_ruleset"]))
            if compiled.ruleset_fingerprint != F86N_FINGERPRINTS[entry["sample_id"]]:
                raise RuntimeError(f"candidate fingerprint drift:{entry['sample_id']}")
            compiled_by_sample[entry["sample_id"]] = compiled
    if set(compiled_by_sample) != set(SAMPLES):
        raise RuntimeError("F86S candidate cohort incomplete")

    targeted = []
    witnesses_by_sample = {}
    for sample_id in SAMPLES:
        census_result = _bounded_census(sample_id, compiled_by_sample[sample_id], STATIC_CAP_PER_CELL)
        census = census_result["census"]
        kinematic = census_result["kinematic"]
        expected = prep["frozen_census_expectations"][sample_id]
        for key, value in expected.items():
            actual = kinematic[key] if key in kinematic else census[key]
            if actual != value:
                raise RuntimeError(f"F86N-R1 census reproduction drift:{sample_id}:{key}:{actual}!={value}")
        if census["ruleset_fingerprint"] != F86N_FINGERPRINTS[sample_id]:
            raise RuntimeError(f"census fingerprint drift:{sample_id}")
        witness_rows = _witness_rows(sample_id, compiled_by_sample[sample_id], census_result)
        expected_count = expected["joint_kinematically_reachable_count"]
        if len(witness_rows) != expected_count:
            raise RuntimeError(f"joint witness count drift:{sample_id}:{len(witness_rows)}!={expected_count}")
        if not all(row["exact_checkmate_confinement"]["legal_defender_reply_count"] == 0 for row in witness_rows):
            raise RuntimeError(f"non-mate static witness:{sample_id}")
        witnesses_by_sample[sample_id] = witness_rows
        targeted.append({
            "sample_id": sample_id,
            "candidate_ruleset_fingerprint": census["ruleset_fingerprint"],
            "candidate_position_count": census["candidate_position_count"],
            "validated_position_count": census["validated_position_count"],
            "validated_template_count": census["validated_template_count"],
            "truncation": census["truncation"],
            "ordinary_assignment_reachable_count": kinematic["ordinary_assignment_reachable_count"],
            "joint_kinematically_reachable_count": kinematic["joint_kinematically_reachable_count"],
            "minimum_optimistic_ply_lower_bound": kinematic["minimum_optimistic_ply_lower_bound"],
            "witness_status": "OBSERVED_UNDER_TRUNCATED_CENSUS" if census["truncation"] else "COMPLETE_CENSUS",
        })
    total = sum(row["candidate_position_count"] for row in targeted)
    if total > STATIC_CAP_TOTAL:
        raise RuntimeError("F86S static total cap exceeded")

    witnesses = [row for sample_id in SAMPLES for row in witnesses_by_sample[sample_id]]
    comparisons = {}
    routes = {}
    for sample_id in SAMPLES:
        static = _static_summary(witnesses_by_sample[sample_id])
        dynamic = _dynamic_control(f86r_result, sample_id)
        comparisons[sample_id] = {"static": static, "dynamic_f86r_arm_n": dynamic}
        routes[sample_id] = _route(static, dynamic)
    overall = routes[SAMPLES[0]] if routes[SAMPLES[0]] == routes[SAMPLES[1]] else "CONFINEMENT_GAP_IS_SAMPLE_DEPENDENT"

    witness_path = output_dir / "witnesses.json"
    _write_json(witness_path, {
        "schema_version": 1,
        "status": "F86S_JOINT_WITNESSES_COMPLETE",
        "manifest": "artifacts/f86s_f86n_r1_joint_witness_confinement/manifest.json",
        "witnesses": witnesses,
    })
    summary = {
        "schema_version": 1,
        "status": "F86S_F86N_R1_JOINT_WITNESS_CONFINEMENT_COMPLETE",
        "manifest": "artifacts/f86s_f86n_r1_joint_witness_confinement/manifest.json",
        "witnesses": "artifacts/f86s_f86n_r1_joint_witness_confinement/witnesses.json",
        "targeted_static_mate_capacity": targeted,
        "static_candidate_checks": {"V4-3": targeted[0]["candidate_position_count"], "V5-3": targeted[1]["candidate_position_count"], "total": total, "per_cell_cap": STATIC_CAP_PER_CELL, "total_cap": STATIC_CAP_TOTAL},
        "joint_witness_counts": {sample_id: len(witnesses_by_sample[sample_id]) for sample_id in SAMPLES},
        "comparisons": comparisons,
        "routing": {"by_sample": routes, "overall": overall},
        "compute_accounting": {"new_games": 0, "new_movement_candidates": 0, "dynamic_beyond_f86r": 0, "alphabeta": 0, "bfs": 0, "training": 0, "teacher": 0, "c2": 0, "f85": 0, "heavy": 0},
        "default_generator_changed": False,
    }
    _write_json(output_dir / "summary.json", summary)
    return summary


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--prep", action="store_true")
    parser.add_argument("--manifest-output", type=Path, default=Path("artifacts/f86s_f86n_r1_joint_witness_confinement/manifest.json"))
    parser.add_argument("--result-dir", type=Path, default=Path("artifacts/f86s_f86n_r1_joint_witness_confinement"))
    args = parser.parse_args()
    if args.prep:
        payload = build_prep(args.root, args.manifest_output)
        print(json.dumps({"status": payload["status"], "samples": payload["targeted_samples"]}, sort_keys=True))
    else:
        payload = run(args.root, args.result_dir)
        print(json.dumps({"status": payload["status"], "witnesses": payload["joint_witness_counts"], "overall_route": payload["routing"]["overall"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
