"""Independent record audit and same-state divergence classification, no new games."""
import json, sys
from collections import Counter
from pathlib import Path

ROOT = Path.cwd()
OUT = Path(__file__).resolve().parent / 'attack-utility'
from generic_chess.rules.schema import ruleset_from_dict
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.session.session import GameSession
from generic_chess.session.serialization import deserialize_game_record

rules = json.loads((OUT / 'rules.json').read_text())
games = [json.loads(line) for line in (OUT / 'games.jsonl').read_text().splitlines()]
keys = [(g['seed'], g['prefix'], g['candidate_owner'], g['arm']) for g in games]
assert len(keys) == len(set(keys)) == 64
compiled = {r['seed']: compile_ruleset_for_execution(ruleset_from_dict(r['definition']))
            for r in rules if 'compile_error' not in r}
checks = []
for game in games:
    if game['record'] is None:
        assert game['error'] and game['unstarted'] and not game['events']
        continue
    c = compiled[game['seed']]
    record = deserialize_game_record(json.dumps(game['record']))
    s = GameSession.replay(c, record)
    assert s.result.status.value == game['status'] and s.result.winner == game['winner']
    assert len(record.actions) == game['prefix'] + game['additional_plies']
    checks.append({'seed': game['seed'], 'prefix': game['prefix'],
                   'owner': game['candidate_owner'], 'arm': game['arm'],
                   'full_record_actions': len(record.actions),
                   'status': game['status'], 'winner': game['winner']})
divergences = []
for seed in compiled:
    for prefix in (3, 4):
        for owner in (0, 1):
            pair = {g['arm']: g for g in games
                    if (g['seed'], g['prefix'], g['candidate_owner']) == (seed, prefix, owner)}
            a, b = pair['legacy'], pair['semantic_native']
            ra, rb = (deserialize_game_record(json.dumps(g['record'])) for g in (a, b))
            assert ra.actions[:prefix] == rb.actions[:prefix]
            first = next((i for i, (x, y) in enumerate(zip(a['events'], b['events']))
                          if x['action'] != y['action']), None)
            if first is None:
                assert a['events'].__len__() == b['events'].__len__()
                classification = 'identical_trajectory'
                detail = None
            else:
                # Before the first differing move the complete records agree,
                # including prior capture/drop/promotion/history transitions.
                assert ra.actions[:prefix + first] == rb.actions[:prefix + first]
                ea, eb = a['events'][first], b['events'][first]
                assert ea['owner'] == eb['owner'] and ea['candidate'] == eb['candidate']
                classification = 'candidate_first' if ea['candidate'] else 'fixed_foe_first'
                detail = {k: [ea[k], eb[k]] for k in
                          ('owner', 'action', 'depth', 'nodes', 'termination', 'caller_seconds')}
            divergences.append({'seed': seed, 'prefix': prefix, 'owner': owner,
                                'first_different_ply': first, 'class': classification,
                                'detail': detail, 'winners': [a['winner'], b['winner']],
                                'statuses': [a['status'], b['status']]})
result = {'all_planned_keys_unique': True, 'replayed_games': len(checks),
          'replayed_actions': sum(x['full_record_actions'] for x in checks),
          'failed_slots_preserved': 64-len(checks),
          'divergence_counts': dict(Counter(x['class'] for x in divergences)),
          'candidate_depth_at_divergence': dict(Counter(
              str(x['detail']['depth']) for x in divergences if x['class']=='candidate_first')),
          'trajectory_pairs': divergences, 'record_checks': checks,
          'limits': 'Posthoc audit, no new outcomes. Wall-capped fixed foe can itself diverge; complete-case or equal-depth subsets are descriptive and cannot replace the frozen denominator.'}
(OUT / 'audit.json').write_text(json.dumps(result, indent=2)+'\n', encoding='utf-8')
print(json.dumps({k:v for k,v in result.items() if k not in ('trajectory_pairs','record_checks')},indent=2))
