"""V2C finite-population prior under an explicit coarse token-state maximum entropy model."""

from __future__ import annotations

from collections import Counter, defaultdict
from fractions import Fraction
from functools import lru_cache
import json
from math import comb
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from generic_chess.rules.compiler import compile_semantic_ruleset
from generic_chess.rules.standard_shogi import build_standard_shogi_ruleset
from generic_chess.rules.western_chess import build_western_chess_ruleset
from scripts.audit_static_semantic_material_prior_v2 import audit_ruleset as audit_v2_ruleset
from scripts.audit_static_semantic_material_prior_v2a import (
    ALL_LABELS,
    OCCUPANCY_STATES,
    _inventory_bound,
    audit_ruleset_v2a,
)


def _fraction(value: Fraction) -> str:
    return f"{value.numerator}/{value.denominator}"


def _binomial_pmf(n: int) -> dict[int, Fraction]:
    if n < 0:
        raise ValueError("binomial trial count cannot be negative")
    return {k: Fraction(comb(n, k), 2**n) for k in range(n + 1)}


def _canonical_events(cubes: list[tuple] | tuple[tuple, ...]) -> tuple[tuple, ...]:
    return tuple(sorted(set(cubes)))


@lru_cache(maxsize=300_000)
def _finite_population_visit(events: tuple[tuple, ...], counts: tuple[int, int, int]) -> Fraction:
    if not events:
        return Fraction(0)
    if () in events:
        return Fraction(1)
    square = min(index for cube in events for index, _labels in cube)
    remaining = sum(counts)
    if remaining == 0:
        return Fraction(0)
    total = Fraction(0)
    for label_index, label in enumerate(OCCUPANCY_STATES):
        label_count = counts[label_index]
        if not label_count:
            continue
        next_counts = list(counts)
        next_counts[label_index] -= 1
        next_events = []
        for cube in events:
            restrictions = dict(cube)
            allowed = restrictions.get(square)
            if allowed is not None and label not in allowed:
                continue
            restrictions.pop(square, None)
            next_events.append(tuple(sorted(
                (index, labels) for index, labels in restrictions.items()
                if frozenset(labels) != ALL_LABELS
            )))
        total += Fraction(label_count, remaining) * _finite_population_visit(
            _canonical_events(next_events), tuple(next_counts)
        )
    return total


def finite_population_union_probability(
    cubes: list[tuple] | tuple[tuple, ...],
    *,
    empty_count: int,
    own_count: int,
    enemy_count: int,
) -> Fraction:
    """Exact probability of a union of V2A occupancy cubes without replacement."""
    counts = (empty_count, own_count, enemy_count)
    if min(counts) < 0:
        raise ValueError("label counts cannot be negative")
    return _finite_population_visit(_canonical_events(cubes), counts)


