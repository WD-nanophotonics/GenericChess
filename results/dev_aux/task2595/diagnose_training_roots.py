from pathlib import Path
import collections, hashlib, json
from generic_chess.rules.schema import ruleset_from_dict
from generic_chess.rules.compiler import compile_ruleset
from results.dev_aux.task2565 import train as T

D = Path('results/dev_aux/task2595')
manifest_path = D / 'root-manifest.json'
manifest_sha = hashlib.sha256(manifest_path.read_bytes()).hexdigest()
registration = json.loads((D / 'registration.json').read_text())
rules_path = D / 'rules-364005.json'
rules = json.loads(rules_path.read_text())
assert hashlib.sha256(rules_path.read_bytes()).hexdigest() == registration['rule_sha256']
assert manifest_sha == registration['root_manifest_sha256']
cc = compile_ruleset(ruleset_from_dict(rules))
initial = T.environment(364005, cc)
first_moves = []
for move in sorted(initial.actions(), key=lambda a: a.uci() if hasattr(a, 'uci') else repr(a)):
    env = T.environment(364005, cc)
    env.push(move)
    first_moves.append(dict(move=repr(move), terminal=env.terminal(), reply_count=len(env.actions())))
rows = json.loads(manifest_path.read_text())['train']
by_plies = collections.defaultdict(list)
for row in rows:
    by_plies[len(row['record']['actions'])].append(row)
unique_records = len({json.dumps(r['record'], sort_keys=True, separators=(',', ':')) for r in rows})
length_summary = {}
for n, group in sorted(by_plies.items()):
    unique_actions = len({json.dumps(r['record']['actions'], sort_keys=True, separators=(',', ':')) for r in group})
    length_summary[str(n)] = dict(
        rows=len(group), unique_action_sequences=unique_actions,
        duplicate_excess=len(group)-unique_actions,
        terminal_or_no_legal=sum(r['terminal'] is not None or r['legal_actions'] == 0 for r in group),
        terminal_results=dict(sorted(collections.Counter(str(r['terminal']) for r in group).items())))
result = dict(
    status='DESCRIPTIVE_TRAIN_ONLY_DIAGNOSIS',
    registration_status=registration['status'], fitness_started=registration['fitness_started'],
    immutable_inputs=dict(rule_sha256=registration['rule_sha256'], root_manifest_sha256=manifest_sha),
    initial_position=dict(terminal=initial.terminal(), legal_moves=len(first_moves),
                          immediate_terminal_moves=sum(m['terminal'] is not None for m in first_moves),
                          first_moves=first_moves),
    train=dict(total_roots=len(rows), unique_histories=unique_records,
               duplicate_excess=len(rows)-unique_records,
               terminal_prefixes=sum(r['terminal'] is not None or r['legal_actions'] == 0 for r in rows),
               lengths=length_summary),
    interpretation='Four-ply random legal-prefix sampling stops at terminal positions. In this fixed rule, 3 of 16 initial legal moves end the game immediately; sampled short prefixes therefore dominate duplicates. This is a root-sampling/admission failure, not evidence about either learner. The registered evaluation set was not inspected by this diagnostic; its frozen admission failure remains as separately recorded.',
    scope='No rule regeneration, no new/evaluation root selection, no fitness run, no seed substitution.')
target = D / 'training-root-diagnosis.json'
assert not target.exists(), f'refusing overwrite {target}'
target.write_text(json.dumps(result, indent=2))
print(json.dumps(result, indent=2))
