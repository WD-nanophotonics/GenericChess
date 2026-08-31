from __future__ import annotations

from dataclasses import replace

import pytest

from generic_chess import (
    Hands,
    Position,
    assess_declaration,
    available_declarations,
    build_standard_shogi_ruleset,
    build_western_chess_ruleset,
    compile_ruleset_for_execution,
)
from generic_chess.core.declarations import InvalidDeclarationError
from generic_chess.core.terminal import TerminalResult, TerminalStatus
from generic_chess.rules.schema import (
    RuleDeclaration,
    RuleDeclarationOutcomeBand,
    RuleSet,
    RuleSpatialSelector,
    RuleStateGuard,
    RuleSquareRef,
    RuleTypeRef,
    RuleWeightedMaterialMetric,
    compute_fingerprint,
)
from generic_chess.rules.serialization import deserialize_ruleset, serialize_ruleset
from generic_chess.rules.validation import RuleValidationError
from generic_chess.session.result import SessionStatus, session_result_from_terminal


def _claim_ruleset() -> RuleSet:
    base = build_western_chess_ruleset()
    zone = RuleSpatialSelector("zone", zone_squares=tuple((file, 0) for file in range(8)))
    claim = RuleDeclaration(
        declaration_id="opaque_claim",
        owner=0,
        state_guards=(
            RuleStateGuard(
                aggregation="exists",
                owner="self",
                type_ref=RuleTypeRef("explicit", "K"),
                compare_field="base",
                promoted="any",
                location="board",
                spatial=zone,
                value=1,
            ),
        ),
        ply_limit=500,
        weighted_metric=RuleWeightedMaterialMetric(
            owner="self",
            compare_field="base",
            weights={"K": 0, "R": 5, "P": 1},
            spatial=zone,
            include_hands=True,
        ),
        outcome_bands=(
            RuleDeclarationOutcomeBand(7, "WIN"),
            RuleDeclarationOutcomeBand(4, "RESTART"),
        ),
        failure_outcome="LOSS",
    )
    return replace(base, declarations=(claim,))


def _claim_position(compiled, *, score_state: str = "win") -> Position:
    board = [None] * 64
    from generic_chess import Piece

    board[0] = Piece(0, "K", "K")
    board[1] = Piece(0, "R", "R")
    board[2] = Piece(0, "P", "P")
    board[24] = Piece(0, "P", "P")  # outside the claim zone: zero score
    board[63] = Piece(1, "K", "K")
    hands = Hands((
        ("P", 1),
    ))
    if score_state == "restart":
        board[2] = None
        hands = Hands.empty()
    if score_state == "loss":
        board[1] = None
        board[2] = None
        hands = Hands.empty()
    return Position(
        tuple(board),
        hands=(hands, Hands.empty()),
        side_to_move=0,
        ruleset_fingerprint=compiled.ruleset_fingerprint,
    )


def test_empty_declarations_are_backward_compatible_and_nonempty_changes_identity():
    base = build_western_chess_ruleset()
    assert "declarations" not in serialize_ruleset(base)
    assert compute_fingerprint(deserialize_ruleset(serialize_ruleset(base))) == compute_fingerprint(base)
    claimed = _claim_ruleset()
    restored = deserialize_ruleset(serialize_ruleset(claimed))
    assert restored.declarations == claimed.declarations
    assert compute_fingerprint(restored) == compute_fingerprint(claimed)
    assert compute_fingerprint(claimed) != compute_fingerprint(base)
    assert compute_fingerprint(replace(claimed, metadata={"note": "neutral"})) == compute_fingerprint(claimed)


def test_assessment_scores_zone_and_hands_without_mutating_position():
    compiled = compile_ruleset_for_execution(_claim_ruleset())
    position = _claim_position(compiled)
    before = position
    result = assess_declaration(position, compiled, "opaque_claim")
    assert result.outcome == "WIN"
    assert result.weighted_score == 7
    assert position == before
    assert [item.declaration_id for item in available_declarations(position, compiled)] == ["opaque_claim"]
    assert compiled.ir.capabilities.native_executable is False


def test_threshold_owner_and_failed_declaration_controls():
    compiled = compile_ruleset_for_execution(_claim_ruleset())
    assert assess_declaration(_claim_position(compiled, score_state="restart"), compiled, "opaque_claim").outcome == "RESTART"
    assert assess_declaration(_claim_position(compiled, score_state="loss"), compiled, "opaque_claim").outcome == "LOSS"
    with pytest.raises(InvalidDeclarationError):
        assess_declaration(replace(_claim_position(compiled), side_to_move=1), compiled, "opaque_claim")
    with pytest.raises(InvalidDeclarationError):
        assess_declaration(_claim_position(compiled), compiled, "missing")


