"""Generator-independent ruleset qualification contracts and cheap probes."""

from __future__ import annotations

import itertools
import math
from collections import Counter, deque
from dataclasses import dataclass, field
from typing import Any

from generic_chess.core.actions import action_is_board
from generic_chess.core.attacks import is_in_check
from generic_chess.core.coordinates import square_to_index
from generic_chess.core.identity import position_identity_key
from generic_chess.core.movement import LeapAtom, RayAtom
from generic_chess.session.session import GameSession

from .game_quality import QualityObservation, profile_from_observations
from .policy_tape import PolicyTape


STATUS_PASS = "PASS"
STATUS_FAIL = "FAIL"
STATUS_DEFER = "DEFER"
STATUS_UNMEASURED = "UNMEASURED"
PROVENANCE = (
    "LITERATURE_SUPPORTED",
    "GENERICCHESS_SPECIFIC",
    "EMPIRICAL_GATE",
    "UNVALIDATED_HEURISTIC",
)


@dataclass(frozen=True, slots=True)
class MetricEvidence:
    value: Any
    provenance: str
    status: str = STATUS_PASS
    note: str = ""

    def __post_init__(self) -> None:
        if self.provenance not in PROVENANCE:
            raise ValueError(f"unknown metric provenance: {self.provenance}")
        if self.status not in {STATUS_PASS, STATUS_FAIL, STATUS_DEFER, STATUS_UNMEASURED}:
            raise ValueError(f"unknown metric status: {self.status}")

    def to_dict(self) -> dict[str, Any]:
        return {
            "value": self.value,
            "provenance": self.provenance,
            "status": self.status,
            "note": self.note,
        }


@dataclass(frozen=True, slots=True)
class GateOutcome:
    name: str
    status: str
    provenance: str
    reason: str
    metric: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "status": self.status,
            "provenance": self.provenance,
            "reason": self.reason,
            "metric": self.metric,
        }


@dataclass(frozen=True, slots=True)
class QualificationReport:
    ruleset_fingerprint: str
    provenance: dict[str, Any]
    experiment_identity: str
    layers: dict[str, str]
    raw_diagnostics: dict[str, Any]
    hard_gates: tuple[GateOutcome, ...]
    fail_defer_reasons: tuple[str, ...]
    compute_usage: dict[str, Any]
    behavior_descriptors: dict[str, MetricEvidence]
    overall_status: str

    def __post_init__(self) -> None:
        if self.overall_status not in {STATUS_PASS, STATUS_FAIL, STATUS_DEFER, STATUS_UNMEASURED}:
            raise ValueError("invalid qualification status")
        if set(self.layers) != {"A", "B", "C", "D", "E"}:
            raise ValueError("qualification report must expose Layers A-E")

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": 1,
            "ruleset_fingerprint": self.ruleset_fingerprint,
            "provenance": self.provenance,
            "experiment_identity": self.experiment_identity,
            "layers": dict(self.layers),
            "raw_diagnostics": self.raw_diagnostics,
            "hard_gates": [gate.to_dict() for gate in self.hard_gates],
            "fail_defer_reasons": list(self.fail_defer_reasons),
            "compute_usage": self.compute_usage,
            "behavior_descriptors": {
                key: value.to_dict() for key, value in self.behavior_descriptors.items()
            },
            "overall_status": self.overall_status,
        }


def _vectors(compiled, type_id: str) -> list[tuple[int, int]]:
    piece_type = next(piece for piece in compiled.piece_types if piece.type_id == type_id)
    vectors: list[tuple[int, int]] = []
    for atom in piece_type.movement_atoms:
        vectors.append(tuple(atom.offset if isinstance(atom, LeapAtom) else atom.direction))
    return sorted(set(vectors))


def _gcd_many(values: list[int]) -> int:
    result = 0
    for value in values:
        result = math.gcd(result, abs(value))
    return result


