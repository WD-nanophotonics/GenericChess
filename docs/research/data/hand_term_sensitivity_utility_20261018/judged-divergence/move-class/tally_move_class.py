"""Classify the first-divergence move pair of each judged cell (zero new search).

Reads the frozen judged-divergence result and writes one tally JSON. Refuses to
overwrite an existing result so the frozen evidence stays immutable.
"""

from __future__ import annotations

import hashlib
import json
import sys
from collections import Counter
from itertools import product
from pathlib import Path

HERE = Path(__file__).resolve().parent
JUDGED_DIR = HERE.parent
SOURCE = JUDGED_DIR / "results_judged_divergence.json"
PLAN = HERE / "plan-move-class.json"
RESULT = HERE / "results_move_class_tally.json"

EXPECTED_SOURCE_SHA256 = (
    "444CDA2632E59ABBB06A2C747AA22A0488385C38C7E987E1B3B70B3434882979"
)
EXPECTED_JUDGED = 45
EXPECTED_VERDICTS = {"served_better": 13, "blind_better": 28, "tie": 4}
EXPECTED_GROUPS = {"divergent_split": 24, "config_decided": 21}

CLASSES = ("drop", "promotion", "quiet")
TRUNCATION_REASONS = {"node_limit", "qsearch_check_hard_limit"}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def classify(move_text: str) -> str:
    if move_text.startswith("DropMove("):
        return "drop"
    if move_text.startswith("BoardMove("):
        if "promotion_target_id=None" in move_text:
            return "quiet"
        return "promotion"
    return "other"


def group_of(pair_kind: str) -> str:
    if pair_kind == "split":
        return "divergent_split"
    if pair_kind in ("sweep", "blind"):
        return "config_decided"
    raise SystemExit(f"unexpected pair_kind {pair_kind!r}")


def completion_of(record: dict) -> str:
    served = record["oracle"]["served"]["reason"]
    blind = record["oracle"]["blind"]["reason"]
    truncated = [r in TRUNCATION_REASONS for r in (served, blind)]
    if not any(truncated):
        return "both_completed"
    if all(truncated):
        return "both_truncated"
    return "one_truncated"


def pair_label(served_class: str, blind_class: str) -> str:
    return f"served={served_class}|blind={blind_class}"


def cross(rows: list[dict], key: str) -> dict:
    table: dict[str, dict] = {}
    for row in rows:
        bucket = table.setdefault(
            row[key], {"cells": 0, "pair_classes": Counter(), "verdicts": Counter()}
        )
        bucket["cells"] += 1
        bucket["pair_classes"][row["pair_class"]] += 1
        bucket["verdicts"][row["verdict"]] += 1
    return {
        k: {
            "cells": v["cells"],
            "pair_classes": dict(sorted(v["pair_classes"].items())),
            "verdicts": dict(sorted(v["verdicts"].items())),
        }
        for k, v in sorted(table.items())
    }


def main() -> int:
    if RESULT.exists():
        print(f"refusing to overwrite existing result: {RESULT}")
        return 1

    actual_sha = sha256(SOURCE)
    if actual_sha != EXPECTED_SOURCE_SHA256:
        print(f"source hash mismatch: {actual_sha} != {EXPECTED_SOURCE_SHA256}")
        return 1

    plan = json.loads(PLAN.read_text(encoding="utf-8"))
    data = json.loads(SOURCE.read_text(encoding="utf-8"))
    judged = [r for r in data["records"] if r.get("status") == "judged"]

    if len(judged) != EXPECTED_JUDGED:
        print(f"expected {EXPECTED_JUDGED} judged cells, found {len(judged)}")
        return 1

    verdicts = Counter(r["verdict"] for r in judged)
    if dict(verdicts) != EXPECTED_VERDICTS:
        print(f"verdict totals {dict(verdicts)} != {EXPECTED_VERDICTS}")
        return 1

    rows = []
    unclassified = 0
    for record in judged:
        moves = record["saved_moves_at_divergence"]
        served_move = moves["served"]
        blind_move = moves["blind"]
        if not served_move or not blind_move:
            print(f"empty saved move at seed {record['seed']} d{record['depth']}")
            return 1
        served_class = classify(served_move)
        blind_class = classify(blind_move)
        unclassified += (served_class == "other") + (blind_class == "other")
        rows.append(
            {
                "seed": record["seed"],
                "depth": record["depth"],
                "pair_kind": record["pair_kind"],
                "group": group_of(record["pair_kind"]),
                "verdict": record["verdict"],
                "completion": completion_of(record),
                "served_class": served_class,
                "blind_class": blind_class,
                "class_changing": served_class != blind_class,
                "involves_drop": "drop" in (served_class, blind_class),
                "involves_promotion": "promotion" in (served_class, blind_class),
                "pair_class": pair_label(served_class, blind_class),
            }
        )

    if unclassified:
        print(f"{unclassified} moves could not be classified")
        return 1

    groups = Counter(r["group"] for r in rows)
    if dict(groups) != EXPECTED_GROUPS:
        print(f"group totals {dict(groups)} != {EXPECTED_GROUPS}")
        return 1

    class_counts = Counter()
    for served_class, blind_class in product(CLASSES, CLASSES):
        class_counts[pair_label(served_class, blind_class)] = sum(
            r["pair_class"] == pair_label(served_class, blind_class) for r in rows
        )

    class_changing = sum(r["class_changing"] for r in rows)
    quiet_vs_quiet = class_counts[pair_label("quiet", "quiet")]
    involves_drop = sum(r["involves_drop"] for r in rows)
    involves_promotion = sum(r["involves_promotion"] for r in rows)
    neither = sum(
        not r["involves_drop"] and not r["involves_promotion"] for r in rows
    )

    threshold = plan["endpoints_written_in_advance"]["concentration_threshold"]
    decision = (
        "class_changing_share_at_or_above_one_third"
        if class_changing >= 15
        else "divergence_mostly_quiet_move_sensitivity"
    )

    result = {
        "question": plan["question"],
        "owner": "DEEPSEEK_AUX",
        "source": {"path": str(SOURCE.relative_to(HERE.parents[2])), "sha256": actual_sha},
        "plan_sha256": sha256(PLAN),
        "zero_new_search": True,
        "judged_cells": len(rows),
        "checks": {
            "judged_cells": len(rows),
            "verdicts": dict(sorted(verdicts.items())),
            "groups": dict(sorted(groups.items())),
            "unclassified_moves": unclassified,
        },
        "summary": {
            "class_changing_pairs": class_changing,
            "same_class_pairs": len(rows) - class_changing,
            "quiet_vs_quiet_pairs": quiet_vs_quiet,
            "cells_involving_a_drop": involves_drop,
            "cells_involving_a_promotion": involves_promotion,
            "cells_with_neither_drop_nor_promotion": neither,
            "pair_class_counts": dict(sorted(class_counts.items())),
            "pre_written_threshold": threshold,
            "decision": decision,
        },
        "cross_tabs": {
            "by_group": cross(rows, "group"),
            "by_verdict": cross(rows, "verdict"),
            "by_completion": cross(rows, "completion"),
        },
        "cells": rows,
        "limits": plan["limits_to_state"],
    }

    RESULT.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result["summary"], indent=2, sort_keys=True))
    print(f"\nwritten: {RESULT}")
    print(f"sha256: {sha256(RESULT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
