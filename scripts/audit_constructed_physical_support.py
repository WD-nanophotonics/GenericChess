"""One predeclared full-inventory Chess mate witness; no repaired layouts."""
from collections import Counter
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import sys
from time import monotonic

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from generic_chess.core.actions import action_from_dict
from generic_chess.core.pieces import Piece
from generic_chess.core.semantic_executor import semantic_engine_for
from generic_chess.core.transition import apply_action, initial_state
from scripts.audit_exchange_custody import synthetic_state
from scripts.audit_f24f_western_chess_perft import standard_engine, position_from_fen
from scripts.audit_physical_placement_sampling import rejection_reason, serialize_board
from scripts.audit_secured_exchange_common_context import Budget, root_score

PROTOCOL = ROOT / 'docs/research/CONSTRUCTED_PHYSICAL_SUPPORT_PROTOCOL.md'
PROTOCOL_SHA = 'a44c83e862531a8458c02056aed0e041fb14ad8dd6b69cb183e163f5e849b088'


def physical_frame(compiled):
    inventory = [(0, 'K', 1, 5), (1, 'K', 0, 7), (0, 'P', 3, 3), (1, 'P', 0, 3),
                 (0, 'R', 0, 0), (0, 'R', 4, 0), (0, 'Q', 3, 0),
                 (0, 'N', 5, 0), (0, 'N', 6, 0), (0, 'B', 7, 0), (0, 'B', 2, 6),
                 (1, 'Q', 2, 1), (1, 'R', 3, 1), (1, 'R', 5, 1),
                 (1, 'B', 1, 1), (1, 'B', 7, 1), (1, 'N', 4, 1), (1, 'N', 6, 1)]
    inventory += [(owner, 'P', file, rank) for owner, rank in [(0, 4), (1, 2)] for file in range(1, 8)]
    board = [None] * 64
    for owner, tid, file, rank in inventory:
        cell = rank * 8 + file
        if board[cell] is not None:
            raise ValueError('constructed overlap')
        board[cell] = Piece(owner, tid, tid)
    template = position_from_fen('8/8/8/8/8/8/8/8 w - - 0 1', compiled)
    return replace(template, board=tuple(board))


def audit(budget=None):
    if hashlib.sha256(PROTOCOL.read_bytes()).hexdigest() != PROTOCOL_SHA:
        raise ValueError('constructed support protocol changed')
    budget = budget or Budget(seconds=10, transitions_limit=2000)
    compiled, _ = standard_engine(); frame = physical_frame(compiled)
    count = lambda pos: Counter((piece.owner, piece.base_type_id) for piece in pos.board if piece)
    if count(frame) != count(initial_state(compiled).position):
        raise ValueError('full physical inventory mismatch')
    if any(not 1 <= index // 8 <= 6 for index, piece in enumerate(frame.board) if piece and piece.current_type_id == 'P'):
        raise ValueError('outside original Pawn-conditioned support')
    reason = rejection_reason(frame, 'chess', compiled, budget)
    if reason:
        raise ValueError('constructed frame rejected: ' + reason)
    board = list(frame.board); board[27] = Piece(0, 'R', 'R')
    position = replace(frame, board=tuple(board))
    row = root_score(compiled, position, budget)
    selected = [item for item in row['actions'] if item['action'].get('to') == [0, 3]
                and item['action'].get('promotion_target_id') is None]
    if len(selected) != 1:
        raise ValueError('predicted unique capture unavailable')
    budget.checkpoint()
    if budget.transitions >= budget.transitions_limit:
        raise RuntimeError('constructed witness replay cap')
    child = apply_action(synthetic_state(compiled, position), action_from_dict(selected[0]['action']), compiled)
    budget.transitions += 1; budget.checkpoint()
    engine = semantic_engine_for(compiled)
    # Check the raw position, independently of terminal GameState action gating.
    replies = list(engine.iter_legal_actions(child.position, checkpoint=budget.checkpoint))
    return {'protocol_sha256': PROTOCOL_SHA,
            'program_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            'complete': True, 'initial_inventory_preserved': True,
            'common_screen_passed': True, 'physical_board': serialize_board(frame),
            'root': row, 'selected_capture': selected[0],
            'terminal': child.terminal_status.status.value, 'winner': child.terminal_status.winner,
            'opponent_in_check': engine.in_check(child.position, 1, checkpoint=budget.checkpoint),
            'raw_position_legal_reply_count': len(replies),
            'materialized_transitions': budget.transitions,
            'elapsed_seconds': monotonic() - budget.started}


if __name__ == '__main__':
    result = audit()
    if len(sys.argv) > 1:
        Path(sys.argv[1]).write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8', newline='\n')
    print(json.dumps({k: v for k, v in result.items() if k not in ('root', 'physical_board')}, indent=2))
