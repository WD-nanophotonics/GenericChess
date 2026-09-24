from dataclasses import replace
from fractions import Fraction
from pathlib import Path
import ast
import sys

from generic_chess.core.pieces import Piece
from generic_chess.rules.compiler import compile_semantic_ruleset
from generic_chess.rules.schema import RuleSquareRef
from generic_chess.rules.standard_shogi import build_standard_shogi_ruleset
from generic_chess.rules.western_chess import build_western_chess_ruleset
from scripts.audit_static_semantic_material_prior_v2c import _event_measure_factory, _token_state_ledger, audit_ruleset_v2c
from scripts.audit_static_semantic_material_prior_v2d import (
    _add_capture_group,
    _capture_rows,
    capture_group_probabilities,
    combine_u_c,
    resolve_removed_square,
)
from tests.test_static_semantic_material_prior_v2a import _synthetic

ROOT = Path(__file__).resolve().parents[1]


def _with_initial_x_tokens(rules):
    board = [list(row) for row in rules.initial_position]
    board[2][2] = Piece(0, "X", "X", False)
    board[5][5] = Piece(1, "X", "X", False)
    return replace(rules, initial_position=tuple(tuple(row) for row in board))


def _synthetic_capture(*, relations=("enemy",), shapes=((1, 0),), disposition="remove_from_game",
                       square_ref=None, removal_owner="opponent"):
    rules, _ = _synthetic(relations=relations, shapes=shapes)
    actions = []
    for action in rules.semantic_actions:
        effects = tuple(replace(effect,
            square_ref=square_ref if square_ref is not None and effect.kind == "remove" else effect.square_ref,
            disposition=disposition if effect.kind == "remove" else effect.disposition,
            piece_owner=removal_owner if effect.kind == "remove" else effect.piece_owner)
            for effect in action.effects)
        actions.append(replace(action, effects=effects))
    return _with_initial_x_tokens(replace(rules, semantic_actions=tuple(actions)))


def _capture_audit(rules):
    compiled = compile_semantic_ruleset(rules)
    inventory = _token_state_ledger(compiled)
    measure = _event_measure_factory(inventory, compiled, "X")
    return compiled, _capture_rows(compiled, "X", measure)


def test_quiet_only_has_no_capture_affordance_and_m_equals_u():
    rules, _ = _synthetic(relations=("empty",))
    rules = _with_initial_x_tokens(rules)
    _compiled, result = _capture_audit(rules)
    u = Fraction(17, 13)
    c = Fraction(result["capture_affordance_exact"])
    assert c == 0
    assert combine_u_c(u, c) == u


def test_one_always_true_physical_capture_group_has_one_unit_probability():
    groups = {}
    cube = ((7, ("enemy",)),)
    _add_capture_group(groups, (0, 3, 7), cube, pattern_name="cap", disposition="remove_from_game",
                       promotion_choices=("X",))
    probabilities = capture_group_probabilities(groups, type_id="X",
        event_measure=lambda owner, _type, cubes: Fraction(int(cube in cubes)))
    assert probabilities == {(0, 3, 7): Fraction(1)}


def test_duplicate_semantic_capture_descriptions_and_promotions_union_once():
    groups = {}
    cube = ((7, ("enemy",)),)
    for name, choice in (("cap", "X"), ("cap_promotion", "Y")):
        _add_capture_group(groups, (0, 3, 7), cube, pattern_name=name,
                           disposition="remove_from_game", promotion_choices=(choice,))
    probability = capture_group_probabilities(groups, type_id="X",
        event_measure=lambda _owner, _type, cubes: Fraction(1, 2) if cube in cubes else Fraction(0))
    row = groups[(0, 3, 7)]
    assert len(probability) == 1 and probability[(0, 3, 7)] == Fraction(1, 2)
    assert len(set(row["cubes"])) == 1
    assert row["promotion_choices"] == {"X", "Y"}


def test_distinct_removed_squares_are_distinct_affordances_and_cannot_reduce_total():
    groups = {}
    cube1, cube2 = ((7, ("enemy",)),), ((9, ("enemy",)),)
    _add_capture_group(groups, (0, 3, 7), cube1, pattern_name="c1", disposition="remove_from_game", promotion_choices=("X",))
    one = capture_group_probabilities(groups, type_id="X", event_measure=lambda *_: Fraction(1))
    _add_capture_group(groups, (0, 3, 9), cube2, pattern_name="c2", disposition="capture_to_hand", promotion_choices=("X",))
    two = capture_group_probabilities(groups, type_id="X", event_measure=lambda *_: Fraction(1))
    assert len(one) == 1 and len(two) == 2
    assert sum(two.values()) >= sum(one.values())


def test_duplicate_patterns_do_not_double_count_but_new_quiet_move_changes_only_u():
    duplicate_rules = _synthetic_capture(relations=("enemy", "enemy"), shapes=((1, 0), (1, 0)))
    _compiled, duplicate = _capture_audit(duplicate_rules)
    assert duplicate["capture_coverage_complete"]
    assert all(len(row["semantic_patterns"]) == 2 for row in duplicate["capture_affordance_event_ledger"])

    capture_only = _synthetic_capture(relations=("enemy",))
    with_quiet = _synthetic_capture(relations=("enemy", "empty"), shapes=((1, 0), (0, 1)))
    compiled1, capture1 = _capture_audit(capture_only)
    compiled2, capture2 = _capture_audit(with_quiet)
    u1 = Fraction(audit_ruleset_v2c(compiled1)["ledger"]["X"]["v2c_exact"])
    u2 = Fraction(audit_ruleset_v2c(compiled2)["ledger"]["X"]["v2c_exact"])
    assert Fraction(capture1["capture_affordance_exact"]) == Fraction(capture2["capture_affordance_exact"])
    assert u2 > u1


