from dataclasses import replace

import pytest

from generic_chess.core.movement import LeapAtom
from generic_chess.core.pieces import Piece, PieceType
from generic_chess.rules.compiler import compile_semantic_ruleset
from generic_chess.rules.schema import (
    RuleActionEffect,
    RuleGeometrySpec,
    RuleSemanticAction,
    RuleSet,
    RuleSquareRef,
)
from generic_chess.rules.standard_shogi import build_standard_shogi_ruleset
from generic_chess.rules.western_chess import build_western_chess_ruleset
from scripts.audit_static_semantic_material_prior_v2 import (
    _promotion_forced,
    _promotion_targets,
    audit_ruleset,
    expected_action_probability,
    expected_drop_option_count,
)


def _compiled_synthetic(*, name="base", shapes=((1, 0),), relations=("empty",)):
    size = 8
    anchor_steps = tuple(
        LeapAtom((df, dr))
        for df in (-1, 0, 1)
        for dr in (-1, 0, 1)
        if (df, dr) != (0, 0)
    )
    rows = [[None for _ in range(size)] for _ in range(size)]
    rows[0][0] = Piece(0, "K", "K", False)
    rows[-1][-1] = Piece(1, "K", "K", False)
    actions = []
    for index, relation in enumerate(relations):
        effects = [RuleActionEffect(
            "move", from_ref=RuleSquareRef("source"), to_ref=RuleSquareRef("target"),
        )]
        if relation == "enemy":
            effects.insert(0, RuleActionEffect(
                "remove", square_ref=RuleSquareRef("target"),
                disposition="remove_from_game", piece_owner="opponent",
            ))
        actions.append(RuleSemanticAction(
            name=f"{name}_{relation}_{index}", type_ids=("X",),
            geometry=RuleGeometrySpec(kind="leap", offset=shapes[index % len(shapes)]),
            target_relation=relation, effects=tuple(effects),
        ))
    ruleset = RuleSet(
        board_size=size,
        piece_types=(PieceType("K", "Anchor", anchor_steps, is_anchor=True), PieceType("X", name, ())),
        initial_position=tuple(tuple(row) for row in rows),
        drop_allowed={"X": ((False,) * (size * size), (False,) * (size * size))},
        semantic_actions=tuple(actions),
    )
    return ruleset, compile_semantic_ruleset(ruleset)


def test_local_option_probability_uses_exact_path_and_endpoint_measure():
    assert expected_action_probability((), "target_empty") == pytest.approx(1 / 3)
    assert expected_action_probability((3, 4), "target_enemy") == pytest.approx(1 / 27)
    assert expected_action_probability((), "target_any") == pytest.approx(1.0)
    assert expected_action_probability((), "unknown") is None


def test_unsupported_path_predicate_fails_closed():
    class Predicate:
        kind = "path_count_eq"

    assert expected_action_probability((1,), "target_empty", (Predicate(),)) is None


def test_piece_id_rename_changes_only_ledger_keys():
    ruleset, compiled = _compiled_synthetic()
    renamed_types = tuple(
        replace(piece_type, type_id="Y") if piece_type.type_id == "X" else piece_type
        for piece_type in ruleset.piece_types
    )
    renamed_actions = tuple(
        replace(action, type_ids=tuple("Y" if tid == "X" else tid for tid in action.type_ids))
        for action in ruleset.semantic_actions
    )
    renamed_drop = {"Y": ruleset.drop_allowed["X"]}
    renamed = compile_semantic_ruleset(replace(
        ruleset,
        piece_types=renamed_types,
        semantic_actions=renamed_actions,
        drop_allowed=renamed_drop,
    ))
    base_row = audit_ruleset(compiled)["ledger"]["X"]
    renamed_row = audit_ruleset(renamed)["ledger"]["Y"]
    assert renamed_row["board_intrinsic"] == pytest.approx(base_row["board_intrinsic"])
    assert renamed_row["hand_drop"] == pytest.approx(base_row["hand_drop"])


