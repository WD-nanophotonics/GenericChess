"""Post-hoc descriptive analysis of the seeds 101-112 probe.

Reads ``results_qsearch_drop_exclusion.json`` and writes
``analysis_stage1.json``.  This does not change the pre-written decision rule
in ``plan.json``; it only classifies the observed excluded drops by material
sign and by whether either depth actually chose one.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.resolve().parents[1]
sys.path.insert(0, str(ROOT))

from generic_chess.ai.evaluation.config import MATE_THRESHOLD  # noqa: E402

RESULT = HERE / "results_qsearch_drop_exclusion.json"
OUT = HERE / "analysis_stage1.json"


def main() -> int:
    payload = json.loads(RESULT.read_text(encoding="utf-8"))
    rows = []
    profitable = 0
    blind = 0
    confirmations_positive = 0
    chosen_excluded = []
    for position in payload["positions"]:
        chosen_actions = {
            "d2": position["d2_action"],
            "d3": position["d3_action"],
        }
        for record in position["excluded_drop_records"]:
            if record["blind_threats"]:
                blind += 1
                if record["max_blind_threat_value_gap"] > 0:
                    profitable += 1
                confirmation = record["confirmation"] or {}
                if confirmation.get("exceeds_parent_static"):
                    confirmations_positive += 1
            if record["action"] in chosen_actions.values():
                chosen_excluded.append(
                    {
                        "seed": position["seed"],
                        "depth": [
                            d
                            for d, action in chosen_actions.items()
                            if action == record["action"]
                        ],
                        "action_key": record["action_key"],
                        "blind_threats": record["blind_threats"],
                        "new_enemy_attacks": record["new_enemy_attacks"],
                    }
                )
        rows.append(
            {
                "seed": position["seed"],
                "mate_bound": abs(position["d2_score"]) >= MATE_THRESHOLD
                or abs(position["d3_score"]) >= MATE_THRESHOLD,
                "excluded_drops": position["excluded_drops"],
                "new_enemy_attack_drops": position["attacked_only_drops"],
                "blind_threat_drops": position["blind_threat_drops"],
                "profitable_blind_threat_drops": sum(
                    1
                    for r in position["excluded_drop_records"]
                    if r["blind_threats"] and r["max_blind_threat_value_gap"] > 0
                ),
                "abs_score_delta_2_3": position["abs_score_delta_2_3"],
                "action_flip_2_3": not position["action_equal_2_3"],
                "d2_chosen_drop": position["d2_action"] is not None
                and position["d2_action"].get("kind") == "drop",
                "d3_chosen_drop": position["d3_action"] is not None
                and position["d3_action"].get("kind") == "drop",
            }
        )
    non_mate = [r for r in rows if not r["mate_bound"]]
    payload_out = {
        "role": "DEEPSEEK_AUX",
        "source": RESULT.name,
        "kind": "post-hoc descriptive classification; pre-written decision unchanged",
        "positions": len(rows),
        "eligible_seeds": [r["seed"] for r in rows],
        "missing_seeds": [108, 111],
        "excluded_drop_count": sum(r["excluded_drops"] for r in rows),
        "new_enemy_attack_drops": sum(r["new_enemy_attack_drops"] for r in rows),
        "blind_threat_drops": blind,
        "profitable_blind_threat_drops": profitable,
        "blind_confirmations_above_parent_static": confirmations_positive,
        "chosen_excluded_drops": chosen_excluded,
        "mate_bound_seeds": [r["seed"] for r in rows if r["mate_bound"]],
        "non_mate_positions": len(non_mate),
        "non_mate_median_abs_delta": _median(
            [r["abs_score_delta_2_3"] for r in non_mate]
        ),
        "non_mate_action_flips": sum(1 for r in non_mate if r["action_flip_2_3"]),
        "rows": rows,
        "interpretation": (
            "Both observed blind threats attack a piece worth less than the "
            "dropped base type (negative value gap) and both depth-1 "
            "confirmations are below the parent static score, so the exclusion "
            "hid no material-winning drop in this panel. The 10-position panel "
            "is too small and 2 rows are mate-bound; this remains descriptive."
        ),
    }
    OUT.write_text(json.dumps(payload_out, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(payload_out, indent=1)[:4000])
    return 0


def _median(values):
    import statistics

    return statistics.median(values) if values else None


if __name__ == "__main__":
    raise SystemExit(main())
