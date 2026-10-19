from __future__ import annotations

import collections
import hashlib
import json
from pathlib import Path

TASK = Path("results/dev_aux/task2601")
SOURCE = Path("results/dev_aux/task2595/root-manifest.json")


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def canonical(record: dict) -> str:
    return json.dumps(record, sort_keys=True, separators=(",", ":"))


def main() -> None:
    assert not (TASK / "root-concentration.json").exists()
    data = json.loads(SOURCE.read_text(encoding="utf-8"))
    rows = data["train"]
    assert len(rows) == 8192
    counts = collections.Counter(canonical(row["record"]) for row in rows)
    n = len(rows)
    sum_sq = sum(c * c for c in counts.values())
    terminal = sum(row["terminal"] is not None for row in rows)
    depths = collections.Counter(len(row["record"]["actions"]) for row in rows)
    first_moves = collections.Counter(
        canonical(row["record"]["actions"][0]) if row["record"]["actions"] else "<empty>"
        for row in rows
    )
    result = {
        "task_id": 2601,
        "status": "DESCRIPTIVE_TRAIN_ONLY",
        "question": "How concentrated are the frozen task2595 TRAIN root draws by complete serialized history?",
        "source": {
            "path": str(SOURCE).replace("\\", "/"),
            "sha256": sha256(SOURCE),
            "rows_read": n,
            "scope": "TRAIN array only; EVAL rows and all outcomes are not accessed",
        },
        "canonicalization": "compact JSON of complete record with sorted object keys; includes ruleset fingerprint and ordered actions",
        "metrics": {
            "draws": n,
            "unique_full_histories": len(counts),
            "unique_fraction": len(counts) / n,
            "duplicate_excess": n - len(counts),
            "sum_squared_cluster_multiplicity": sum_sq,
            "simpson_concentration_equivalent_draws": n * n / sum_sq,
            "simpson_concentration_fraction": n / sum_sq,
            "max_history_multiplicity": max(counts.values()),
            "terminal_draws": terminal,
            "terminal_fraction": terminal / n,
            "history_depth_counts": dict(sorted(depths.items())),
            "distinct_first_actions": len(first_moves),
            "top_five_first_action_counts": [
                {"action": json.loads(action), "draws": count}
                for action, count in first_moves.most_common(5)
            ],
        },
        "interpretation_limit": (
            "The Simpson value is a descriptive concentration equivalent under "
            "row-frequency weights, not a claim about independent games or a "
            "valid inferential sample size. Repeated histories remain valid "
            "weighted draws if that is the declared target."
        ),
        "prohibited_inferences": [
            "No learner fitness result.",
            "No population claim about Generic rules.",
            "No new admission gate for task2595.",
            "No EVAL root or outcome inspection, root replacement, or rerun.",
        ],
    }
    (TASK / "root-concentration.json").write_text(
        json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(json.dumps(result["metrics"], separators=(",", ":")))


if __name__ == "__main__":
    main()