def test_owner_mirror_leaves_intrinsic_measure_unchanged():
    ruleset, compiled = _compiled_synthetic()
    mirrored_position = tuple(
        tuple(replace(piece, owner=1 - piece.owner) if piece is not None else None for piece in row)
        for row in ruleset.initial_position
    )
    mirrored = compile_semantic_ruleset(replace(ruleset, initial_position=mirrored_position))
    base_row = audit_ruleset(compiled)["ledger"]["X"]
    mirror_row = audit_ruleset(mirrored)["ledger"]["X"]
    assert mirror_row["board_intrinsic"] == pytest.approx(base_row["board_intrinsic"])


def test_adding_executable_movement_cannot_reduce_board_component():
    _, base = _compiled_synthetic()
    _, expanded = _compiled_synthetic(
        name="expanded", shapes=((1, 0), (0, 1)), relations=("empty", "enemy"),
    )
    base_score = audit_ruleset(base)["ledger"]["X"]["board_intrinsic"]
    expanded_score = audit_ruleset(expanded)["ledger"]["X"]["board_intrinsic"]
    assert expanded_score >= base_score


def test_drop_component_is_monotone_in_valid_drop_freedom():
    one_owner = (True, False, False, False)
    two_owners = (one_owner, one_owner)
    expanded = ((True, True, False, False), (True, True, False, False))
    assert expected_drop_option_count(expanded) >= expected_drop_option_count(two_owners)


def test_western_pawn_has_semantic_value_and_promotion_ledger():
    compiled = compile_semantic_ruleset(build_western_chess_ruleset())
    result = audit_ruleset(compiled)
    pawn = result["ledger"]["P"]
    assert pawn["board_intrinsic"] > 0.0
    assert pawn["promotion_transitions"]
    assert result["classification"] == "STATIC_SEMANTIC_MATERIAL_PRIOR_V2_INCONCLUSIVE"
    assert any(row["pattern"].startswith("en_passant") for row in pawn["conditional_rules"])
    assert "pawn_double_step" not in {row["pattern"] for row in pawn["unsupported_semantics"]}
    assert any(row["effect"] == "set_token" for row in pawn["state_transition_effects"])


def test_beneficial_reachable_promotion_branch_cannot_reduce_option_count():
    ruleset = build_western_chess_ruleset()
    no_promotion_actions = tuple(
        replace(action, promotion_mode="none")
        if "P" in action.type_ids and action.name in {
            "pawn_one_step", "pawn_capture_right", "pawn_capture_left",
        }
        else action
        for action in ruleset.semantic_actions
    )
    no_promotion = compile_semantic_ruleset(replace(ruleset, semantic_actions=no_promotion_actions))
    with_promotion = compile_semantic_ruleset(ruleset)
    base = audit_ruleset(no_promotion)["ledger"]["P"]["board_intrinsic"]
    promoted = audit_ruleset(with_promotion)["ledger"]["P"]["board_intrinsic"]
    assert promoted >= base


def test_promotion_masks_are_owner_specific():
    compiled = compile_semantic_ruleset(build_western_chess_ruleset())
    source_square, target_square = next(iter(compiled.support.promotion_allowed["P"][0]))
    assert (source_square, target_square) not in compiled.support.promotion_allowed["P"][1]
    n = compiled.board_size
    source = source_square.rank * n + source_square.file
    target = target_square.rank * n + target_square.file
    destinations = compiled.support.type_metadata["P"].promotion_target_ids
    assert _promotion_targets(compiled, "P", 0, source, target) == destinations
    assert _promotion_targets(compiled, "P", 1, source, target) == ()

    forced_square = next(iter(compiled.support.promotion_forced["P"][0]))
    assert forced_square not in compiled.support.promotion_forced["P"][1]
    forced_target = forced_square.rank * n + forced_square.file
    assert _promotion_forced(compiled, "P", 0, forced_target)
    assert not _promotion_forced(compiled, "P", 1, forced_target)


@pytest.mark.parametrize(
    "ruleset",
    [build_western_chess_ruleset(), build_standard_shogi_ruleset()],
)
def test_real_rulesets_report_not_silently_zeroed_semantics(ruleset):
    result = audit_ruleset(compile_semantic_ruleset(ruleset))
    assert result["human_metrics_computed"] is False
    assert (result["unsupported_semantics"] or result["state_dependent_semantics"]
            or result["coverage_complete"])
    for row in result["ledger"].values():
        assert "unsupported_semantics" in row
        assert "conditional_rules" in row
        assert row["board_intrinsic"] >= 0.0
