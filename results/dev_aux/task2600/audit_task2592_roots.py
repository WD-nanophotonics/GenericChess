from pathlib import Path
import collections, hashlib, json
from generic_chess.rules.schema import ruleset_from_dict
from generic_chess.rules.compiler import compile_ruleset
from results.dev_aux.task2565 import train as T

D = Path('results/dev_aux/task2600')
P = json.loads((D / 'design-v3.json').read_text())
assert P['status'] in {'FROZEN_BEFORE_STRUCTURE_AUDIT', 'FROZEN_PRE_AUDIT_AFTER_PIN_CORRECTION', 'FROZEN_PRE_AUDIT_AFTER_PIN_CORRECTION_2'}
for name, expected in P['frozen_sha256'].items():
    actual = hashlib.sha256(Path(name).read_bytes()).hexdigest()
    assert actual == expected, (name, actual, expected)
reg = json.loads(Path('results/dev_aux/task2592/registration.json').read_text())
plan = json.loads(Path('results/dev_aux/task2592/eval/eval-plan.json').read_text())
assert reg['rules'] == P['scope']['rules']
assert reg['heldout_families'] == P['scope']['evaluation_families']
plan_families = {str(gs): sorted({slot[2] for slot in plan['slots'] if slot[0] == gs}) for gs in P['scope']['rules']}
assert plan_families == {k: sorted(v) for k, v in P['scope']['evaluation_families'].items()}

# Read only training generator seed and full initial history; never inspect outcomes/scores/weights.
train = collections.defaultdict(list)
with Path('results/dev_aux/task2592/generic/games.jsonl').open(encoding='utf-8') as f:
    for line_no, line in enumerate(f, 1):
        row = json.loads(line)
        gs = row.get('generator_seed')
        if gs in P['scope']['rules']:
            train[str(gs)].append(row['initial_record'])

def canon(record):
    return json.dumps(record, sort_keys=True, separators=(',', ':'))

def evaluation_root(gs, family, cc):
    env = T.environment(gs, cc)
    T.prefix(env, gs, family, 4)
    return env.record()

per_rule = {}
for gs in P['scope']['rules']:
    key = str(gs)
    rules = json.loads(Path(f'results/dev_aux/task2592/rules-{gs}.json').read_text())
    cc = compile_ruleset(ruleset_from_dict(rules))
    eval_rows = [evaluation_root(gs, family, cc) for family in P['scope']['evaluation_families'][key]]
    eval_canon = [canon(r) for r in eval_rows]
    train_canon = {canon(r) for r in train[key]}
    per_rule[key] = dict(
        registered_eval_count=len(eval_rows),
        unique_eval_histories=len(set(eval_canon)),
        duplicate_eval_excess=len(eval_canon)-len(set(eval_canon)),
        actual_logged_train_games=len(train[key]),
        unique_actual_train_histories=len(train_canon),
        eval_histories_matching_actual_train=sum(r in train_canon for r in eval_canon),
        family_ids=P['scope']['evaluation_families'][key])

all_ok = all(x['duplicate_eval_excess'] == 0 and x['eval_histories_matching_actual_train'] == 0 for x in per_rule.values())
result = dict(
    status='PASS_ROOT_IDENTITY' if all_ok else 'STRUCTURAL_ROOT_INDEPENDENCE_FAILURE',
    design_sha256=hashlib.sha256((D/'design-v3.json').read_bytes()).hexdigest(),
    inputs_verified=P['frozen_sha256'],
    eval_plan_families_match_registered=True,
    per_rule=per_rule,
    outcomes_read=False,
    no_fitness_or_rule_regeneration=True,
    interpretation='This is a root-identity audit of the already exposed task2592 Generic experiment only. It does not recalculate or challenge any W/L result and does not reopen task2595.')
target = D/'root-audit-v2.json'
assert not target.exists(), f'refusing overwrite {target}'
target.write_text(json.dumps(result, indent=2))
print(json.dumps(result, indent=2))
