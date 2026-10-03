"""Predeclared Bishop/Rook swap controls; no new random sample or utility."""
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

from generic_chess.core.actions import action_from_dict, action_to_dict
from generic_chess.core.semantic_executor import semantic_engine_for, iter_semantic_public_actions
from generic_chess.core.transition import apply_action, initial_state
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.standard_shogi import build_standard_shogi_ruleset
from scripts.audit_constructed_physical_support import physical_frame as chess_frame
from scripts.audit_constructed_shogi_support import physical_frame as shogi_frame
from scripts.audit_exchange_custody import custody, synthetic_state
from scripts.audit_f24f_western_chess_perft import standard_engine
from scripts.audit_physical_placement_sampling import rejection_reason, serialize_board, substituted
from scripts.audit_secured_exchange_common_context import Budget, root_score

PROTOCOL = ROOT / 'docs/research/NONTERMINAL_PHYSICAL_SUPPORT_PROTOCOL.md'
PROTOCOL_SHA = '9b7cbf6805cc4c2dbb42f8ee1c012eea68b08dfa26425cc07519456fe093864d'


def control_frame(compiled, game):
    original = (chess_frame if game == 'chess' else shogi_frame)(compiled)
    n = compiled.board_size; bishop = (6 if game == 'chess' else 7) * n + 2
    board = list(original.board); board[bishop], board[4] = board[4], board[bishop]
    return original, replace(original, board=tuple(board))


def audit(budget=None):
    if hashlib.sha256(PROTOCOL.read_bytes()).hexdigest() != PROTOCOL_SHA:
        raise ValueError('nonterminal physical support protocol changed')
    budget = budget or Budget(seconds=10, transitions_limit=4000)
    chess, _ = standard_engine()
    shogi = compile_ruleset_for_execution(build_standard_shogi_ruleset())
    rows = []; replayed = 0
    def replay(state, action, compiled):
        nonlocal replayed
        budget.checkpoint()
        if budget.transitions >= budget.transitions_limit:
            raise RuntimeError('nonterminal support replay cap')
        after = apply_action(state, action, compiled)
        budget.transitions += 1; replayed += 1; budget.checkpoint()
        return after
    for game, compiled in [('chess', chess), ('shogi', shogi)]:
        original, frame = control_frame(compiled, game)
        count = lambda pos: Counter((p.owner, p.base_type_id) for p in pos.board if p)
        if count(frame) != count(initial_state(compiled).position):
            raise ValueError('inventory mismatch')
        pawn_cells = lambda pos: [i for i, p in enumerate(pos.board) if p and p.current_type_id == 'P']
        if pawn_cells(frame) != pawn_cells(original):
            raise ValueError('changed Pawn-conditioned support')
        reason = rejection_reason(frame, game, compiled, budget)
        if reason:
            raise ValueError('control rejected: ' + reason)
        position = substituted(frame, 'R', compiled); row = root_score(compiled, position, budget)
        selected = [item for item in row['actions'] if item['action'].get('to') == [0, 3]
                    and item['action'].get('promotion_target_id') is None]
        if len(selected) != 1:
            raise ValueError('unique predicted capture absent')
        engine = semantic_engine_for(compiled)
        anchors = {tid for tid, item in compiled.support.type_metadata.items() if item.is_anchor}
        baseline = custody(position, anchors)
        child = replay(synthetic_state(compiled, position), action_from_dict(selected[0]['action']), compiled)
        reply_evidence = []
        for action in iter_semantic_public_actions(engine, child.position, checkpoint=budget.checkpoint):
            after = replay(child, action, compiled)
            reply_evidence.append({'action': action_to_dict(action), 'terminal': after.terminal_status.status.value,
                                   'custody_delta': custody(after.position, anchors) - baseline})
        rows.append({'game': game, 'physical_board': serialize_board(frame), 'root': row,
                     'selected_capture': selected[0], 'capture_terminal': child.terminal_status.status.value,
                     'opponent_in_check': engine.in_check(child.position, 1, checkpoint=budget.checkpoint),
                     'replies': reply_evidence})
    return {'protocol_sha256': PROTOCOL_SHA,
            'program_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            'frame_sources_sha256': {name: hashlib.sha256((ROOT / 'scripts' / name).read_bytes()).hexdigest()
                for name in ('audit_constructed_physical_support.py', 'audit_constructed_shogi_support.py')},
            'complete': True, 'roots': rows, 'replayed_transitions': replayed,
            'materialized_transitions': budget.transitions, 'elapsed_seconds': monotonic() - budget.started}


if __name__ == '__main__':
    result = audit()
    if len(sys.argv) > 1:
        Path(sys.argv[1]).write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8', newline='\n')
    print(json.dumps({**{k: v for k, v in result.items() if k != 'roots'},
                     'controls': [{k: v for k, v in row.items() if k not in ('root', 'physical_board')} for row in result['roots']]}, indent=2))
