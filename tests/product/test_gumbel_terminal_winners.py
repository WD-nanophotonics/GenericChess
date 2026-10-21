"""Actual Core winners survive the existing Gumbel leaf/back-up boundary."""
from dataclasses import replace

import pytest

from generic_chess import build_builtin_ruleset, compile_ruleset_for_execution
from generic_chess.core.pieces import Piece
from generic_chess.learning.gumbel_mcts import SemanticGumbelMCTSV0, _Node
from generic_chess.native.adapter import pack_semantic_search_position
from generic_chess.native.compiler import compile_native_semantic_rules
from generic_chess.native.semantic import public_action, snapshot, terminal_status
from generic_chess.session.session import GameSession
from native_test_helpers import requires_native

pytestmark = requires_native


def _terminal_route(winner, policy, goal):
    board = [[None] * 8 for _ in range(8)]
    board[6][5] = Piece(winner, 'K', 'K')
    board[4][6] = Piece(winner, 'Q', 'Q')
    board[7 if winner == 0 else 6][7] = Piece(1 - winner, 'K', 'K')
    compiled = compile_ruleset_for_execution(replace(build_builtin_ruleset('western_chess'),
        initial_position=tuple(map(tuple, board)), stalemate_result=policy))
    session = GameSession(compiled)
    if winner == 1:
        wait = next(a for a in session.legal_actions() if
                    (a.from_square.file, a.from_square.rank, a.to_square.file, a.to_square.rank)
                    == (7, 6, 7, 7))
        session.submit(wait)
    action = next(a for a in session.legal_actions() if
                  (a.from_square.file, a.from_square.rank, a.to_square.file, a.to_square.rank)
                  == (6, 4, 6, 5 if goal == 'stalemate' else 6))
    return compiled, session, action


@pytest.mark.parametrize('winner', (0, 1))
@pytest.mark.parametrize('policy', ('draw', 'loss'))
@pytest.mark.parametrize('goal', ('stalemate', 'checkmate'))
def test_gumbel_propagates_core_terminal_winner_from_a_legally_played_child(winner, policy, goal):
    compiled, session, action = _terminal_route(winner, policy, goal)
    native = compile_native_semantic_rules(compiled)
    packed = pack_semantic_search_position(compiled, native, session)
    saved = snapshot(native, packed)
    sampler = SemanticGumbelMCTSV0(compiled, native, policy=None, simulations=16)
    root = _Node(packed, session.state.position.side_to_move)
    sampler._expand(root)
    edge, = [e for e in root.edges.values() if public_action(native, e.action) == action]
    # Force this real legal edge to isolate terminal back-up; keep the complete
    # action set and checked Native child construction, not a fabricated node.
    for candidate in root.edges.values():
        candidate.prior = float(candidate is edge)
    child = sampler._child(root, edge)
    session.submit(action)
    replay = GameSession.replay(compiled, session.to_record())
    assert replay.state == session.state
    actual = terminal_status(native, child.position)
    expected_winner = winner if goal == 'checkmate' or policy == 'loss' else None
    assert session.state.terminal_status.status.value == actual['status'] == goal
    assert session.state.terminal_status.winner == actual['winner'] == expected_winner
    assert snapshot(native, child.position) == snapshot(native,
        pack_semantic_search_position(compiled, native, session))
    expected_child = -1.0 if expected_winner is not None else 0.0
    assert sampler._terminal_for_node(child) == (expected_child, None)
    assert sampler._simulate(root, 0) == -expected_child
    assert edge.visits == 1 and edge.total_value == -expected_child
    assert snapshot(native, packed) == saved

@pytest.mark.parametrize('checker', (0, 1))
def test_gumbel_preserves_winner_from_a_legally_replayed_checking_cycle(checker):
    board = [[None] * 9 for _ in range(9)]
    if checker == 0:
        pieces = ((0, 'K', 8, 0), (1, 'K', 4, 8), (0, 'R', 3, 7))
        route = (((3, 7), (4, 7)), ((4, 8), (3, 8)),
                 ((4, 7), (3, 7)), ((3, 8), (4, 8))) * 3
    else:
        pieces = ((0, 'K', 5, 0), (1, 'K', 0, 8), (1, 'R', 3, 1))
        route = (((5, 0), (4, 0)),) + (
            ((3, 1), (4, 1)), ((4, 0), (3, 0)),
            ((4, 1), (3, 1)), ((3, 0), (4, 0))) * 3
    for owner, tid, file, rank in pieces:
        board[rank][file] = Piece(owner, tid, tid)
    compiled = compile_ruleset_for_execution(replace(build_builtin_ruleset('standard_shogi'),
        initial_position=tuple(map(tuple, board))))
    session = GameSession(compiled)
    for source, target in route:
        action, = [a for a in session.legal_actions() if hasattr(a, 'from_square')
            and (a.from_square.file, a.from_square.rank) == source
            and (a.to_square.file, a.to_square.rank) == target
            and a.promotion_target_id is None]
        session.submit(action)
    replay = GameSession.replay(compiled, session.to_record())
    assert replay.state == session.state
    assert session.state.terminal_status.status.value == 'perpetual_check'
    assert session.state.terminal_status.winner == 1 - checker
    assert session.state.position.side_to_move == checker
    native = compile_native_semantic_rules(compiled)
    packed = pack_semantic_search_position(compiled, native, session)
    assert terminal_status(native, packed) == {'status': 'perpetual_check', 'winner': 1 - checker}
    sampler = SemanticGumbelMCTSV0(compiled, native, policy=None, simulations=16)
    node = _Node(packed, checker)
    assert sampler._terminal_for_node(node) == (-1.0, None)
    assert sampler._simulate(node, 0) == -1.0