def lattice_info(compiled, type_id: str) -> dict[str, Any]:
    """Return the F86M displacement/lattice contract for one piece type."""
    vectors = _vectors(compiled, type_id)
    nonzero = [vector for vector in vectors if vector != (0, 0)]
    coordinate_gcd = _gcd_many([value for vector in nonzero for value in vector])
    determinants = [
        left[0] * right[1] - left[1] * right[0]
        for left, right in itertools.combinations(nonzero, 2)
    ]
    index = _gcd_many(determinants)
    if not nonzero:
        rank = 0
    elif index:
        rank = 2
    else:
        rank = 1
    invariant = None
    if rank == 1:
        dx, dy = nonzero[0]
        invariant = {
            "kind": "rank_one_linear_invariant",
            "expression": f"{-dy}*file+{dx}*rank",
            "modulus": None,
            "meaning": "constant on the infinite movement lattice",
        }
    elif rank == 2 and index > 1:
        coefficients = None
        for a in range(index):
            for b in range(index):
                if (a, b) != (0, 0) and all((a * dx + b * dy) % index == 0 for dx, dy in nonzero):
                    coefficients = (a, b)
                    break
            if coefficients is not None:
                break
        invariant = {
            "kind": "finite_residue_invariant",
            "expression": f"{coefficients[0]}*file+{coefficients[1]}*rank mod {index}" if coefficients else None,
            "coefficients": list(coefficients) if coefficients else None,
            "modulus": index,
        }
    return {
        "type_id": type_id,
        "displacement_generators": [list(vector) for vector in vectors],
        "integer_lattice_rank": rank,
        "lattice_index": index if rank == 2 else None,
        "smith_invariant_factors": [coordinate_gcd or 1, index // (coordinate_gcd or 1)] if rank == 2 else None,
        "residue_or_invariant": invariant,
    }


def _adjacency(compiled, type_id: str, owner: int = 0) -> tuple[tuple[int, ...], ...]:
    n = compiled.board_size
    return tuple(
        tuple(sorted(target.rank * n + target.file for target in compiled.empty_mobility[type_id][owner][source]))
        for source in range(n * n)
    )


def _scc(adjacency: tuple[tuple[int, ...], ...]) -> tuple[list[tuple[int, ...]], dict[int, int]]:
    index = 0
    stack: list[int] = []
    on_stack: set[int] = set()
    indices: dict[int, int] = {}
    low: dict[int, int] = {}
    components: list[tuple[int, ...]] = []

    def visit(node: int) -> None:
        nonlocal index
        indices[node] = low[node] = index
        index += 1
        stack.append(node)
        on_stack.add(node)
        for target in adjacency[node]:
            if target not in indices:
                visit(target)
                low[node] = min(low[node], low[target])
            elif target in on_stack:
                low[node] = min(low[node], indices[target])
        if low[node] == indices[node]:
            members = []
            while True:
                member = stack.pop()
                on_stack.remove(member)
                members.append(member)
                if member == node:
                    break
            components.append(tuple(sorted(members)))

    for node in range(len(adjacency)):
        if node not in indices:
            visit(node)
    components.sort(key=lambda component: component[0])
    ids = {node: component_id for component_id, component in enumerate(components) for node in component}
    return components, ids


def _reachable(adjacency: tuple[tuple[int, ...], ...], source: int) -> set[int]:
    reached = {source}
    queue = deque([source])
    while queue:
        current = queue.popleft()
        for target in adjacency[current]:
            if target not in reached:
                reached.add(target)
                queue.append(target)
    return reached


def _opening_sources(compiled) -> dict[str, list[dict[str, Any]]]:
    anchor_ids = {piece.type_id for piece in compiled.piece_types if piece.is_anchor}
    ordinals: Counter[str] = Counter()
    rows: dict[str, list[dict[str, Any]]] = {}
    for index, piece in enumerate(compiled.initial_position.board):
        if piece is None or piece.owner != 0 or piece.current_type_id in anchor_ids:
            continue
        ordinals[piece.current_type_id] += 1
        rows.setdefault(piece.current_type_id, []).append({
            "source_id": f"{piece.current_type_id}@o0#{ordinals[piece.current_type_id]}",
            "type_id": piece.current_type_id,
            "square_index": index,
        })
    return rows


def component_info(compiled, type_id: str) -> dict[str, Any]:
    adjacency = _adjacency(compiled, type_id)
    components, component_ids = _scc(adjacency)
    opening = _opening_sources(compiled).get(type_id, [])
    return {
        "type_id": type_id,
        "component_count": len(components),
        "component_sizes": [len(component) for component in components],
        "opening_piece_components": [
            {"source_id": row["source_id"], "component_id": component_ids[row["square_index"]]}
            for row in opening
        ],
    }


def structural_profile(compiled) -> dict[str, Any]:
    """Shared Layer-B diagnostics; all fields are diagnostics, not universal gates."""
    n2 = compiled.board_size * compiled.board_size
    anchor_ids = {piece.type_id for piece in compiled.piece_types if piece.is_anchor}
    type_ids = [piece.type_id for piece in compiled.piece_types if piece.type_id not in anchor_ids]
    source_rows = _opening_sources(compiled)
    type_profiles = []
    for type_id in sorted(type_ids):
        adjacency = _adjacency(compiled, type_id)
        components, component_ids = _scc(adjacency)
        edge_count = sum(len(targets) for targets in adjacency)
        reverse_edges = sum(int(source in adjacency[target]) for source, targets in enumerate(adjacency) for target in targets)
        sinks = sum(not targets for targets in adjacency)
        reached = set().union(*(_reachable(adjacency, row["square_index"]) for row in source_rows.get(type_id, []))) if source_rows.get(type_id) else set()
        type_profiles.append({
            "type_id": type_id,
            "movement_lattice": lattice_info(compiled, type_id),
            "component_profile": component_info(compiled, type_id),
            "directed_sink_fraction": sinks / n2,
            "direct_reverse_edge_fraction": reverse_edges / edge_count if edge_count else 0.0,
            "nontrivial_scc_vertex_fraction": sum(len(component) for component in components if len(component) > 1) / n2,
            "opening_sources": source_rows.get(type_id, []),
            "opening_source_reachable_union_square_count": len(reached),
            "opening_source_reachable_union_fraction": len(reached) / n2 if reached else 0.0,
            "opening_source_component_diversity": len({component_ids[row["square_index"]] for row in source_rows.get(type_id, [])}),
        })
    material_counts = Counter(
        piece.current_type_id
        for piece in compiled.initial_position.board
        if piece is not None and piece.owner == 0 and piece.current_type_id not in anchor_ids
    )
    return {
        "schema_version": 1,
        "board_size": compiled.board_size,
        "ruleset_fingerprint": compiled.ruleset_fingerprint,
        "materialized_type_counts": dict(sorted(material_counts.items())),
        "type_profiles": type_profiles,
        "universal_lattice_gate": MetricEvidence(
            "not_applied",
            "UNVALIDATED_HEURISTIC",
            STATUS_DEFER,
            "rank/index is a diagnostic; no universal rank-2/index-1 gate",
        ).to_dict(),
    }


def _normalized_terminal(session: GameSession, max_ply: int) -> tuple[str, bool]:
    status = session.result.status.value
    if status == "ongoing" and len(session.history) >= max_ply:
        return "CENSORED", True
    return status, False


def common_tape_games(compiled, *, pair_count: int, max_ply: int, seed: int, tape_length: int = 32) -> dict[str, Any]:
    """Run a tiny generator-independent Common-Tape harness with role swaps."""
    tapes = {
        (pair, role): PolicyTape.from_seed(f"qualification-{pair}-{role}", seed * 1009 + pair * 2 + role, tape_length)
        for pair in range(pair_count) for role in (0, 1)
    }
    records: list[dict[str, Any]] = []
    observations: list[QualityObservation] = []
    for pair in range(pair_count):
        for swapped in (False, True):
            session = GameSession(compiled)
            branchings: list[int] = []
            move_index = {0: 0, 1: 0}
            captures = 0
            checks = 0
            while session.result.status.value == "ongoing" and len(session.history) < max_ply:
                legal = session.legal_actions()
                if not legal:
                    break
                branchings.append(len(legal))
                actor = session.state.position.side_to_move
                role = (1 - actor) if swapped else actor
                action = legal[tapes[(pair, role)].choose_index(move_index[role], len(legal))]
                move_index[role] += 1
                if action_is_board(action):
                    target = session.state.position.board[square_to_index(action.to_square, compiled.board_size)]
                    if target is not None and target.owner != actor:
                        captures += 1
                session.submit(action)
                if is_in_check(session.state.position, session.state.position.side_to_move, compiled):
                    checks += 1
            terminal, censored = _normalized_terminal(session, max_ply)
            records.append({
                "pair_index": pair,
                "role_swap": swapped,
                "opening_identity": position_identity_key(compiled.initial_position, compiled),
                "terminal_status": terminal,
                "completion": "CENSORED" if censored else "TERMINAL",
                "plies": len(session.history),
                "branching_sequence": list(branchings),
                "capture_count": captures,
                "check_count": checks,
                "side_to_move_final": session.state.position.side_to_move,
            })
            observations.append(QualityObservation(tuple(branchings), len(session.history), terminal))
    profile = profile_from_observations(observations, ruleset_fingerprint=compiled.ruleset_fingerprint, board_size=compiled.board_size)
    branchings = [count for row in records for count in row["branching_sequence"]]
    total_moves = sum(row["plies"] for row in records)
    total_captures = sum(row["capture_count"] for row in records)
    total_checks = sum(row["check_count"] for row in records)
    return {
        "tape_schema": "PolicyTape",
        "pair_count": pair_count,
        "max_ply": max_ply,
        "tape_length": tape_length,
        "records": records,
        "profile": profile.to_dict(),
        "terminal_counts": dict(sorted(Counter(row["terminal_status"] for row in records).items())),
        "censored_count": sum(row["completion"] == "CENSORED" for row in records),
        "branching_distribution": dict(sorted(Counter(branchings).items())),
        "legal_action_collapse_fraction": sum(count <= 1 for count in branchings) / len(branchings) if branchings else 0.0,
        "capture_check_density": {
            "captures": total_captures,
            "checks": total_checks,
            "moves": total_moves,
            "capture_rate": total_captures / total_moves if total_moves else 0.0,
            "check_rate": total_checks / total_moves if total_moves else 0.0,
        },
        "side_bias": profile.side_bias_magnitude,
        "opening_identity_sensitivity": len({row["opening_identity"] for row in records}),
    }


def qualification_report(*, compiled, provenance: dict[str, Any], experiment_identity: str, structural: dict[str, Any], dynamic: dict[str, Any], replay_equal: bool, dynamic_status: str = STATUS_PASS, scope: str = "F87A") -> QualificationReport:
    gates = (
        GateOutcome("ruleset_executes", STATUS_PASS, "GENERICCHESS_SPECIFIC", "compiler/core accepted the ruleset", "layer_a_execution"),
        GateOutcome("shared_structural_probe", STATUS_PASS, "GENERICCHESS_SPECIFIC", "shared lattice/SCC/reachability probe completed", "layer_b_probe"),
        GateOutcome("common_tape_replay", dynamic_status if dynamic_status == STATUS_DEFER else (STATUS_PASS if replay_equal else STATUS_FAIL), "EMPIRICAL_GATE", "semantic runtime required" if dynamic_status == STATUS_DEFER else ("identical bounded replay" if replay_equal else "bounded replay changed"), "layer_c_replay"),
    )
    layers = {"A": STATUS_PASS, "B": STATUS_PASS, "C": dynamic_status if dynamic_status == STATUS_DEFER else (STATUS_PASS if replay_equal else STATUS_FAIL), "D": STATUS_DEFER, "E": STATUS_DEFER}
    reasons = (
        "Layer D paired strength-response is defined but intentionally not measured in F87A",
        "Layer E learning/transfer adapter is defined but intentionally not measured in F87A",
    )
    descriptors = {
        "structural_probe": MetricEvidence(structural, "GENERICCHESS_SPECIFIC", STATUS_PASS),
        "censored_trajectory_count": MetricEvidence(dynamic["censored_count"], "GENERICCHESS_SPECIFIC", dynamic_status),
        "skill_discrimination": MetricEvidence(None, "EMPIRICAL_GATE", STATUS_DEFER, "agent ladder/Arena not run in F87A"),
    }
    return QualificationReport(
        ruleset_fingerprint=compiled.ruleset_fingerprint,
        provenance=provenance,
        experiment_identity=experiment_identity,
        layers=layers,
        raw_diagnostics={"layer_b": structural, "layer_c": dynamic},
        hard_gates=gates,
        fail_defer_reasons=reasons,
        compute_usage={"dynamic_games": len(dynamic["records"]), "dynamic_plies": sum(row.get("plies", 0) for row in dynamic["records"]), "search_nodes": 0, "heavy": 0},
        behavior_descriptors=descriptors,
        overall_status=STATUS_DEFER if replay_equal else STATUS_FAIL,
    )


__all__ = [
    "GateOutcome", "MetricEvidence", "QualificationReport", "STATUS_DEFER", "STATUS_FAIL",
    "STATUS_PASS", "STATUS_UNMEASURED", "common_tape_games", "component_info",
    "lattice_info", "qualification_report", "structural_profile",
]
