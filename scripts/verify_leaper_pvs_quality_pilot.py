"""Literal saved-record verification and fixed-denominator OFF/ON endpoints.

No Player, solver or producer implementation is imported or called.
"""
from collections import Counter, defaultdict
import argparse
import gzip
import hashlib
import json
from pathlib import Path

from generic_chess.rules.schema import ruleset_from_dict, compute_fingerprint
from generic_chess.rules.compiler import compile_legacy_ruleset_for_semantic_execution
from generic_chess.session.serialization import deserialize_game_record
from generic_chess.session.session import GameSession
from scripts.research_record import record_value, write_record


def load(path):
    path = Path(path)
    if not path.exists():
        path = Path(str(path) + '.gz')
    raw = path.read_bytes()
    return json.loads(gzip.decompress(raw) if path.suffix == '.gz' else raw)


_RETURN_ARCHIVES = {}


def original_return(folder, query_id):
    path = folder / 'returns' / (query_id + '.json')
    if path.exists():
        return load(path)
    key = str(folder.resolve())
    if key not in _RETURN_ARCHIVES:
        _RETURN_ARCHIVES[key] = load(folder / 'returns.json')
    item = _RETURN_ARCHIVES[key][query_id]
    raw = item['original_utf8'].encode('utf-8')
    assert hashlib.sha256(raw).hexdigest() == item['sha256'], 'raw byte hash mismatch'
    return json.loads(raw)


def full_digest(record):
    return hashlib.sha256(json.dumps(record_value(record), sort_keys=True,
                                    separators=(',', ':')).encode()).hexdigest()


def action(raw, session):
    matches = [a for a in session.legal_actions() if record_value(a) == raw]
    assert len(matches) == 1, 'full action not uniquely legal'
    return matches[0]


def points(game):
    if game['status'] != 'TERMINAL':
        return None
    terminal = game['Core_terminal']
    if terminal['winner'] is not None:
        assert terminal['winner'] in (0, 1)
        return float(terminal['winner'] == game['on_seat'])
    assert terminal['status'] in ('repetition', 'max_ply', 'stalemate')
    return 0.5


def fixed_bounds(scores, denominator):
    assert len(scores) == denominator and denominator > 0
    known = [s for s in scores if s is not None]
    assert all(0 <= s <= 1 for s in known)
    missing = denominator - len(known)
    return {'planned': denominator, 'known': len(known), 'missing': missing,
            'score_sum_known': sum(known),
            'mean_bounds': [sum(known) / denominator,
                            (sum(known) + missing) / denominator]}


