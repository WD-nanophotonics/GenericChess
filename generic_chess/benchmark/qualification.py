"""Generator-independent ruleset qualification contracts and cheap probes."""

from __future__ import annotations

import itertools
import hashlib
import json
import math
from collections import Counter, deque
from dataclasses import dataclass, field
from typing import Any

from generic_chess.core.actions import action_is_board, action_to_dict
from generic_chess.core.attacks import is_in_check
from generic_chess.core.coordinates import square_to_index
from generic_chess.core.identity import position_identity_key
from generic_chess.core.movement import LeapAtom, RayAtom
from generic_chess.core.semantic_executor import semantic_engine_for, semantic_public_actions
from generic_chess.core.transition import apply_action, initial_state
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
    qualification_target: str
    required_layers: tuple[str, ...]
    measurement_status: str
    calibration_expectation_status: str
    layers: dict[str, str]
    raw_diagnostics: dict[str, Any]
    hard_gates: tuple[GateOutcome, ...]
    integrity_gates: tuple[GateOutcome, ...]
    qualification_gates: tuple[GateOutcome, ...]
    reason_codes: tuple[str, ...]
    layer_reasons: dict[str, tuple[str, ...]]
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
            "qualification_target": self.qualification_target,
            "required_layers": list(self.required_layers),
            "measurement_status": self.measurement_status,
            "calibration_expectation_status": self.calibration_expectation_status,
            "layers": dict(self.layers),
            "raw_diagnostics": self.raw_diagnostics,
            "hard_gates": [gate.to_dict() for gate in self.hard_gates],
            "integrity_gates": [gate.to_dict() for gate in self.integrity_gates],
            "qualification_gates": [gate.to_dict() for gate in self.qualification_gates],
            "reason_codes": list(self.reason_codes),
            "layer_reasons": {key: list(value) for key, value in self.layer_reasons.items()},
            "fail_defer_reasons": list(self.fail_defer_reasons),
            "compute_usage": self.compute_usage,
            "behavior_descriptors": {
                key: value.to_dict() for key, value in self.behavior_descriptors.items()
            },
            "overall_status": self.overall_status,
        }


def reduce_qualification_status(layers: dict[str, str], *, required_layers: tuple[str, ...], integrity_gates: tuple[GateOutcome, ...], qualification_gates: tuple[GateOutcome, ...]) -> str:
    """Single status reducer; integrity and qualification gates remain separate."""
    all_gates = integrity_gates + qualification_gates
    if any(gate.status == STATUS_FAIL for gate in all_gates):
        return STATUS_FAIL
    if any(layers.get(layer) != STATUS_PASS for layer in required_layers):
        return STATUS_DEFER
    if any(gate.status in {STATUS_DEFER, STATUS_UNMEASURED} for gate in all_gates):
        return STATUS_DEFER
    return STATUS_PASS


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


def movement_graph(compiled, type_id: str, owner: int = 0) -> tuple[tuple[int, ...], ...]:
    return _adjacency(compiled, type_id, owner)


def scc_info(adjacency: tuple[tuple[int, ...], ...]) -> tuple[list[tuple[int, ...]], dict[int, int]]:
    return _scc(adjacency)


def reachable_squares(adjacency: tuple[tuple[int, ...], ...], source: int) -> set[int]:
    return _reachable(adjacency, source)


def opening_sources(compiled, *, owner: int | None = None, include_anchors: bool = True) -> dict[str, list[dict[str, Any]]]:
    return _opening_sources(compiled, owner=owner, include_anchors=include_anchors)


