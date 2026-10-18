"""Real reachable history collisions in the diagnostic Native trace key."""
import pytest

from generic_chess.ai.limits import SearchLimits
from generic_chess.core.movement import LeapAtom
from generic_chess.core.pieces import Piece, PieceType
from generic_chess.core.transition import apply_action
from generic_chess.learning.material import LearnableMaterialCheckpoint
from generic_chess.native import native_available
from generic_chess.native.compiler import compile_native_semantic_rules
from generic_chess.native.semantic_engine import SemanticSearchEngine
from generic_chess.rules.compiler import compile_legacy_ruleset_for_semantic_execution
from generic_chess.rules.schema import RuleSet
from generic_chess.session.session import GameSession

pytestmark = pytest.mark.skipif(not native_available(), reason="native extension unavailable")


def _reachable_parents():
    king = PieceType("K", "K", (), is_anchor=True)
    atoms = (LeapAtom((0, 1)), LeapAtom((0, -1)))
    types = (king, PieceType("F", "F", atoms), PieceType("G", "G", atoms),
             PieceType("Z", "Z", ()))
    rows = [[None] * 6 for _ in range(6)]
    for x, y, owner, tid in (
        (0, 0, 0, "K"), (5, 5, 1, "K"),
        (0, 1, 0, "F"), (1, 1, 0, "F"),
        (4, 4, 1, "G"), (5, 4, 1, "G"),
        (0, 3, 0, "Z"), (1, 3, 0, "Z"), (1, 0, 0, "Z"),
        (4, 2, 1, "Z"), (5, 2, 1, "Z"), (4, 5, 1, "Z"),
    ):
        rows[y][x] = Piece(owner, tid, tid)
    ruleset = RuleSet(
        board_size=6, piece_types=types, initial_position=tuple(map(tuple, rows)),
        drop_allowed={t: ((False,) * 36,) * 2 for t in ("F", "G", "Z")},
        repetition_limit=3, max_ply=512, stalemate_result="draw",
    )
    compiled = compile_legacy_ruleset_for_semantic_execution(ruleset)
    paths = (
        ((0,1,0,2), (4,4,4,3), (1,1,1,2), (5,4,5,3),
         (0,2,0,1), (4,3,4,4), (1,2,1,1)),
        ((0,1,0,2), (4,4,4,3), (0,2,0,1), (4,3,4,4),
         (0,1,0,2), (5,4,5,3), (0,2,0,1)),
    )
    sessions = []
    for path in paths:
        session = GameSession(compiled)
        for fx, fy, tx, ty in path:
            action = next(
                a for a in session.legal_actions()
                if (a.from_square.file, a.from_square.rank,
                    a.to_square.file, a.to_square.rank) == (fx, fy, tx, ty)
            )
            session.submit(action)
        replayed = GameSession.replay(compiled, session.to_record())
        assert (replayed.state, replayed.history, replayed._search_witnesses) == (
            session.state, session.history, session._search_witnesses)
        sessions.append(session)
    return compiled, sessions


@pytest.mark.parametrize("root_window", (False, True))
def test_same_board_and_ply_need_distinct_history_targets(root_window):
    compiled, (a, b) = _reachable_parents()
    assert a.state.position == b.state.position
    assert a.state.ply_count == b.state.ply_count == 7
    assert a.state.history != b.state.history
    assert a.state.repetition_counts != b.state.repetition_counts
    assert not a.state.terminal_status.is_terminal and not b.state.terminal_status.is_terminal
    native = compile_native_semantic_rules(compiled)
    checkpoint = LearnableMaterialCheckpoint(
        ruleset_fingerprint=compiled.ruleset_fingerprint,
        board_weights={"K": 0., "F": 2., "G": 1., "Z": 0.},
        hand_weights={"K": 0., "F": 2., "G": 1., "Z": 0.},
    )
    roots = []
    for session, expected in ((a, -2), (b, 0)):
        before = (session.state, session.to_record(), session.history,
                  session._search_witnesses)
        children = [apply_action(session.state, action, compiled)
                    for action in session.legal_actions()]
        # Side 1 minimizes the player-0 material value. Terminal draws are 0.
        values = [0 if child.terminal_status.is_terminal else 2 for child in children]
        assert -min(values) == expected
        engine = SemanticSearchEngine(
            compiled, native, checkpoint=checkpoint, tt_megabytes=0)
        result = engine.search(
            session, SearchLimits(max_depth=1, max_nodes=8192,
                                  max_time_seconds=2, quiescence_max_depth=0),
            root_window_pruning=root_window, trace_enabled=True,
        )
        assert result.completed_depth == 1 and not result.used_fallback
        assert result.score == expected
        assert before == (session.state, session.to_record(), session.history,
                          session._search_witnesses)
        root = next(row for row in result.training_trace
                    if row["search_ply"] == 0 and row["remaining_depth"] == 1)
        assert root["bound_class"] == "EXACT"
        assert root["score_native"] == expected
        roots.append(root)
    # The diagnostic key describes position, not a complete history context.
    for key in ("position_identity", "side_to_move", "remaining_depth",
                "search_ply", "ruleset_fingerprint", "board_counts",
                "hand_counts", "board_features"):
        assert roots[0][key] == roots[1][key]
