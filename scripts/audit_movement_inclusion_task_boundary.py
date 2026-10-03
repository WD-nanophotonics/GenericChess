"""Movement inclusion does not imply unchanged transition/payoff inclusion."""
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import sys
from time import monotonic

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from generic_chess.core.actions import action_from_dict, action_to_dict
from generic_chess.core.pieces import Piece
from generic_chess.core.semantic_executor import semantic_engine_for, iter_semantic_public_actions
from generic_chess.core.transition import apply_action
from scripts.audit_exchange_custody import custody, synthetic_state
from scripts.audit_f24f_western_chess_perft import standard_engine, position_from_fen
from scripts.audit_physical_placement_sampling import rejection_reason, substituted, serialize_board
from scripts.audit_secured_exchange_common_context import Budget, root_score

PROTOCOL = ROOT / 'docs/research/MOVEMENT_INCLUSION_TASK_BOUNDARY_PROTOCOL.md'
PROTOCOL_SHA = '25c15b3a3a366898b6cb1eca01ee960c852119dbc9b9274b9022dd49007d8d3c'


def frame_position(compiled):
    board = [None] * 64
    for owner, tid, file, rank in [(0, 'K', 6, 4), (0, 'B', 5, 5), (0, 'P', 3, 3),
                                    (1, 'K', 7, 6), (1, 'P', 3, 4)]:
        board[rank * 8 + file] = Piece(owner, tid, tid)
    return replace(position_from_fen('8/8/8/8/8/8/8/8 w - - 0 1', compiled), board=tuple(board))


def coordinates(row):
    return {(tuple(item['action']['from']), tuple(item['action']['to']), item['action']['promotion_target_id'])
            for item in row['actions']}


def audit(budget=None):
    if hashlib.sha256(PROTOCOL.read_bytes()).hexdigest() != PROTOCOL_SHA:
        raise ValueError('movement inclusion protocol changed')
    budget = budget or Budget(seconds=10, transitions_limit=2000)
    compiled, _ = standard_engine(); frame = frame_position(compiled)
    reason = rejection_reason(frame, 'chess', compiled, budget)
    if reason:
        raise ValueError('common sparse frame rejected: ' + reason)
    engine = semantic_engine_for(compiled)
    anchors = {tid for tid, item in compiled.support.type_metadata.items() if item.is_anchor}
    rows = []; replays = 0
    for tid in ('R', 'Q'):
        position = substituted(frame, tid, compiled); score = root_score(compiled, position, budget)
        selected = [item for item in score['actions'] if item['action']['to'] == [3, 4]]
        if len(selected) != 1:
            raise ValueError('predicted unique capture unavailable')
        budget.checkpoint()
        if budget.transitions >= budget.transitions_limit:
            raise RuntimeError('movement inclusion replay cap')
        child = apply_action(synthetic_state(compiled, position), action_from_dict(selected[0]['action']), compiled)
        budget.transitions += 1; replays += 1; budget.checkpoint()
        replies = [action_to_dict(action) for action in iter_semantic_public_actions(
            engine, child.position, checkpoint=budget.checkpoint)]
        rows.append({'focal_type': tid, 'root': score, 'selected_capture': selected[0],
                     'capture_terminal': child.terminal_status.status.value,
                     'opponent_in_check': engine.in_check(child.position, 1, checkpoint=budget.checkpoint),
                     'immediate_custody_gain': custody(child.position, anchors) - custody(position, anchors),
                     'raw_position_replies': replies})
    return {'protocol_sha256': PROTOCOL_SHA,
            'program_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            'complete': True, 'scope': 'sparse semantics context; not full-inventory sampling law',
            'physical_board': serialize_board(frame), 'roots': rows,
            'rook_coordinate_actions_included_in_queen': coordinates(rows[0]['root']) <= coordinates(rows[1]['root']),
            'replayed_transitions': replays, 'materialized_transitions': budget.transitions,
            'elapsed_seconds': monotonic() - budget.started}


if __name__ == '__main__':
    result = audit()
    if len(sys.argv) > 1:
        Path(sys.argv[1]).write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8', newline='\n')
    print(json.dumps({**{k: v for k, v in result.items() if k not in ('roots', 'physical_board')},
        'comparisons': [{**{k: v for k, v in row.items() if k != 'root'}, 'root_score': row['root']['success']}
                        for row in result['roots']]}, indent=2))
