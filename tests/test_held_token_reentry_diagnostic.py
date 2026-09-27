from dataclasses import replace

import pytest

from generic_chess.core.actions import action_is_board
from generic_chess.core.coordinates import square_to_index
from generic_chess.core.movement import LeapAtom
from generic_chess.core.pieces import Piece, PieceType
from generic_chess.core.transition import apply_action
from generic_chess.rules.compiler import compile_semantic_ruleset
from generic_chess.rules.schema import (
    RuleActionEffect,
    RuleGeometrySpec,
    RuleInvariant,
    RuleReplaceSelector,
    RuleSemanticAction,
    RuleSet,
    RuleSpatialSelector,
    RuleSquareRef,
    RuleStateGuard,
    RuleTypeRef,
)
from generic_chess.core.movegen import legal_actions

from scripts.diagnose_held_token_reentry import reentry_successor_state_keys
from conftest import make_state, sq


def _king_type(type_id="K"):
    return PieceType(
        type_id,
        type_id,
        tuple(LeapAtom((df, dr)) for df in (-1, 0, 1) for dr in (-1, 0, 1) if df or dr),
        is_anchor=True,
    )


def _capture_probe(
    *, disposition="capture_to_hand", allowed_drop_squares=(),
    duplicate_drop_pattern=False, pawn_id="P", attacker_id="R", nifu=False, owner=0,
):
    size = 8
    all_squares = size * size
    allowed = set(allowed_drop_squares)
    masks = (
        tuple(index in allowed for index in range(all_squares)),
        tuple(
            (index % size) + (size - 1 - index // size) * size in allowed
            for index in range(all_squares)
        ),
    )
    king = _king_type()
    pawn = PieceType(pawn_id, pawn_id, ())
    rook = PieceType(attacker_id, attacker_id, ())
    capture = RuleSemanticAction(
        name="capture_probe",
        type_ids=(attacker_id,),
        geometry=RuleGeometrySpec(kind="leap", offset=(0, 1), owner_relative=True),
        target_relation="enemy",
        composition="augment",
        effects=(
            RuleActionEffect(
                "remove", square_ref=RuleSquareRef("target"), disposition=disposition,
                piece_owner="opponent",
            ),
            RuleActionEffect("move", from_ref=RuleSquareRef("source"), to_ref=RuleSquareRef("target")),
        ),
        invariants=(RuleInvariant("own_anchor_safe"),),
    )
    drop_effects = (
        RuleActionEffect("remove_from_hand", piece_type_ref=RuleTypeRef(kind="action_base")),
        RuleActionEffect("place", to_ref=RuleSquareRef("target"),
                         piece_type_ref=RuleTypeRef(kind="action_base")),
    )
    guard = ()
    if nifu:
        guard = (RuleStateGuard(
            aggregation="count", owner="self", type_ref=RuleTypeRef(kind="action_base"),
            compare_field="base", promoted="no", location="board",
            spatial=RuleSpatialSelector(kind="same_file", refs=(RuleSquareRef("target"),)),
            comparison="eq", value=0,
        ),)
    drop_actions = [RuleSemanticAction(
        name="drop_probe",
        type_ids=(pawn_id,),
        geometry=RuleGeometrySpec(kind="drop"),
        target_relation="empty",
        composition="replace_legacy",
        replace_selector=RuleReplaceSelector(
            type_ids=(pawn_id,), action_family="drop", target_relation="empty",
        ),
        state_guards=guard,
        effects=drop_effects,
        invariants=(RuleInvariant("own_anchor_safe"),),
    )]
    if duplicate_drop_pattern:
        drop_actions.append(replace(drop_actions[0], name="equivalent_drop_probe"))

    rows = [[None for _ in range(size)] for _ in range(size)]
    rows[0][0] = Piece(0, "K", "K")
    rows[-1][-1] = Piece(1, "K", "K")
    drop_allowed = {pawn_id: masks, attacker_id: ((False,) * all_squares,) * 2}
    ruleset = RuleSet(
        board_size=size,
        piece_types=(king, pawn, rook),
        initial_position=tuple(tuple(row) for row in rows),
        drop_allowed=drop_allowed,
        semantic_actions=(capture, *drop_actions),
    )
    compiled = compile_semantic_ruleset(ruleset)

    lines = ["........" for _ in range(size)]
    lines[0] = ".......k"
    lines[-1] = "K......."
    actor_file = 1
    actor_rank = 1
    victim_rank = 2
    lines[size - 1 - actor_rank] = "." + attacker_id + "......"
    lines[size - 1 - victim_rank] = "." + pawn_id.lower() + "......"
    if nifu:
        lines[size - 1 - 1] = "." + attacker_id + "." + pawn_id + "...."
    if owner == 1:
        # Reflect the fixture vertically and swap ownership, preserving the
        # owner-relative capture geometry and the same rule consequences.
        lines = list(reversed(lines))
        lines = [line.swapcase() for line in lines]
        actor_rank = size - 1 - actor_rank
        victim_rank = size - 1 - victim_rank
    state = make_state(compiled, lines, side_to_move=owner)
    return compiled, state, actor_file, actor_rank, victim_rank, pawn_id


def _capture(compiled, state, file, actor_rank, victim_rank):
    actions = legal_actions(state, compiled)
    action = next(
        action for action in actions
        if action_is_board(action)
        and action.from_square == sq(file, actor_rank)
        and action.to_square == sq(file, victim_rank)
    )
    return action, apply_action(state, action, compiled)


def _probe(compiled, state, file, actor_rank, victim_rank, pawn_id):
    action, after = _capture(compiled, state, file, actor_rank, victim_rank)
    states = reentry_successor_state_keys(
        state.position, after.position, compiled, state.position.side_to_move
    )
    return action, after, states


def test_capture_to_hand_and_remove_from_game_have_separate_reentry_outcomes():
    square = square_to_index(sq(3, 3), 8)
    hand_rules, hand_state, file, actor_rank, victim_rank, pawn_id = _capture_probe(
        allowed_drop_squares=(square,),
    )
    hand_action, hand_after, hand_states = _probe(
        hand_rules, hand_state, file, actor_rank, victim_rank, pawn_id
    )
    remove_rules, remove_state, file, actor_rank, victim_rank, pawn_id = _capture_probe(
        disposition="remove_from_game", allowed_drop_squares=(square,),
    )
    _, remove_after, remove_states = _probe(
        remove_rules, remove_state, file, actor_rank, victim_rank, pawn_id
    )

    assert hand_action in legal_actions(hand_state, hand_rules)
    assert hand_after.position.board == remove_after.position.board
    assert hand_after.position.board[square_to_index(sq(file, victim_rank), 8)] is not None
    assert remove_after.position.board[square_to_index(sq(file, victim_rank), 8)] is not None
    assert hand_after.position.hands[0].count(pawn_id) == 1
    assert remove_after.position.hands[0].count(pawn_id) == 0
    assert len(hand_states[pawn_id]) == 1
    assert remove_states == {}


@pytest.mark.parametrize(
    "destinations, expected",
    [([], 0), ([(3, 3)], 1), ([(2, 3), (3, 3), (4, 3)], 3)],
)
def test_reentry_successor_set_tracks_distinct_legal_destinations(destinations, expected):
    indices = tuple(square_to_index(sq(file, rank), 8) for file, rank in destinations)
    compiled, state, file, actor_rank, victim_rank, pawn_id = _capture_probe(
        allowed_drop_squares=indices,
    )
    _, _, states = _probe(compiled, state, file, actor_rank, victim_rank, pawn_id)
    assert len(states[pawn_id]) == expected


def test_adding_unique_legal_destinations_strictly_expands_the_normalized_set():
    first = (square_to_index(sq(2, 3), 8),)
    expanded = tuple(square_to_index(sq(file, 3), 8) for file in (2, 3, 4))
    first_rules, first_state, file, actor_rank, victim_rank, pawn_id = _capture_probe(
        allowed_drop_squares=first,
    )
    _, _, first_result = _probe(
        first_rules, first_state, file, actor_rank, victim_rank, pawn_id
    )
    expanded_rules, expanded_state, file, actor_rank, victim_rank, pawn_id = _capture_probe(
        allowed_drop_squares=expanded,
    )
    _, _, expanded_result = _probe(
        expanded_rules, expanded_state, file, actor_rank, victim_rank, pawn_id
    )
    first_targets = {target for target, _key in first_result[pawn_id]}
    expanded_targets = {target for target, _key in expanded_result[pawn_id]}
    assert first_targets < expanded_targets


def test_equivalent_drop_descriptions_collapse_to_the_same_successor_states():
    indices = tuple(square_to_index(sq(file, 3), 8) for file in (2, 3, 4))
    compiled, state, file, actor_rank, victim_rank, pawn_id = _capture_probe(
        allowed_drop_squares=indices, duplicate_drop_pattern=True,
    )
    _, _, states = _probe(compiled, state, file, actor_rank, victim_rank, pawn_id)
    assert len(states[pawn_id]) == len(indices)


def test_legal_drop_restrictions_remove_same_file_destinations():
    indices = tuple(square_to_index(sq(file, 3), 8) for file in (2, 3, 4))
    compiled, state, file, actor_rank, victim_rank, pawn_id = _capture_probe(
        allowed_drop_squares=indices, nifu=True,
    )
    _, after, _ = _probe(compiled, state, file, actor_rank, victim_rank, pawn_id)
    result = reentry_successor_state_keys(
        state.position, after.position, compiled, state.position.side_to_move
    )
    assert len(result[pawn_id]) == 2
    assert {target % 8 for target, _key in result[pawn_id]} == {2, 4}


def test_label_renaming_preserves_normalized_destinations():
    indices = tuple(square_to_index(sq(file, 3), 8) for file in (2, 3, 4))
    base, base_state, file, actor_rank, victim_rank, base_type = _capture_probe(
        allowed_drop_squares=indices,
    )
    _, _, base_states = _probe(
        base, base_state, file, actor_rank, victim_rank, base_type
    )
    renamed, renamed_state, file, actor_rank, victim_rank, renamed_type = _capture_probe(
        allowed_drop_squares=indices, pawn_id="X", attacker_id="Y",
    )
    _, _, renamed_states = _probe(
        renamed, renamed_state, file, actor_rank, victim_rank, renamed_type
    )
    assert {target for target, _key in base_states[base_type]} == set(indices)
    assert {target for target, _key in renamed_states[renamed_type]} == set(indices)


def test_owner_reflection_preserves_reflected_normalized_destinations():
    indices = tuple(square_to_index(sq(file, 3), 8) for file in (2, 3, 4))
    compiled, state, file, actor_rank, victim_rank, pawn_id = _capture_probe(
        allowed_drop_squares=indices,
    )
    _, _, owner_zero_states = _probe(compiled, state, file, actor_rank, victim_rank, pawn_id)
    mirrored, mirror_state, file, actor_rank, victim_rank, pawn_id = _capture_probe(
        allowed_drop_squares=indices, owner=1,
    )
    _, _, owner_one_states = _probe(
        mirrored, mirror_state, file, actor_rank, victim_rank, pawn_id
    )
    expected = {(index % 8) + (7 - index // 8) * 8 for index in indices}
    assert {target for target, _key in owner_one_states[pawn_id]} == expected
    assert len(owner_one_states[pawn_id]) == len(owner_zero_states[pawn_id])
