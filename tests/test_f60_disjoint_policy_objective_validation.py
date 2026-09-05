"""Focused contracts for F60's frozen data and selection protocol."""

from scripts.f60_disjoint_policy_objective_validation import (
    _aggregate_policy,
    _partition_by_source_group,
    _record_keys,
    _source_group_overlap,
    _take_unique,
)


def _record(key):
    return {"position_key": key}


def test_take_unique_enforces_forbidden_position_keys():
    records = [_record("a"), _record("b"), _record("c")]
    assert [row["position_key"] for row in _take_unique(records, {"a"}, 2)] == ["b", "c"]
    assert _record_keys(records) == {"a", "b", "c"}


def test_policy_aggregate_gives_d1_and_d2_equal_weight():
    aggregate = _aggregate_policy({
        "D1_V2_SELFPLAY": {"normalized_regret_mean": 0.0, "top1_agreement": 1.0, "ranking_accuracy": 0.8},
        "D2_V2_PV_CORRIDOR": {"normalized_regret_mean": 1.0, "top1_agreement": 0.0, "ranking_accuracy": 0.4},
    })
    assert aggregate == {"normalized_regret_mean": 0.5, "top1_agreement": 0.5, "ranking_accuracy": 0.6000000000000001}


def test_source_groups_are_partitioned_without_cross_split_overlap():
    records = [
        {"position_key": "a", "source_group": "g0"},
        {"position_key": "b", "source_group": "g1"},
        {"position_key": "c", "source_group": "g2"},
    ]
    parts = _partition_by_source_group(records, (1, 1, 1))
    split_records = {"D0": dict(zip(("fit", "development", "final_holdout"), parts))}
    matrix = _source_group_overlap(split_records)
    assert matrix["D0|fit"]["D0|development"] == 0
    assert matrix["D0|development"]["D0|final_holdout"] == 0
