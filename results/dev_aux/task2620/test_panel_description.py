"""Check independent bound signs, censoring and immutable-prefix selection."""
import json

from results.dev_aux.task2620.describe_panel import contrasts
from results.dev_aux.task2620.replay_queries import select


def test_independent_bounds_preserve_missing_denominator_and_color_signs():
    endpoints = ("initial", "TreeStrap", "TDLeaf", "WDL")
    slots = [[0, 7, 1, color, endpoint] for color in (0, 1) for endpoint in endpoints]
    plan = dict(evaluation=dict(ordered_slots=slots, caps_by_family={"1": 20000}))
    games = []
    for slot in slots:
        color, endpoint = slot[-2:]
        if endpoint == "WDL":
            continue
        outcome = 1 if endpoint == "initial" else (1 if color == 0 else -1) if endpoint == "TreeStrap" else None
        games.append(dict(slot=slot, outcome_white_relative=outcome))
    result = {row["left_minus_right"]: row for row in contrasts(plan, games)}
    assert len(result) == 6
    assert result["initial - TreeStrap"]["exact_bounds"] == ["-1", "-1"]
    assert result["TreeStrap - TDLeaf"]["difference_bounds"] == [0., 2.]
    assert result["TreeStrap - WDL"]["difference_bounds"] == [0., 2.]
    assert result["TDLeaf - WDL"]["pair_status_counts"] == {"unknown/missing": 2}
    assert result["TDLeaf - WDL"]["difference_bounds"] == [-2., 2.]
    assert all(row["denominator"] == 2 and row["per_cap"]["20000"]["denominator"] == 2
               and row["per_seed"]["7"]["denominator"] == 2 for row in result.values())


def test_snapshot_selection_takes_first_group_and_excludes_live_partial_tail():
    def row(index, complete=True):
        return dict(slot=[0, 7, 1, 0, "initial"], endpoint="initial", actor=0,
                    complete=complete, slot_index=index)
    rows = [row(0), row(1), row(2, False)]
    raw = b"".join(json.dumps(value).encode() + b"\n" for value in rows) + b'{"inflight":'
    selected, excluded = select(raw)
    assert [sample["query"]["slot_index"] for sample in selected] == [0, 2]
    assert [sample["line_number"] for sample in selected] == [1, 3]
    assert excluded == len(b'{"inflight":')
