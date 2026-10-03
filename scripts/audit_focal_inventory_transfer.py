"""Inventory invariant gives a conditional support-separation certificate."""
from collections import Counter
import hashlib
import json
from pathlib import Path
import sys
from time import monotonic

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from generic_chess.core.transition import initial_state
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.standard_shogi import build_standard_shogi_ruleset
from scripts.audit_f24f_western_chess_perft import standard_engine

PROTOCOL = ROOT / 'docs/research/FOCAL_INVENTORY_TRANSFER_PROTOCOL.md'
PROTOCOL_SHA = '3bb8a0b07abad43a196ab08094afc610fae5159804cb2938774f156f1e092a89'
SAMPLER = ROOT / 'scripts/audit_physical_placement_sampling.py'
SAMPLER_SHA = '717e03547c326ef2300a370d25f8a158a65497ff608c131471b8362b1f192954'


def inventory(position):
    return Counter((piece.owner, piece.base_type_id) for piece in position.board if piece)


def vector(counts):
    return [{'owner': owner, 'type': tid, 'count': count} for (owner, tid), count in sorted(counts.items()) if count]


def audit(seconds=5):
    for path, digest in [(PROTOCOL, PROTOCOL_SHA), (SAMPLER, SAMPLER_SHA)]:
        if hashlib.sha256(path.read_bytes()).hexdigest() != digest:
            raise ValueError('frozen transfer protocol/source changed')
    started = monotonic(); chess, _ = standard_engine()
    shogi = compile_ruleset_for_execution(build_standard_shogi_ruleset()); rows = []
    for game, compiled in [('chess', chess), ('shogi', shogi)]:
        actual = inventory(initial_state(compiled).position)
        types = sorted(tid for owner, tid in actual if owner == 0 and not compiled.support.type_metadata[tid].is_anchor)
        for tid in types:
            if monotonic() - started > seconds:
                raise TimeoutError('inventory transfer audit time cap')
            query = actual.copy(); query[(0, 'P')] -= 1; query[(0, tid)] += 1
            distance = sum(abs(query[key] - actual[key]) for key in set(query) | set(actual))
            rows.append({'game': game, 'query_type': tid, 'query_inventory': vector(query),
                         'actual_inventory': vector(actual), 'count_l1_distance': distance,
                         'disjoint_inventory_support': distance > 0,
                         'position_space_tv_if_both_laws_exist': 1 if distance else None,
                         'interpretation': 'trivial bounded-task transfer bound' if distance else 'inventory alone does not identify TV'})
    return {'protocol_sha256': PROTOCOL_SHA, 'sampler_sha256': SAMPLER_SHA,
            'program_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            'complete': True, 'rows': rows, 'elapsed_seconds': monotonic() - started,
            'scope': 'symbolic invariant; neither reference nonemptiness nor task mean difference proved'}


if __name__ == '__main__':
    result = audit()
    if len(sys.argv) > 1:
        Path(sys.argv[1]).write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8', newline='\n')
    print(json.dumps({**{k: v for k, v in result.items() if k != 'rows'},
                     'comparisons': [{k: v for k, v in row.items() if k not in ('query_inventory', 'actual_inventory')} for row in result['rows']]}, indent=2))
