"""Compare per-candidate train/eval rates from the frozen D2 bound receipts."""
from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
TASK = ROOT / "results/dev_aux/task2636"
OUTPUT = TASK / "query-cap-phase-alignment-audit.json"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def pearson(x: list[float], y: list[float]) -> float:
    mx, my = sum(x) / len(x), sum(y) / len(y)
    numerator = sum((a - mx) * (b - my) for a, b in zip(x, y))
    denominator = math.sqrt(sum((a - mx) ** 2 for a in x) * sum((b - my) ** 2 for b in y))
    return numerator / denominator


def average_ranks(values: list[float]) -> list[float]:
    order = sorted(range(len(values)), key=values.__getitem__)
    ranks = [0.0] * len(values)
    i = 0
    while i < len(order):
        j = i + 1
        while j < len(order) and values[order[j]] == values[order[i]]:
            j += 1
        rank = ((i + 1) + j) / 2
        for k in range(i, j):
            ranks[order[k]] = rank
        i = j
    return ranks


def main() -> dict:
    if OUTPUT.exists():
        raise FileExistsError(f"write-once output already exists: {OUTPUT}")
    train_path = TASK / "query-cap-fullpool-audit.json"
    eval_path = TASK / "query-cap-evaluation-fullpool-audit.json"
    train = json.loads(train_path.read_text(encoding="utf-8"))
    evaluation = json.loads(eval_path.read_text(encoding="utf-8"))
    if train["status"] != "PASS_FULL_FROZEN_TRAINING_ROOT_D2_CAP_BOUND_NO_SEARCH_NO_OUTCOME_READ":
        raise ValueError("training bound receipt status mismatch")
    if evaluation["status"] != "PASS_FROZEN_EVALUATION_ROOT_D2_CAP_BOUND_NO_SEARCH_NO_OUTCOME_READ":
        raise ValueError("evaluation bound receipt status mismatch")
    if train["plan_sha256"] != evaluation["plan_sha256"] or train["candidate_index_sha256"] != evaluation["candidate_index_sha256"]:
        raise ValueError("phase receipts do not share frozen plan and candidate index")
    train_groups = train["screen"]["by_group"]
    eval_groups = evaluation["screen"]["by_group"]
    if set(train_groups) != set(eval_groups) or len(train_groups) != 16:
        raise ValueError("phase candidate groups differ")
    rows = []
    for candidate in sorted(train_groups, key=int):
        tr, ev = train_groups[candidate], eval_groups[candidate]
        rows.append({"candidate_index": int(candidate),
                     "training_roots": tr["roots"], "training_gt_cap": tr["gt_cap"],
                     "training_fraction_gt_cap": tr["gt_cap"] / tr["roots"],
                     "evaluation_roots": ev["roots"], "evaluation_gt_cap": ev["gt_cap"],
                     "evaluation_fraction_gt_cap": ev["gt_cap"] / ev["roots"]})
    tx = [row["training_fraction_gt_cap"] for row in rows]
    ex = [row["evaluation_fraction_gt_cap"] for row in rows]
    result = {
        "status": "PASS_DESCRIPTIVE_CANDIDATE_PHASE_ALIGNMENT_NO_SEARCH",
        "training_receipt_sha256": sha(train_path),
        "evaluation_receipt_sha256": sha(eval_path),
        "shared_plan_sha256": train["plan_sha256"],
        "shared_candidate_index_sha256": train["candidate_index_sha256"],
        "candidate_count": len(rows),
        "per_candidate": rows,
        "correlation_of_candidate_fractions": {
            "n_candidates": len(rows), "pearson_r": pearson(tx, ex),
            "spearman_rho_average_ties": pearson(average_ranks(tx), average_ranks(ex)),
            "interpretation": "Descriptive alignment of unpruned full-width D2 upper-bound exceedance fractions across the same 16 candidate rules; not an independent-sample test, causal effect, AlphaBeta cap-hit rate, UNKNOWN rate or runtime estimate.",
        },
        "execution_state": {"training_search_or_evaluation_run": False,
                            "registration": False, "run_v1_exists": (TASK / "run-v1").exists()},
    }
    if result["execution_state"]["run_v1_exists"]:
        raise ValueError("a task2636 run appeared during the descriptive alignment audit")
    OUTPUT.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True))
    return result


if __name__ == "__main__":
    main()
