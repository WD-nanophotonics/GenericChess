"""Attribute selected ray-price changes to raw capability and roster median."""
from __future__ import annotations

import json
from dataclasses import replace

from generic_chess.ai.evaluation import EvaluationConfig
from generic_chess.ai.evaluation.analyzer import (
    build_movement_capability, profile_movement_atoms,
)
from generic_chess.ai.evaluation.config import MAX_STATIC_EVAL
from generic_chess.ai.evaluation.profile import (
    _initially_reachable_type_ids, _median, _raw_capability_score,
    build_ruleset_profile,
)
from generic_chess.core.movement import RayAtom
from generic_chess.generation.config import GeneratorConfig
from generic_chess.generation.generator import generate_game
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.schema import (
    RuleActionEffect, RuleGeometrySpec, RuleInvariant, RuleSemanticAction,
    RuleSquareRef,
)

SEEDS = tuple(range(202610431, 202610439))
DIRECTIONS = ((1, 0), (-1, 0), (0, 1), (0, -1),
              (1, 1), (1, -1), (-1, 1), (-1, -1))


def raw_by_type(compiled, config):
    values = {}
    for pt in compiled.piece_types:
        atoms = profile_movement_atoms(compiled, pt.type_id)
        cap = build_movement_capability(compiled.board_size, atoms, config)
        values[pt.type_id] = _raw_capability_score(cap, config)
    return values


def normalize(raw, median, scale):
    if median <= 0.0:
        return 1
    return max(1, min(int(round(scale * raw / median)), MAX_STATIC_EVAL))


def run_seed(seed, config):
    base_game = generate_game(GeneratorConfig(
        seed=seed, board_size=6, setup_preset="classic_like"))
    base = base_game.compiled_ruleset
    present = {p.current_type_id for row in base_game.ruleset.initial_position
               for p in row if p}
    eligible = []
    for pt in base.piece_types:
        existing = {a.direction for a in pt.movement_atoms if isinstance(a, RayAtom)}
        if (not pt.is_anchor and not pt.is_promotable and pt.type_id in present
                and pt.movement_atoms):
            eligible.extend((pt, d) for d in DIRECTIONS if d not in existing)

    base_raw = raw_by_type(base, config)
    base_reachable = _initially_reachable_type_ids(base)
    base_norm_types = [pt.type_id for pt in base.piece_types
                       if not pt.is_anchor and pt.type_id in base_reachable]
    if not base_norm_types:
        base_norm_types = [pt.type_id for pt in base.piece_types if not pt.is_anchor]
    base_median = _median([base_raw[t] for t in base_norm_types])
    scale = config.normal_piece_median_value
    rows = []
    for index, (pt, direction) in enumerate(eligible):
        name = f"ray_pair_{index:03d}"
        action = RuleSemanticAction(
            name=name, type_ids=(pt.type_id,),
            geometry=RuleGeometrySpec(kind="ray", direction=direction,
                                      min_steps=1, max_steps=3),
            target_relation="empty", composition="augment",
            effects=(RuleActionEffect("move", from_ref=RuleSquareRef("source"),
                                      to_ref=RuleSquareRef("target")),),
            invariants=(RuleInvariant("own_anchor_safe"),),
        )
        compiled = compile_ruleset_for_execution(
            replace(base_game.ruleset, semantic_actions=(action,)))
        profile = build_ruleset_profile(compiled, config)
        ray_raw = raw_by_type(compiled, config)
        # Semantic executables normalize against every declared ordinary type.
        ray_norm_types = [p.type_id for p in compiled.piece_types if not p.is_anchor]
        ray_median = _median([ray_raw[t] for t in ray_norm_types])
        selected = pt.type_id
        base_price = profile.board_value_by_type[selected]
        actual_price = profile.board_value_by_type[selected]
        # base_price is read from the independently built legacy profile below.
        base_profile = build_ruleset_profile(base, config)
        base_price = base_profile.board_value_by_type[selected]
        held_median_price = normalize(ray_raw[selected], base_median, scale)
        raw_component = held_median_price - base_price
        actual_delta = actual_price - base_price
        median_component = actual_delta - raw_component
        rows.append({
            "type_id": selected, "direction": list(direction),
            "base_raw": base_raw[selected], "ray_raw": ray_raw[selected],
            "base_median": base_median, "ray_median": ray_median,
            "base_price": base_price, "actual_price": actual_price,
            "actual_delta": actual_delta,
            "held_base_median_counterfactual_price": held_median_price,
            "raw_component_under_base_median": raw_component,
            "median_shift_component": median_component,
            "identity_holds": actual_delta == raw_component + median_component,
            "other_type_price_deltas": {
                t: profile.board_value_by_type[t] - base_profile.board_value_by_type[t]
                for t in base_profile.board_value_by_type if t != selected
            },
        })
    return rows


def main():
    config = EvaluationConfig()
    roots = [{"seed": s, "pairs": run_seed(s, config)} for s in SEEDS]
    rows = [r for root in roots for r in root["pairs"]]
    summary = {
        "roots": len(roots), "pairs": len(rows),
        "identity_failures": sum(not r["identity_holds"] for r in rows),
        "sum_raw_component": sum(r["raw_component_under_base_median"] for r in rows),
        "sum_median_shift_component": sum(r["median_shift_component"] for r in rows),
        "sum_actual_delta": sum(r["actual_delta"] for r in rows),
        "median_component_signs": {
            "negative": sum(r["median_shift_component"] < 0 for r in rows),
            "zero": sum(r["median_shift_component"] == 0 for r in rows),
            "positive": sum(r["median_shift_component"] > 0 for r in rows),
        },
        "limitations": "Exact algebraic attribution on the frozen 8 roots/127 absent rays; holding the baseline median is a decomposition, not a calibrated alternative evaluator. No utility/outcomes/search/training claim.",
    }
    print(json.dumps({"question": "How much selected normalized ray price comes from raw capability versus roster-median shift?", "summary": summary, "roots": roots}, indent=2))


if __name__ == "__main__":
    main()