def _token_state_ledger(compiled: Any) -> dict[str, Any]:
    inventory = _inventory_bound(compiled)
    rows = [piece for rank in compiled.support.initial_position for piece in rank if piece is not None]
    mandatory_by_owner = Counter()
    optional_by_owner = Counter()
    initial_base_counts = Counter()
    base_owner_counts: dict[str, Counter] = defaultdict(Counter)
    for piece in rows:
        metadata = compiled.support.type_metadata.get(piece.current_type_id)
        if metadata is None:
            return {"complete": False, "failure_reasons": [f"missing_metadata:{piece.current_type_id}"]}
        initial_base_counts[piece.base_type_id] += 1
        base_owner_counts[piece.base_type_id][piece.owner] += 1
        (mandatory_by_owner if metadata.is_anchor else optional_by_owner)[piece.owner] += 1

    type_rows = {}
    failure_reasons: list[str] = []
    for base_type in sorted(initial_base_counts):
        metadata = compiled.support.type_metadata.get(base_type)
        if metadata is None:
            failure_reasons.append(f"missing_base_metadata:{base_type}")
            continue
        if metadata.is_anchor:
            type_rows[base_type] = {
                "initial_token_count": initial_base_counts[base_type],
                "initial_owner_counts": dict(base_owner_counts[base_type]),
                "anchor": True,
                "persistence_state": "mandatory_board",
                "promotion_targets": list(metadata.promotion_target_ids),
            }
            continue

        current_types = {base_type, *metadata.promotion_target_ids}
        dispositions = set()
        capture_rows = []
        drop_pairs = set()
        for pattern in compiled.ir.patterns:
            if not (set(pattern.type_ids) & current_types):
                continue
            geometry_kinds = {compiled.ir.geometry[gid].kind for gid in pattern.geometry_ids}
            if "drop" in geometry_kinds and base_type in pattern.type_ids:
                effect_kinds = Counter(effect.kind for effect in pattern.effects)
                drop_pairs.add((effect_kinds["remove_from_hand"], effect_kinds["place"]))
            for effect in pattern.effects:
                if effect.kind == "remove":
                    dispositions.add(effect.disposition)
                    capture_rows.append({
                        "pattern": pattern.name,
                        "disposition": effect.disposition,
                        "victim_owner": effect.piece_owner,
                    })
        if len(dispositions) != 1 or not dispositions:
            failure_reasons.append(f"ambiguous_capture_disposition:{base_type}:{sorted(str(x) for x in dispositions)}")
            continue
        disposition = next(iter(dispositions))
        if disposition == "remove_from_game":
            state = "board_or_removed"
            allowed_drops = sum(
                bool(value)
                for mask in compiled.support.drop_allowed.get(base_type, ())[:2]
                for value in mask
            )
            if allowed_drops:
                failure_reasons.append(f"removed_token_has_drop_effect:{base_type}")
        elif disposition == "capture_to_hand":
            state = "board_or_hand"
            if not drop_pairs or any(pair != (1, 1) for pair in drop_pairs):
                failure_reasons.append(f"hand_token_drop_not_one_for_one:{base_type}:{sorted(drop_pairs)}")
        else:
            failure_reasons.append(f"unknown_persistence_disposition:{base_type}:{disposition}")
            continue
        type_rows[base_type] = {
            "initial_token_count": initial_base_counts[base_type],
            "initial_owner_counts": dict(base_owner_counts[base_type]),
            "anchor": False,
            "persistence_state": state,
            "capture_disposition": disposition,
            "capture_effects": capture_rows,
            "promotion_targets": list(metadata.promotion_target_ids),
            "drop_effect_pairs": sorted(drop_pairs),
            "allowed_drop_square_count": allowed_drops if disposition == "remove_from_game" else sum(
                bool(value) for mask in compiled.support.drop_allowed.get(base_type, ())[:2] for value in mask
            ),
        }

    if not inventory["complete"]:
        failure_reasons.extend(inventory["failure_reasons"])
    status_states = {row.get("persistence_state") for row in type_rows.values() if not row.get("anchor")}
    if len(status_states) != 1:
        failure_reasons.append(f"nonuniform_nonanchor_persistence_states:{sorted(str(x) for x in status_states)}")
    return {
        "complete": not failure_reasons,
        "board_square_count": inventory["board_square_count"],
        "initial_token_count": inventory["initial_token_count"],
        "anchor_token_count": sum(mandatory_by_owner.values()),
        "optional_token_count": sum(optional_by_owner.values()),
        "mandatory_board_by_owner": {str(k): mandatory_by_owner[k] for k in (0, 1)},
        "optional_token_by_initial_owner": {str(k): optional_by_owner[k] for k in (0, 1)},
        "token_types": type_rows,
        "failure_reasons": sorted(set(failure_reasons)),
        "owner_model": (
            "initial_owner_persists"
            if "board_or_removed" in status_states
            else "maximum_entropy_symmetric_owner_given_board_state"
        ),
        "owner_model_is_rule_unique": "board_or_hand" not in status_states,
        "probability_assumption": "independent equiprobable binary persistence state for each non-anchor physical token; explicit coarse token-state maximum-entropy prior, not a rule-derived game-position frequency",
    }


