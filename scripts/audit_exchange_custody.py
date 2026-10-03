"""Three frozen legal-action witnesses for the proposed token utility.

Synthetic Chess/Shogi contexts, not reachable-state samples or type scores.
At most 1000 enumerated actions and 30 seconds; no deeper search.
"""
from dataclasses import replace
from pathlib import Path
import sys
from time import monotonic

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from generic_chess.core.actions import SemanticDropMove
from generic_chess.core.identity import repetition_identity_key
from generic_chess.core.movegen import legal_actions
from generic_chess.core.pieces import Piece
from generic_chess.core.position import Hands, HistoryRecord
from generic_chess.core.semantic_executor import semantic_engine_for
from generic_chess.core.transition import apply_action, initial_state, legal_successors
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.standard_shogi import build_standard_shogi_ruleset
from scripts.audit_f24f_western_chess_perft import standard_engine, position_from_fen


def custody(position, anchors):
    counts = [hand.total() for hand in position.hands]
    for piece in position.board:
        if piece and piece.current_type_id not in anchors:
            counts[piece.owner] += 1
    return counts[0] - counts[1]


def synthetic_state(compiled, position):
    state = initial_state(compiled)
    key = repetition_identity_key(position, compiled)
    counts = ((key, 1),)
    engine = semantic_engine_for(compiled)
    return replace(state, position=position, repetition_counts=counts,
                   history=(HistoryRecord(key, -1, '', False),),
                   terminal_status=engine.terminal_result(position, 0, counts))


def audit():
    started = monotonic(); enumerated = 0

    def execute(compiled, position, match):
        nonlocal enumerated
        if monotonic() - started > 30:
            raise TimeoutError('custody witness budget exceeded')
        state = synthetic_state(compiled, position)
        actions = legal_actions(state, compiled); enumerated += len(actions)
        if enumerated > 1000:
            raise RuntimeError('custody witness action cap exceeded')
        chosen = [action for action in actions if match(action)]
        assert len(chosen) == 1, chosen
        child = apply_action(state, chosen[0], compiled)
        metadata = compiled.support.type_metadata
        anchors = {tid for tid, piece in metadata.items() if piece.is_anchor}
        if monotonic() - started > 30:
            raise TimeoutError('custody witness budget exceeded')
        baseline = custody(position, anchors)
        replies = legal_successors(child, compiled)
        enumerated += len(replies)
        if not replies and not child.terminal_status.is_terminal:
            raise ValueError('nonterminal empty reply set requires explicit RuleSet handling')
        def success(state):
            terminal = state.terminal_status
            if terminal.is_terminal:
                if terminal.status.value == 'no_contest':
                    raise ValueError('no-contest outcome outside this frozen task contract')
                return terminal.winner == 0
            return custody(state.position, anchors) > baseline
        secured = success(child) if child.terminal_status.is_terminal else all(success(s) for _, s in replies)
        if enumerated > 1000 or monotonic() - started > 30:
            raise RuntimeError('custody witness reply budget exceeded; no score returned')
        return {'delta': custody(child.position, anchors) - baseline,
                'own_hand_before': position.hands[0].total(),
                'own_hand_after': child.position.hands[0].total(),
                'terminal': child.terminal_status.status.value,
                'complete_reply_count': len(replies), 'secured_task_success': secured}

    def capture(action):
        return (getattr(action, 'actor_type_id', None) == 'R'
                and action.from_square.file == 3 and action.from_square.rank == 3
                and action.to_square.file == 3 and action.to_square.rank == 4
                and action.promotion_target_id is None)

    chess, _ = standard_engine()
    cp = position_from_fen('7k/8/8/3p4/3R4/8/8/K7 w - - 0 1', chess)
    chess_result = execute(chess, cp, capture)
    shogi = compile_ruleset_for_execution(build_standard_shogi_ruleset())
    board = [None] * 81
    for owner, tid, file, rank in ((0, 'K', 0, 0), (1, 'K', 8, 8),
                                   (0, 'R', 3, 3), (1, 'P', 3, 4)):
        board[rank * 9 + file] = Piece(owner, tid, tid)
    sp = replace(initial_state(shogi).position, board=tuple(board), side_to_move=0,
                 hands=(Hands.empty(), Hands.empty()))
    shogi_result = execute(shogi, sp, capture)
    drop_result = execute(shogi, replace(sp, hands=(Hands((('P', 1),)), Hands.empty())),
                          lambda a: isinstance(a, SemanticDropMove) and a.base_type_id == 'P'
                          and a.to_square.file == 4 and a.to_square.rank == 4)
    return {'chess_capture': chess_result, 'shogi_capture': shogi_result,
            'shogi_drop': drop_result, 'enumerated_actions': enumerated,
            'elapsed_seconds': monotonic() - started}


if __name__ == '__main__':
    import json
    print(json.dumps(audit(), indent=2))
