"""Direct action-list cross-check independent of the prefix-hash audit."""
from __future__ import annotations

import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
TASK = ROOT / "results/dev_aux/task2636"
PLAN = json.loads((TASK / "one-init-root-plan.json").read_text(encoding="utf-8"))
POOL = json.loads((TASK / "one-init-root-pools.json").read_text(encoding="utf-8"))
EPISODE_PATH = ROOT / "results/dev_aux/task2635/run-v2/episodes.jsonl"
OUT = TASK / "one-init-root-direct-prefix-check.json"


def sha_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    if OUT.exists():
        raise FileExistsError(f"write-once direct check already exists: {OUT}")
    expected_source = PLAN["source_sha256"]["results/dev_aux/task2635/run-v2/episodes.jsonl"]
    if sha_file(EPISODE_PATH) != expected_source:
        raise ValueError("task2635 source hash mismatch")
    prior: dict[str, list[list[dict]]] = defaultdict(list)
    rows = 0
    with EPISODE_PATH.open(encoding="utf-8") as stream:
        for line in stream:
            if not line.strip():
                continue
            episode = json.loads(line)
            record = episode["full_history_record"]
            prior[record["ruleset_fingerprint"]].append(record["actions"])
            rows += 1
    direct_comparisons = overlaps = 0
    train_keys: dict[str, set[str]] = defaultdict(set)
    by_candidate = {"training": Counter(), "evaluation": Counter()}
    channel_active = {"training": defaultdict(Counter), "evaluation": defaultdict(Counter)}
    for split in ("training", "evaluation"):
        for root in POOL[f"{split}_roots"]:
            fp = root["ruleset_fingerprint"]
            actions = root["record"]["actions"]
            if len(actions) != 8:
                raise ValueError("root history is not eight actions")
            for old_actions in prior[fp]:
                for length in range(1, min(8, len(old_actions)) + 1):
                    direct_comparisons += 1
                    if actions[:length] == old_actions[:length]:
                        overlaps += 1
                        raise ValueError(f"direct prefix equality at candidate {root['candidate_index']} length {length}")
            if split == "training":
                train_keys[fp].add(json.dumps(root["record"], sort_keys=True, separators=(",", ":")))
            elif json.dumps(root["record"], sort_keys=True, separators=(",", ":")) in train_keys[fp]:
                raise ValueError("train/evaluation exact record intersection")
            by_candidate[split][root["candidate_index"]] += 1
            for name, value in zip(root["channels"], root["features"]):
                channel_active[split][root["candidate_index"]]["/".join(name)] += int(value != 0)

    result = {
        "status": "PASS_DIRECT_ACTION_LIST_PREFIX_EQUALITY_CHECK",
        "episode_source_sha256": expected_source, "prior_histories": rows,
        "roots_checked": sum(by_candidate[s][i] for s in by_candidate for i in by_candidate[s]),
        "direct_prefix_comparisons": direct_comparisons, "direct_prefix_overlaps": overlaps,
        "training_by_candidate": {str(k): v for k, v in sorted(by_candidate["training"].items())},
        "evaluation_by_candidate": {str(k): v for k, v in sorted(by_candidate["evaluation"].items())},
        "active_roots_by_channel": {
            split: {str(candidate): dict(counts) for candidate, counts in candidate_rows.items()}
            for split, candidate_rows in channel_active.items()
        },
        "outcomes_or_search_values_read": False,
        "scope": "Direct Python action-list prefix equality and descriptive channel activation only; no WDL, search, learner or population inference.",
    }
    OUT.write_text(json.dumps(result, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in result.items() if k != "active_roots_by_channel"}, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
