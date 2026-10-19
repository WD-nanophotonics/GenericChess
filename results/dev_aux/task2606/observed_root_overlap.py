"""Descriptive exact-record overlap check keyed by rule and observed histories."""
from collections import defaultdict
from pathlib import Path
import hashlib,json
D=Path('results/dev_aux/task2606')
def canonical(x): return json.dumps(x,sort_keys=True,separators=(',',':'),ensure_ascii=False)
training=defaultdict(set)
with (D/'games.jsonl').open(encoding='utf-8') as f:
 for line in f:
  if line.strip():
   g=json.loads(line); training[(g['generator_seed'],canonical(g['initial_record']))].add(g['family'])
manifest=json.loads((D/'root-manifest.json').read_text(encoding='utf-8'))
eval=defaultdict(list)
for key,record in manifest['roots'].items():
 rule,family=map(int,key.split(':',1)); eval[(rule,canonical(record))].append(family)
overlaps=[]; duplicates=[]
for (rule,hist),families in sorted(eval.items()):
 if len(families)>1: duplicates.append({'rule':rule,'families':families})
 if (rule,hist) in training: overlaps.append({'rule':rule,'eval_families':families,'observed_train_families':sorted(training[(rule,hist)])})
out={'evaluation_root_family_count':len(manifest['roots']),'unique_evaluation_rule_history_pairs':len(eval),'observed_unique_training_rule_history_pairs':len(training),'exact_overlapping_unique_eval_roots':len(overlaps),'exact_overlap_eval_family_count':sum(len(x['eval_families']) for x in overlaps),'evaluation_duplicate_groups':duplicates,'overlaps':overlaps,'identity_method':'Exact canonical JSON of (complete rule-seed identity, complete stored initial_record) pairs; no semantic normalization of log/irrelevant IDs.','scope_limit':'This checks start histories appearing in completed training games, not every potential recipe root or any later training search state. Exact match is sufficient to flag overlap; no match is not proof of semantic novelty.'}
(D/'observed-root-overlap.json').write_text(json.dumps(out,indent=2,sort_keys=True)+'\n',encoding='utf-8'); print(json.dumps(out,indent=2))