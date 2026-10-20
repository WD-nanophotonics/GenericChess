from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
PLAN = ROOT / "results/dev_aux/task2636/one-init-study-plan.json"
OUT = ROOT / "results/dev_aux/task2636/root-channel-coverage.json"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def summarize(rows: list[dict], channel_order: list[list[str]]) -> dict:
    active_roots = Counter()
    active_by_root_count = Counter()
    for row in rows:
        active = [i for i, value in enumerate(row["features"]) if value != 0]
        active_roots.update(active)
        active_by_root_count[len(active)] += 1
    return {
        "roots": len(rows),
        "channels": [
            {"index": i, "name": channel_order[i], "nonzero_root_count": active_roots[i]}
            for i in range(len(channel_order))
        ],
        "channels_active_on_at_least_one_root": sum(active_roots[i] > 0 for i in range(len(channel_order))),
        "root_active_channel_count_histogram": {str(k): active_by_root_count[k] for k in sorted(active_by_root_count)},
    }


def main() -> None:
    plan = json.loads(PLAN.read_text(encoding="utf-8"))
    pool_path = ROOT / plan["source_lineage"]["root_pool"]
    audit_path = ROOT / plan["source_lineage"]["root_audit"]
    if sha(pool_path) != plan["source_lineage"]["root_pool_sha256"]:
        raise ValueError("frozen root pool hash changed")
    if sha(audit_path) != plan["source_lineage"]["root_audit_sha256"]:
        raise ValueError("frozen root audit hash changed")
    pool = json.loads(pool_path.read_text(encoding="utf-8"))
    if pool["root_pool_registered"] or pool["learner_or_search_started"]:
        raise ValueError("coverage review requires the unregistered, unexecuted frozen pool")
    result = {"training": {}, "evaluation": {}}
    for candidate in range(16):
        train = [r for r in pool["training_roots"] if r["candidate_index"] == candidate]
        evaluation = [r for r in pool["evaluation_roots"] if r["candidate_index"] == candidate]
        orders = {tuple(tuple(channel) for channel in r["channels"]) for r in train + evaluation}
        if len(orders) != 1:
            raise ValueError(f"candidate {candidate}: root channel order differs")
        order = [list(channel) for channel in next(iter(orders))]
        result["training"][str(candidate)] = summarize(train, order)
        result["evaluation"][str(candidate)] = summarize(evaluation, order)

    summaries = {}
    for phase in ("training", "evaluation"):
        counts = [item["channels_active_on_at_least_one_root"] for item in result[phase].values()]
        summaries[phase] = {
            "candidate_count": len(counts),
            "candidates_missing_any_channel": sum(count < 10 for count in counts),
            "minimum_channels_supported": min(counts),
            "maximum_channels_supported": max(counts),
            "scope": "Frozen root-start feature support only; descendant activation and TD update exposure are not inferred.",
        }
    output = {
        "status": "PASS_FROZEN_ROOT_CHANNEL_COVERAGE_REPLAY",
        "root_pool_sha256": sha(pool_path),
        "root_audit_sha256": sha(audit_path),
        "analyzer_sha256": sha(Path(__file__)),
        "channel_order_shared_across_candidates": True,
        "training_summary": summaries["training"],
        "evaluation_summary": summaries["evaluation"],
        "per_candidate": result,
        "outcome_or_search_values_used": False,
        "root_selection_changed": False,
        "training_or_evaluation_started": False,
        "interpretation_limit": "Finite selected-root description only; do not claim population support or descendant training exposure and do not change/select roots on these counts.",
    }
    OUT.write_text(json.dumps(output, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in output.items() if k != "per_candidate"}, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
