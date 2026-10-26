"""Independent saved-byte consumer. Never imports/calls the producer or Player."""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from datetime import datetime
import gzip
import hashlib
import json
from pathlib import Path
from statistics import median
import time

from generic_chess.rules.schema import ruleset_from_dict, compute_fingerprint
from generic_chess.rules.compiler import compile_legacy_ruleset_for_semantic_execution
from generic_chess.session.session import GameSession
from generic_chess.session.serialization import deserialize_game_record
from scripts.research_record import record_value, write_record


TIMING = {'elapsed_seconds', 'time_to_first_legal_action', 'time_to_first_completed_iteration',
          'ordering_seconds', 'legal_generation_seconds', 'evaluation_seconds'}


def original_bytes(path):
    path = Path(path)
    if not path.exists():
        path = Path(str(path) + '.gz')
    b = path.read_bytes()
    return gzip.decompress(b) if path.suffix == '.gz' else b


def load(path):
    return json.loads(original_bytes(path))


def verify_public_manifest(path):
    path = Path(path)
    root = path.parent.resolve()
    manifest = json.loads(path.read_bytes())
    for name, entry in manifest['members'].items():
        target = (root / (name + '.gz')).resolve()
        assert target.is_relative_to(root) and target.is_file()
        compressed = target.read_bytes(); raw = gzip.decompress(compressed)
        assert hashlib.sha256(compressed).hexdigest() == entry['gzip_sha256'], name
        assert hashlib.sha256(raw).hexdigest() == entry['original_sha256'], name
        assert len(raw) == entry['original_bytes'], name
    return len(manifest['members'])


def full_digest(record):
    return hashlib.sha256(json.dumps(record_value(record), sort_keys=True,
                                    separators=(',', ':')).encode()).hexdigest()


def decision_fields(raw):
    return {k: v for k, v in raw.items() if k not in TIMING}


def native_counts(raw):
    return {g: {k: v for k, v in group.items() if not k.endswith('seconds')}
            for g, group in raw.items()}


def acceptance(pairs, root_ids, setup):
    """Frozen engineering gate; missing is not zero or a replacement slot."""
    eligible = [p for p in pairs if p['eligible']]
    eligible_keys = {(p['case_id'], p['depth'], p['repetition']) for p in eligible}
    coverage = {str(d): sum(all((r, d, k) in eligible_keys for k in range(3))
                           for r in root_ids) for d in (3, 6)}
    base = sum(p['off_seconds'] for p in eligible)
    on = sum(p['on_seconds'] for p in eligible) + setup['candidate_import_wall_seconds']
    base_cpu = sum(p['off_cpu'] for p in eligible)
    on_cpu = sum(p['on_cpu'] for p in eligible) + setup['candidate_import_cpu_seconds']
    ratios = {r: median(p['ratio'] for p in eligible if p['case_id'] == r)
              for r in root_ids if any(p['case_id'] == r for p in eligible)}
    total_ratio = on / base if base else None
    cpu_ratio = on_cpu / base_cpu if base_cpu else None
    gates = {'coverage_each_depth': all(x >= 10 for x in coverage.values()),
             'at_least_5pct_wall_gain': total_ratio is not None and total_ratio <= 0.95,
             'eight_root_medians_faster': sum(v < 1 for v in ratios.values()) >= 8,
             'no_root_median_over_1_10': bool(ratios) and max(ratios.values()) <= 1.10,
             'no_CPU_regression': cpu_ratio is not None and cpu_ratio <= 1}
    result = ('UNKNOWN' if not gates['coverage_each_depth'] else
              'SCOPED_ENGINEERING_GO' if all(gates.values()) else 'NO_GO')
    return {'decision': result, 'eligible_pairs': len(eligible),
            'complete_root_triplets': coverage, 'gates': gates,
            'off_target_seconds': base, 'on_target_plus_import_seconds': on,
            'charged_wall_ratio': total_ratio, 'off_CPU_seconds': base_cpu,
            'on_CPU_plus_import_seconds': on_cpu, 'charged_CPU_ratio': cpu_ratio,
            'root_median_pair_ratios': ratios,
            'root_faster_count': sum(v < 1 for v in ratios.values()),
            'population_confidence_or_strength_claim': False}