def _source_joint_counts(
    ledger: dict[str, Any], source_owner: int, *, source_is_anchor: bool
) -> dict[tuple[int, int, int], Fraction]:
    """PMF of (empty, own, enemy) labels on non-source squares, conditioned on source present."""
    area = ledger["board_square_count"]
    anchor = {owner: ledger["mandatory_board_by_owner"][str(owner)] for owner in (0, 1)}
    optional = {owner: ledger["optional_token_by_initial_owner"][str(owner)] for owner in (0, 1)}
    if source_is_anchor:
        if anchor[source_owner] < 1:
            raise ValueError("source owner has no mandatory anchor token")
        anchor[source_owner] -= 1
    else:
        if optional[source_owner] < 1:
            raise ValueError("source owner has no non-anchor token to condition on board")
        optional[source_owner] -= 1
    m = sum(optional.values())
    joint: dict[tuple[int, int, int], Fraction] = defaultdict(Fraction)
    if ledger["owner_model"] == "initial_owner_persists":
        source_pmf = _binomial_pmf(optional[source_owner])
        other_pmf = _binomial_pmf(optional[1 - source_owner])
        for own_survivors, own_probability in source_pmf.items():
            for enemy_survivors, enemy_probability in other_pmf.items():
                own = anchor[source_owner] + own_survivors
                enemy = anchor[1 - source_owner] + enemy_survivors
                empty = area - 1 - own - enemy
                joint[(empty, own, enemy)] += own_probability * enemy_probability
    else:
        # Board/hand status is sampled first; owner relation is a separate, explicit
        # symmetric maximum-entropy assignment for each other board token.
        for other_board_count, status_probability in _binomial_pmf(m).items():
            for own_other, owner_probability in _binomial_pmf(other_board_count).items():
                own = anchor[source_owner] + own_other
                enemy = anchor[1 - source_owner] + (other_board_count - own_other)
                empty = area - 1 - own - enemy
                joint[(empty, own, enemy)] += status_probability * owner_probability
    if sum(joint.values(), Fraction(0)) != 1:
        raise ArithmeticError("source-conditioned joint owner/occupancy PMF does not sum to one")
    return dict(joint)


def _board_count_pmf(ledger: dict[str, Any], *, source_conditioned: bool = False) -> dict[int, Fraction]:
    a = ledger["anchor_token_count"]
    m = ledger["optional_token_count"]
    if source_conditioned:
        if m < 1:
            raise ValueError("no optional source token available")
        offset, trials = a + 1, m - 1
    else:
        offset, trials = a, m
    return {offset + successes: probability for successes, probability in _binomial_pmf(trials).items()}


def _pmf_stats(pmf: dict[int, Fraction]) -> dict[str, Any]:
    mean = sum(Fraction(value) * probability for value, probability in pmf.items())
    variance = sum((Fraction(value) - mean) ** 2 * probability for value, probability in pmf.items())
    return {
        "pmf": {str(value): _fraction(probability) for value, probability in sorted(pmf.items())},
        "mass_exact": _fraction(sum(pmf.values(), Fraction(0))),
        "mean_exact": _fraction(mean),
        "variance_exact": _fraction(variance),
        "minimum": min(pmf),
        "maximum": max(pmf),
    }


def _event_measure_factory(ledger: dict[str, Any], compiled: Any, type_id: str):
    source_is_anchor = bool(compiled.support.type_metadata[type_id].is_anchor)
    source_distributions = {
        owner: _source_joint_counts(ledger, owner, source_is_anchor=source_is_anchor)
        for owner in (0, 1)
    }
    square_count = ledger["board_square_count"] - 1

    @lru_cache(maxsize=None)
    def measure(owner: int, events: tuple[tuple, ...]) -> Fraction:
        distribution = source_distributions[owner]
        return sum((
            mass * finite_population_union_probability(
                events,
                empty_count=empty,
                own_count=own,
                enemy_count=enemy,
            )
            for (empty, own, enemy), mass in distribution.items()
        ), Fraction(0))

    def callback(owner: int, current_type: str, cubes: list[tuple]) -> Fraction:
        if current_type != type_id:
            raise ValueError("event measure bound to unexpected piece type")
        return measure(owner, _canonical_events(cubes))

    return callback