def transport_type_profile(compiled, type_id: str, sources: list[dict[str, Any]], owner: int = 0) -> dict[str, Any]:
    n = compiled.board_size
    adjacency = movement_graph(compiled, type_id, owner)
    components, component_ids = scc_info(adjacency)
    edges = sum(len(targets) for targets in adjacency)
    reverse_edges = sum(int(source in adjacency[target]) for source, targets in enumerate(adjacency) for target in targets)
    sinks = sum(not targets for targets in adjacency)
    source_rows = []
    for source in sources:
        reached = reachable_squares(adjacency, source["square_index"])
        component = components[component_ids[source["square_index"]]]
        files = [index % n for index in component]
        ranks = [index // n if owner == 0 else n - 1 - (index // n) for index in component]
        source_rows.append({
            "source_id": source["source_id"],
            "opening_square": [source["square_index"] % n, source["square_index"] // n],
            "reachable_set_size": len(reached),
            "reachable_board_fraction": len(reached) / (n * n),
            "scc_component_id": component_ids[source["square_index"]],
            "scc_component_size": len(component),
            "scc_file_span": [min(files), max(files)],
            "scc_owner_relative_rank_span": [min(ranks), max(ranks)],
        })
    union = set().union(*(reachable_squares(adjacency, source["square_index"]) for source in sources)) if sources else set()
    return {
        "type_id": type_id,
        "used_in_opening": bool(sources),
        "movement_lattice": lattice_info(compiled, type_id),
        "directed_sink_fraction": sinks / (n * n),
        "direct_reverse_edge_fraction": reverse_edges / edges if edges else 0.0,
        "nontrivial_scc_fraction": sum(len(component) for component in components if len(component) > 1) / (n * n),
        "transitive_source_union_square_count": len(union),
        "transitive_source_union_board_fraction": len(union) / (n * n) if union else 0.0,
        "source_component_diversity": len({row["scc_component_id"] for row in source_rows}),
        "source_pairwise_reachable_overlap": [
            len(reachable_squares(adjacency, left["square_index"]).intersection(reachable_squares(adjacency, right["square_index"])))
            for index, left in enumerate(sources) for right in sources[index + 1:]
        ],
        "opening_sources": source_rows,
    }


def _opening_sources(compiled, *, owner: int | None = None, include_anchors: bool = True) -> dict[str, list[dict[str, Any]]]:
    anchor_ids = {piece.type_id for piece in compiled.piece_types if piece.is_anchor}
    ordinals: Counter[str] = Counter()
    rows: dict[str, list[dict[str, Any]]] = {}
    for index, piece in enumerate(compiled.initial_position.board):
        if piece is None or (owner is not None and piece.owner != owner) or (not include_anchors and piece.current_type_id in anchor_ids):
            continue
        key = f"{piece.owner}:{piece.current_type_id}"
        ordinals[key] += 1
        rows.setdefault(piece.current_type_id, []).append({
            "source_id": f"{piece.current_type_id}@o{piece.owner}#{ordinals[key]}",
            "owner": piece.owner,
            "type_id": piece.current_type_id,
            "square_index": index,
        })
    return rows


def component_info(compiled, type_id: str, owner: int = 0, *, opening_sources: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    adjacency = _adjacency(compiled, type_id, owner)
    components, component_ids = _scc(adjacency)
    opening = opening_sources if opening_sources is not None else _opening_sources(compiled, owner=owner).get(type_id, [])
    return {
        "type_id": type_id,
        "owner": owner,
        "component_count": len(components),
        "component_sizes": [len(component) for component in components],
        "opening_piece_components": [
            {"source_id": row["source_id"], "component_id": component_ids[row["square_index"]]}
            for row in opening
        ],
    }


def structural_profile(compiled, *, semantic_type_ids: set[str] | None = None) -> dict[str, Any]:
    """Shared Layer-B diagnostics; all fields are diagnostics, not universal gates."""
    n2 = compiled.board_size * compiled.board_size
    semantic_type_ids = semantic_type_ids or set()
    type_profiles = []
    for type_id in sorted(piece.type_id for piece in compiled.piece_types):
        piece_type = next(piece for piece in compiled.piece_types if piece.type_id == type_id)
        owner_profiles = []
        for owner in (0, 1):
            adjacency = _adjacency(compiled, type_id, owner)
            components, component_ids = _scc(adjacency)
            edge_count = sum(len(targets) for targets in adjacency)
            reverse_edges = sum(int(source in adjacency[target]) for source, targets in enumerate(adjacency) for target in targets)
            sinks = sum(not targets for targets in adjacency)
            source_rows = _opening_sources(compiled, owner=owner).get(type_id, [])
            reached = set().union(*(_reachable(adjacency, row["square_index"]) for row in source_rows)) if source_rows else set()
            transport = transport_type_profile(compiled, type_id, source_rows, owner)
            owner_profiles.append({
                "owner": owner,
                "semantic_applicability": "DEFER_SEMANTIC_MOVEMENT" if type_id in semantic_type_ids else "APPLICABLE",
                "movement_lattice": lattice_info(compiled, type_id),
                "component_profile": component_info(compiled, type_id, owner, opening_sources=source_rows),
                "opening_source_transport": transport,
                "directed_sink_fraction": sinks / n2,
                "direct_reverse_edge_fraction": reverse_edges / edge_count if edge_count else 0.0,
                "nontrivial_scc_vertex_fraction": sum(len(component) for component in components if len(component) > 1) / n2,
                "opening_sources": source_rows,
                "opening_source_reachable_union_square_count": len(reached),
                "opening_source_reachable_union_fraction": len(reached) / n2 if reached else 0.0,
                "opening_source_component_diversity": len({component_ids[row["square_index"]] for row in source_rows}),
            })
        type_profiles.append({
            "type_id": type_id,
            "is_anchor": piece_type.is_anchor,
            "semantic_type": type_id in semantic_type_ids,
            "owner_profiles": owner_profiles,
        })
    material_counts = Counter(piece.current_type_id for piece in compiled.initial_position.board if piece is not None)
    material_by_owner = Counter(
        f"o{piece.owner}:{piece.current_type_id}"
        for piece in compiled.initial_position.board
        if piece is not None
    )
    return {
        "schema_version": 2,
        "board_size": compiled.board_size,
        "ruleset_fingerprint": compiled.ruleset_fingerprint,
        "materialized_type_counts": dict(sorted(material_counts.items())),
        "materialized_type_counts_by_owner": dict(sorted(material_by_owner.items())),
        "type_profiles": type_profiles,
        "semantic_applicability": {
            type_id: ("DEFER_SEMANTIC_MOVEMENT" if type_id in semantic_type_ids else "APPLICABLE")
            for type_id in sorted(piece.type_id for piece in compiled.piece_types)
        },
        "universal_lattice_gate": MetricEvidence(
            "not_applied",
            "UNVALIDATED_HEURISTIC",
            STATUS_DEFER,
            "rank/index is a diagnostic; no universal rank-2/index-1 gate",
        ).to_dict(),
    }


def calibration_reason_codes(structural: dict[str, Any], *, control_class: str, terminal_transport: dict[str, Any] | None = None) -> tuple[str, ...]:
    """Translate measured Layer-B/authority facts into stable calibration codes."""
    profiles = [owner for row in structural["type_profiles"] for owner in row["owner_profiles"]]
    codes: list[str] = []
    if control_class == "negative":
        if any(owner["movement_lattice"]["integer_lattice_rank"] < 2 for owner in profiles):
            codes.append("LATTICE_RANK_DEFICIT")
        if any((owner["movement_lattice"]["lattice_index"] or 1) > 1 for owner in profiles):
            codes.append("LATTICE_RESIDUE_CONFINEMENT")
        if any(owner["directed_sink_fraction"] > 0 for owner in profiles):
            codes.append("SINK_COMPONENTS")
        if any(owner["direct_reverse_edge_fraction"] == 0 for owner in profiles):
            codes.append("ONE_WAY_TRANSPORT")
        if any(owner["opening_source_reachable_union_fraction"] < 1 for owner in profiles if owner["opening_sources"]):
            codes.append("FINITE_REACHABILITY_CONFINEMENT")
        if any(owner["direct_reverse_edge_fraction"] >= 0.5 for owner in profiles):
            codes.append("HIGH_LOCAL_REVERSIBILITY")
        if terminal_transport and terminal_transport.get("reason_code"):
            codes.append(terminal_transport["reason_code"])
    elif control_class == "boundary":
        if any(owner["opening_source_reachable_union_square_count"] > 1 for owner in profiles):
            codes.append("STRUCTURAL_BACKBONE_WITNESS")
        codes.append("BOUNDARY_NOT_ADMISSION")
    elif any(value != "APPLICABLE" for value in structural.get("semantic_applicability", {}).values()):
        codes.append("SEMANTIC_MOVEMENT_NOT_APPLICABLE")
    return tuple(dict.fromkeys(codes))


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
            action_sequence: list[dict[str, Any]] = []
            while session.result.status.value == "ongoing" and len(session.history) < max_ply:
                legal = sorted(
                    session.legal_actions(),
                    key=lambda candidate: json.dumps(action_to_dict(candidate), sort_keys=True, separators=(",", ":")),
                )
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
                action_sequence.append({"actor": actor, "action": action_to_dict(action), "legal_action_count": len(legal)})
                session.submit(action)
                if is_in_check(session.state.position, session.state.position.side_to_move, compiled):
                    checks += 1
            terminal, censored = _normalized_terminal(session, max_ply)
            first_score = None if censored else (0.5 if session.result.winner is None else (1.0 if session.result.winner == 0 else 0.0))
            second_score = None if censored else (0.5 if session.result.winner is None else (1.0 if session.result.winner == 1 else 0.0))
            sequence_bytes = json.dumps(action_sequence, sort_keys=True, separators=(",", ":")).encode("utf-8")
            records.append({
                "pair_index": pair,
                "role_swap": swapped,
                "seat_assignment": {"player0": "B" if swapped else "A", "player1": "A" if swapped else "B"},
                "opening_identity": position_identity_key(compiled.initial_position, compiled),
                "terminal_status": terminal,
                "completion": "CENSORED" if censored else "TERMINAL",
                "winner": session.result.winner,
                "first_player_score": first_score,
                "second_player_score": second_score,
                "plies": len(session.history),
                "branching_sequence": list(branchings),
                "capture_count": captures,
                "check_count": checks,
                "side_to_move_final": session.state.position.side_to_move,
                "action_sequence_sha256": hashlib.sha256(sequence_bytes).hexdigest(),
                "final_position_digest": position_identity_key(session.state.position, compiled),
            })
            observations.append(QualityObservation(tuple(branchings), len(session.history), terminal, first_score, second_score))
    profile = profile_from_observations(observations, ruleset_fingerprint=compiled.ruleset_fingerprint, board_size=compiled.board_size)
    branchings = [count for row in records for count in row["branching_sequence"]]
    total_moves = sum(row["plies"] for row in records)
    total_captures = sum(row["capture_count"] for row in records)
    total_checks = sum(row["check_count"] for row in records)
    opening_identity_count = len({row["opening_identity"] for row in records})
    terminal_counts = Counter(row["terminal_status"] for row in records)
    completed = len(records) - sum(row["completion"] == "CENSORED" for row in records)
    decisive = sum(row["winner"] is not None for row in records if row["completion"] != "CENSORED")
    return {
        "tape_schema": "PolicyTape",
        "pair_count": pair_count,
        "max_ply": max_ply,
        "tape_length": tape_length,
        "records": records,
        "profile": profile.to_dict(),
        "terminal_counts": dict(sorted(terminal_counts.items())),
        "censored_count": sum(row["completion"] == "CENSORED" for row in records),
        "completion_fraction": completed / len(records) if records else 0.0,
        "terminal_fractions": {
            "decisive": decisive / len(records) if records else 0.0,
            "checkmate": terminal_counts["checkmate"] / len(records) if records else 0.0,
            "stalemate": terminal_counts["stalemate"] / len(records) if records else 0.0,
            "repetition": terminal_counts["repetition"] / len(records) if records else 0.0,
            "other_draw": sum(terminal_counts[key] for key in ("draw", "perpetual_check")) / len(records) if records else 0.0,
            "censored": terminal_counts["CENSORED"] / len(records) if records else 0.0,
        },
        "branching_distribution": dict(sorted(Counter(branchings).items())),
        "legal_action_collapse_fraction": sum(count <= 1 for count in branchings) / len(branchings) if branchings else 0.0,
        "capture_check_density": {
            "captures": total_captures,
            "checks": total_checks,
            "moves": total_moves,
            "capture_rate": total_captures / total_moves if total_moves else 0.0,
            "check_rate": total_checks / total_moves if total_moves else 0.0,
        },
        "side_bias": {
            "magnitude": profile.side_bias_magnitude,
            "first_player_score": profile.first_player_score,
            "second_player_score": profile.second_player_score,
            "scoreable_games": sum(row["first_player_score"] is not None for row in records),
        },
        "opening_identity_count": opening_identity_count,
        "opening_sensitivity": {"status": "UNMEASURED" if opening_identity_count < 2 else "MEASURED", "identity_count": opening_identity_count},
    }


def _semantic_action_key(action) -> str:
    return json.dumps(action_to_dict(action), sort_keys=True, separators=(",", ":"))


def _semantic_piece_value(piece, compiled) -> int:
    """Small deterministic capture value used only by the greedy probe."""
    if piece is None:
        return 0
    if compiled.support.type_metadata.get(piece.current_type_id, None) and compiled.support.type_metadata[piece.current_type_id].is_anchor:
        return 1000
    token = piece.current_type_id.lstrip("+").upper()
    return {"P": 1, "L": 2, "N": 3, "S": 3, "G": 4, "B": 5, "R": 5, "Q": 9, "K": 100}.get(token, 1)


def _semantic_greedy_index(actions, position, compiled) -> int:
    actor = position.side_to_move
    ranked = []
    for index, action in enumerate(actions):
        target = position.board[square_to_index(action.to_square, compiled.board_size)]
        capture_value = _semantic_piece_value(target, compiled) if target is not None and target.owner != actor else 0
        promotion = int(getattr(action, "promotion_target_id", None) is not None)
        progress = 0
        if action_is_board(action):
            source = action.from_square
            target_square = action.to_square
            source_rank = source.rank if actor == 0 else compiled.board_size - 1 - source.rank
            target_rank = target_square.rank if actor == 0 else compiled.board_size - 1 - target_square.rank
            progress = target_rank - source_rank
        ranked.append((capture_value, promotion, progress, -index, index))
    return max(ranked)[-1]


def semantic_runtime_contract(compiled) -> dict[str, Any]:
    """Direct contract checks for the production semantic runtime."""
    engine = semantic_engine_for(compiled)
    if engine is None:
        return {"status": STATUS_DEFER, "reason": "compiled ruleset has no semantic runtime", "checks": {}}
    state = initial_state(compiled)
    actions_a = tuple(sorted(semantic_public_actions(engine, state.position), key=_semantic_action_key))
    actions_b = tuple(sorted(semantic_public_actions(engine, state.position), key=_semantic_action_key))
    initial_terminal = state.terminal_status.status.value
    child = apply_action(state, actions_a[0], compiled) if actions_a else None
    checks = {
        "legal_action_generation": bool(actions_a),
        "canonical_order_stable": tuple(_semantic_action_key(action) for action in actions_a) == tuple(_semantic_action_key(action) for action in actions_b),
        "initial_terminal_ongoing": initial_terminal == "ongoing",
        "action_application": child is not None,
        "side_to_move_switches": child is not None and child.position.side_to_move == 1 - state.position.side_to_move,
        "terminal_authority_available": child is not None and child.terminal_status.status.value in {"ongoing", "checkmate", "stalemate", "repetition", "perpetual_check", "max_ply", "no_contest"},
        "canonical_position_identity": child is not None and bool(position_identity_key(child.position, compiled)),
    }
    return {
        "status": STATUS_PASS if all(checks.values()) else STATUS_FAIL,
        "checks": checks,
        "initial_legal_action_count": len(actions_a),
        "initial_terminal_status": initial_terminal,
        "ruleset_fingerprint": compiled.ruleset_fingerprint,
    }


def semantic_tape_games(
    compiled,
    *,
    policy_id: str,
    pair_count: int,
    max_ply: int,
    seed: int,
    tape_length: int = 64,
) -> dict[str, Any]:
    """Run bounded role-swapped games through the production semantic Core path."""
    engine = semantic_engine_for(compiled)
    if engine is None:
        raise TypeError("semantic_tape_games requires a compiled semantic ruleset")
    if policy_id not in {"canonical_common_tape_random", "deterministic_material_capture_greedy"}:
        raise ValueError(f"unsupported semantic calibration policy: {policy_id}")
    tapes = {
        (pair, role): PolicyTape.from_seed(
            f"{policy_id}-{pair}-{role}", seed * 1009 + pair * 2 + role, tape_length
        )
        for pair in range(pair_count)
        for role in (0, 1)
    }
    records: list[dict[str, Any]] = []
    observations: list[QualityObservation] = []
    opening_identity = position_identity_key(engine._initial_position(), compiled)
    for pair in range(pair_count):
        for swapped in (False, True):
            state = initial_state(compiled)
            branchings: list[int] = []
            move_index = {0: 0, 1: 0}
            captures = checks = 0
            action_sequence: list[dict[str, Any]] = []
            material_start = sum(piece is not None for piece in state.position.board)
            while state.terminal_status.status.value == "ongoing" and state.ply_count < max_ply:
                legal = sorted(semantic_public_actions(engine, state.position), key=_semantic_action_key)
                if not legal:
                    break
                branchings.append(len(legal))
                actor = state.position.side_to_move
                role = (1 - actor) if swapped else actor
                if policy_id == "canonical_common_tape_random":
                    choice = tapes[(pair, role)].choose_index(move_index[role], len(legal))
                else:
                    choice = _semantic_greedy_index(legal, state.position, compiled)
                move_index[role] += 1
                action = legal[choice]
                target = state.position.board[square_to_index(action.to_square, compiled.board_size)]
                if action_is_board(action) and target is not None and target.owner != actor:
                    captures += 1
                action_sequence.append({"actor": actor, "action": action_to_dict(action), "legal_action_count": len(legal)})
                state = apply_action(state, action, compiled)
                if engine.in_check(state.position, state.position.side_to_move):
                    checks += 1
            status = state.terminal_status.status.value
            censored = status in {"ongoing", "max_ply"} and state.ply_count >= max_ply
            terminal = "CENSORED" if censored else status
            winner = None if censored else state.terminal_status.winner
            first_score = None if censored else (0.5 if winner is None else (1.0 if winner == 0 else 0.0))
            second_score = None if censored else (0.5 if winner is None else (1.0 if winner == 1 else 0.0))
            sequence_bytes = json.dumps(action_sequence, sort_keys=True, separators=(",", ":")).encode("utf-8")
            material_end = sum(piece is not None for piece in state.position.board)
            records.append({
                "policy_id": policy_id,
                "pair_index": pair,
                "role_swap": swapped,
                "seat_assignment": {"player0": "B" if swapped else "A", "player1": "A" if swapped else "B"},
                "opening_identity": opening_identity,
                "terminal_status": terminal,
                "completion": "CENSORED" if censored else "TERMINAL",
                "winner": winner,
                "first_player_score": first_score,
                "second_player_score": second_score,
                "plies": state.ply_count,
                "branching_sequence": list(branchings),
                "capture_count": captures,
                "check_count": checks,
                "material_start": material_start,
                "material_end": material_end,
                "material_reduction": material_start - material_end,
                "side_to_move_final": state.position.side_to_move,
                "action_sequence_sha256": hashlib.sha256(sequence_bytes).hexdigest(),
                "final_position_digest": position_identity_key(state.position, compiled),
            })
            observations.append(QualityObservation(tuple(branchings), state.ply_count, terminal, first_score, second_score))
    profile = profile_from_observations(observations, ruleset_fingerprint=compiled.ruleset_fingerprint, board_size=compiled.board_size)
    branchings = [count for row in records for count in row["branching_sequence"]]
    total_moves = sum(row["plies"] for row in records)
    terminal_counts = Counter(row["terminal_status"] for row in records)
    completed = sum(row["completion"] != "CENSORED" for row in records)
    return {
        "policy_id": policy_id,
        "tape_schema": "PolicyTape" if policy_id == "canonical_common_tape_random" else "deterministic_policy",
        "pair_count": pair_count,
        "game_count": len(records),
        "max_ply": max_ply,
        "tape_length": tape_length,
        "records": records,
        "profile": profile.to_dict(),
        "terminal_counts": dict(sorted(terminal_counts.items())),
        "censored_count": terminal_counts["CENSORED"],
        "completion_fraction": completed / len(records) if records else 0.0,
        "terminal_fractions": {
            "decisive": sum(row["winner"] is not None for row in records) / len(records) if records else 0.0,
            "checkmate": terminal_counts["checkmate"] / len(records) if records else 0.0,
            "stalemate": terminal_counts["stalemate"] / len(records) if records else 0.0,
            "repetition": terminal_counts["repetition"] / len(records) if records else 0.0,
            "other_draw": sum(terminal_counts[key] for key in ("perpetual_check", "no_contest")) / len(records) if records else 0.0,
            "censored": terminal_counts["CENSORED"] / len(records) if records else 0.0,
        },
        "branching_distribution": dict(sorted(Counter(branchings).items())),
        "legal_action_collapse_fraction": sum(count <= 1 for count in branchings) / len(branchings) if branchings else 0.0,
        "capture_check_density": {
            "captures": sum(row["capture_count"] for row in records),
            "checks": sum(row["check_count"] for row in records),
            "moves": total_moves,
            "capture_rate": sum(row["capture_count"] for row in records) / total_moves if total_moves else 0.0,
            "check_rate": sum(row["check_count"] for row in records) / total_moves if total_moves else 0.0,
        },
        "material_progress": {
            "games_with_reduction": sum(row["material_reduction"] > 0 for row in records),
            "total_material_reduction": sum(row["material_reduction"] for row in records),
        },
        "side_bias": {
            "magnitude": profile.side_bias_magnitude,
            "first_player_score": profile.first_player_score,
            "second_player_score": profile.second_player_score,
            "scoreable_games": sum(row["first_player_score"] is not None for row in records),
        },
        "opening_identity_count": len({row["opening_identity"] for row in records}),
        "opening_sensitivity": {"status": "UNMEASURED", "identity_count": 1},
    }


def _semantic_position_material_score(position, compiled, perspective: int) -> int:
    score = 0
    for piece in position.board:
        if piece is not None:
            value = _semantic_piece_value(piece, compiled)
            score += value if piece.owner == perspective else -value
    for owner, hand in enumerate(position.hands):
        hand_score = sum(_semantic_piece_value(type("HandPiece", (), {"current_type_id": type_id})(), compiled) * count for type_id, count in hand)
        score += hand_score if owner == perspective else -hand_score
    return score


def _semantic_search_action_score(state, action, compiled, engine, root_actor, nodes, node_cap, depth: int = 2) -> tuple[float, int]:
    if nodes[0] >= node_cap:
        return float("-inf"), nodes[0]
    child = apply_action(state, action, compiled)
    nodes[0] += 1
    result = child.terminal_status
    if result.winner is not None:
        terminal_value = 1_000_000 if result.winner == root_actor else -1_000_000
        return float(terminal_value), nodes[0]
    value = float(_semantic_position_material_score(child.position, compiled, root_actor))
    if depth <= 1 or result.status.value != "ongoing" or nodes[0] >= node_cap:
        return value, nodes[0]
    replies = sorted(semantic_public_actions(engine, child.position), key=_semantic_action_key)
    reply_values = []
    for reply in replies:
        if nodes[0] >= node_cap:
            break
        reply_value, _ = _semantic_search_action_score(child, reply, compiled, engine, root_actor, nodes, node_cap, depth=1)
        reply_values.append(reply_value)
    if reply_values:
        value = min(reply_values)
    return value, nodes[0]


def semantic_search_games(
    compiled,
    *,
    pair_count: int,
    max_ply: int,
    node_cap: int,
) -> dict[str, Any]:
    """Run a deterministic, terminal-aware shallow semantic search control."""
    engine = semantic_engine_for(compiled)
    if engine is None:
        raise TypeError("semantic_search_games requires a compiled semantic ruleset")
    records: list[dict[str, Any]] = []
    for pair in range(pair_count):
        for swapped in (False, True):
            state = initial_state(compiled)
            branchings: list[int] = []
            action_sequence: list[dict[str, Any]] = []
            captures = checks = 0
            nodes = [0]
            identities = [position_identity_key(state.position, compiled)]
            recurrence_counts = Counter(identities)
            while state.terminal_status.status.value == "ongoing" and state.ply_count < max_ply:
                legal = sorted(semantic_public_actions(engine, state.position), key=_semantic_action_key)
                if not legal:
                    break
                branchings.append(len(legal))
                actor = state.position.side_to_move
                root_actor = actor
                scored = []
                for index, action in enumerate(legal):
                    if nodes[0] >= node_cap and scored:
                        break
                    value, _ = _semantic_search_action_score(state, action, compiled, engine, root_actor, nodes, node_cap)
                    scored.append((value, -index, index))
                choice = max(scored)[-1] if scored else 0
                action = legal[choice]
                target = state.position.board[square_to_index(action.to_square, compiled.board_size)]
                if action_is_board(action) and target is not None and target.owner != actor:
                    captures += 1
                action_sequence.append({"actor": actor, "action": action_to_dict(action), "legal_action_count": len(legal), "search_nodes": nodes[0]})
                state = apply_action(state, action, compiled)
                if engine.in_check(state.position, state.position.side_to_move):
                    checks += 1
                identity = position_identity_key(state.position, compiled)
                identities.append(identity)
                recurrence_counts[identity] += 1
            status = state.terminal_status.status.value
            censored = status in {"ongoing", "max_ply"} and state.ply_count >= max_ply
            terminal = "CENSORED" if censored else status
            winner = None if censored else state.terminal_status.winner
            sequence_bytes = json.dumps(action_sequence, sort_keys=True, separators=(",", ":")).encode("utf-8")
            repeated_positions = sum(count - 1 for count in recurrence_counts.values() if count > 1)
            records.append({
                "policy_id": "deterministic_semantic_shallow_search",
                "pair_index": pair,
                "role_swap": swapped,
                "seat_assignment": {"player0": "B" if swapped else "A", "player1": "A" if swapped else "B"},
                "opening_identity": identities[0],
                "terminal_status": terminal,
                "completion": "CENSORED" if censored else "TERMINAL",
                "winner": winner,
                "first_player_score": None if censored else (0.5 if winner is None else (1.0 if winner == 0 else 0.0)),
                "second_player_score": None if censored else (0.5 if winner is None else (1.0 if winner == 1 else 0.0)),
                "plies": state.ply_count,
                "branching_sequence": list(branchings),
                "capture_count": captures,
                "check_count": checks,
                "search_nodes": nodes[0],
                "search_node_cap": node_cap,
                "distinct_position_count": len(recurrence_counts),
                "position_return_count": repeated_positions,
                "max_position_multiplicity": max(recurrence_counts.values()),
                "recurrence_fraction": repeated_positions / len(identities) if identities else 0.0,
                "side_to_move_final": state.position.side_to_move,
                "action_sequence_sha256": hashlib.sha256(sequence_bytes).hexdigest(),
                "final_position_digest": identities[-1],
            })
    branchings = [count for row in records for count in row["branching_sequence"]]
    terminal_counts = Counter(row["terminal_status"] for row in records)
    total_moves = sum(row["plies"] for row in records)
    return {
        "policy_id": "deterministic_semantic_shallow_search",
        "pair_count": pair_count,
        "game_count": len(records),
        "max_ply": max_ply,
        "search_node_cap": node_cap,
        "records": records,
        "terminal_counts": dict(sorted(terminal_counts.items())),
        "censored_count": terminal_counts["CENSORED"],
        "completion_fraction": sum(row["completion"] != "CENSORED" for row in records) / len(records) if records else 0.0,
        "terminal_fractions": {
            "checkmate": terminal_counts["checkmate"] / len(records) if records else 0.0,
            "stalemate": terminal_counts["stalemate"] / len(records) if records else 0.0,
            "repetition": terminal_counts["repetition"] / len(records) if records else 0.0,
            "other_draw": sum(terminal_counts[key] for key in ("perpetual_check", "no_contest")) / len(records) if records else 0.0,
            "censored": terminal_counts["CENSORED"] / len(records) if records else 0.0,
        },
        "branching_distribution": dict(sorted(Counter(branchings).items())),
        "legal_action_collapse_fraction": sum(count <= 1 for count in branchings) / len(branchings) if branchings else 0.0,
        "capture_check_density": {
            "captures": sum(row["capture_count"] for row in records),
            "checks": sum(row["check_count"] for row in records),
            "moves": total_moves,
        },
        "recurrence": {
            "games_with_position_return": sum(row["position_return_count"] > 0 for row in records),
            "total_position_returns": sum(row["position_return_count"] for row in records),
            "max_position_multiplicity": max((row["max_position_multiplicity"] for row in records), default=0),
        },
        "search_nodes": sum(row["search_nodes"] for row in records),
    }


def qualification_report(*, compiled, provenance: dict[str, Any], experiment_identity: str, structural: dict[str, Any], dynamic: dict[str, Any], replay_equal: bool, dynamic_status: str = STATUS_PASS, control_class: str = "unknown", control_name: str = "", layer_b_reason_codes: tuple[str, ...] = (), terminal_transport: dict[str, Any] | None = None, calibration_authority: dict[str, Any] | None = None, layer_c_status: str = STATUS_DEFER, layer_c_reason: str = "playability authority is not calibrated in F87A-R1", scope: str = "F87A") -> QualificationReport:
    required_layers = ("A", "B", "C")
    layer_c_integrity = dynamic_status if dynamic_status in {STATUS_DEFER, STATUS_UNMEASURED} else (STATUS_PASS if replay_equal else STATUS_FAIL)
    integrity_gates = (
        GateOutcome("ruleset_executes", STATUS_PASS, "GENERICCHESS_SPECIFIC", "compiler/core accepted the ruleset", "layer_a_execution"),
        GateOutcome("shared_structural_probe_integrity", STATUS_PASS, "GENERICCHESS_SPECIFIC", "shared owner/anchor structural probe completed", "layer_b_probe"),
        GateOutcome("common_tape_replay_identity", layer_c_integrity, "EMPIRICAL_GATE", "semantic runtime required" if dynamic_status in {STATUS_DEFER, STATUS_UNMEASURED} else ("identical canonical bounded replay" if replay_equal else "canonical replay changed"), "layer_c_replay"),
    )
    if control_class == "negative":
        layer_b_status = STATUS_FAIL if calibration_authority and calibration_authority.get("status") == STATUS_FAIL else (STATUS_DEFER if not layer_b_reason_codes else STATUS_PASS)
        layer_b_reason = "frozen negative environment authority confirms known pathology" if layer_b_status == STATUS_FAIL else ("calibrated structural pathology reason codes recorded" if layer_b_reason_codes else "negative control produced no calibrated pathology reason")
    elif control_class == "boundary":
        layer_b_status = STATUS_DEFER
        layer_b_reason = "boundary witness is diagnostic; admission authority remains deferred"
    else:
        layer_b_status = STATUS_DEFER if structural.get("semantic_applicability", {}).values() and any(value != "APPLICABLE" for value in structural["semantic_applicability"].values()) else STATUS_DEFER
        layer_b_reason = "semantic movement metrics are not applicable to the legacy empty-mobility probe"
    qualification_gates = (
        GateOutcome("layer_b_ruleset_state", layer_b_status, "EMPIRICAL_GATE", layer_b_reason, "layer_b_qualification"),
        GateOutcome("calibration_expectation", STATUS_PASS if layer_b_reason_codes else STATUS_DEFER, "EMPIRICAL_GATE", "frozen qualitative expectation observed" if layer_b_reason_codes else "no qualitative expectation evidence", "calibration_expectation"),
        GateOutcome("layer_c_playability", layer_c_status, "EMPIRICAL_GATE", layer_c_reason, "layer_c_qualification"),
    )
    layers = {"A": STATUS_PASS, "B": layer_b_status, "C": layer_c_status, "D": STATUS_DEFER, "E": STATUS_DEFER}
    reason_codes = tuple(dict.fromkeys(layer_b_reason_codes + (("CALIBRATION_NEGATIVE_ENVIRONMENT_AUTHORITY",) if layer_b_status == STATUS_FAIL else ()) + (("SEMANTIC_MOVEMENT_NOT_APPLICABLE",) if layer_b_status == STATUS_DEFER and control_class == "positive_semantic" else ()) + (("PLAYABILITY_AUTHORITY_UNCALIBRATED",) if layer_c_status != STATUS_PASS else ())))
    reasons = (
        "Layer C replay identity is an integrity gate; playability qualification is separately calibrated",
        "Layer D paired strength-response is defined but intentionally not measured in F87A-R1",
        "Layer E learning/transfer adapter is defined but intentionally not measured in F87A-R1",
    )
    descriptors = {
        "structural_probe": MetricEvidence(structural, "GENERICCHESS_SPECIFIC", STATUS_PASS),
        "censored_trajectory_count": MetricEvidence(dynamic.get("censored_count", 0), "GENERICCHESS_SPECIFIC", dynamic_status),
        "terminal_transport": MetricEvidence(terminal_transport, "GENERICCHESS_SPECIFIC", STATUS_DEFER if terminal_transport is None else terminal_transport.get("status", STATUS_DEFER)),
        "calibration_authority": MetricEvidence(calibration_authority, "EMPIRICAL_GATE", calibration_authority.get("status", STATUS_DEFER) if calibration_authority else STATUS_DEFER),
        "skill_discrimination": MetricEvidence(None, "EMPIRICAL_GATE", STATUS_DEFER, "agent ladder/Arena not run in F87A-R1"),
    }
    overall_status = reduce_qualification_status(layers, required_layers=required_layers, integrity_gates=integrity_gates, qualification_gates=qualification_gates)
    return QualificationReport(
        ruleset_fingerprint=compiled.ruleset_fingerprint,
        provenance={**provenance, "control_class": control_class, "control_name": control_name},
        experiment_identity=experiment_identity,
        qualification_target="PLAYABILITY",
        required_layers=required_layers,
        measurement_status=STATUS_PASS if all(gate.status == STATUS_PASS for gate in integrity_gates) else STATUS_UNMEASURED,
        calibration_expectation_status=STATUS_PASS if layer_b_reason_codes else STATUS_DEFER,
        layers=layers,
        raw_diagnostics={"layer_b": structural, "layer_c": dynamic, "calibration_authority": calibration_authority},
        hard_gates=integrity_gates + qualification_gates,
        integrity_gates=integrity_gates,
        qualification_gates=qualification_gates,
        reason_codes=reason_codes,
        layer_reasons={"B": tuple(layer_b_reason_codes), "C": ("PLAYABILITY_AUTHORITY_UNCALIBRATED",) if layer_c_status != STATUS_PASS else ("POSITIVE_DYNAMIC_CALIBRATION_PASS",)},
        fail_defer_reasons=reasons,
        compute_usage={"dynamic_games": len(dynamic.get("records", [])), "dynamic_plies": sum(row.get("plies", 0) for row in dynamic.get("records", [])), "search_nodes": 0, "heavy": 0},
        behavior_descriptors=descriptors,
        overall_status=overall_status,
    )


__all__ = [
    "GateOutcome", "MetricEvidence", "QualificationReport", "STATUS_DEFER", "STATUS_FAIL",
    "STATUS_PASS", "STATUS_UNMEASURED", "calibration_reason_codes", "common_tape_games", "component_info",
    "lattice_info", "movement_graph", "opening_sources", "qualification_report", "reachable_squares",
    "reduce_qualification_status", "scc_info", "semantic_runtime_contract", "semantic_search_games", "semantic_tape_games", "structural_profile", "transport_type_profile",
]