def verify(data, inputs):
    start = time.perf_counter()
    plan = load(data / 'execution-plan.json'); batch = load(data / 'batch.json')
    assert len(plan['slots']) == len(batch['slots']) == 144
    assert len({s['slot_id'] for s in plan['slots']}) == 144
    assert hashlib.sha256(Path(inputs).read_bytes()).hexdigest() == plan['input_sha256']
    capsule = load(data / 'executed-source.json')
    assert set(capsule) == set(plan['sources'])
    for name, source in capsule.items():
        assert hashlib.sha256(source.encode('utf-8')).hexdigest() == plan['sources'][name]
    roots = {r['id']: r for r in load(inputs)['rows'] if r['prefix_length'] == 2}
    assert list(roots) == plan['root_ids'] and len(roots) == 12
    expected = []
    for i, r in enumerate(roots):
        for j, d in enumerate((3, 6)):
            for k in range(3):
                order = (False, True) if (i+j+k) % 2 == 0 else (True, False)
                for on in order:
                    expected.append({'slot_id': 's%03d' % len(expected), 'case_id': r,
                                     'depth': d, 'repetition': k, 'candidate': on})
    assert plan['slots'] == expected
    contexts = {}
    for rid, root in roots.items():
        rule = ruleset_from_dict(root['RuleSet'])
        assert compute_fingerprint(rule) == root['fingerprint']
        compiled = compile_legacy_ruleset_for_semantic_execution(rule)
        session = GameSession.replay(compiled, deserialize_game_record(json.dumps(root['record'])))
        contexts[rid] = compiled, session
    raw_ids = {p.name.removesuffix('.gz').removesuffix('.json')
               for p in (data / 'returns').glob('*.json*')}
    observed_ids = set(); records = {}; checks = []; pv_plies = empty_pvs = 0
    sources, reasons, depths, counters = Counter(), Counter(), Counter(), {False: Counter(), True: Counter()}
    for specification, slot in zip(expected, batch['slots']):
        assert all(slot[k] == v for k, v in specification.items())
        if slot['status'] not in ('RETURNED', 'FAILED'):
            assert slot['status'] == 'NOT_RUN'
            continue
        path = data / 'returns' / (slot['slot_id'] + '.json')
        if slot['slot_id'] not in raw_ids:
            assert slot['status'] == 'FAILED'
            continue
        raw = load(path); observed_ids.add(slot['slot_id']); records[slot['slot_id']] = raw
        assert all(raw[k] == v for k, v in specification.items())
        assert raw['target_seconds'] >= 0 and raw['target_cpu_seconds'] >= 0
        assert raw['factory_restored'] is True
        if raw['status'] != 'RETURNED':
            assert raw['status'] == 'RAISED'
            continue
        limits = raw['limits']; d = raw['decision']; on = raw['candidate']
        assert limits['max_depth'] == slot['depth'] and limits['max_nodes'] == 500000
        assert limits['max_time_seconds'] == 3
        assert (limits['quiescence_max_depth'], limits['quiescence_hard_max_depth']) == (4, 8)
        assert raw['complete'] == (d['completed_depth'] == slot['depth'])
        assert raw['time_eligible'] == (raw['target_seconds'] <= 3)
        assert raw['constructor_seconds'] + raw['outer_choose_seconds'] <= raw['target_seconds'] + 1e-6
        assert d['pvs_null_window_searches'] == d['pvs_researches'] == 0
        assert d['runtime_depth_balanced'] is True
        assert raw['native_provider_present'] and d['native_legality_fallbacks'] == 0
        assert d['native_legality_operational_failures'] == 0
        assert raw['runtime_factory_seen'] == ('ChildRuntime' if on else 'SearchPathRuntime')
        if on:
            m = raw['candidate_metrics']
            assert m['runtime_count'] == 1 and m['attempts'] >= m['successes'] > 0
            for k in ('runtime_count', 'attempts', 'successes', 'fallbacks', 'certification_seconds'):
                counters[True][k] += m[k]
        compiled, root_session = contexts[raw['case_id']]
        assert raw['full_root_record_sha256'] == full_digest(root_session.to_record())
        legal = root_session.legal_actions()
        assert len([a for a in legal if record_value(a) == d['action']]) == 1
        replay = GameSession.replay(compiled, root_session.to_record())
        if d['principal_variation']:
            assert d['principal_variation'][0] == d['action']
        else:
            empty_pvs += 1
        for a in d['principal_variation']:
            matches = [v for v in replay.legal_actions() if record_value(v) == a]
            assert len(matches) == 1
            replay.submit(matches[0]); pv_plies += 1
        sources[d['result_source']] += 1; reasons[d['termination_reason']] += 1
        depths[(slot['depth'], on, d['completed_depth'])] += 1
        for k in ('nodes', 'qnodes', 'runtime_pushes', 'runtime_pops', 'tt_probes', 'tt_hits',
                  'evaluation_calls', 'native_legality_calls'):
            counters[on][k] += d[k]
        for k in ('target_seconds', 'target_cpu_seconds', 'constructor_seconds', 'outer_choose_seconds'):
            counters[on][k] += raw[k]
        checks.append({'slot_id': slot['slot_id'], 'raw_sha256': hashlib.sha256(
            original_bytes(path)).hexdigest(),
            'full_root_action_PV_replay': True})
    assert observed_ids == raw_ids, 'orphan or missing original returns'
    pairs = []
    for left, right in zip(expected[::2], expected[1::2]):
        a, b = records.get(left['slot_id']), records.get(right['slot_id'])
        p = {k: left[k] for k in ('case_id', 'depth', 'repetition')}
        p.update(eligible=False, planned_slots=[left['slot_id'], right['slot_id']],
                 first_candidate=left['candidate'])
        if a and b and a['status'] == b['status'] == 'RETURNED':
            off, on = (b, a) if a['candidate'] else (a, b)
            complete = off['complete'] and on['complete']
            if complete:
                assert decision_fields(off['decision']) == decision_fields(on['decision'])
                assert native_counts(off['provider_delta']) == native_counts(on['provider_delta'])
            p.update(complete=complete, eligible=complete and off['time_eligible'] and on['time_eligible'],
                     off_seconds=off['target_seconds'], on_seconds=on['target_seconds'],
                     off_cpu=off['target_cpu_seconds'], on_cpu=on['target_cpu_seconds'],
                     ratio=on['target_seconds']/off['target_seconds'],
                     complete_decision_work_Native_equal=bool(complete),
                     off_depth=off['decision']['completed_depth'], on_depth=on['decision']['completed_depth'])
        pairs.append(p)
    setup = load(data / 'initial-process-cost.json')
    outcome = acceptance(pairs, list(roots), setup)
    strata = []
    for depth in (3, 6):
        rows = [p for p in pairs if p['depth'] == depth]
        e = [p for p in rows if p['eligible']]
        strata.append({'requested_depth': depth, 'planned_pairs': 36, 'eligible_pairs': len(e),
                       'ineligible': [p['planned_slots'] for p in rows if not p['eligible']],
                       'complete_pairs': sum(p.get('complete', False) for p in rows),
                       'eligible_wall_ratio_plus_half_setup':
                           (sum(p['on_seconds'] for p in e)+setup['candidate_import_wall_seconds']/2)
                           / sum(p['off_seconds'] for p in e) if e else None,
                       'pair_ratios': [p['ratio'] for p in e]})
    return {'verified_original_returns': len(records), 'PV_plies': pv_plies, 'empty_PVs': empty_pvs,
            'result_sources': dict(sources), 'termination_reasons': dict(reasons),
            'depths': {str(k): v for k, v in depths.items()}, 'raw_checks': checks,
            'pairs': pairs, 'outcome': outcome, 'depth_strata': strata,
            'actual_trajectory_counters': {str(k): dict(v) for k, v in counters.items()},
            'candidate_one_time_import': setup, 'batch_seconds': batch['outer_seconds'],
            'non_target_batch_remainder': batch['outer_seconds'] - sum(
                r['target_seconds'] for r in records.values()),
            'no_new_Player_game_solver_calls': True,
            'reader_seconds': time.perf_counter() - start}


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--data', type=Path, required=True)
    p.add_argument('--inputs', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--manifest', type=Path)
    a = p.parse_args()
    if a.manifest:
        verify_public_manifest(a.manifest)
    r = verify(a.data, a.inputs); write_record(a.output, r)
    print(json.dumps({k: r[k] for k in ('verified_original_returns', 'PV_plies', 'outcome', 'reader_seconds')},
                     ensure_ascii=True))
