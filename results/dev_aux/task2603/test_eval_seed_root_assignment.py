from results.dev_aux.task2603.audit_eval_seed_root_assignment import audit


def test_task2594_eval_roots_are_disjoint_seed_blocks_without_outcome_reads():
    result = audit()
    assert result["total_seed_root_assignments"] == 128
    assert result["total_distinct_roots"] == 128
    assert set(result["pairwise_root_overlap_counts"].values()) == {0}
    assert {row["root_count"] for row in result["per_seed"].values()} == {32}
    assert {row["slot_count"] for row in result["per_seed"].values()} == {192}
    assert {tuple(row["slots_per_root_counts"].items()) for row in result["per_seed"].values()} == {((6, 32),)}
    assert {tuple(row["colors_per_root_counts"].items()) for row in result["per_seed"].values()} == {((2, 32),)}
    assert {tuple(row["endpoints_per_root_counts"].items()) for row in result["per_seed"].values()} == {((3, 32),)}
