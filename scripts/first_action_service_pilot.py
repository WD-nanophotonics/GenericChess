"""Pre-reference exact first-action spatial-service pilot.

Implements FIRST_ACTION_SERVICE_PILOT_PROTOCOL.md. No human references,
engine scores, fitted coefficients, or Xiangqi material tables are used.
"""

from __future__ import annotations

from collections import deque
from fractions import Fraction
from time import monotonic

from scripts.audit_static_semantic_material_prior_v2c import (
    _event_measure_factory, _token_state_ledger,
)
from scripts.intrinsic_action_events import (
    collect_intrinsic_board_events, collect_intrinsic_held_drop_events,
)


def canonical_occupancy_cubes(cubes: tuple[tuple, ...]) -> tuple[tuple, ...]:
    """Rename sampled squares canonically; V2C is exchangeable over them."""
    squares = sorted({square for cube in cubes for square, _labels in cube})
    rename = {square: index for index, square in enumerate(squares)}
    return tuple(sorted({tuple(sorted((rename[square], labels)
                                   for square, labels in cube)) for cube in cubes}))


def reachable_board_square_count(adjacency: dict[tuple, set[tuple]],
                                  start: tuple) -> int:
    """Count board squares reachable via directed positive-mass edges."""
    seen = {start}
    queue = deque([start])
    while queue:
        for neighbor in adjacency.get(queue.popleft(), ()):
            if neighbor not in seen:
                seen.add(neighbor)
                queue.append(neighbor)
    return len({node[2] for node in seen})


def hand_target_empty_probability(ledger: dict) -> Fraction:
    """Shogi held-token conditioning under the declared V2C status model."""
    if ledger["owner_model"] != "maximum_entropy_symmetric_owner_given_board_state":
        raise ValueError("held probability requires symmetric owner model")
    if any(row.get("persistence_state") != "board_or_hand"
           for row in ledger["token_types"].values() if not row.get("anchor")):
        raise ValueError("held probability requires board-or-hand token persistence")
    area = ledger["board_square_count"]
    optional_others = ledger["optional_token_count"] - 1
    if optional_others < 0:
        raise ValueError("no optional held token available")
    empty_expectation = Fraction(area - ledger["anchor_token_count"]) - Fraction(optional_others, 2)
    if not 0 <= empty_expectation <= area:
        raise ValueError("invalid held occupancy expectation")
    return empty_expectation / area


