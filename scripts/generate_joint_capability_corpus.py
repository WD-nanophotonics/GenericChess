"""New frozen corpus via law-preserving intrinsic joint sampler; no labels."""
from collections import Counter
from dataclasses import replace
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
from generic_chess.core.lazy_transitions import iter_legal_successor_handles
from generic_chess.core.transition import initial_state
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.standard_shogi import build_standard_shogi_ruleset
from scripts.audit_actual_inventory_sampling import sample_actual_frame, rejection_reason
from scripts.audit_exchange_custody import synthetic_state
from scripts.audit_f24f_western_chess_perft import standard_engine
from scripts.audit_post_capture_scope import capture_key, state_evidence
from scripts.audit_secured_exchange_common_context import Budget

from scripts.generate_capability_corpus import own_counts, type_captures
from scripts.audit_joint_actual_frame import ShogiJointSampler

PROTOCOL = ROOT / 'docs/research/JOINT_CAPABILITY_CORPUS_PROTOCOL.md'
PROTOCOL_SHA = 'e5d8ced1854bfada7b0ae6914b41d77ec0bd672a94e666eee192e0f660bb6caa'


def generate(budget=None, reference_limit=128, stratum_limit=128):
    if hashlib.sha256(PROTOCOL.read_bytes()).hexdigest() != PROTOCOL_SHA:
        raise ValueError('frozen corpus protocol changed')
    if not 1 <= reference_limit <= 128 or not 1 <= stratum_limit <= 128:
        raise ValueError('proposal gates must remain at most 128')
    budget = budget or Budget(seconds=25, transitions_limit=5000)
    chess, _ = standard_engine()
    shogi = compile_ruleset_for_execution(build_standard_shogi_ruleset())
    joint = ShogiJointSampler(shogi, budget)
    def sample(compiled, game, rng):
        return joint.sample(rng) if game == 'shogi' else sample_actual_frame(compiled, game, rng)
    result = {'protocol_sha256': PROTOCOL_SHA,
              'program_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              'dependency_sha256': {name: hashlib.sha256((ROOT / 'scripts' / name).read_bytes()).hexdigest()
                                    for name in ('audit_joint_actual_frame.py', 'audit_file_joint_unrank.py',
                                                 'audit_file_joint_count.py', 'audit_actual_inventory_sampling.py',
                                                 'generate_capability_corpus.py')},
              'complete': False, 'games': {}, 'scope': 'unlabelled finite pilot; no task scores or coefficients'}
    for game, compiled, ref_seed, dep_seed in (
            ('chess', chess, 202610040501, 202610040601),
            ('shogi', shogi, 202610040502, 202610040701)):
        reference = []; rejected = Counter(); rng = Random(ref_seed)
        for attempt in range(1, reference_limit + 1):
            budget.checkpoint(); position = sample(compiled, game, rng)
            reason = rejection_reason(compiled, position, game, budget)
            if reason == 'dead_nonpawn_placement':
                raise ValueError('joint sampler emitted intrinsic dead placement')
            if reason:
                rejected[reason] += 1
                continue
            reference.append(state_evidence(synthetic_state(compiled, position), compiled))
            if len(reference) == 4:
                break
        initial_counts = own_counts(compiled, initial_state(compiled).position)
        entry = {'initial_counts': dict(initial_counts), 'reference_seed': ref_seed,
                 'reference_proposals': attempt, 'reference_rejected': dict(rejected),
                 'reference': reference, 'deployment': []}
        result['games'][game] = entry
        if len(reference) != 4:
            result['failure'] = f'{game}: incomplete four-root reference'
            break
        reference_boards = {json.dumps(r['physical_board']) for r in reference}
        for index, kind in enumerate(sorted(initial_counts)):
            rng = Random(dep_seed + index); rejected = Counter(); selected = None
            for attempt in range(1, stratum_limit + 1):
                budget.checkpoint(); position = sample(compiled, game, rng)
                reason = rejection_reason(compiled, position, game, budget)
                if reason == 'dead_nonpawn_placement':
                    raise ValueError('joint sampler emitted intrinsic dead placement')
                if reason:
                    rejected['Q:' + reason] += 1
                    continue
                parent = synthetic_state(compiled, replace(position, side_to_move=1))
                candidates = type_captures(compiled, parent, kind, budget)
                if not candidates:
                    rejected['no_ongoing_type_capture'] += 1
                    continue
                action, child = rng.choice(candidates)
                parent_evidence = state_evidence(parent, compiled)
                if json.dumps(parent_evidence['physical_board']) in reference_boards:
                    raise ValueError('reference/deployment-parent overlap; frozen run rejected')
                expected = initial_counts.copy(); expected[kind] -= 1
                if own_counts(compiled, child.position) != +expected or child.position.side_to_move != 0 or child.position.hands[0].total():
                    raise ValueError('unexpected deployment inventory/owner/hand scope')
                selected = {'victim_type': kind, 'seed': dep_seed + index,
                            'capture_candidates': len(candidates), 'selected_action': action,
                            'parent': parent_evidence, 'child': state_evidence(child, compiled)}
                break
            entry['deployment'].append({'victim_type': kind, 'proposals': attempt,
                                        'rejected': dict(rejected), 'selected': selected})
            if selected is None:
                result['failure'] = f'{game}: incomplete {kind} deployment stratum'
                break
        if 'failure' in result:
            break
    budget.checkpoint()
    result['complete'] = len(result['games']) == 2 and 'failure' not in result
    result['materialized_capture_transitions'] = budget.transitions
    result['elapsed_seconds'] = monotonic() - budget.started
    return result


if __name__ == '__main__':
    result = generate()
    if len(sys.argv) > 1:
        Path(sys.argv[1]).write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8', newline='\n')
    print(json.dumps({k: v for k, v in result.items() if k != 'games'}, indent=2))
    print(json.dumps({game: {'reference_roots': len(row['reference']),
                             'strata': {d['victim_type']: d['proposals'] for d in row['deployment']},
                             'complete_strata': sum(d['selected'] is not None for d in row['deployment'])}
                      for game, row in result['games'].items()}, indent=2))
