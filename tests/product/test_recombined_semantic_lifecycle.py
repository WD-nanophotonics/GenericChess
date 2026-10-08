"""Executable event coverage, rather than compile-only capability coverage."""
from dataclasses import replace

from generic_chess.core.pieces import Piece
from generic_chess.core.transition import apply_action, legal_successors
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.session.session import GameSession
from rule_semantics_ir_fixtures import weird_rulesets


def test_promotion_expiry_and_drop_capacity_through_real_capture_history():
    fixtures = weird_rulesets()
    guard = fixtures[1].semantic_actions[0]
    promotion = fixtures[2].semantic_actions[0]
    board = [[None] * 8 for _ in range(8)]
    for owner, tid, file, rank in (
        (0, "K", 4, 0), (1, "K", 7, 7),
        (0, "R", 0, 0), (0, "R", 0, 1), (0, "R", 0, 2),
        (0, "R", 1, 1), (1, "R", 1, 3), (1, "R", 1, 4),
    ):
        board[rank][file] = Piece(owner, tid, tid)
    definition = replace(
        fixtures[2], initial_position=tuple(map(tuple, board)),
        semantic_actions=(guard, promotion),
        drop_allowed={"R": ((True,) * 64, (True,) * 64),
                      "TP": ((False,) * 64, (False,) * 64)},
    )
    compiled = compile_ruleset_for_execution(definition)
    session = GameSession(compiled)
    route = (
        ((1, 1), (1, 3), False), ((7, 7), (6, 7), False),
        ((1, 3), (1, 4), False), ((6, 7), (5, 7), False),
        ((0, 0), (1, 1), True), ((5, 7), (4, 7), False),
        (None, (0, 0), False), ((4, 7), (3, 7), False),
    )
    for ply in range(9):
        pairs = legal_successors(session.state, compiled)
        assert tuple(a for a, _ in pairs) == session.legal_actions()
        for action, child in pairs:
            assert child == apply_action(session.state, action, compiled)
        drops = [a for a, _ in pairs if hasattr(a, "base_type_id")]
        if ply in (2, 4, 8):
            assert session.state.position.hands[0].count("R") > 0
            assert not drops
        if ply == 5:
            promoted = session.state.position.board[9]
            assert (promoted.base_type_id, promoted.current_type_id, promoted.promoted) == (
                "R", "TP", True)
            assert dict(session.state.position.aux_state)[(0, -1)] == 1
        if ply == 6:
            assert dict(session.state.position.aux_state)[(0, -1)] == 0
            assert len(drops) == 58
        if ply == 8:
            assert session.state.position.hands[0].count("R") == 1
            break
        source, target, semantic = route[ply]
        candidates = []
        for action, _ in pairs:
            if (action.to_square.file, action.to_square.rank) != target:
                continue
            if source is None:
                if hasattr(action, "base_type_id"):
                    candidates.append(action)
            elif (hasattr(action, "from_square")
                  and (action.from_square.file, action.from_square.rank) == source
                  and action.pattern_id.startswith("sem_") == semantic):
                candidates.append(action)
        action, = candidates
        session.submit(action)
