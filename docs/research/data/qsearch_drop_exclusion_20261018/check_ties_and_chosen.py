"""Zero-search check: were the addendum ties actually served, and which
excluded drops were chosen by the served depth-2/depth-3 search?

Reads only ``results_stage2_fresh_seeds.json`` and ``results_addendum.json``
and writes ``tie_and_chosen_check.json``.  No search is run.
"""

from __future__ import annotations

import json
from pathlib import Path

HERE = Path(__file__).resolve().parent


def action_key(action):
    if action is None:
        return None
    if action["kind"] == "drop":
        x, y = action["to"]
        return f"{action.get('base_type_id')}@{chr(97 + x)}{y + 1}"
    if action["kind"] == "board":
        fx, fy = action["from"]
        tx, ty = action["to"]
        key = f"{chr(97 + fx)}{fy + 1}-{chr(97 + tx)}{ty + 1}"
        if action.get("promotion_target_id"):
            key += "=" + action["promotion_target_id"]
        return key
    return str(action)


def main() -> int:
    stage2 = json.loads((HERE / "results_stage2_fresh_seeds.json").read_text())
    addendum = json.loads((HERE / "results_addendum.json").read_text())
    positions = {p["seed"]: p for p in stage2["positions"]}

    ties = []
    for position in addendum["positions"]:
        for drop in position["drops"]:
            if drop["vs_parent_d3"] == 0:
                ties.append(
                    (position["seed"], drop["action_key"], drop["child_d2_mover_value"])
                )

    tie_rows = []
    for seed, key, value in ties:
        served = positions[seed]
        d2_key = action_key(served["d2_action"])
        d3_key = action_key(served["d3_action"])
        tie_rows.append(
            {
                "seed": seed,
                "tie_action": key,
                "child_value": value,
                "d2_action": d2_key,
                "d3_action": d3_key,
                "chosen_at_d2": d2_key == key,
                "chosen_at_d3": d3_key == key,
            }
        )

    chosen = []
    for position in stage2["positions"]:
        d2_key = action_key(position["d2_action"])
        d3_key = action_key(position["d3_action"])
        for record in position["excluded_drop_records"]:
            if record["action_key"] in (d2_key, d3_key):
                chosen.append(
                    {
                        "seed": position["seed"],
                        "action_key": record["action_key"],
                        "depth": [
                            name
                            for name, key in (("d2", d2_key), ("d3", d3_key))
                            if key == record["action_key"]
                        ],
                        "blind_threats": record["blind_threats"],
                        "new_enemy_attacks": record["new_enemy_attacks"],
                    }
                )

    payload = {
        "role": "DEEPSEEK_AUX",
        "source": ["results_stage2_fresh_seeds.json", "results_addendum.json"],
        "ties": tie_rows,
        "stage2_chosen_excluded_drops": chosen,
        "counts": {
            "ties": len(tie_rows),
            "ties_chosen": sum(
                1 for row in tie_rows if row["chosen_at_d2"] or row["chosen_at_d3"]
            ),
            "stage2_chosen_excluded": len(chosen),
        },
    }
    (HERE / "tie_and_chosen_check.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(payload["counts"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
