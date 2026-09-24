"""Fail-closed pre-reference freeze for augmented lifetime reachability."""

from __future__ import annotations

from fractions import Fraction
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
from scripts.audit_static_material_v2f_lifetime_reachability import (
    CAPABILITY_RAW,
    OUTPUT as RAW,
    TOPOLOGY_RAW,
    _canonical_sha,
    _fraction,
    _load_frozen_inputs,
    _sha,
    audit,
    build_augmented_graph,
    summarize_source,
)

FREEZE = ROOT / ".generic_chess_flow/static-material-v2f-lifetime-reachability-freeze.json"
FILES = (
    "docs/architecture/ADR-130-static-material-lifetime-reachability-diagnostic.md",
    "scripts/audit_static_material_v2f_lifetime_reachability.py",
    "scripts/freeze_static_material_v2f_lifetime_reachability.py",
    "tests/test_static_material_v2f_lifetime_reachability.py",
    ".generic_chess_flow/static-semantic-material-prior-v2c-freeze.json",
    ".generic_chess_flow/static-semantic-material-prior-v2c-board.json",
    ".generic_chess_flow/static-semantic-material-prior-v2d-freeze.json",
    ".generic_chess_flow/static-semantic-material-prior-v2d-capture-affordance.json",
    ".generic_chess_flow/static-material-domain-fragmentation-freeze.json",
    ".generic_chess_flow/static-material-domain-fragmentation-topology.json",
    ".generic_chess_flow/static-material-domain-conditional-capability-freeze.json",
    ".generic_chess_flow/static-material-domain-conditional-capability.json",
)


def _verify_candidate(candidate: dict[str, Any]) -> dict[str, Any]:
    reproduced = audit()
    if candidate != reproduced:
        raise RuntimeError("Raw candidate differs from deterministic frozen-input recomputation")
    required_false = (
        "human_reference_imported", "human_validation_performed", "material_formula_modified",
        "material_candidate_created", "context_weight_used", "v2e_transition_value_used",
        "transport_efficiency_used", "piece_specific_logic", "game_specific_logic",
    )
    if any(candidate.get(key) is not False for key in required_false):
        raise RuntimeError("Candidate violates its no-human/no-score diagnostic boundary")
    if candidate.get("classification") != "STATIC_MATERIAL_LIFETIME_REACHABILITY_DIAGNOSTIC_COMPLETE":
        raise RuntimeError("Cannot freeze an inconclusive lifetime reachability candidate")
    return reproduced