def verify_game(game, root, folder):
    assert game['case_id'] == root['id']
    assert game['family'] == root['family'] and game['fingerprint'] == root['fingerprint']
    assert game['initial_record'] == root['record']
    rules = ruleset_from_dict(root['RuleSet'])
    assert compute_fingerprint(rules) == root['fingerprint']
    compiled = compile_legacy_ruleset_for_semantic_execution(rules)
    session = GameSession.replay(compiled, deserialize_game_record(json.dumps(root['record'])))
    pvs = empty_pvs = forced = over = 0
    sources, reasons, depths = Counter(), Counter(), Counter()
    by_policy = {False: Counter(), True: Counter()}
    first = None
    provider = {False: defaultdict(Counter), True: defaultdict(Counter)}
    for q in game['queries']:
        raw = original_return(folder, q['query_id'])
        assert all(q[k] == v for k, v in raw.items()), 'annotated query differs from saved original'
        assert q['seat'] == session.state.position.side_to_move
        assert q['on'] == (q['seat'] == game['on_seat'])
        assert q['ply_before'] == session.state.ply_count
        before = session.to_record()
        assert q['record_before_sha256'] == full_digest(before)
        d = q['decision']
        chosen = action(d['action'], session)
        assert d['runtime_depth_balanced'] is True
        legal_count = len(session.legal_actions())
        forced += legal_count == 1
        pv = GameSession.replay(compiled, before)
        if d['principal_variation']:
            assert d['principal_variation'][0] == d['action']
        else:
            empty_pvs += 1
        for a in d['principal_variation']:
            pv.submit(action(a, pv))
            pvs += 1
        prior_position = session.state.position
        session.submit(chosen)
        following = session.state.position
        width = compiled.board_shape.width
        expected_cells = {chosen.from_square.rank * width + chosen.from_square.file,
                          chosen.to_square.rank * width + chosen.to_square.file}
        changed_cells = {i for i, (a, b) in enumerate(zip(prior_position.board, following.board))
                         if a != b}
        assert changed_cells == expected_cells, 'ordinary Leaper two-cell footprint mismatch'
        assert prior_position.hands == following.hands
        assert prior_position.aux_state == following.aux_state
        assert following.side_to_move == 1 - prior_position.side_to_move
        assert following.ruleset_fingerprint == prior_position.ruleset_fingerprint
        assert q['record_after_sha256'] == full_digest(session.to_record())
        assert q['limits']['max_time_seconds'] == 1
        assert q['limits']['max_nodes'] == 500000 and q['limits']['max_depth'] == 64
        assert q['limits']['quiescence_max_depth'] == 4
        assert q['limits']['quiescence_hard_max_depth'] == 8
        assert q['timing_eligible'] == (q['outer_seconds'] <= 1.1)
        over += not q['timing_eligible']
        sources[d['result_source']] += 1
        reasons[d['termination_reason']] += 1
        depths[str(d['completed_depth'])] += 1
        b = by_policy[q['on']]
        b.update(calls=1, wall=q['outer_seconds'], cpu=q['cpu_seconds'],
                 elapsed=d['elapsed_seconds'], nodes=d['nodes'], qnodes=d['qnodes'],
                 pvs_null=d['pvs_null_window_searches'], pvs_research=d['pvs_researches'],
                 tt_probes=d['tt_probes'], tt_hits=d['tt_hits'], tt_cutoffs=d['tt_cutoffs'],
                 outer_deadline_observed=int(q['caller_deadline_observed']),
                 native_legality=d['native_legality_calls'],
                 native_fallback=d['native_legality_fallbacks'],
                 runtime_pushes=d['runtime_pushes'],
                 fallback=int(d['result_source'] in ('legal_fallback', 'root_scan_fallback')))
        for group, vals in q['provider_delta'].items():
            provider[q['on']][group].update(vals)
        if first is None:
            first = {'on': q['on'], 'action': d['action'], 'score': d['score'],
                     'source': d['result_source'], 'depth': d['completed_depth'],
                     'qdepth': d['result_ordinary_qdepth'],
                     'pvs_null': d['pvs_null_window_searches'],
                     'timing_eligible': q['timing_eligible']}
    if game['status'] == 'TERMINAL':
        assert session.state.terminal_status.is_terminal
        assert record_value(session.to_record()) == game['final_record']
        assert record_value(session.state.terminal_status) == game['Core_terminal']
        assert record_value(session.result) == game['Session_result']
        assert game['timing_eligible'] == (over == 0)
    return {'game_id': game['game_id'], 'case_id': game['case_id'],
            'family': game['family'], 'on_seat': game['on_seat'],
            'status': game['status'], 'points_ON': points(game),
            'timing_eligible': game.get('timing_eligible', False),
            'queries': len(game['queries']), 'literal_PV_plies': pvs,
            'selected_two_cell_checks': len(game['queries']),
            'empty_PV': empty_pvs, 'forced': forced,
            'overtime_calls': over, 'first_decision': first,
            'sources': dict(sources), 'reasons': dict(reasons), 'depths': dict(depths),
            'by_policy': {str(k): dict(v) for k, v in by_policy.items()},
            'actual_provider': {str(k): {g: dict(v) for g, v in groups.items()}
                                for k, groups in provider.items()}}


