"""Pre-registration replay: verify the proposed task2611 eval roots against every planned task2606-family training start record."""
from pathlib import Path
import hashlib, json
from results.dev_aux.task2606.train import compiled, environment, prefix
R = Path('results/dev_aux')
plan = json.loads((R/'task2606/plan.json').read_text(encoding='utf-8'))
feas = json.loads((R/'task2611/feasibility.json').read_text(encoding='utf-8'))
candidates = json.loads((R/'task2607/root-candidates.json').read_text(encoding='utf-8'))
assert hashlib.sha256((R/'task2607/root-candidates.json').read_bytes()).hexdigest() == feas['candidate_source_sha256']
assert plan['training_family_offset'] == 990000 and plan['prefix_plies'] == 4 and plan['max_games'] == 1024

def identity(rule, record):
    return (rule, record['ruleset_fingerprint'], json.dumps(record, sort_keys=True, separators=(',', ':')))

train = set()
for rule in plan['rules']:
    cc = compiled(rule)
    for family in range(plan['training_family_offset'], plan['training_family_offset'] + plan['max_games']//2):
        env = environment(rule, cc)
        prefix(env, rule, family, plan['prefix_plies'])
        train.add(identity(rule, env.record()))

by_rule_family = {(row['rule'], row['family']): row for row in candidates}
selected = []
for rule_s, families in feas['proposed_third_panel'].items():
    rule = int(rule_s)
    for family in families:
        row = by_rule_family[(rule, family)]
        assert row['reason'] == 'VALID_AFTER_TARGET'
        key = identity(rule, row['record'])
        assert key not in train, (rule, family, 'overlaps prospective complete training-root set')
        restored = __import__('results.dev_aux.task2606.train', fromlist=['restore']).restore(rule, compiled(rule), row['record'])
        assert restored.record() == row['record'] and restored.terminal() is None and len(row['record']['actions']) == 4
        selected.append({'rule': rule, 'family': family, 'identity_sha256': hashlib.sha256(key[2].encode()).hexdigest(), 'train_overlap': False, 'replay': 'PASS'})
assert len(selected) == 64 and len({(x['rule'], x['identity_sha256']) for x in selected}) == 64
pins = {
    'results/dev_aux/task2606/train.py': hashlib.sha256((R/'task2606/train.py').read_bytes()).hexdigest(),
    'results/dev_aux/task2606/plan.json': hashlib.sha256((R/'task2606/plan.json').read_bytes()).hexdigest(),
    'results/dev_aux/task2607/root-candidates.json': hashlib.sha256((R/'task2607/root-candidates.json').read_bytes()).hexdigest(),
    'results/dev_aux/task2611/feasibility.json': hashlib.sha256((R/'task2611/feasibility.json').read_bytes()).hexdigest(),
}
out = {
    'status': 'PASS',
    'task': 'DEV_AUX2611_PROSPECTIVE_TRAIN_ROOT_OVERLAP_AUDIT',
    'scope': 'pre-registration; outcome-blind; validates only if task2611 retains task2606 training-family offset, prefix length, max-games range, rules and root generator',
    'training_family_records_replayed': len(plan['rules']) * (plan['max_games']//2),
    'unique_training_rule_history_records': len(train),
    'training_root_rng_formula': 'generator_seed * 1_000_000 + family_id',
    'root_generator_independent_of_learner_seed': True,
    'proposed_eval_records_replayed': len(selected),
    'eval_vs_all_planned_train_root_overlaps': 0,
    'eval_vs_within_panel_identity_duplicates': 0,
    'source_sha256': pins,
    'selected_eval_root_identities': selected,
    'must_reaudit_if': ['training_family_offset','prefix_plies','max_games','rules','root-generation source or RNG recipe changes']
}
(R/'task2611/prospective-train-root-audit.json').write_text(json.dumps(out, indent=2, sort_keys=True)+'\n', encoding='utf-8')
(R/'task2611/prospective_train_root_audit.py').write_text(Path(__file__).read_text(encoding='utf-8'), encoding='utf-8')
print(json.dumps({k:v for k,v in out.items() if k!='selected_eval_root_identities'}, indent=2))