def audit_ruleset_v2c(compiled: Any) -> dict[str, Any]:
    ledger = _token_state_ledger(compiled)
    if not ledger["complete"]:
        return {
            "classification": "STATIC_MATERIAL_PRIOR_V2C_MAXENT_TOKEN_ENSEMBLE_INCONCLUSIVE",
            "coverage_complete": False,
            "human_metrics_computed": False,
            "token_state_ledger": ledger,
            "ledger": {},
        }
    base = audit_ruleset_v2a(compiled)
    base_b = audit_ruleset_v2a(compiled, fixed_at_rho_max=True)
    v2 = audit_v2_ruleset(compiled)
    measure_cache = {
        type_id: _event_measure_factory(ledger, compiled, type_id)
        for type_id in compiled.support.type_metadata
    }

    def event_measure(owner: int, type_id: str, cubes: list[tuple]) -> Fraction:
        return measure_cache[type_id](owner, type_id, cubes)

    result = audit_ruleset_v2a(compiled, event_measure=event_measure)
    output_rows = result["ledger"]
    for type_id, row in output_rows.items():
        baseline_a = base["ledger"][type_id]
        baseline_b = base_b["ledger"][type_id]
        row["v2_fixed_rho_2_3"] = v2["ledger"].get(type_id, {}).get("board_intrinsic")
        row["v2a_uniform_0_rho_max"] = baseline_a["v2a_phase_averaged_board_intrinsic"]
        row["v2a_exact"] = baseline_a["v2a_raw_exact"]
        row["v2b_fixed_rho_max"] = baseline_b["v2b_fixed_rho_max_board_intrinsic"]
        row["v2b_exact"] = baseline_b["v2b_raw_exact"]
        row["v2c_maxent_token_board_intrinsic"] = row.pop("v2a_phase_averaged_board_intrinsic")
        row["v2c_exact"] = row.pop("v2a_raw_exact")
        row["components_v2c"] = row["components"]
        row["components_v2c_exact"] = row["components_exact"]
        row["v2c_coverage"] = row.pop("v2a_coverage")
    board_pmf = _pmf_stats(_board_count_pmf(ledger))
    source_pmf = _pmf_stats(_board_count_pmf(ledger, source_conditioned=True))
    owner_conditioned = {
        str(owner): [
            {"empty": e, "own": o, "enemy": x, "probability": _fraction(probability)}
            for (e, o, x), probability in sorted(
                _source_joint_counts(ledger, owner, source_is_anchor=False).items()
            )
        ]
        for owner in (0, 1)
    }
    coverage_complete = base["coverage_complete"] and base_b["coverage_complete"] and result["coverage_complete"] and all(
        row["v2c_coverage"] == "COMPLETE" for row in output_rows.values()
    )
    return {
        "schema_version": 1,
        "kind": "STATIC_MATERIAL_PRIOR_V2C_MAXENT_TOKEN_ENSEMBLE_CANDIDATE",
        "human_reference_imported": False,
        "human_metrics_computed": False,
        "transport_term_used": False,
        "free_density_parameter": False,
        "density_scan_used": False,
        "coverage_complete": coverage_complete,
        "classification": "STATIC_MATERIAL_PRIOR_V2C_MAXENT_TOKEN_ENSEMBLE_READY_FOR_HUMAN_VALIDATION" if coverage_complete else "STATIC_MATERIAL_PRIOR_V2C_MAXENT_TOKEN_ENSEMBLE_INCONCLUSIVE",
        "token_state_ledger": ledger,
        "board_token_count_distribution": board_pmf,
        "source_conditioned_board_token_count_distribution": source_pmf,
        "source_conditioned_non_source_square_label_counts": owner_conditioned,
        "source_conditioning": "Fix evaluated non-anchor token on board exactly once; remaining optional physical tokens retain independent fair binary states; then apply finite-population sampling without replacement over board_size-1 squares.",
        "finite_population_event_model": "For each joint (E,O,X) count, exact union of semantic occupancy cubes sampled without replacement; average over source-conditioned joint count PMF.",
        "ruleset": {
            "board_square_count": ledger["board_square_count"],
            "rho_max_inventory_reference_only": _fraction(Fraction(ledger["initial_token_count"], ledger["board_square_count"])),
            "rho_used_as_parameter": False,
        },
        "ledger": output_rows,
    }


def audit_benchmarks_v2c() -> dict[str, Any]:
    rulesets = {
        "western_chess": compile_semantic_ruleset(build_western_chess_ruleset()),
        "standard_shogi": compile_semantic_ruleset(build_standard_shogi_ruleset()),
    }
    return {
        "schema_version": 1,
        "kind": "STATIC_MATERIAL_PRIOR_V2C_MAXENT_TOKEN_ENSEMBLE_PRE_REFERENCE_FREEZE",
        "human_reference_imported": False,
        "human_metrics_computed": False,
        "transport_term_used": False,
        "free_density_parameter": False,
        "density_scan_used": False,
        "rulesets": {name: audit_ruleset_v2c(compiled) for name, compiled in rulesets.items()},
    }


def main() -> int:
    result = audit_benchmarks_v2c()
    output = ROOT / ".generic_chess_flow" / "static-semantic-material-prior-v2c-board.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "output": str(output),
        "rulesets": {
            name: {"classification": row["classification"], "coverage_complete": row["coverage_complete"],
                   "board_mean": row["board_token_count_distribution"]["mean_exact"],
                   "board_variance": row["board_token_count_distribution"]["variance_exact"]}
            for name, row in result["rulesets"].items()
        },
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
