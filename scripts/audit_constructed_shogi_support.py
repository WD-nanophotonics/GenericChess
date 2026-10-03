"""One predeclared board-capture mate, with full inventory and hand custody."""
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
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.standard_shogi import build_standard_shogi_ruleset
from scripts.audit_exchange_custody import custody, synthetic_state
from scripts.audit_physical_placement_sampling import rejection_reason, serialize_board, substituted
from scripts.audit_secured_exchange_common_context import Budget, root_score

PROTOCOL = ROOT / 'docs/research/CONSTRUCTED_SHOGI_SUPPORT_PROTOCOL.md'
PROTOCOL_SHA = '3c657abfd7848e645bcb9f7feaff48a599f8017f073f6c5e08183adb412b1e22'


def physical_frame(compiled):
    inventory = [(0, 'K', 1, 6), (0, 'B', 2, 7), (0, 'R', 4, 0),
                 (0, 'L', 0, 0), (0, 'L', 8, 0), (0, 'N', 5, 0), (0, 'N', 6, 0),
                 (0, 'G', 1, 0), (0, 'G', 2, 0), (0, 'S', 3, 0), (0, 'S', 7, 0),
                 (0, 'P', 3, 3), (0, 'P', 0, 2), (1, 'P', 0, 3),
                 (1, 'K', 0, 8), (1, 'L', 0, 1), (1, 'L', 8, 1),
                 (1, 'R', 4, 1), (1, 'B', 7, 1), (1, 'G', 1, 1), (1, 'G', 2, 1),
                 (1, 'S', 3, 1), (1, 'S', 5, 1), (1, 'N', 4, 3), (1, 'N', 6, 3)]
    inventory += [(0, 'P', file, 4) for file in (1, 2, 4, 5, 6, 7, 8)]
    inventory += [(1, 'P', file, 2) for file in range(1, 9)]
    board = [None] * 81
    for owner, tid, file, rank in inventory:
        cell = rank * 9 + file
        if board[cell] is not None:
            raise ValueError('constructed overlap')
        board[cell] = Piece(owner, tid, tid)
    return replace(initial_state(compiled).position, board=tuple(board), side_to_move=0)


def audit(budget=None):
    if hashlib.sha256(PROTOCOL.read_bytes()).hexdigest() != PROTOCOL_SHA:
        raise ValueError('constructed Shogi support protocol changed')
    budget = budget or Budget(seconds=10, transitions_limit=2000)
    compiled = compile_ruleset_for_execution(build_standard_shogi_ruleset()); frame = physical_frame(compiled)
    count = lambda pos: Counter((p.owner, p.base_type_id) for p in pos.board if p)
    if count(frame) != count(initial_state(compiled).position):
        raise ValueError('full physical inventory mismatch')
    for owner in (0, 1):
        pawn_cells = [index for index, p in enumerate(frame.board) if p and p.owner == owner and p.current_type_id == 'P']
        if len(pawn_cells) != 9 or len({cell % 9 for cell in pawn_cells}) != 9:
            raise ValueError('outside original Pawn file support')
        if any(cell // 9 == (8 if owner == 0 else 0) for cell in pawn_cells):
            raise ValueError('dead Pawn')
    reason = rejection_reason(frame, 'shogi', compiled, budget)
    if reason:
        raise ValueError('constructed frame rejected: ' + reason)
    position = substituted(frame, 'R', compiled); row = root_score(compiled, position, budget)
    selected = [item for item in row['actions'] if item['action'].get('to') == [0, 3]
                and item['action'].get('promotion_target_id') is None]
    if len(selected) != 1:
        raise ValueError('predicted unique capture unavailable')
    budget.checkpoint()
    if budget.transitions >= budget.transitions_limit:
        raise RuntimeError('constructed Shogi replay cap')
    child = apply_action(synthetic_state(compiled, position), action_from_dict(selected[0]['action']), compiled)
    budget.transitions += 1; budget.checkpoint(); engine = semantic_engine_for(compiled)
    replies = list(engine.iter_legal_actions(child.position, checkpoint=budget.checkpoint))
    anchors = {tid for tid, item in compiled.support.type_metadata.items() if item.is_anchor}
    return {'protocol_sha256': PROTOCOL_SHA,
            'program_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            'complete': True, 'initial_inventory_preserved': True, 'common_screen_passed': True,
            'physical_board': serialize_board(frame), 'root': row, 'selected_capture': selected[0],
            'terminal': child.terminal_status.status.value, 'winner': child.terminal_status.winner,
            'opponent_in_check': engine.in_check(child.position, 1, checkpoint=budget.checkpoint),
            'raw_position_legal_reply_count': len(replies),
            'hand_pawn_gain': child.position.hands[0].count('P') - position.hands[0].count('P'),
            'custody_gain': custody(child.position, anchors) - custody(position, anchors),
            'materialized_transitions': budget.transitions, 'elapsed_seconds': monotonic() - budget.started}


if __name__ == '__main__':
    result = audit()
    if len(sys.argv) > 1:
        Path(sys.argv[1]).write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8', newline='\n')
    print(json.dumps({k: v for k, v in result.items() if k not in ('root', 'physical_board')}, indent=2))
