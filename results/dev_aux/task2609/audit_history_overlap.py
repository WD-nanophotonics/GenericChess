"""Compare logged full GameSession histories without using outcomes or values."""
from pathlib import Path
from collections import Counter, defaultdict
import hashlib, json

BASE = Path("results/dev_aux")
TRAIN = BASE / "task2606/queries.jsonl"
EVAL = BASE / "task2609/eval-queries.jsonl"
OUT = BASE / "task2609/history-overlap.json"
ROOTS = json.loads((BASE / "task2609/root-manifest.json").read_text(encoding="utf-8"))

fingerprint_to_rule = {}
for key, record in ROOTS["roots"].items():
    rule = int(key.split(":", 1)[0])
    fingerprint = record["ruleset_fingerprint"]
    assert fingerprint not in fingerprint_to_rule or fingerprint_to_rule[fingerprint] == rule
    fingerprint_to_rule[fingerprint] = rule

def canonical(record):
    return json.dumps(record, sort_keys=True, separators=(",", ":"), ensure_ascii=False)

def sha(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(4 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()

train_states = {rule: set() for rule in fingerprint_to_rule.values()}
train_rows = Counter()
with TRAIN.open(encoding="utf-8") as stream:
    for line in stream:
        row = json.loads(line)
        fingerprint = row["record_before"]["ruleset_fingerprint"]
        rule = fingerprint_to_rule[fingerprint]
        assert row["record_after"]["ruleset_fingerprint"] == fingerprint
        train_rows[rule] += 1
        train_states[rule].add(canonical(row["record_before"]))
        train_states[rule].add(canonical(row["record_after"]))

eval_states = {rule: set() for rule in fingerprint_to_rule.values()}
eval_occurrences = Counter()
eval_slots = defaultdict(set)
slot_occurrences = defaultdict(Counter)
eval_rows = Counter()
with EVAL.open(encoding="utf-8") as stream:
    for line in stream:
        row = json.loads(line)
        rule, seed, family, color, endpoint, _foe = row["slot"]
        before, after = row["record_before"], row["record_after"]
        fingerprint = before["ruleset_fingerprint"]
        assert fingerprint_to_rule[fingerprint] == rule
        assert after["ruleset_fingerprint"] == fingerprint
        eval_rows[rule] += 1
        slot = (rule, seed, family, color, endpoint)
        for record in (before, after):
            key = canonical(record)
            eval_states[rule].add(key)
            eval_occurrences[rule] += 1
            slot_occurrences[slot]["occurrences"] += 1
            if key in train_states[rule]:
                slot_occurrences[slot]["matched_occurrences"] += 1
                eval_slots[rule].add(slot)

by_rule = {}
for rule in sorted(train_states):
    overlap = train_states[rule] & eval_states[rule]
    matched_occurrences = sum(v["matched_occurrences"] for k, v in slot_occurrences.items() if k[0] == rule)
    slots = [k for k in slot_occurrences if k[0] == rule]
    by_rule[str(rule)] = {
        "training_query_rows": train_rows[rule],
        "training_unique_pre_or_post_search_histories": len(train_states[rule]),
        "evaluation_query_rows": eval_rows[rule],
        "evaluation_unique_pre_or_post_search_histories": len(eval_states[rule]),
        "exact_history_intersection_unique": len(overlap),
        "evaluation_history_occurrences": eval_occurrences[rule],
        "evaluation_occurrences_matching_training": matched_occurrences,
        "evaluation_slots_with_any_exact_history_match": len(eval_slots[rule]),
        "evaluation_slots": len(slots),
    }

result = {
    "status": "AUDITED",
    "identity": "Exact canonical JSON of full GameSession record, including ruleset fingerprint and complete ordered action history; no normalization or transposition equivalence.",
    "outcome_or_value_fields_used": False,
    "training_source": "task2606 logged query record_before/record_after only.",
    "evaluation_source": "task2609 logged query record_before/record_after only.",
    "input_sha256": {str(TRAIN): sha(TRAIN), str(EVAL): sha(EVAL)},
    "rules": by_rule,
    "scope": "Post-hoc exact full-history intersection among actually logged search decision states/actions. It does not compare unvisited interior search nodes, semantic/transposed positions, or establish an independent population holdout.",
}
OUT.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
print(json.dumps(result, indent=2))
