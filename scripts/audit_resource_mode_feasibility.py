"""Six frozen origin-refined root observations; no child/value/goal sampling."""
from collections import Counter
from dataclasses import asdict, replace
import hashlib
import json
from pathlib import Path
from random import Random
import sys
from time import monotonic

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from generic_chess.core.actions import action_to_dict
from generic_chess.core.declarations import DeclarationAssessment
from generic_chess.core.identity import repetition_identity_key
from generic_chess.core.position import HistoryRecord
from generic_chess.core.semantic_executor import semantic_engine_for
from generic_chess.core.transition import initial_state
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.standard_shogi import build_standard_shogi_ruleset
from generic_chess.rules.western_chess import build_western_chess_ruleset
from scripts.audit_physical_placement_sampling import serialize_board
from scripts.public_goal_intervals import PublicGame
from scripts.sample_resource_modes import sample_resource_mode

PROTOCOL = 'docs/research/RESOURCE_MODE_FEASIBILITY_PROTOCOL.md'
PROTOCOL_SHA = '90894e85bf19423bafd975d11a49f9427e7c75e2ca40a8d98b4ccd52a8097aa0'
STRATA = (
    ('chess', ('board', 'P', 'P'), 20261004101, 42),
    ('chess', ('board', 'P', 'Q'), 20261004102, 42),
    ('chess', ('board', 'Q', 'Q'), 20261004103, 44),
    ('shogi', ('board', 'P', 'P'), 20261004104, 42),
    ('shogi', ('board', 'P', 'TP'), 20261004105, 42),
    ('shogi', ('hand', 'P'), 20261004106, 44),
)


def canonical_choice(action):
    payload = {'claim': asdict(action)} if isinstance(action, DeclarationAssessment) else action_to_dict(action)
    return json.dumps(payload, sort_keys=True, separators=(',', ':'))


def ongoing_root(compiled, position, game, checkpoint):
    """Declared synthetic boundary; subsequent actual children never reset it."""
    files = Counter()
    for square, piece in enumerate(position.board):
        checkpoint()
        if piece is None:
            continue
        if not compiled.support.empty_mobility[piece.current_type_id][piece.owner][square]:
            return None, 'dead_board_mode'
        if piece.current_type_id == 'P':
            if game == 'chess' and square//8 in (0, 7):
                return None, 'pawn_terminal_rank'
            files[piece.owner, square % compiled.board_size] += 1
    if game == 'shogi' and any(n > 1 for n in files.values()):
        return None, 'nifu'
    engine = semantic_engine_for(compiled)
    if any(engine.in_check(position, owner, checkpoint=checkpoint) for owner in (0, 1)):
        return None, 'anchor_check'
    key = repetition_identity_key(position, compiled)
    counts = ((key, 1),); history = (HistoryRecord(key, -1, '', False),)
    terminal = engine.terminal_result(position, 0, counts, history, checkpoint=checkpoint)
    if terminal.is_terminal:
        return None, 'terminal_root'
    return replace(initial_state(compiled), position=position, repetition_counts=counts,
                   history=history, terminal_status=terminal), None


def audit():
    started = monotonic(); enumerated = 0; rows = []; stopped = None
    def checkpoint():
        if monotonic()-started >= 15:
            raise TimeoutError('15-second resource-mode root cap')
    if hashlib.sha256((ROOT/PROTOCOL).read_bytes()).hexdigest() != PROTOCOL_SHA:
        raise ValueError('frozen resource-mode feasibility protocol changed')
    try:
        compiled_games = {'chess': compile_ruleset_for_execution(build_western_chess_ruleset()),
                          'shogi': compile_ruleset_for_execution(build_standard_shogi_ruleset())}
        for game, mode, seed, allowance in STRATA:
            checkpoint(); rng = Random(seed)
            row = {'game': game, 'mode': mode, 'seed': seed, 'allocation': allowance,
                   'proposals': 0, 'rejected': {}, 'admitted': False,
                   'choices_complete': False, 'canonical_choices': []}
            rows.append(row); rejected = Counter()
            for attempt in range(1, allowance+1):
                checkpoint(); row['proposals'] = attempt
                position, tag, reason = sample_resource_mode(compiled_games[game], game, mode, rng)
                if reason is None:
                    state, reason = ongoing_root(compiled_games[game], position, game, checkpoint)
                if reason:
                    rejected[reason] += 1; row['rejected'] = dict(rejected)
                    continue
                row.update(admitted=True, board=serialize_board(position),
                           hands=[dict(h.items()) for h in position.hands],
                           tag={**tag, 'board': {str(k): str(v) for k, v in tag['board'].items()},
                                'held': str(tag['held']), 'lost': str(tag['lost'])},
                           aux_state=position.aux_state, history=[asdict(h) for h in state.history],
                           ply_count=state.ply_count, repetition_counts=state.repetition_counts)
                for action in PublicGame(compiled_games[game]).actions(state, checkpoint):
                    checkpoint(); enumerated += 1
                    key = canonical_choice(action)
                    if key in row['canonical_choices']:
                        raise ValueError('duplicate canonical complete choice')
                    row['canonical_choices'].append(key)
                    if len(row['canonical_choices']) > 128:
                        row['choice_stop'] = 'root_choice_cap'; break
                    if enumerated > 5000:
                        raise TimeoutError('global5000 enumeration cap')
                else:
                    if not row['canonical_choices']:
                        raise ValueError('ongoing root has no complete choices')
                    row['choices_complete'] = True
                break  # Admission is immutable, including an incomplete choice set.
        checkpoint()
    except TimeoutError as exc:
        stopped = str(exc)
    paths = [PROTOCOL, 'docs/research/RESOURCE_MODE_CONTEXT_DESIGN.md',
             'scripts/audit_resource_mode_feasibility.py', 'scripts/sample_resource_modes.py',
             'scripts/resource_mode_context.py', 'scripts/owned_tag_trace.py',
             'scripts/public_goal_intervals.py', 'generic_chess/core/semantic_executor.py',
             'generic_chess/core/transition.py', 'generic_chess/rules/western_chess.py',
             'generic_chess/rules/standard_shogi.py']
    return {'complete': len(rows) == 6 and all(r['admitted'] and r['choices_complete'] for r in rows),
            'scope': 'synthetic full-resource root feasibility, no coefficient/goal/path samples',
            'strata': rows, 'enumerated_choices': enumerated, 'public_transitions': 0,
            'stop_reason': stopped, 'elapsed_seconds': monotonic()-started,
            'sha256': {p: hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in paths}}


if __name__ == '__main__':
    result = audit()
    if len(sys.argv) > 1:
        (ROOT/sys.argv[1]).write_text(json.dumps(result, indent=2)+'\n', encoding='utf-8', newline='\n')
    print(json.dumps({k: v for k, v in result.items() if k not in ('strata', 'sha256')}, indent=2))
    print(json.dumps([{k: v for k, v in r.items() if k not in
                      ('board', 'hands', 'tag', 'aux_state', 'history', 'repetition_counts', 'canonical_choices')}
                     | {'visited_choices': len(r['canonical_choices'])} for r in result['strata']], indent=2))