def test_declarations_do_not_change_board_action_sets_or_production_fingerprints():
    base = build_western_chess_ruleset()
    claimed = _claim_ruleset()
    base_compiled = compile_ruleset_for_execution(base)
    claimed_compiled = compile_ruleset_for_execution(claimed)
    from generic_chess import legal_actions
    from generic_chess.core.transition import initial_state

    assert {str(a) for a in legal_actions(initial_state(base_compiled), base_compiled)} == {
        str(a) for a in legal_actions(initial_state(claimed_compiled), claimed_compiled)
    }
    assert not build_western_chess_ruleset().declarations
    assert not build_standard_shogi_ruleset().declarations


def test_perpetual_check_session_mapping_preserves_winner():
    result = session_result_from_terminal(TerminalResult(TerminalStatus.PERPETUAL_CHECK, 1))
    assert result.status is SessionStatus.PERPETUAL_CHECK
    assert result.winner == 1
    assert "player 0 loses" in str(result)
    assert session_result_from_terminal(TerminalResult(TerminalStatus.REPETITION)).status is SessionStatus.REPETITION
    from generic_chess.session.session import GameSession

    session = GameSession(compile_ruleset_for_execution(build_western_chess_ruleset()))
    session._state = replace(session.state, terminal_status=TerminalResult(TerminalStatus.PERPETUAL_CHECK, 1))
    assert session.result.status is SessionStatus.PERPETUAL_CHECK
    assert session.result.winner == 1


def test_invalid_action_bound_declaration_reference_fails_closed():
    bad = replace(
        _claim_ruleset(),
        declarations=(
            replace(
                _claim_ruleset().declarations[0],
                state_guards=(replace(_claim_ruleset().declarations[0].state_guards[0], spatial=RuleSpatialSelector("exact", refs=(RuleSquareRef("source"),))),),
            ),
        ),
    )
    with pytest.raises(RuleValidationError):
        compile_ruleset_for_execution(bad)


def _shogi_certification_declarations():
    def one(owner: int):
        ranks = (6, 7, 8) if owner == 0 else (0, 1, 2)
        zone = tuple((file, rank) for rank in ranks for file in range(9))
        spatial = RuleSpatialSelector("zone", zone_squares=zone)
        return RuleDeclaration(
            declaration_id=f"claim_owner_{owner}",
            owner=owner,
            state_guards=(
                RuleStateGuard("exists", "self", RuleTypeRef("explicit", "K"), "base", "any", "board", spatial, value=1),
                RuleStateGuard("count", "self", RuleTypeRef("any"), "base", "any", "board", spatial, comparison="ge", value=11),
            ),
            ply_limit=500,
            weighted_metric=RuleWeightedMaterialMetric(
                weights={"K": 0, "P": 1, "L": 1, "N": 1, "S": 1, "G": 1, "B": 5, "R": 5},
                spatial=spatial,
                include_hands=True,
            ),
            outcome_bands=(RuleDeclarationOutcomeBand(31, "WIN"), RuleDeclarationOutcomeBand(24, "RESTART")),
        )
    return (one(0), one(1))


def test_standard_shogi_certification_copy_uses_generic_declaration_semantics():
    product = build_standard_shogi_ruleset()
    certified = replace(product, declarations=_shogi_certification_declarations())
    compiled = compile_ruleset_for_execution(certified)
    from generic_chess import Piece

    board = [None] * 81
    board[0] = Piece(1, "K", "K")
    board[54] = Piece(0, "K", "K")
    # Ten nonking pieces in owner 0's enemy camp: eight low pieces and two bishops.
    for index in range(55, 63):
        board[index] = Piece(0, "P", "P")
    board[63] = Piece(0, "B", "B")
    board[64] = Piece(0, "B", "B")
    position = Position(
        tuple(board),
        hands=(Hands((("P", 13),)), Hands.empty()),
        side_to_move=0,
        ruleset_fingerprint=compiled.ruleset_fingerprint,
    )
    result = assess_declaration(position, compiled, "claim_owner_0")
    assert result.outcome == "WIN"
    assert result.weighted_score == 31
    board1 = [None] * 81
    board1[80] = Piece(0, "K", "K")
    board1[26] = Piece(1, "K", "K")
    for index in range(18, 26):
        board1[index] = Piece(1, "P", "P")
    board1[9] = Piece(1, "B", "B")
    board1[10] = Piece(1, "B", "B")
    owner1 = Position(
        tuple(board1),
        hands=(Hands.empty(), Hands((("P", 13),))),
        side_to_move=1,
        ruleset_fingerprint=compiled.ruleset_fingerprint,
    )
    assert assess_declaration(owner1, compiled, "claim_owner_1").outcome == "WIN"
    assert compute_fingerprint(product) == "5b3d04eda31a342b729fc9af8a04cdde13c796646b2b37024891f8c99703c345"
    assert product.metadata["nyugyoku_supported"] is False