def freeze() -> dict[str, Any]:
    if not RAW.is_file():
        raise RuntimeError("Raw lifetime reachability candidate is missing")
    candidate = json.loads(RAW.read_text(encoding="utf-8"))
    _verify_candidate(candidate)
    topology, capability, input_sha = _load_frozen_inputs()
    if candidate.get("input_sha256") != input_sha:
        raise RuntimeError("Candidate frozen-input hash manifest mismatch")

    compiled_sets = {
        "western_chess": compile_semantic_ruleset(build_western_chess_ruleset()),
        "standard_shogi": compile_semantic_ruleset(build_standard_shogi_ruleset()),
    }
    ruleset_manifest: dict[str, Any] = {}
    terminal_count = 0
    transition_count = 0
    for ruleset, compiled in compiled_sets.items():
        area = compiled.support.board_size ** 2
        current_types = sorted(type_id for type_id, metadata in compiled.support.type_metadata.items()
                               if not metadata.is_anchor)
        topology_pieces = topology["rulesets"][ruleset]["pieces"]
        capability_types = capability["rulesets"][ruleset]["types"]
        candidate_ruleset = candidate["rulesets"][ruleset]
        if set(candidate_ruleset["types"]) != set(current_types):
            raise RuntimeError(f"Candidate non-anchor type set mismatch: {ruleset}")
        piece_manifest: dict[str, Any] = {}
        for type_id in current_types:
            candidate_type = candidate_ruleset["types"][type_id]
            capability_type = capability_types[type_id]
            topology_piece = topology_pieces[type_id]
            terminal = not bool(topology_piece["has_outgoing_type_transition"])
            if candidate_type["terminal_current_type"] is not terminal:
                raise RuntimeError(f"Terminal/transition classification mismatch: {ruleset}/{type_id}")
            if (candidate_type["frozen_v2d_u_exact"] != capability_type["u_exact"]
                    or candidate_type["frozen_v2d_c_exact"] != capability_type["c_exact"]
                    or candidate_type["frozen_v2d_b0_exact"] != capability_type["b0_exact"]):
                raise RuntimeError(f"Frozen V2D aggregate evidence mismatch: {ruleset}/{type_id}")
            owner_manifest: dict[str, Any] = {}
            q_cap = Fraction(0)
            for owner in (0, 1):
                owner_key = str(owner)
                graph, transition_data = build_augmented_graph(
                    area, current_types,
                    {key: topology_pieces[key] for key in current_types}, owner)
                owner_candidate = candidate_type["owner_graphs"][owner_key]
                all_edges = [
                    [source_type, source_square, target_type, target_square]
                    for (source_type, source_square), neighbors in sorted(graph.items())
                    for target_type, target_square in neighbors
                ]
                graph_sha = _canonical_sha(all_edges)
                if (owner_candidate["graph_sha256"] != graph_sha
                        or owner_candidate["graph_node_count"] != area * len(current_types)
                        or owner_candidate["graph_edge_count"] != len(all_edges)):
                    raise RuntimeError(f"Augmented graph hash/count mismatch: {ruleset}/{type_id}/{owner}")

                source_rows = capability_type["owner_graphs"][owner_key]["source_rows"]
                summaries = owner_candidate["source_summaries"]
                if len(summaries) != area or len(source_rows) != area:
                    raise RuntimeError(f"Per-source coverage mismatch: {ruleset}/{type_id}/{owner}")
                source_hash = _canonical_sha(source_rows)
                if candidate_type["source_u_c_b_sha256_by_owner"][owner_key] != source_hash:
                    raise RuntimeError(f"Source capability hash mismatch: {ruleset}/{type_id}/{owner}")
                local_bq = Fraction(0)
                for source_row, stored in zip(source_rows, summaries):
                    expected = summarize_source(graph, type_id, int(source_row["source_square"]), area)
                    for key, value in expected.items():
                        if stored.get(key) != value:
                            raise RuntimeError(
                                f"Source reachability does not recompute: {ruleset}/{type_id}/{owner}/{source_row['source_square']}/{key}")
                    if (_fraction(stored["u_exact"]) != _fraction(source_row["u_exact"])
                            or _fraction(stored["c_exact"]) != _fraction(source_row["c_exact"])
                            or _fraction(stored["b_exact"]) != _fraction(source_row["b_exact"])):
                        raise RuntimeError(f"Source U/C/B differs from ADR-129: {ruleset}/{type_id}/{owner}")
                    local_bq += _fraction(source_row["b_exact"]) * _fraction(stored["q_exact"])
                q_cap += local_bq / (2 * area)

                type_edges = [edge for edge in transition_data["transition_edges"] if edge[0] == type_id]
                if owner_candidate["transition_edges"] != type_edges:
                    raise RuntimeError(f"Transition-edge ledger mismatch: {ruleset}/{type_id}/{owner}")
                owner_manifest[owner_key] = {
                    "augmented_graph_sha256": graph_sha,
                    "augmented_graph_node_count": len(graph),
                    "augmented_graph_edge_count": len(all_edges),
                    "type_outgoing_edge_sha256": owner_candidate["type_outgoing_edge_sha256"],
                    "transition_edge_count": len(type_edges),
                    "transition_event_ledger_sha256": _canonical_sha(
                        owner_candidate["transition_event_ledger_for_type"]),
                    "source_u_c_b_sha256": source_hash,
                    "source_reachability_sha256": _canonical_sha(summaries),
                    "fraction_start_sources_reaching_type_change_exact": owner_candidate[
                        "fraction_start_sources_reaching_type_change_exact"],
                    "mean_pre_transition_reachable_board_fraction_exact": owner_candidate[
                        "mean_pre_transition_reachable_board_fraction_exact"],
                    "mean_lifetime_reachable_board_fraction_exact": owner_candidate[
                        "mean_lifetime_reachable_board_fraction_exact"],
                }
            if _fraction(candidate_type["q_cap_exact"]) != q_cap:
                raise RuntimeError(f"Q_cap exact source expectation mismatch: {ruleset}/{type_id}")
            if terminal:
                terminal_count += 1
                j = _fraction(capability_type["j_exact"])
                if (_fraction(candidate_type["adr129_same_weak_domain_j_exact"]) != j
                        or _fraction(candidate_type["q_cap_minus_adr129_j_exact"]) != q_cap - j):
                    raise RuntimeError(f"Terminal Q_cap/J comparison mismatch: {ruleset}/{type_id}")
            else:
                transition_count += 1
                if candidate_type["adr129_same_weak_domain_j_exact"] is not None:
                    raise RuntimeError(f"Transition-bearing type assigned terminal J: {ruleset}/{type_id}")
            piece_manifest[type_id] = {
                "terminal_current_type": terminal,
                "frozen_v2d_u_exact": capability_type["u_exact"],
                "frozen_v2d_c_exact": capability_type["c_exact"],
                "frozen_v2d_b0_exact": capability_type["b0_exact"],
                "q_cap_exact": _fraction(candidate_type["q_cap_exact"]).__str__(),
                "adr129_same_weak_domain_j_exact": candidate_type["adr129_same_weak_domain_j_exact"],
                "q_cap_minus_adr129_j_exact": candidate_type["q_cap_minus_adr129_j_exact"],
                "owners": owner_manifest,
            }
        ruleset_manifest[ruleset] = {
            "board_area": area,
            "anchor_types_excluded": candidate_ruleset["anchor_types_excluded_from_augmented_graph"],
            "types": piece_manifest,
        }

    if terminal_count == 0 or transition_count == 0:
        raise RuntimeError("Expected both terminal and transition-bearing non-anchor benchmark types")
    output = {
        "schema_version": 1,
        "kind": "STATIC_MATERIAL_LIFETIME_REACHABILITY_PRE_REFERENCE_FREEZE",
        "classification": candidate["classification"],
        "candidate_sha256": _sha(RAW),
        "reference_data_read": False,
        "human_validation_performed": False,
        "material_formula_modified": False,
        "material_candidate_created": False,
        "context_weight_used": False,
        "terminal_non_anchor_type_count": terminal_count,
        "transition_bearing_non_anchor_type_count": transition_count,
        "all_frozen_v2d_source_capabilities_reconstructed_exactly": True,
        "all_augmented_source_reachability_recomputed_exactly": True,
        "terminal_q_cap_and_adr129_j_differences_recomputed_exactly": True,
        "inputs": input_sha,
        "sha256": {relative: _sha(ROOT / relative) for relative in FILES},
        "rulesets": ruleset_manifest,
    }
    FREEZE.write_text(json.dumps(output, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return output


def main() -> int:
    result = freeze()
    print(json.dumps({
        "freeze": str(FREEZE), "candidate_sha256": result["candidate_sha256"],
        "classification": result["classification"],
        "terminal_non_anchor_type_count": result["terminal_non_anchor_type_count"],
        "transition_bearing_non_anchor_type_count": result["transition_bearing_non_anchor_type_count"],
        "reference_data_read": result["reference_data_read"],
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
