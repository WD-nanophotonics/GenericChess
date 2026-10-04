"""Replay frozen Chess proposals after a source-qualified Pawn guard repair."""
from collections import Counter
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
from random import Random
import sys
from time import monotonic

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.western_chess import build_western_chess_ruleset
from scripts.audit_physical_placement_sampling import serialize_board
from scripts.audit_resource_mode_feasibility import STRATA, canonical_choice
from scripts.public_goal_intervals import PublicGame
from scripts.resource_mode_structure import ongoing_resource_root
from scripts.sample_resource_modes import sample_resource_mode

PROTOCOL = 'docs/research/RESOURCE_MODE_FEASIBILITY_CORRECTION.md'
PROTOCOL_SHA = '3109f8390af7cd804be56cf1a06d0e83fed42f919184cc04991d36a41c4119a3'
ORIGINAL = 'docs/research/data/resource_mode_feasibility_20261004.json'
ORIGINAL_SHA = 'd7b18b86386b99fde59fd1da383fdad5a6d3b7b0656997d2d9da7a916438f72f'


def audit():
    started = monotonic(); rows = []; stopped = None
    for path, expected in ((PROTOCOL, PROTOCOL_SHA), (ORIGINAL, ORIGINAL_SHA)):
        if hashlib.sha256((ROOT/path).read_bytes()).hexdigest() != expected:
            raise ValueError('immutable correction input changed')
    original = json.loads((ROOT/ORIGINAL).read_text(encoding='utf-8'))
    for path, expected in original['sha256'].items():
        if hashlib.sha256((ROOT/path).read_bytes()).hexdigest() != expected:
            raise ValueError('original pinned source changed')
    enumerated = original['enumerated_choices']
    def checkpoint():
        if monotonic()-started + original['elapsed_seconds'] >= 15:
            raise TimeoutError('combined original/correction15-second cap')
    try:
        compiled = compile_ruleset_for_execution(build_western_chess_ruleset())
        for game, mode, seed, allowance in STRATA[:3]:
            checkpoint(); rng = Random(seed); rejected = Counter()
            row = {'game': game, 'mode': mode, 'seed': seed, 'allocation': allowance,
                   'proposals': 0, 'rejected': {}, 'admitted': False,
                   'choices_complete': False, 'canonical_choices': []}
            rows.append(row)
            for attempt in range(1, allowance+1):
                checkpoint(); row['proposals'] = attempt
                position, tag, reason = sample_resource_mode(compiled, game, mode, rng)
                if reason is None:
                    state, reason = ongoing_resource_root(compiled, position, game, checkpoint)
                if reason:
                    rejected[reason] += 1; row['rejected'] = dict(rejected); continue
                row.update(admitted=True, board=serialize_board(position),
                           hands=[dict(h.items()) for h in position.hands],
                           tag={**tag, 'board': {str(k): str(v) for k, v in tag['board'].items()},
                                'held': str(tag['held']), 'lost': str(tag['lost'])},
                           aux_state=position.aux_state, history=[asdict(h) for h in state.history],
                           ply_count=state.ply_count, repetition_counts=state.repetition_counts)
                for action in PublicGame(compiled).actions(state, checkpoint):
                    checkpoint(); enumerated += 1; key = canonical_choice(action)
                    if key in row['canonical_choices']:
                        raise ValueError('duplicate canonical complete choice')
                    row['canonical_choices'].append(key)
                    if len(row['canonical_choices']) > 128:
                        row['choice_stop'] = 'root_choice_cap'; break
                    if enumerated > 5000:
                        raise TimeoutError('combined5000 enumeration cap')
                else:
                    if not row['canonical_choices']:
                        raise ValueError('ongoing empty choice set')
                    row['choices_complete'] = True
                break
        checkpoint()
    except TimeoutError as exc:
        stopped = str(exc)
    rows += [r for r in original['strata'] if r['game'] == 'shogi']
    paths = [PROTOCOL, 'scripts/audit_resource_mode_correction.py',
             'scripts/resource_mode_structure.py', 'tests/test_resource_mode_context.py']
    return {'complete': len(rows) == 6 and all(r['admitted'] and r['choices_complete'] for r in rows),
            'scope': 'same-stream source correction; synthetic root feasibility only',
            'original_report_sha256': ORIGINAL_SHA, 'original_source_sha256': original['sha256'],
            'original_invalid_chess_guard_examinations': 128,
            'strata': rows, 'enumerated_choices_including_original': enumerated,
            'public_transitions': 0, 'stop_reason': stopped,
            'correction_elapsed_seconds': monotonic()-started,
            'combined_elapsed_seconds': monotonic()-started+original['elapsed_seconds'],
            'sha256': {p: hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in paths}}


if __name__ == '__main__':
    result = audit()
    if len(sys.argv) > 1:
        (ROOT/sys.argv[1]).write_text(json.dumps(result, indent=2)+'\n', encoding='utf-8', newline='\n')
    print(json.dumps({k: v for k, v in result.items() if k not in
                     ('strata', 'sha256', 'original_source_sha256')}, indent=2))
    print(json.dumps([{k: r[k] for k in ('game', 'mode', 'proposals', 'rejected', 'admitted', 'choices_complete')}
                     | {'choices': len(r['canonical_choices'])} for r in result['strata']], indent=2))