def run(folder, inputs):
    folder = Path(folder)
    plan = load(folder.parent / 'execution-plan.json')
    captured = load(folder / 'executed-source.json')
    plan_path = folder.parent / 'execution-plan.json'
    plan_bytes = (plan_path.read_bytes() if plan_path.exists() else
                  gzip.decompress(Path(str(plan_path) + '.gz').read_bytes()))
    assert hashlib.sha256(plan_bytes).hexdigest() == captured['plan_sha256']
    assert hashlib.sha256(Path(inputs).read_bytes()).hexdigest() == captured['input_sha256']
    assert captured['input_sha256'] == plan['input_sha256']
    for name, text in captured['product_sources'].items():
        assert hashlib.sha256(text.encode('utf-8')).hexdigest() == plan['sources'][name]
    assert hashlib.sha256(captured['driver'].encode('utf-8')).hexdigest() == plan['sources']['scripts/leaper_pvs_quality_pilot.py']
    roots = {r['id']: r for r in load(inputs)['rows'] if r['prefix_length'] == 2}
    games = load(folder / 'games.json')
    assert len(games) == 24 and len({g['game_id'] for g in games}) == 24
    assert {g['game_id'] for g in games} == set(range(24))
    reports = [verify_game(g, roots[g['case_id']], folder) for g in games]
    pairs, families = [], []
    for ri, root in enumerate(roots.values()):
        rs = [r for r in reports if r['case_id'] == root['id']]
        assert len(rs) == 2 and {r['on_seat'] for r in rs} == {0, 1}
        assert [r['on_seat'] for r in rs] == ([0, 1] if ri % 2 == 0 else [1, 0])
        valid = all(r['timing_eligible'] and r['status'] == 'TERMINAL' for r in rs)
        first = [r['first_decision'] for r in rs]
        pairs.append({'case_id': root['id'], 'family': root['family'],
                      'actual': fixed_bounds([r['points_ON'] for r in rs], 2),
                      'both_timing_eligible': valid,
                      'budgeted': fixed_bounds([r['points_ON'] if valid else None for r in rs], 2),
                      'initial_action_equal': first[0]['action'] == first[1]['action']
                      if all(first) else None, 'first_decisions': first})
    for f in sorted({r['family'] for r in roots.values()}):
        rs = [r for r in reports if r['family'] == f]
        assert len(rs) == 4
        valid_cases = {p['case_id'] for p in pairs if p['both_timing_eligible']}
        families.append({'family': f, 'actual': fixed_bounds([r['points_ON'] for r in rs], 4),
                         'budgeted': fixed_bounds([r['points_ON'] if r['case_id'] in valid_cases
                                                   else None for r in rs], 4)})
    quals = load(folder / 'qualification.json')
    bound_ids = [r['query_id'] for g in games for r in g['queries']]
    bound_ids += [r['query_id'] for r in quals if r['status'] == 'RETURNED']
    assert len(set(bound_ids)) == len(bound_ids), 'duplicate raw return association'
    if (folder / 'returns').exists():
        observed_ids = {p.stem for p in (folder / 'returns').glob('*.json')}
    else:
        observed_ids = set(load(folder / 'returns.json'))
    assert set(bound_ids) == observed_ids, 'orphan or missing original returns'
    q_reports = []
    for root in roots.values():
        rs = [r for r in quals if r['case_id'] == root['id']]
        assert len(rs) == 2 and {r['on'] for r in rs} == {False, True}
        if all(r['status'] == 'RETURNED' for r in rs):
            assert all(r['decision']['completed_depth'] == 3 for r in rs)
            assert rs[0]['decision']['score'] == rs[1]['decision']['score']
            rules = ruleset_from_dict(root['RuleSet'])
            c = compile_legacy_ruleset_for_semantic_execution(rules)
            s = GameSession.replay(c, deserialize_game_record(json.dumps(root['record'])))
            for r in rs:
                raw = original_return(folder, r['query_id'])
                assert r['decision'] == raw['decision']
                assert raw['record_before_sha256'] == full_digest(s.to_record())
                assert raw['limits']['max_depth'] == 3
                assert raw['limits']['max_nodes'] == 50000
                assert raw['limits']['max_time_seconds'] == 3
                action(r['decision']['action'], s)
                pv = GameSession.replay(c, s.to_record())
                for a in r['decision']['principal_variation']:
                    pv.submit(action(a, pv))
        q_reports.append({'case': root['id'], 'slots': rs})
    return {'all_actual': fixed_bounds([r['points_ON'] for r in reports], 24),
            'planned_games': 24, 'actual_terminals': sum(r['status'] == 'TERMINAL' for r in reports),
            'timing_eligible_games': sum(r['timing_eligible'] for r in reports),
            'complete_timing_pairs': sum(p['both_timing_eligible'] for p in pairs),
            'literal_replayed_decisions': sum(r['queries'] for r in reports),
            'literal_replayed_PV_plies': sum(r['literal_PV_plies'] for r in reports),
            'empty_PV': sum(r['empty_PV'] for r in reports),
            'families': families, 'rule_pairs': pairs, 'games': reports,
            'qualification': q_reports, 'new_Player': 0, 'new_solver': 0,
            'new_games': 0,
            'limits': 'Saved-data replay, not independent search rerun or WDL proof. '
                      'Fixed denominators retain missing/ineligible as UNKNOWN. '
                      'Six correlated development families, not iid or holdout.'}


if __name__ == '__main__':
    p = argparse.ArgumentParser(__doc__)
    p.add_argument('--data', type=Path, required=True)
    p.add_argument('--inputs', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    assert not a.output.exists()
    result = run(a.data, a.inputs)
    write_record(a.output, result)
    print(json.dumps({k: v for k, v in result.items()
                      if k not in ('games', 'families', 'rule_pairs', 'qualification')}))
