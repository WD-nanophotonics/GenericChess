"""Replay only the frozen pilot's first refutations; no new search or sampling."""
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
from generic_chess.core.transition import initial_state, apply_action
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.standard_shogi import build_standard_shogi_ruleset
from scripts.audit_exchange_custody import custody, synthetic_state
from scripts.audit_f24f_western_chess_perft import standard_engine, position_from_fen
from scripts.audit_physical_placement_sampling import substituted


def diagnose(data):
    if not data.get('complete') or data.get('seed') != 20261003:
        raise ValueError('complete frozen sampling evidence required')
    chess, _ = standard_engine()
    games = {'chess': chess, 'shogi': compile_ruleset_for_execution(build_standard_shogi_ruleset())}
    started = monotonic(); counts = Counter(); witnesses = []; transitions = 0
    def checkpoint():
        if monotonic() - started > 10 or transitions >= 100:
            raise RuntimeError('frozen-refutation replay cap; no complete diagnosis')
    for row in data['roots']:
        game = row['game']; compiled = games[game]; n = compiled.board_size
        template = (position_from_fen('8/8/8/8/8/8/8/8 w - - 0 1', compiled)
                    if game == 'chess' else initial_state(compiled).position)
        board = tuple(None if p is None else Piece(*p) for p in data['games'][game]['physical_board'])
        position = substituted(replace(template, board=board), row['focal_type'], compiled)
        state = synthetic_state(compiled, position)
        anchors = {tid for tid, item in compiled.support.type_metadata.items() if item.is_anchor}
        baseline = custody(position, anchors)
        for record in row['actions']:
            checkpoint()
            action = action_from_dict(record['action'])
            child = apply_action(state, action, compiled); transitions += 1
            gain = custody(child.position, anchors) - baseline
            if gain <= 0:
                counts['no_immediate_custody_gain'] += 1
                continue
            ref = record['first_refutation']
            if ref is None:
                counts['immediate_gain_not_refuted'] += 1
                continue
            reply = action_from_dict(ref['action'])
            checkpoint()
            after = apply_action(child, reply, compiled); transitions += 1
            assert custody(after.position, anchors) - baseline == ref['custody_delta']
            assert after.terminal_status.status.value == ref['terminal']
            destination = getattr(reply, 'to_square', None)
            victim = None if destination is None else child.position.board[destination.rank * n + destination.file]
            focal_destination = (action.to_square.file, action.to_square.rank)
            same_focal = destination is not None and (destination.file, destination.rank) == focal_destination
            if after.terminal_status.is_terminal:
                cause = 'terminal_refutation'
            elif victim is not None and victim.owner == 0:
                cause = 'focal_recapture' if same_focal else 'other_token_countercapture'
            else:
                cause = 'other_refutation'
            counts[cause] += 1
            witnesses.append({'game': game, 'focal_type': row['focal_type'], 'first_action': record['action'],
                              'immediate_gain': gain, 'first_refutation': ref, 'cause': cause})
    return {'program_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            'input_content_sha256': hashlib.sha256(json.dumps(data, sort_keys=True, separators=(',', ':')).encode()).hexdigest(),
            'counts': dict(counts), 'gain_action_witnesses': witnesses,
            'replayed_transitions': transitions, 'elapsed_seconds': monotonic() - started,
            'scope': 'first recorded refutation of each immediate-gain action only; not all refutation causes'}


if __name__ == '__main__':
    data = json.loads(Path(sys.argv[1]).read_text(encoding='utf-8'))
    result = diagnose(data)
    if len(sys.argv) > 2:
        Path(sys.argv[2]).write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({k: v for k, v in result.items() if k != 'gain_action_witnesses'}, indent=2))
