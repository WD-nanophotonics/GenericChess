"""Feature expressiveness on all saved choices, without new game events."""
from pathlib import Path
from time import monotonic
import hashlib
import json
import sys
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT))
from scripts.research_record import write_record
OUT = ROOT/'docs/research/data/shallow_reference_features_20261006.json'
RAW = 'docs/research/data/lichess_complete_children_20261006.json'
SOURCES = ('scripts/audit_shallow_reference_features.py',
           'docs/research/SHALLOW_REFERENCE_FEATURE_PROTOCOL.md', 'scripts/research_record.py', RAW)


def vector(state):
    result = dict.fromkeys('PNBRQ', 0)
    for p in state['position']['board']:
        if p and p['current_type_id'] != 'K': result[p['current_type_id']] += 1 if p['owner'] == 0 else -1
    return result


def main():
    if OUT.exists(): raise FileExistsError('feature obstruction never rerun')
    start = monotonic()
    r = dict(complete=False, action_deltas={}, feature_groups={}, mode_terms=0,
             public_transitions=0, runtime_pushes=0, source_queries=0,
             source_sha256={p: hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in SOURCES})
    try:
        raw = json.loads((ROOT/RAW).read_text())
        if not raw['complete'] or not raw['source_hashes_unchanged']: raise ValueError('complete saved child table required')
        for p, digest in raw['source_sha256'].items():
            if hashlib.sha256((ROOT/p).read_bytes()).hexdigest() != digest: raise ValueError('input drift')
        before = vector(raw['root']); r['root_vector'] = before
        for key, child in raw['children'].items():
            after = vector(child); delta = {m: after[m]-before[m] for m in before}
            r['mode_terms'] += 5; r['action_deltas'][key] = delta
            signature = repr(tuple(delta[m] for m in 'PNBRQ'))
            r['feature_groups'].setdefault(signature, []).append(key)
            if r['mode_terms'] > 256 or monotonic()-start >= 15: raise ValueError('finite feature budget')
        zero = dict.fromkeys('PNBRQ', 0); capture = {**zero, 'P': 1}
        r['all_deltas_zero_or_enemy_pawn_capture'] = all(v in (zero, capture) for v in r['action_deltas'].values())
        answer = next(iter(raw['reference_comparison'].values()))['advertised_answer']
        reference = [key for key, s in raw['source_checks'].items() if s['uci'] == answer]
        if len(reference) != 1: raise ValueError('unique reference action identity required')
        r['reference_action'] = reference[0]; r['reference_delta'] = r['action_deltas'][reference[0]]
        r['quiet_count'] = sum(v == zero for v in r['action_deltas'].values())
        r['capture_count'] = sum(v == capture for v in r['action_deltas'].values())
        r['positive_pawn_price_cannot_select_reference_proved'] = r['all_deltas_zero_or_enemy_pawn_capture'] and r['reference_delta'] == zero and r['capture_count'] > 0
        r['actual_quantized_pawn_weights'] = {law: policy['integer_weights']['P'] for law, policy in raw['policies'].items()}
        r['complete'] = True
    except Exception as error: r['error'] = f'{type(error).__name__}: {error}'
    r['seconds'] = monotonic()-start
    r['source_hashes_unchanged'] = all(hashlib.sha256((ROOT/p).read_bytes()).hexdigest() == digest for p, digest in r['source_sha256'].items())
    write_record(OUT, r)
    print(json.dumps({k: v for k, v in r.items() if k not in ('source_sha256', 'action_deltas', 'feature_groups')}))


if __name__ == '__main__': main()