def test_remove_from_game_and_capture_to_hand_count_board_removal_only():
    remove_compiled = compile_semantic_ruleset(_synthetic_capture(disposition="remove_from_game"))
    hand_compiled = compile_semantic_ruleset(_synthetic_capture(disposition="capture_to_hand"))
    deterministic_measure = lambda _owner, _type, cubes: Fraction(bool(cubes))
    remove_game = _capture_rows(remove_compiled, "X", deterministic_measure)
    to_hand = _capture_rows(hand_compiled, "X", deterministic_measure)
    assert Fraction(remove_game["capture_affordance_exact"]) == Fraction(to_hand["capture_affordance_exact"])
    assert to_hand["capture_dispositions_observed"] == ["capture_to_hand"]


def test_off_target_effect_uses_actual_removed_square_not_move_target():
    ref = RuleSquareRef(kind="offset_from_source", offset=(0, 1))
    rules = _synthetic_capture(square_ref=ref)
    _compiled, result = _capture_audit(rules)
    rows = result["capture_affordance_event_ledger"]
    assert rows
    assert all(row["removed_square"] == row["source_square"] + 8 for row in rows if row["owner"] == 0)

    resolved = resolve_removed_square(RuleSquareRef(kind="path_step", step=0), owner=0,
        source=10, target=14, path=(11, 12, 13), area_width=8)
    assert resolved == 11


def test_self_removal_and_state_effects_are_never_counted_as_opponent_capture():
    _compiled, result = _capture_audit(_synthetic_capture(removal_owner="self"))
    assert result["capture_affordance_exact"] == "0/1"
    assert result["excluded_nonopponent_removals"]


def test_capture_type_rename_and_owner_mirror_preserve_c():
    rules = _synthetic_capture()
    compiled, baseline = _capture_audit(rules)
    value = baseline["capture_affordance_exact"]

    mirrored_position = tuple(tuple(
        replace(piece, owner=1 - piece.owner) if piece is not None else None for piece in row
    ) for row in rules.initial_position)
    mirrored = compile_semantic_ruleset(replace(rules, initial_position=mirrored_position))
    mirrored_result = _capture_rows(mirrored, "X", _event_measure_factory(_token_state_ledger(mirrored), mirrored, "X"))
    assert mirrored_result["capture_affordance_exact"] == value

    renamed_types = tuple(replace(row, type_id="Y") if row.type_id == "X" else row for row in rules.piece_types)
    renamed_actions = tuple(replace(row, type_ids=tuple("Y" if tid == "X" else tid for tid in row.type_ids))
                            for row in rules.semantic_actions)
    renamed_position = tuple(tuple(
        replace(piece, base_type_id="Y", current_type_id="Y")
        if piece is not None and piece.current_type_id == "X" else piece for piece in row
    ) for row in rules.initial_position)
    renamed_rules = replace(rules, piece_types=renamed_types, semantic_actions=renamed_actions,
                            initial_position=renamed_position, drop_allowed={"Y": rules.drop_allowed["X"]})
    renamed = compile_semantic_ruleset(renamed_rules)
    renamed_result = _capture_rows(renamed, "Y", _event_measure_factory(_token_state_ledger(renamed), renamed, "Y"))
    assert renamed_result["capture_affordance_exact"] == value


def test_history_only_en_passant_capture_is_ledgered_but_excluded():
    compiled = compile_semantic_ruleset(build_western_chess_ruleset())
    ledger = _token_state_ledger(compiled)
    result = _capture_rows(compiled, "P", _event_measure_factory(ledger, compiled, "P"))
    rows = result["excluded_history_conditioned_capture_rows"]
    assert any(row["classification"] == "history_or_auxiliary_state_excluded_no_stationary_prior"
               and row["resolved_removed_square_indices"] for row in rows)
    history_names = {row["pattern"] for row in rows}
    assert all(not (history_names & set(row["semantic_patterns"]))
               for row in result["capture_affordance_event_ledger"])


def test_shogi_capture_to_hand_is_board_removal_without_hand_bonus_and_no_reference_imports():
    compiled = compile_semantic_ruleset(build_standard_shogi_ruleset())
    ledger = _token_state_ledger(compiled)
    result = _capture_rows(compiled, "P", _event_measure_factory(ledger, compiled, "P"))
    assert result["capture_dispositions_observed"] == ["capture_to_hand"]
    assert result["capture_affordance"] > 0
    assert "held_drop" not in result

    tree = ast.parse((ROOT / "scripts/audit_static_semantic_material_prior_v2d.py").read_text(encoding="utf-8"))
    imported = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            imported.append(node.module or "")
    assert not any("validate_static_material" in name or name.startswith("tests.fixtures")
                   or "transport_efficiency" in name for name in imported)
