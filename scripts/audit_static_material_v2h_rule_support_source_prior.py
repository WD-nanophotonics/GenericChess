"""Build the exact pre-reference rule-support-conditioned source prior."""

from __future__ import annotations

from collections import deque
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
from scripts.audit_static_material_domain_conditional_capability import (
    V2C_FREEZE, V2D_FREEZE, _read_frozen,
)
from scripts.audit_static_material_v2f_lifetime_reachability import (
    TOPOLOGY_FREEZE, TOPOLOGY_RAW, _canonical_sha, _fraction, _load_frozen_inputs, _sha,
    build_augmented_graph,
)

OUTPUT = ROOT / ".generic_chess_flow/static-material-v2h-rule-support-source-prior.json"
EXPECTED_SUPPORT = {
    ("western_chess", "P"): 48,
    ("standard_shogi", "L"): 72,
    ("standard_shogi", "N"): 63,
    ("standard_shogi", "P"): 72,
}
RESTRICTED_B = {
    ("western_chess", "P"): Fraction(23945, 13392),
    ("standard_shogi", "L"): Fraction(19728450347, 5917542400),
    ("standard_shogi", "N"): Fraction(2519, 1260),
    ("standard_shogi", "P"): Fraction(1559, 1280),
}


def _fstr(value: Fraction) -> str:
    return f"{value.numerator}/{value.denominator}"


def _reachable_nodes(graph: dict[tuple[str, int], set[tuple[str, int]]],
                    seeds: set[tuple[str, int]]) -> set[tuple[str, int]]:
    if not seeds or not seeds <= set(graph):
        raise RuntimeError("Support seeds must be nonempty graph nodes")
    reached = set(seeds)
    queue = deque(sorted(seeds))
    while queue:
        for neighbor in graph[queue.popleft()]:
            if neighbor not in graph:
                raise RuntimeError(f"Support edge leaves executable node set: {neighbor}")
            if neighbor not in reached:
                reached.add(neighbor)
                queue.append(neighbor)
    return reached


def _conditional_mean(values: list[Fraction], support: list[int]) -> Fraction:
    if not support or any(square < 0 or square >= len(values) for square in support):
        raise RuntimeError("Conditional source support is empty or out of bounds")
    if len(set(support)) != len(support):
        raise RuntimeError("Conditional source support contains duplicate squares")
    return sum((values[square] for square in support), Fraction(0)) / len(support)


def _support_by_type(compiled: Any, current_types: list[str], topology_pieces: dict[str, Any],
                     owner: int) -> tuple[dict[str, list[int]], dict[str, Any]]:
    support_rules = compiled.support
    shape = support_rules.board_shape
    area = support_rules.board_area
    if area != shape.area:
        raise RuntimeError("Compiled support board area disagrees with its shape")
    graph, transitions = build_augmented_graph(area, current_types, topology_pieces, owner)
    seeds: set[tuple[str, int]] = set()
    initial_nodes = []
    for rank, row in enumerate(support_rules.initial_position):
        for file, piece in enumerate(row):
            if piece is not None and piece.owner == owner and piece.current_type_id in current_types:
                node = (piece.current_type_id, rank * shape.width + file)
                seeds.add(node)
                initial_nodes.append(node)
    drop_seed_squares: dict[str, list[int]] = {}
    for type_id in current_types:
        mask = support_rules.drop_allowed.get(type_id)
        allowed = [] if mask is None else [square for square, ok in enumerate(mask[owner]) if ok]
        drop_seed_squares[type_id] = allowed
        seeds.update((type_id, square) for square in allowed)
    if not seeds:
        raise RuntimeError(f"No initial or permitted drop seeds for owner {owner}")

    reached = _reachable_nodes(graph, seeds)
    support = {type_id: sorted(square for tid, square in reached if tid == type_id)
               for type_id in current_types}
    if any(not squares for squares in support.values()):
        empty = sorted(type_id for type_id, squares in support.items() if not squares)
        raise RuntimeError(f"Empty rule-derived support owner={owner}: {empty}")
    evidence = {
        "initial_seed_nodes": [list(node) for node in sorted(initial_nodes)],
        "drop_seed_squares_by_type": drop_seed_squares,
        "positive_support_transition_edges": transitions["transition_edges"],
    }
    return support, evidence


