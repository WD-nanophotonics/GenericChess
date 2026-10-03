"""Four frozen inventory-preserving backgrounds under the unchanged task."""
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
from generic_chess.core.position import Hands
from generic_chess.core.transition import initial_state, apply_action
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.standard_shogi import build_standard_shogi_ruleset
from scripts.audit_exchange_custody import custody, synthetic_state
from scripts.audit_f24f_western_chess_perft import standard_engine, position_from_fen
from scripts.audit_secured_exchange_common_context import Budget, root_score

PROTOCOL = ROOT / 'docs/research/EXCHANGE_BACKGROUND_COUPLING_PROTOCOL.md'
PROTOCOL_SHA = '744aaf3e57e269dffbaf6fbb43d0161563c50d07cc88d0ab25a8e1f5dd101506'


def position_for(compiled, game, exposed):
    n = compiled.board_size
    template = (position_from_fen('8/8/8/8/8/8/8/8 w - - 0 1', compiled)
                if game == 'chess' else initial_state(compiled).position)
    board = [None] * (n * n)
    for owner, tid, file, rank in [(0, 'K', 0, 0), (0, 'R', 3, 3), (1, 'P', 3, 4),
                                   (1, 'K', n-1, n-2), (1, 'R', n-2, n-1),
                                   (0, 'P', n-2 if exposed else n-3, n-2)]:
        board[rank * n + file] = Piece(owner, tid, tid)
    return replace(template, board=tuple(board), hands=(Hands.empty(), Hands.empty()), side_to_move=0)


def audit(budget=None):
    if hashlib.sha256(PROTOCOL.read_bytes()).hexdigest() != PROTOCOL_SHA:
        raise ValueError('frozen background protocol changed')
    budget = budget or Budget(seconds=10, transitions_limit=2000)
    chess, _ = standard_engine()
    games = [('chess', chess), ('shogi', compile_ruleset_for_execution(build_standard_shogi_ruleset()))]
    rows = []; comparisons = {}
    replayed = 0
    def replay(state, action, compiled):
        nonlocal replayed
        budget.checkpoint()
        if budget.transitions >= budget.transitions_limit:
            raise RuntimeError('background replay cap; no complete vector')
        after = apply_action(state, action, compiled)
        budget.transitions += 1; replayed += 1; budget.checkpoint()
        return after
    for game, compiled in games:
        pair = []
        for exposed in (False, True):
            position = position_for(compiled, game, exposed)
            result = root_score(compiled, position, budget)
            row = {'game': game, 'background': 'exposed' if exposed else 'shifted', **result}
            selected = [e for e in result['actions'] if e['action'].get('to') == [3, 4]
                        and e['action'].get('promotion_target_id') is None]
            if len(selected) != 1:
                raise ValueError('unique unpromoted focal capture required')
            evidence = selected[0]; state = synthetic_state(compiled, position)
            child = replay(state, action_from_dict(evidence['action']), compiled)
            anchors = {tid for tid, item in compiled.support.type_metadata.items() if item.is_anchor}
            row['selected_capture_success'] = evidence['success']
            row['immediate_gain'] = custody(child.position, anchors) - custody(position, anchors)
            if exposed:
                ref = evidence['first_refutation']
                if not ref:
                    raise ValueError('predicted refutation absent')
                after = replay(child, action_from_dict(ref['action']), compiled)
                focal = after.position.board[4 * compiled.board_size + 3]
                row['selected_refutation'] = ref
                row['focal_survives_refutation'] = focal is not None and focal.owner == 0 and focal.current_type_id == 'R'
                row['net_gain_after_refutation'] = custody(after.position, anchors) - custody(position, anchors)
            budget.checkpoint(); rows.append(row); pair.append(row)
        comparisons[game] = {'same_focal_actions': [a['action'] for a in pair[0]['actions']] == [a['action'] for a in pair[1]['actions']],
                             'shifted_score': pair[0]['success'], 'exposed_score': pair[1]['success']}
    return {'protocol_sha256': PROTOCOL_SHA,
            'program_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            'complete': True, 'comparisons': comparisons, 'roots': rows,
            'materialized_transitions': budget.transitions,
            'enumeration_transitions': budget.transitions - replayed, 'replayed_transitions': replayed,
            'elapsed_seconds': monotonic() - budget.started}


if __name__ == '__main__':
    result = audit()
    if len(sys.argv) > 1:
        Path(sys.argv[1]).write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({k: v for k, v in result.items() if k != 'roots'}, indent=2))
