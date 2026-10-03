"""Bounded existence search, never a sequentially stopped population estimate."""
from collections import Counter
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
from generic_chess.rules.standard_shogi import build_standard_shogi_ruleset
from scripts.audit_f24f_western_chess_perft import standard_engine
from scripts.audit_physical_placement_sampling import sample_frame, rejection_reason, substituted, serialize_board, SEED
from scripts.audit_secured_exchange_common_context import Budget, root_score

PROTOCOL = ROOT / 'docs/research/PHYSICAL_EXCHANGE_SUPPORT_PROTOCOL.md'
PROTOCOL_SHA = '73660ce449d0f5ca64fc61123dfc2c20bbf81224e601b722d22dcb27fbfbe94a'
SAMPLER = ROOT / 'scripts/audit_physical_placement_sampling.py'
SAMPLER_SHA = '717e03547c326ef2300a370d25f8a158a65497ff608c131471b8362b1f192954'


def audit(budget=None, proposal_limit=128, frame_limit=8):
    if hashlib.sha256(PROTOCOL.read_bytes()).hexdigest() != PROTOCOL_SHA:
        raise ValueError('frozen support protocol changed')
    if hashlib.sha256(SAMPLER.read_bytes()).hexdigest() != SAMPLER_SHA:
        raise ValueError('frozen physical sampler changed')
    budget = budget or Budget(); rng = Random(SEED)
    chess, _ = standard_engine()
    shogi = compile_ruleset_for_execution(build_standard_shogi_ruleset())
    result = {'protocol_sha256': PROTOCOL_SHA, 'sampler_sha256': SAMPLER_SHA,
              'program_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              'seed': SEED, 'complete': True, 'games': {}, 'roots': [],
              'interpretation': 'support witnesses only; no population averages'}
    for game, compiled in [('chess', chess), ('shogi', shogi)]:
        rejected = Counter(); attempts = 0; scored = 0; status = 'incomplete'
        for attempts in range(1, proposal_limit + 1):
            budget.checkpoint()
            candidate = sample_frame(compiled, game, rng)
            reason = rejection_reason(candidate, game, compiled, budget)
            if reason:
                rejected[reason] += 1
                continue
            position = substituted(candidate, 'R', compiled)
            row = root_score(compiled, position, budget); scored += 1
            result['roots'].append({'game': game, 'proposal': attempts,
                                    'physical_board': serialize_board(candidate), **row})
            if row['success']:
                status = 'witness'; break
            if scored >= frame_limit:
                status = 'no_witness_within_cap'; break
        result['games'][game] = {'status': status, 'proposals': attempts,
                                 'scored_frames': scored, 'rejected': dict(rejected)}
        if status == 'incomplete':
            result['complete'] = False
    result.update(materialized_transitions=budget.transitions, elapsed_seconds=monotonic() - budget.started)
    return result


if __name__ == '__main__':
    result = audit()
    if len(sys.argv) > 1:
        Path(sys.argv[1]).write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({k: v for k, v in result.items() if k != 'roots'}, indent=2))