def audit_first_action_service(compiled, *, max_seconds: float = 60,
                               max_candidates_per_type: int = 100_000) -> dict:
    """Compute exact board/held raw and max-gauge vectors from compiled rules."""
    started = monotonic()

    def check_budget() -> None:
        if monotonic() - started > max_seconds:
            raise TimeoutError("first-action service audit time budget exceeded")

    if max_seconds <= 0 or max_candidates_per_type < 1:
        raise ValueError("positive time and candidate budgets required")
    ledger = _token_state_ledger(compiled)
    if not ledger["complete"]:
        raise RuntimeError(f"V2C token-state model incomplete: {ledger['failure_reasons']}")
    area = ledger["board_square_count"]
    type_ids = sorted(type_id for type_id, metadata in compiled.support.type_metadata.items()
                      if not metadata.is_anchor)
    adjacency: dict[tuple, set[tuple]] = {
        (owner, type_id, square): set()
        for owner in (0, 1) for type_id in type_ids for square in range(area)
    }
    weighted_events: list[tuple[str, int, str, int, Fraction]] = []
    probability_cache: dict[tuple, Fraction] = {}
    board_coverage = {}
    event_counter = 0
    for type_id in type_ids:
        audit = collect_intrinsic_board_events(compiled, type_id,
                                               max_candidates=max_candidates_per_type)
        if not audit["coverage_complete"]:
            raise RuntimeError(f"unsupported intrinsic board events for {type_id}: "
                               f"{audit['unsupported_intrinsic']}")
        board_coverage[type_id] = {
            "candidate_count": audit["candidate_count"],
            "physical_event_count": len(audit["events"]),
            "excluded_history": audit["excluded_history"],
            "excluded_dynamic": audit["excluded_dynamic"],
            "excluded_auxiliary_effects": audit["excluded_auxiliary_effects"],
        }
        measure = _event_measure_factory(ledger, compiled, type_id)
        for key, cubes in audit["events"].items():
            owner, _type, source, target, _state, _removals, result_type = key
            if any(square == source for cube in cubes for square, _labels in cube):
                raise RuntimeError("source-conditioned cube constrains source square")
            signature = canonical_occupancy_cubes(cubes)
            cache_key = (type_id, owner, signature)
            probability = probability_cache.get(cache_key)
            if probability is None:
                probability = measure(owner, type_id, list(signature))
                probability_cache[cache_key] = probability
            if probability > 0:
                start = (owner, type_id, source)
                destination = (owner, result_type, target)
                if destination not in adjacency:
                    raise RuntimeError("event results in an unknown board type")
                adjacency[start].add(destination)
                weighted_events.append((type_id, owner, result_type, target, probability))
            event_counter += 1
            if event_counter % 1_024 == 0:
                check_budget()
        check_budget()

    reach = {}
    for index, node in enumerate(adjacency):
        reach[node] = reachable_board_square_count(adjacency, node)
        if index % 32 == 0:
            check_budget()
    raw_board_by_owner = {(type_id, owner): Fraction(0)
                          for type_id in type_ids for owner in (0, 1)}
    for type_id, owner, result_type, target, probability in weighted_events:
        raw_board_by_owner[(type_id, owner)] += probability * reach[(owner, result_type, target)]
    raw_board = {type_id: (raw_board_by_owner[(type_id, 0)]
                           + raw_board_by_owner[(type_id, 1)]) / (2 * area * area)
                 for type_id in type_ids}

    held = {}
    held_empty = None
    for type_id in type_ids:
        held_audit = collect_intrinsic_held_drop_events(compiled, type_id)
        if not held_audit["coarse_coverage_complete"]:
            raise RuntimeError(f"unsupported intrinsic held events for {type_id}: "
                               f"{held_audit['unsupported_intrinsic']}")
        if not held_audit["events"]:
            continue
        if held_empty is None:
            held_empty = hand_target_empty_probability(ledger)
        total = sum((held_empty * reach[(key[0], type_id, key[3])]
                     for key in held_audit["events"]), Fraction(0))
        held[type_id] = {
            "raw": total / (2 * area),
            "coarse_event_count": len(held_audit["events"]),
            "excluded_state_constraints": held_audit["excluded_state_constraints"],
            "excluded_dynamic": held_audit["excluded_dynamic"],
        }
        check_budget()

    ordinary = [type_id for type_id, row in ledger["token_types"].items()
                if not row.get("anchor") and type_id in raw_board]
    gauge = max((raw_board[type_id] for type_id in ordinary), default=Fraction(0))
    if gauge <= 0:
        raise RuntimeError("nonpositive ordinary-type reporting gauge")
    check_budget()
    return {
        "ruleset_fingerprint": compiled.support.ruleset_fingerprint,
        "area": area,
        "raw_board": raw_board,
        "raw_board_by_owner": {
            type_id: (raw_board_by_owner[(type_id, 0)] / (area * area),
                      raw_board_by_owner[(type_id, 1)] / (area * area))
            for type_id in type_ids},
        "normalized_board": {type_id: value / gauge for type_id, value in raw_board.items()},
        "raw_held": {type_id: row["raw"] for type_id, row in held.items()},
        "normalized_held": {type_id: row["raw"] / gauge for type_id, row in held.items()},
        "held_empty_probability": held_empty,
        "gauge": gauge,
        "board_coverage": board_coverage,
        "held_coverage": held,
        "positive_board_events": len(weighted_events),
        "occupancy_probability_cache_size": len(probability_cache),
        "elapsed_seconds": monotonic() - started,
    }
