from scripts import f61_gen0_gen1_strength_triage as triage
import shutil
import tempfile
from pathlib import Path
from types import SimpleNamespace

import numpy as np


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


def test_generated_fixture_executes_same_smoke_fit_and_arena_path(monkeypatch, request):
    output_dir = tempfile.mkdtemp(prefix="gc-f61-")
    monkeypatch.setattr(triage, "OUT", Path(output_dir))
    request.addfinalizer(lambda: shutil.rmtree(output_dir, ignore_errors=True))
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


def test_fit_one_separates_model_seed_from_frozen_training_records(monkeypatch):
    compiled = SimpleNamespace(ruleset_fingerprint="fingerprint")
    parent = SimpleNamespace(checkpoint_id="parent")
    record = {"position_key": "root"}
    rows = [
        [
            triage.f59.SpectrumRow(
                {"move": 0}, "a", np.asarray([1.0, 0.0]), 0.1, q_20k=0.2
            ),
            triage.f59.SpectrumRow(
                {"move": 1}, "b", np.asarray([0.0, 1.0]), 0.2, q_20k=0.4
            ),
        ]
    ]
    seen = {}
    monkeypatch.setattr(
        triage, "_load_root_checkpoint",
        lambda *_args, **_kwargs: rows[0],
    )
    def fake_fit(*args):
        seen["fit_seed"] = args[-1]
        return "model"

    monkeypatch.setattr(triage.f61, "_fit_serializable", fake_fit)
    monkeypatch.setattr(
        triage.f61, "_candidate_checkpoint",
        lambda _parent, _compiled, _model, spec: (
            SimpleNamespace(checkpoint_id="child"),
            {"model": spec},
        ),
    )

    _child, training = triage._fit_one(
        compiled, None, parent, [record], smoke=True, model_seed=59011
    )

    assert seen["fit_seed"] == 59011
    assert training["training_seed"] == 59011
    assert training["model_sha256"] == triage.f61.stable_sha256(
        {"model": {
            "candidate_id": "F61_D0_PAIRWISE_SEED_59011",
            "training_distribution": "D0_RANDOM_REACHABLE",
            "objective": "PAIRWISE_RANKING",
            "seed": 59011,
        }}
    )


def test_arena_uses_game_resumable_path_and_preserves_summary_shape(monkeypatch, tmp_path):
    compiled = SimpleNamespace(ruleset_fingerprint="shogi-fingerprint")
    parent = SimpleNamespace(checkpoint_id="parent")
    child = SimpleNamespace(checkpoint_id="child")
    summary = SimpleNamespace(
        pair_count=2, pair_scores=(0.5, 1.0), mean_pair_score=0.75,
        child_better_pairs=1, tied_pairs=1, child_worse_pairs=0,
        game_wins=1, game_draws=1, game_losses=0,
        bootstrap_low=0.5, bootstrap_high=1.0,
    )
    seen = {}
    monkeypatch.setattr(triage, "OUT", tmp_path)
    monkeypatch.setattr(triage, "generate_arena_openings", lambda *args, **kwargs: "openings")

    def fake_resumable(*args, **kwargs):
        seen["config"] = args[4]
        seen.update(kwargs)
        return SimpleNamespace(
            status="COMPLETE", summary=summary, completed_games=4,
            total_games=4, reason=None,
        )

    monkeypatch.setattr(triage, "run_arena_game_resumable", fake_resumable)
    result = triage._arena(compiled, "native", parent, child, seed=620700, smoke=True)

    assert seen["config"].pairs == 2
    assert seen["config"].nodes_per_move == 100
    assert seen["config"].workers == 1
    assert seen["openings"] == "openings"
    assert seen["stop_on_decision"] is False
    assert str(seen["progress_dir"]).endswith("arena-progress\\shogi-fingerprint\\seed-59012")
    assert result["pair_scores"] == [0.5, 1.0]
    assert result["game_wins"] == 1 and result["game_draws"] == 1
