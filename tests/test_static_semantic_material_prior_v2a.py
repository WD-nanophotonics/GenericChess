from dataclasses import replace
from fractions import Fraction
from pathlib import Path
import sys
from types import SimpleNamespace

import pytest

from generic_chess.core.movement import LeapAtom
from generic_chess.core.pieces import Piece, PieceType
from generic_chess.rules.compiler import compile_semantic_ruleset
from generic_chess.rules.schema import RuleActionEffect, RuleGeometrySpec, RuleSemanticAction, RuleSet, RuleSquareRef
from generic_chess.rules.standard_shogi import build_standard_shogi_ruleset
from generic_chess.rules.western_chess import build_western_chess_ruleset
from scripts.audit_static_semantic_material_prior_v2a import (
    _inventory_bound,
    audit_ruleset_v2a,
    event_probability,
    integrate_density_polynomial,
    union_probability_polynomial,
)
from scripts.audit_static_semantic_material_prior_v2 import _promotion_forced, _promotion_targets


def _cube(path=(), target=("empty",)):
    return tuple(sorted(
        [(square, ("empty",)) for square in set(path)]
        + ([(99, tuple(sorted(target)))] if set(target) != {"empty", "own", "enemy"} else [])
    ))


def _synthetic(*, name="X", owner_mirror=False, shapes=((1, 0),), relations=("empty",)):
    size = 8
    anchors = tuple(
        LeapAtom((df, dr))
        for df in (-1, 0, 1) for dr in (-1, 0, 1) if df or dr
    )
    rows = [[None for _ in range(size)] for _ in range(size)]
    rows[0][0] = Piece(0 if not owner_mirror else 1, "K", "K", False)
    rows[-1][-1] = Piece(1 if not owner_mirror else 0, "K", "K", False)
    actions = []
    for index, relation in enumerate(relations):
        effects = [RuleActionEffect("move", from_ref=RuleSquareRef("source"), to_ref=RuleSquareRef("target"))]
        if relation == "enemy":
            effects.insert(0, RuleActionEffect("remove", square_ref=RuleSquareRef("target"),
                                               disposition="remove_from_game", piece_owner="opponent"))
        actions.append(RuleSemanticAction(
            name=f"{name}_{relation}_{index}", type_ids=(name,),
            geometry=RuleGeometrySpec(kind="ray" if len(shapes[index % len(shapes)]) == 3 else "leap",
                                      direction=shapes[index % len(shapes)] if len(shapes[index % len(shapes)]) == 3 else None,
                                      min_steps=1 if len(shapes[index % len(shapes)]) == 3 else None,
                                      max_steps=3 if len(shapes[index % len(shapes)]) == 3 else None,
                                      offset=shapes[index % len(shapes)] if len(shapes[index % len(shapes)]) == 2 else None),
            target_relation=relation, effects=tuple(effects),
        ))
    rules = RuleSet(
        board_size=size,
        piece_types=(PieceType("K", "Anchor", anchors, is_anchor=True), PieceType(name, name, ())),
        initial_position=tuple(tuple(row) for row in rows),
        drop_allowed={name: ((False,) * 64, (False,) * 64)},
        semantic_actions=tuple(actions),
    )
    return rules, compile_semantic_ruleset(rules)


def test_closed_form_phase_integrals_for_leap_and_ray_events():
    rho_max = Fraction(1, 2)
    assert event_probability(_cube(), rho_max) == Fraction(3, 4)  # quiet leap
    assert event_probability(_cube(target=("enemy",)), rho_max) == Fraction(1, 8)  # capture leap
    assert event_probability(_cube(path=(1,), target=("empty",)), rho_max) == Fraction(7, 12)
    assert event_probability(_cube(path=(1,), target=("enemy",)), rho_max) == Fraction(1, 12)


def test_shared_density_union_is_integrated_after_conditional_union():
    # E1=empty and E2=own on the same square are disjoint and together have
    # probability 1-rho/2.  Independently averaging then multiplying is wrong.
    poly = union_probability_polynomial([_cube(target=("empty",)), _cube(target=("own",))])
    assert poly == (Fraction(1), Fraction(-1, 2))
    assert integrate_density_polynomial(poly, Fraction(1, 2)) == Fraction(7, 8)


def test_zero_density_limit_restores_path_clear_quiet_ray_capability():
    assert event_probability(_cube(path=(1, 2, 3), target=("empty",)), Fraction(0)) == 1


def test_more_density_cannot_increase_path_clear_quiet_ray_mass():
    cube = _cube(path=(1, 2, 3), target=("empty",))
    assert event_probability(cube, Fraction(1, 2)) < event_probability(cube, Fraction(1, 4))


def test_identical_successor_events_are_unioned_not_double_counted():
    cube = _cube(path=(1,), target=("empty",))
    assert event_probability(cube, Fraction(1, 2)) == event_probability(cube, Fraction(1, 2))
    assert union_probability_polynomial([cube, cube]) == union_probability_polynomial([cube])


