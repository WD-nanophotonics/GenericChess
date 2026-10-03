"""Compare net custody and local survival on identical frozen successors."""
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import sys
from time import monotonic

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from generic_chess.core.actions import action_to_dict
from generic_chess.core.lazy_transitions import iter_legal_successor_handles
from generic_chess.core.pieces import Piece
from generic_chess.core.transition import initial_state
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.standard_shogi import build_standard_shogi_ruleset
from scripts.audit_exchange_custody import custody, synthetic_state
from scripts.audit_exchange_background_coupling import position_for
from scripts.audit_f24f_western_chess_perft import standard_engine, position_from_fen
from scripts.audit_physical_placement_sampling import substituted
from scripts.audit_secured_exchange_common_context import Budget, task_success

PROTOCOL = ROOT / 'docs/research/FOCAL_SURVIVAL_DIAGNOSTIC_PROTOCOL.md'
PROTOCOL_SHA = '3e22a06cd9e2da74a0639259f62a11264a39f6ec7baeee2b82cf621279a7d0f8'
INPUT = ROOT / 'docs/research/data/physical_placement_sampling_20261003.json'


def dual_root(compiled, position, budget):
    state = synthetic_state(compiled, position)
    if state.terminal_status.is_terminal:
        raise ValueError('frozen diagnostic requires ongoing roots')
    n = compiled.board_size
    anchors = {tid for tid, item in compiled.support.type_metadata.items() if item.is_anchor}
    baseline = custody(position, anchors); actions = []
    for handle in iter_legal_successor_handles(state, compiled, checkpoint=budget.checkpoint):
        action = handle.action; source = getattr(action, 'from_square', None)
        if source is None or (source.file, source.rank) != (3, 3):
            continue
        child = budget.child(state, handle, compiled)
        target = action.to_square.rank * n + action.to_square.file
        actor = child.position.board[target]
        if actor is None or actor.owner != 0:
            raise ValueError('acting token not tracked by this board-action scope')
        immediate_gain = custody(child.position, anchors) - baseline
        net = True; local = True; count = 0; losses = 0; background = 0
        first_local = None; first_net = None
        def local_success(after):
            terminal = after.terminal_status
            if terminal.is_terminal:
                if terminal.status.value == 'no_contest':
                    raise ValueError('no-contest outside task scope')
                return terminal.winner == 0
            return immediate_gain > 0 and after.position.board[target] == actor
        if child.terminal_status.is_terminal:
            net = task_success(child, anchors, baseline); local = local_success(child)
        else:
            for reply in iter_legal_successor_handles(child, compiled, checkpoint=budget.checkpoint):
                after = budget.child(child, reply, compiled); count += 1
                net_ok = task_success(after, anchors, baseline); local_ok = local_success(after)
                net = net and net_ok; local = local and local_ok
                if not net_ok and first_net is None:
                    first_net = action_to_dict(reply.action)
                if not local_ok and first_local is None:
                    first_local = action_to_dict(reply.action)
                if immediate_gain > 0:
                    losses += int(after.position.board[target] != actor)
                    background += int(local_ok and not net_ok)
            if count == 0:
                raise ValueError('empty nonterminal reply set; incomplete evidence')
        actions.append({'action': action_to_dict(action), 'immediate_gain': immediate_gain,
                        'reply_count': count, 'net_success': net, 'local_success': local,
                        'focal_loss_replies': losses, 'local_ok_net_failure_replies': background,
                        'first_net_refutation': first_net, 'first_local_refutation': first_local})
    budget.checkpoint()
    return {'net_score': int(any(a['net_success'] for a in actions)),
            'local_score': int(any(a['local_success'] for a in actions)), 'actions': actions}


def audit(budget=None):
    if hashlib.sha256(PROTOCOL.read_bytes()).hexdigest() != PROTOCOL_SHA:
        raise ValueError('frozen local-survival protocol changed')
    data = json.loads(INPUT.read_text())
    if not data['complete'] or len(data['roots']) != 12:
        raise ValueError('complete frozen physical roots required')
    if data['program_sha256'] != hashlib.sha256((ROOT / 'scripts/audit_physical_placement_sampling.py').read_bytes()).hexdigest():
        raise ValueError('sampling source changed; no silent input rebase')
    budget = budget or Budget(); chess, _ = standard_engine()
    games = {'chess': chess, 'shogi': compile_ruleset_for_execution(build_standard_shogi_ruleset())}
    rows = []
    for row in data['roots']:
        game = row['game']; compiled = games[game]
        template = (position_from_fen('8/8/8/8/8/8/8/8 w - - 0 1', compiled)
                    if game == 'chess' else initial_state(compiled).position)
        board = tuple(None if p is None else Piece(*p) for p in data['games'][game]['physical_board'])
        position = substituted(replace(template, board=board), row['focal_type'], compiled)
        result = dual_root(compiled, position, budget)
        assert result['net_score'] == row['success']
        assert [a['action'] for a in result['actions']] == [a['action'] for a in row['actions']]
        assert [a['reply_count'] for a in result['actions']] == [a['reply_count'] for a in row['actions']]
        rows.append({'population': 'frozen_full_inventory', 'game': game, 'focal_type': row['focal_type'], **result})
    for game, compiled in games.items():
        for exposed in (False, True):
            result = dual_root(compiled, position_for(compiled, game, exposed), budget)
            rows.append({'population': 'background_control', 'game': game, 'focal_type': 'R',
                         'background': 'exposed' if exposed else 'shifted', **result})
    return {'protocol_sha256': PROTOCOL_SHA,
            'program_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            'input_sha256': hashlib.sha256(INPUT.read_bytes()).hexdigest(),
            'complete': True, 'roots': rows, 'materialized_transitions': budget.transitions,
            'elapsed_seconds': monotonic() - budget.started}


if __name__ == '__main__':
    result = audit()
    if len(sys.argv) > 1:
        Path(sys.argv[1]).write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({**{k: v for k, v in result.items() if k != 'roots'},
                      'scores': [{k: v for k, v in r.items() if k != 'actions'} for r in result['roots']]}, indent=2))
