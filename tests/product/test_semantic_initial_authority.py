"""Initial validation must use the executor that will play the rules."""
from dataclasses import replace

import pytest

from generic_chess.core.pieces import Piece, PieceType
from generic_chess.rules.compiler import compile_ruleset, compile_ruleset_for_execution
from generic_chess.rules.schema import RuleInitialSetupOption
from generic_chess.rules.validation import RuleValidationError
from generic_chess.session.session import GameSession
from rule_semantics_ir_fixtures import cannon_ruleset


def layout(screen=False):
    board = [[None] * 8 for _ in range(8)]
    board[0][0] = Piece(0, "K", "K")
    board[7][3] = Piece(1, "K", "K")
    board[3][3] = Piece(0, "C", "C")
    if screen:
        board[5][3] = Piece(0, "Z", "Z")
    return tuple(map(tuple, board))


def definition(screen=False, alternate=False):
    rules = cannon_ruleset()
    rules = replace(rules,
        piece_types=(*rules.piece_types, PieceType("Z", "Z", ())),
        drop_allowed={**rules.drop_allowed, "Z": ((False,) * 64,) * 2})
    if alternate:
        start = [list(row) for row in layout(screen)]
        start[3][2], start[3][3] = start[3][3], None
        return replace(rules, initial_position=tuple(map(tuple, start)), initial_setup_options=(
            RuleInitialSetupOption("cannon-start", layout(screen)),))
    return replace(rules, initial_position=layout(screen))


@pytest.mark.parametrize("alternate", [False, True])
def test_semantically_safe_cannon_initial_layout_is_playable(alternate):
    rules = definition(alternate=alternate)
    compiled = compile_ruleset_for_execution(rules)
    session = GameSession(compiled, "cannon-start" if alternate else None)
    assert session.legal_actions()
    session.submit(session.legal_actions()[0])


@pytest.mark.parametrize("alternate", [False, True])
def test_semantically_attacked_initial_layout_remains_rejected(alternate):
    with pytest.raises(RuleValidationError, match="INITIAL_ANCHOR_ATTACKED"):
        compile_ruleset_for_execution(definition(screen=True, alternate=alternate))


def test_public_legacy_validation_is_unchanged():
    with pytest.raises(RuleValidationError, match="INITIAL_ANCHOR_ATTACKED"):
        compile_ruleset(definition(), allow_semantic_actions=True)


def test_semantic_start_without_any_legal_action_remains_rejected():
    rules = cannon_ruleset()
    # The unused cannon patterns leave two immobile anchors. Deferring the
    # legacy position check must still run the semantic no-legal-action check.
    rules = replace(rules, piece_types=tuple(
        replace(piece, movement_atoms=()) if piece.is_anchor else piece
        for piece in rules.piece_types))
    with pytest.raises(RuleValidationError, match="INITIAL_NO_LEGAL_MOVE"):
        compile_ruleset_for_execution(rules)