def test_type_rename_does_not_change_rule_only_score():
    rules, compiled = _synthetic()
    renamed_types = tuple(replace(row, type_id="Y") if row.type_id == "X" else row for row in rules.piece_types)
    renamed_actions = tuple(replace(row, type_ids=("Y",)) for row in rules.semantic_actions)
    renamed = compile_semantic_ruleset(replace(
        rules, piece_types=renamed_types, semantic_actions=renamed_actions,
        drop_allowed={"Y": rules.drop_allowed["X"]},
    ))
    assert audit_ruleset_v2a(compiled)["ledger"]["X"]["v2a_raw_exact"] == audit_ruleset_v2a(renamed)["ledger"]["Y"]["v2a_raw_exact"]


def test_owner_mirror_does_not_change_rule_only_score():
    rules, compiled = _synthetic()
    mirrored_position = tuple(tuple(
        replace(piece, owner=1 - piece.owner) if piece is not None else None for piece in row
    ) for row in rules.initial_position)
    mirrored = compile_semantic_ruleset(replace(rules, initial_position=mirrored_position))
    assert audit_ruleset_v2a(compiled)["ledger"]["X"]["v2a_raw_exact"] == audit_ruleset_v2a(mirrored)["ledger"]["X"]["v2a_raw_exact"]


def test_adding_executable_action_cannot_reduce_intrinsic_option_value():
    _, one = _synthetic(name="X", shapes=((1, 0),), relations=("empty",))
    _, two = _synthetic(name="X", shapes=((1, 0), (0, 1)), relations=("empty", "enemy"))
    base = audit_ruleset_v2a(one)["ledger"]["X"]["v2a_phase_averaged_board_intrinsic"]
    expanded = audit_ruleset_v2a(two)["ledger"]["X"]["v2a_phase_averaged_board_intrinsic"]
    assert expanded >= base


def test_real_rulesets_have_bounded_inventory_and_no_unmodeled_creation():
    chess = audit_ruleset_v2a(compile_semantic_ruleset(build_western_chess_ruleset()))
    shogi = audit_ruleset_v2a(compile_semantic_ruleset(build_standard_shogi_ruleset()))
    assert chess["inventory_bound"]["initial_token_count"] == 32
    assert chess["inventory_bound"]["rho_max"] == "1/2"
    assert shogi["inventory_bound"]["initial_token_count"] == 40
    assert shogi["inventory_bound"]["rho_max"] == "40/81"
    assert chess["inventory_bound"]["complete"] and shogi["inventory_bound"]["complete"]
    for result in (chess, shogi):
        for row in result["ledger"].values():
            assert row["fixed_three_label_reproduction"]["absolute_difference"] < 1e-12


def test_promotion_masks_remain_owner_specific_under_v2a():
    compiled = compile_semantic_ruleset(build_western_chess_ruleset())
    source_square, target_square = next(iter(compiled.support.promotion_allowed["P"][0]))
    source = source_square.rank * compiled.board_size + source_square.file
    target = target_square.rank * compiled.board_size + target_square.file
    assert _promotion_targets(compiled, "P", 0, source, target)
    assert not _promotion_targets(compiled, "P", 1, source, target)
    forced_square = next(iter(compiled.support.promotion_forced["P"][0]))
    forced_target = forced_square.rank * compiled.board_size + forced_square.file
    assert _promotion_forced(compiled, "P", 0, forced_target)
    assert not _promotion_forced(compiled, "P", 1, forced_target)


def test_own_anchor_safety_is_ledgered_but_not_a_board_score_blocker():
    result = audit_ruleset_v2a(compile_semantic_ruleset(build_western_chess_ruleset()))
    pawn = result["ledger"]["P"]
    assert pawn["dynamic_positional_legality_ledger_count"] > 0
    assert pawn["dynamic_positional_legality_reason"] == "global positional legality; excluded from intrinsic piece-type material prior"
    assert pawn["v2a_coverage"] == "COMPLETE"


def test_shogi_pawn_drop_rules_are_ledgered_not_claimed_as_modeled():
    result = audit_ruleset_v2a(compile_semantic_ruleset(build_standard_shogi_ruleset()))
    pawn = result["ledger"]["P"]
    assert pawn["held_drop_semantics_ledger_count"] > 0
    assert pawn["held_drop_special_rows"]
    assert any(row["postconditions"] for row in pawn["held_drop_special_rows"])
    assert pawn["components"]["held_drop"] == 0.0


def test_no_human_reference_modules_are_imported_by_candidate():
    from scripts import audit_static_semantic_material_prior_v2a as candidate
    source = Path(candidate.__file__).read_text(encoding="utf-8")
    assert "human material" not in source.lower()
    assert not any(name.startswith("tests.fixtures") and "material" in name for name in sys.modules)


def test_unknown_inventory_effect_fails_closed():
    effect = SimpleNamespace(kind="spawn_piece", disposition=None)
    pattern = SimpleNamespace(name="bad", effects=(effect,), geometry_ids=(0,))
    compiled = SimpleNamespace(
        ir=SimpleNamespace(patterns=(pattern,), geometry={0: SimpleNamespace(kind="leap")}),
        support=SimpleNamespace(initial_position=((object(), None),)),
    )
    result = _inventory_bound(compiled)
    assert not result["complete"]
    assert any("unrecognized_effect" in reason for reason in result["failure_reasons"])
