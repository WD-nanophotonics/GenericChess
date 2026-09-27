from dataclasses import fields, replace
from typing import get_args

from generic_chess import build_western_chess_ruleset, compile_ruleset_for_execution
from generic_chess.core.actions import Action
from generic_chess.core.identity import repetition_identity_key
from generic_chess.core.movegen import legal_actions
from generic_chess.core.repetition import update_repetition_counts
from generic_chess.core.transition import initial_state
from generic_chess.rules.schema import RuleSet


def test_public_rule_and_action_schemas_have_no_opt_in_pass_variant_yet():
    rule_fields = {field.name for field in fields(RuleSet)}
    action_types = {action_type.__name__ for action_type in get_args(Action)}

    assert "pass_allowed" not in rule_fields
    assert "pass_policy" not in rule_fields
    assert action_types == {
        "BoardMove", "DropMove", "SemanticBoardMove", "SemanticDropMove"
    }

    compiled = compile_ruleset_for_execution(build_western_chess_ruleset())
    actions = legal_actions(initial_state(compiled), compiled)
    assert actions
    assert {type(action).__name__ for action in actions} <= action_types


def test_existing_position_identity_tracks_side_only_turn_changes_and_repeats():
    compiled = compile_ruleset_for_execution(build_western_chess_ruleset())
    state = initial_state(compiled)
    first = state.position
    after_one_hypothetical_pass = replace(first, side_to_move=1)
    after_two_hypothetical_passes = replace(after_one_hypothetical_pass, side_to_move=0)

    first_key = repetition_identity_key(first, compiled)
    other_side_key = repetition_identity_key(after_one_hypothetical_pass, compiled)
    returned_key = repetition_identity_key(after_two_hypothetical_passes, compiled)
    assert first.board == after_one_hypothetical_pass.board
    assert first.hands == after_one_hypothetical_pass.hands
    assert first_key != other_side_key
    assert returned_key == first_key

    counts = update_repetition_counts(((first_key, 1),), other_side_key)
    counts = update_repetition_counts(counts, returned_key)
    assert dict(counts)[first_key] == 2
