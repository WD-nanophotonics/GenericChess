"""Sanity checks for score_margin.py (statistics only, no new outcomes)."""
import importlib.util
import json
import random
import statistics
from pathlib import Path

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('score_margin', HERE / 'score_margin.py')
sm = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sm)

checks = []

# 1. Exact sign test against hand-computed values.
assert abs(sm.sign_test(10, 0) - 2 / 1024) < 1e-12
assert sm.sign_test(5, 5) == 1.0
assert sm.sign_test(0, 0) is None
checks.append('sign_test exact values ok (10-0=0.001953125, 5-5=1, 0-0=None)')

# 2. A cluster bootstrap must be wider than a pair-level bootstrap when pairs
#    inside a family are perfectly correlated.
families = {str(i): [100.0, 100.0, 100.0] if i % 2 else [-100.0, -100.0, -100.0]
            for i in range(32)}
by_rule_family = {'r': families}
rng = random.Random(7)
cluster = sm.bootstrap_envelope(by_rule_family, rng)
pair_pool = [d for v in families.values() for d in v]
rng = random.Random(7)
pair_stats = []
for _ in range(2000):
    pair_stats.append(statistics.fmean(rng.choice(pair_pool) for _ in pair_pool))
pair_stats.sort()
pair_env = [pair_stats[49], pair_stats[1949]]
assert (cluster[1] - cluster[0]) > 1.5 * (pair_env[1] - pair_env[0])
checks.append('cluster envelope %.1f wide vs pair %.1f wide under perfect '
              'within-family correlation' % (cluster[1] - cluster[0],
                                             pair_env[1] - pair_env[0]))

# 3. Determinism on the frozen free6 evidence.
a = sm.analyse('free6_nonmirror_5x5', HERE)
b = sm.analyse('free6_nonmirror_5x5', HERE)
assert json.dumps(a, sort_keys=True) == json.dumps(b, sort_keys=True)
checks.append('two analyse() runs on frozen free6 evidence are identical')

# 4. Structural invariants of the written score_margin.json.
saved = json.loads((HERE / 'score_margin.json').read_text())
for name, block in saved.items():
    assert block['same_state_pairs'] == block['pairs'], name
    assert block['same_root_pairs'] == block['pairs'], name
    assert block['same_ply_pairs'] == block['pairs'], name
    scored = sum(f['pairs'] for f in block['per_foe'].values())
    assert scored + block['terminal_band_pairs'] == block['pairs'], name
    for foe, f in block['per_foe'].items():
        lo, hi = f['family_cluster_envelope']
        assert lo <= f['mean'] <= hi, (name, foe)
        assert sum(f['families'].values()) > 0, (name, foe)
        assert f['positive'] + f['zero'] + f['negative'] == f['pairs'], (name, foe)
        for owner, o in f['per_owner'].items():
            lo, hi = o['family_cluster_envelope']
            assert lo <= o['mean'] <= hi, (name, foe, owner)
            assert o['positive'] + o['zero'] + o['negative'] == o['pairs']
        assert f['balanced_owner0']['pairs'] == f['per_owner']['0']['pairs']
        assert f['balanced_owner0']['mean'] == f['per_owner']['0']['mean']
checks.append('score_margin.json invariants ok for %d datasets' % len(saved))

print(json.dumps(dict(checks=checks, status='PASS'), indent=1))
