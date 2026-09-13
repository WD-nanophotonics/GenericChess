from scripts import f61_gen0_gen1_strength_triage as triage
from types import SimpleNamespace


def test_strength_triage_freezes_small_ruleset_order_and_real_strength_gate():
    assert triage.RULESET_ORDER == (
        "B_CANONICAL_STANDARD_SHOGI",
        "A_CANONICAL_WESTERN_CHESS",
        "GEN_CLASSIC_LIKE_4_101",
    )
    assert triage.ROOT_COUNT == 24
    assert triage.ARENA_PAIRS == 4
    assert triage._directional_failure({
        "mean_pair_score": 0.49,
        "child_better_pairs": 1,
        "child_worse_pairs": 3,
    })
    assert not triage._directional_failure({
        "mean_pair_score": 0.49,
        "child_better_pairs": 3,
        "child_worse_pairs": 1,
    })


def test_generated_fixture_executes_same_smoke_fit_and_arena_path():
    compiled, native, parent, ruleset_id = triage._generated_context()
    records = triage._d0_records(compiled, 620101, count=3, smoke=True)
    child, training = triage._fit_one(compiled, native, parent, records, smoke=True)
    resumed_child, resumed_training = triage._fit_one(
        compiled, native, parent, records, smoke=True
    )
    arena = triage._arena(compiled, native, parent, child, seed=620701, smoke=True)
    assert ruleset_id == "gen_classic_like_4_101"
    assert compiled._legacy_compiled.ruleset_fingerprint == compiled.ruleset_fingerprint
    assert child.parent_checkpoint_id == parent.checkpoint_id
    assert training["training_roots"] >= 1
    assert resumed_child.to_dict() == child.to_dict()
    assert resumed_training == training
    assert arena["pair_count"] == 2
    assert len(arena["pair_scores"]) == 2


def test_training_spectrum_is_row_equivalent_to_full_f59_smoke_path():
    compiled, native, parent, _ruleset_id = triage._generated_context()
    record = triage._d0_records(compiled, 620102, count=1, smoke=True)[0]
    full, _meta = triage.f59._spectrum_for_root(
        compiled, native, parent, parent, record, smoke=True
    )
    lean = triage._lean_spectrum_for_root(
        compiled, native, parent, record, smoke=True
    )
    assert triage._training_rows_equivalent(full, lean)


def test_ruleset_selector_limits_run_to_requested_mainline_arm(monkeypatch):
    compiled = SimpleNamespace(ruleset_fingerprint="fingerprint")
    parent = SimpleNamespace(checkpoint_id="parent")
    child = SimpleNamespace(checkpoint_id="child", parent_checkpoint_id="parent")
    monkeypatch.setattr(triage, "_context", lambda label: (compiled, None, parent, label))
    monkeypatch.setattr(triage, "_d0_records", lambda *args, **kwargs: [])
    monkeypatch.setattr(triage, "_fit_one", lambda *args, **kwargs: (child, {"training_roots": 0}))
    monkeypatch.setattr(triage, "_arena", lambda *args, **kwargs: {
        "mean_pair_score": 0.5, "child_worse_pairs": 0, "child_better_pairs": 0,
    })
    payload = triage.run(smoke=True, ruleset="B_CANONICAL_STANDARD_SHOGI")
    assert payload["ruleset_order"] == ["B_CANONICAL_STANDARD_SHOGI"]