def audit() -> dict[str, Any]:
    for path in (V2C_FREEZE, V2D_FREEZE):
        _read_frozen(path)
    topology_freeze = json.loads(TOPOLOGY_FREEZE.read_text(encoding="utf-8"))
    if topology_freeze.get("human_reference_read") is not False:
        raise RuntimeError("ADR-128 was not frozen pre-reference")
    topology, capability, input_sha = _load_frozen_inputs()
    v2c = json.loads((ROOT / ".generic_chess_flow/static-semantic-material-prior-v2c-board.json").read_text(encoding="utf-8"))
    v2d = json.loads((ROOT / ".generic_chess_flow/static-semantic-material-prior-v2d-capture-affordance.json").read_text(encoding="utf-8"))
    if any(data.get("human_reference_imported") is not False for data in (v2c, v2d, capability)):
        raise RuntimeError("Human-reference data entered an inherited source")
    compiled_sets = {
        "western_chess": compile_semantic_ruleset(build_western_chess_ruleset()),
        "standard_shogi": compile_semantic_ruleset(build_standard_shogi_ruleset()),
    }
    output: dict[str, Any] = {
        "kind": "STATIC_MATERIAL_RULE_SUPPORT_CONDITIONED_SOURCE_PRIOR_PRE_REFERENCE_CANDIDATE",
        "classification": "INCONCLUSIVE",
        "causal_diagnostic": True,
        "human_reference_imported": False,
        "human_validation_performed": False,
        "production_evaluator_modified": False,
        "games_played": 0,
        "formula": {
            "owner_probability": "1/2",
            "square_given_owner_type": "uniform over independently rule-reachable support",
            "u_definition": "frozen V2C event semantics reconstructed per source",
            "c_definition": "frozen V2D unique physical board-removal event semantics per source",
            "b_definition": "u+c",
            "human_fitting": False,
            "piece_specific_or_game_specific_adjustment": False,
        },
        "input_sha256": input_sha,
        "rulesets": {},
        "coverage_complete": True,
        "reconstruction_complete": True,
        "support_gates_pass": True,
    }

    for name, compiled in compiled_sets.items():
        board_shape = compiled.support.board_shape
        area = board_shape.area
        v2c_types = v2c["rulesets"][name]["ledger"]
        v2d_types = v2d["rulesets"][name]["ledger"]
        topology_pieces_all = topology["rulesets"][name]["pieces"]
        current_types = sorted(type_id for type_id, meta in compiled.support.type_metadata.items()
                               if not meta.is_anchor)
        if any(not set(current_types) <= set(rows)
               for rows in (v2c_types, v2d_types, topology_pieces_all)):
            raise RuntimeError(f"Frozen/current type coverage mismatch in {name}")
        topology_pieces = {type_id: topology_pieces_all[type_id] for type_id in current_types}
        token_ledger = v2c["rulesets"][name]["token_state_ledger"]
        if not token_ledger.get("complete"):
            raise RuntimeError(f"Incomplete V2C token-state ledger in {name}")
        ruleset_out: dict[str, Any] = {"board_width": board_shape.width,
            "board_height": board_shape.height, "board_area": area, "types": {}}
        support_by_owner: dict[str, dict[str, list[int]]] = {}
        support_evidence_by_owner: dict[str, dict[str, Any]] = {}
        for owner in (0, 1):
            support_by_owner[str(owner)], support_evidence_by_owner[str(owner)] = _support_by_type(
                compiled, current_types, topology_pieces, owner)

        for type_id in current_types:
            cap_type = capability["rulesets"][name]["types"][type_id]
            type_u: dict[str, list[Fraction]] = {}
            type_c: dict[str, list[Fraction]] = {}
            type_b: dict[str, list[Fraction]] = {}
            type_support: dict[str, list[int]] = {}
            owner_evidence: dict[str, Any] = {}
            source_rows_by_owner: dict[str, list[dict[str, Any]]] = {}
            source_coverage_complete = cap_type.get("semantic_coverage") == {
                "u": True, "c": True, "topology": True}
            if not source_coverage_complete:
                output["coverage_complete"] = False
            for owner in (0, 1):
                owner_key = str(owner)
                frozen_rows = cap_type["owner_graphs"][owner_key]["source_rows"]
                if len(frozen_rows) != area or [int(row["source_square"]) for row in frozen_rows] != list(range(area)):
                    raise RuntimeError(f"Frozen ADR-129 source coverage is incomplete: {name}/{type_id}/{owner}")
                type_u[owner_key] = [Fraction(row["u_exact"]) for row in frozen_rows]
                type_c[owner_key] = [Fraction(row["c_exact"]) for row in frozen_rows]
                type_b[owner_key] = [Fraction(row["b_exact"]) for row in frozen_rows]
                if any(type_u[owner_key][square] + type_c[owner_key][square] != type_b[owner_key][square]
                       for square in range(area)):
                    output["reconstruction_complete"] = False
                u_values = type_u[owner_key]
                c_values = type_c[owner_key]
                support = support_by_owner[owner_key][type_id]
                type_support[owner_key] = support
                support_set = set(support)
                source_rows_by_owner[owner_key] = [{
                    "source_square": square,
                    "in_support": square in support_set,
                    "u_exact": _fstr(u_values[square]),
                    "c_exact": _fstr(c_values[square]),
                    "b_exact": _fstr(type_b[owner_key][square]),
                } for square in range(area)]
                owner_evidence[owner_key] = {
                    **support_evidence_by_owner[owner_key],
                    "support_squares": support,
                    "support_sha256": _canonical_sha(support),
                    "support_count": len(support),
                    "u_full_board_average_exact": _fstr(sum(u_values, Fraction(0)) / area),
                    "c_full_board_average_exact": _fstr(sum(c_values, Fraction(0)) / area),
                    "b_full_board_average_exact": _fstr(
                        sum(type_b[owner_key], Fraction(0)) / area),
                }

            expected_count = EXPECTED_SUPPORT.get((name, type_id), area)
            if any(len(type_support[str(owner)]) != expected_count for owner in (0, 1)):
                output["support_gates_pass"] = False
            us = sum((_conditional_mean(type_u[str(owner)], type_support[str(owner)])
                      for owner in (0, 1)), Fraction(0)) / 2
            cs = sum((_conditional_mean(type_c[str(owner)], type_support[str(owner)])
                      for owner in (0, 1)), Fraction(0)) / 2
            bs = us + cs
            baseline = v2d_types[type_id]
            v2d_u = Fraction(baseline["v2c_u_exact"])
            v2d_c = Fraction(baseline["capture_affordance_exact"])
            v2d_b = Fraction(baseline["v2d_m_exact"])
            u_global = sum((sum(type_u[str(owner)], Fraction(0)) for owner in (0, 1)), Fraction(0)) / (2 * area)
            c_global = sum((sum(type_c[str(owner)], Fraction(0)) for owner in (0, 1)), Fraction(0)) / (2 * area)
            b_global = sum((sum(type_b[str(owner)], Fraction(0)) for owner in (0, 1)), Fraction(0)) / (2 * area)
            if (u_global != v2d_u or c_global != v2d_c or b_global != v2d_b or u_global + c_global != b_global
                    or Fraction(v2c_types[type_id]["v2c_exact"]) != v2d_u):
                output["reconstruction_complete"] = False
            restricted = (name, type_id) in EXPECTED_SUPPORT
            if not restricted and (us != v2d_u or cs != v2d_c or bs != v2d_b):
                output["reconstruction_complete"] = False
            if restricted and bs != RESTRICTED_B[(name, type_id)]:
                output["reconstruction_complete"] = False
            ruleset_out["types"][type_id] = {
                "restricted_support": restricted,
                "owners": owner_evidence,
                "source_components_by_owner": source_rows_by_owner,
                "u_support_exact": _fstr(us),
                "c_support_exact": _fstr(cs),
                "b_support_exact": _fstr(bs),
                "frozen_v2d_u_exact": _fstr(v2d_u),
                "frozen_v2d_c_exact": _fstr(v2d_c),
                "frozen_v2d_b_exact": _fstr(v2d_b),
                "full_support_reproduces_v2d": (us == v2d_u and cs == v2d_c and bs == v2d_b),
                "component_sum_exact": us + cs == bs,
                "source_coverage_complete": source_coverage_complete,
            }
        ruleset_out["support_digests"] = {
            type_id: {owner: ruleset_out["types"][type_id]["owners"][owner]["support_sha256"]
                      for owner in ("0", "1")} for type_id in current_types
        }
        output["rulesets"][name] = ruleset_out

    if output["coverage_complete"] and output["reconstruction_complete"] and output["support_gates_pass"]:
        output["classification"] = "STATIC_MATERIAL_RULE_SUPPORT_CONDITIONED_SOURCE_PRIOR_COMPLETE"
    return output


def main() -> int:
    result = audit()
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(OUTPUT), "classification": result["classification"],
                      "coverage_complete": result["coverage_complete"],
                      "reconstruction_complete": result["reconstruction_complete"],
                      "support_gates_pass": result["support_gates_pass"],
                      "human_reference_imported": result["human_reference_imported"]}, indent=2))
    return 0 if result["classification"].endswith("COMPLETE") else 2


if __name__ == "__main__":
    raise SystemExit(main())
