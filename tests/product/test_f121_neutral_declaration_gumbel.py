from generic_chess.core.identity import repetition_identity_key
from generic_chess.core.pieces import Piece
from generic_chess.core.position import GameState, Hands, HistoryRecord, Position
from generic_chess.core.terminal import TerminalResult, TerminalStatus
from generic_chess.learning.gumbel_mcts import (
    SemanticGumbelMCTSV0,
    _neutral_outside_option,
    _select_root_decision,
)
from generic_chess.native.adapter import pack_semantic_search_position
from generic_chess.native.compiler import compile_native_semantic_rules
from generic_chess.native.semantic import available_declarations
from generic_chess.rules.compiler import compile_semantic_ruleset
from generic_chess.rules.standard_shogi import build_standard_shogi_ruleset
from generic_chess.session.session import GameSession


def _context():
    compiled = compile_semantic_ruleset(build_standard_shogi_ruleset())
    return compiled, compile_native_semantic_rules(compiled)


def _declaration_session(compiled, rooks):
    board = [None] * 81
    board[6 * 9 + 4] = Piece(0, "K", "K")
    board[0] = Piece(1, "K", "K")
    zone_slots = [index for index in range(6 * 9, 9 * 9) if index != 6 * 9 + 4]
    for offset, index in enumerate(zone_slots[:10]):
        type_id = "R" if offset < rooks else "P"
        board[index] = Piece(0, type_id, type_id)
    position = Position(tuple(board), (Hands.empty(), Hands.empty()), 0, compiled.ruleset_fingerprint)
    key = repetition_identity_key(position, compiled)
    session = GameSession(compiled)
    session._state = GameState(
        position,
        0,
        ((key, 1),),
        TerminalResult(TerminalStatus.ONGOING),
        (HistoryRecord(key, -1, "", False),),
    )
    return session


def test_f121_standard_shogi_restart_is_authoritative_across_core_native_and_session():
    compiled, native_rules = _context()
    session = _declaration_session(compiled, rooks=5)
    core = session.available_declarations()
    native = available_declarations(native_rules, pack_semantic_search_position(compiled, native_rules, session))
    assert [(item.declaration_id, item.outcome) for item in core] == [("claim_owner_0", "RESTART")]
    assert [(item.declaration_id, item.outcome) for item in native] == [("claim_owner_0", "RESTART")]
    result = session.declare("claim_owner_0")
    assert result.declaration_id == "claim_owner_0"
    assert result.declaration_outcome == "RESTART"
    assert result.winner is None


def test_f121_neutral_outside_option_and_root_tie_decision():
    assert _neutral_outside_option(-0.2, True) == 0.0
    assert _neutral_outside_option(0.2, True) == 0.2
    assert _neutral_outside_option(-0.2, False) == -0.2
    assert _select_root_decision(0.2, "claim_owner_0", 17) == (17, None, False, True)
    assert _select_root_decision(0.0, "claim_owner_0", 17) == (None, "claim_owner_0", True, False)
    assert _select_root_decision(-0.2, "claim_owner_0", 17) == (None, "claim_owner_0", True, False)


def test_f121_neutral_root_search_keeps_board_policy_and_reports_telemetry():
    compiled, native_rules = _context()
    session = _declaration_session(compiled, rooks=5)
    first = SemanticGumbelMCTSV0(compiled, native_rules, policy=None, simulations=16).search(session, search_seed=1210101)
    second = SemanticGumbelMCTSV0(compiled, native_rules, policy=None, simulations=16).search(session, search_seed=1210101)
    assert first.action in first.root_actions
    assert first.declaration_id is None
    assert first.neutral_declaration_id == "claim_owner_0"
    assert first.neutral_declaration_available is True
    assert first.neutral_declaration_selected is False
    assert first.neutral_declarations_declined == 1
    assert first.target_policy == first.improved_policy
    assert first.action == second.action
    assert first.root_gumbels == second.root_gumbels
    assert first.neutral_declaration_encounters > 0


def test_f121_winning_declaration_still_dominates_immediately():
    compiled, native_rules = _context()
    session = _declaration_session(compiled, rooks=6)
    result = SemanticGumbelMCTSV0(compiled, native_rules, policy=None, simulations=16).search(session, search_seed=1210102)
    assert result.action is None
    assert result.declaration_id == "claim_owner_0"
    assert result.winning_declaration_id == "claim_owner_0"
    assert result.neutral_declaration_available is False
    assert result.simulations == 0
