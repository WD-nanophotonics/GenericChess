"""Recompute the saved first-action/reward association without launching games."""
from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[4]
GAMES = HERE / "games.jsonl"
EXPECTED = ROOT / "docs/research/data/static_v2_first_choice_contrast_20261020.json"


def first_candidate_move(row):
    return next((m for m in row["moves"] if m.get("role") == "candidate"), None)


def action_key(action):
    # Geometry/pattern identifiers are compiler-local; these fields describe
    # the move semantics used by the paired game records.
    keys = ("kind", "actor_type_id", "base_type_id", "from_square",
            "to_square", "promotion_target_id")
    return tuple(json.dumps(action.get(k), sort_keys=True) for k in keys)


def number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def build():
    rows = [json.loads(line) for line in GAMES.read_text(encoding="utf-8").splitlines() if line]
    arms = defaultdict(dict)
    for row in rows:
        if row.get("candidate") not in ("unit", "static_v2"):
            continue
        root = row["game_id"].split("|foe=", 1)[0]
        key = (root, row["foe"], int(row["candidate_owner"]))
        arm = row["candidate"]
        if arm in arms[key]:
            raise AssertionError(f"duplicate {arm} arm for {key}")
        arms[key][arm] = row

    pairs = []
    for key, pair in sorted(arms.items()):
        if set(pair) != {"unit", "static_v2"}:
            raise AssertionError(f"unpaired slot {key}: {sorted(pair)}")
        u, s = pair["unit"], pair["static_v2"]
        um, sm = first_candidate_move(u), first_candidate_move(s)
        if um is None and sm is None:
            category = "no_candidate_action_in_either_arm"
            if not number(u["reward"]) or not number(s["reward"]):
                raise AssertionError(f"no-action pair unexpectedly UNKNOWN: {key}")
        elif um is None or sm is None:
            category = "one_candidate_action_missing"
        elif um["state_before"] != sm["state_before"]:
            category = "state_mismatch"
        elif action_key(um["action"]) != action_key(sm["action"]):
            category = "changed_action_same_state"
        else:
            category = "same_action_same_state"

        interval = None
        delta = None
        ur, sr = u.get("reward"), s.get("reward")
        if number(ur) and number(sr):
            delta = float(sr) - float(ur)
            interval = [delta, delta]
        elif number(ur) and not number(sr):
            interval = [-1.0 - float(ur), 1.0 - float(ur)]
        elif not number(ur) and number(sr):
            interval = [float(sr) - 1.0, float(sr) + 1.0]
        else:
            interval = [-2.0, 2.0]
        pairs.append({"key": key, "foe": u["foe"], "owner": int(u["candidate_owner"]),
                      "category": category, "delta": delta, "interval": interval})

    def summarize(group):
        observed = [p["delta"] for p in group if p["delta"] is not None]
        lo = sum(p["interval"][0] for p in group)
        hi = sum(p["interval"][1] for p in group)
        return {"pairs": len(group), "complete_pairs": len(observed),
                "unknown_pairs": len(group) - len(observed),
                "complete_delta_sum": round(sum(observed), 10),
                "complete_pair_mean": round(sum(observed) / len(observed), 10) if observed else None,
                "all_pair_mean_bounds": [round(lo / len(group), 10), round(hi / len(group), 10)]}

    categories = {}
    for name in ("changed_action_same_state", "same_action_same_state",
                 "no_candidate_action_in_either_arm", "one_candidate_action_missing", "state_mismatch"):
        group = [p for p in pairs if p["category"] == name]
        if group:
            categories[name] = summarize(group)
    overall = summarize(pairs)
    strata = {}
    for foe in ("unit", "static_v2"):
        for owner in (0, 1):
            group = [p for p in pairs if p["foe"] == foe and p["owner"] == owner]
            strata[f"{foe}_foe_owner_{owner}"] = summarize(group)

    return {"rows": len(rows), "selected_rows": len(rows) - sum(r.get("candidate") not in ("unit", "static_v2") for r in rows),
            "matched_pairs": len(pairs), "categories": categories, "overall": overall,
            "by_fixed_foe_and_candidate_owner": strata}


def main():
    result = build()
    expected = json.loads(EXPECTED.read_text(encoding="utf-8"))
    assert result["selected_rows"] == expected["integrity"]["selected_game_rows"] == 128
    assert result["matched_pairs"] == expected["integrity"]["matched_pairs"] == 64
    assert result["categories"]["changed_action_same_state"]["pairs"] == 22
    assert result["categories"]["same_action_same_state"]["pairs"] == 34
    assert result["categories"]["no_candidate_action_in_either_arm"]["pairs"] == 8
    assert sum(item["pairs"] for item in result["categories"].values()) == 64
    assert result["categories"].get("state_mismatch", {"pairs": 0})["pairs"] == 0
    assert result["categories"].get("one_candidate_action_missing", {"pairs": 0})["pairs"] == 0
    assert result["overall"]["complete_pairs"] == 62
    assert result["overall"]["all_pair_mean_bounds"] == expected["overall"]["all_pair_mean_bounds"]
    for key, values in expected["by_fixed_foe_and_candidate_owner"].items():
        assert result["by_fixed_foe_and_candidate_owner"][key]["all_pair_mean_bounds"] == values["all_pair_mean_bounds"], key
    print(json.dumps(result, indent=2, sort_keys=True))
    print("\nPASS: saved-data contrast and UNKNOWN bounds match the published evidence.")


if __name__ == "__main__":
    main()
