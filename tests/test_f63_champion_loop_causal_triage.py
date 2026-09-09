"""Static contracts for the F63 causal triage harness."""

import inspect
import hashlib
import json
from types import SimpleNamespace

import pytest

from scripts import f63_champion_loop_causal_triage as f63


def test_f63_freezes_teacher_gate_and_candidate_population():
    assert f63.WORK_ORDER == "GENERICCHESS-F63-CHAMPION-LOOP-CAUSAL-TRIAGE"
    assert f63.SHALLOW_NODES == 2_000
    assert f63.DEEP_NODES == 20_000
    assert f63.GEN2_SEEDS == (59011, 59012, 59013)
    assert f63.F62_STAGE_SHA == (
        "e7a93423d6058c68fe7ccbc61302584ca1e8869aa828586254f72f4dfdac2c70"
    )
    assert f63.F62_RECORDS_SHA == (
        "b7a6dc134bf1232fa90d9734ad070c184ecd09f691bc92958686093181d3ff61"
    )


def test_f63_teacher_gate_is_stricter_than_a_tied_triage():
    tied = {
        "mean_pair_score": 0.5,
        "child_better_pairs": 2,
        "child_worse_pairs": 2,
    }
    clear = {
        "mean_pair_score": 0.75,
        "child_better_pairs": 3,
        "child_worse_pairs": 1,
    }
    assert not f63._teacher_is_clearly_supported(tied)
    assert f63._teacher_is_clearly_supported(clear)


def test_f63_frozen_teacher_artifact_records_exact_seven_pair_evidence():
    artifact = json.loads(f63.TEACHER_DECISION_PATH.read_text(encoding="utf-8"))
    assert artifact["schema"] == "generic-chess-f63-teacher-decision-v1"
    assert artifact["stage"]["requested_pairs"] == 8
    assert artifact["stage"]["completed_pairs"] == 7
    assert [row["pair_index"] for row in artifact["pair_files"]] == list(range(1, 8))
    assert artifact["observed_total"] == pytest.approx(4.75)
    assert artifact["worst_possible_final_mean"] == pytest.approx(0.59375)
    assert artifact["decision_state"] == "PASS_LOCKED"
    assert artifact["strength_estimate_complete"] is False


def test_candidate_stage_routes_game_v1_with_explicit_caps_and_pause_path(monkeypatch):
    captured = {}

    monkeypatch.setattr(
        f63,
        "generate_arena_openings",
        lambda *args, **kwargs: "openings",
    )

    class Bound:
        decision_state = "UNRESOLVED"
        decision_sufficient = False
        strength_estimate_complete = False

    def fake_game_runner(*args, **kwargs):
        captured.update(kwargs)
        return type(
            "Run",
            (),
            {
                "status": "INCOMPLETE",
                "completed_games": 0,
                "completed_pairs": 0,
                "total_games": 8,
                "reason": "test",
                "decision_bound": Bound(),
                "summary": None,
            },
        )()

    monkeypatch.setattr(f63, "run_arena_game_resumable", fake_game_runner)
    payload = f63._run_candidate_stage(
        object(), object(), object(), object(), 4, 630403, "candidate-test"
    )
    assert payload["status"] == "INCOMPLETE"
    assert captured["stage_id"] == "candidate-test"
    assert captured["pause_file"] == f63.OUT / "candidate-pause.request"
    assert captured["execution_caps"].max_stage_games == 8
    assert captured["execution_caps"].per_game_wall_seconds == 10_000.0
    assert captured["execution_caps"].per_game_nodes == 1_000_000
    assert captured["execution_caps"].per_game_plies == 512
    assert captured["execution_caps"].stage_wall_seconds == 10_800.0


def test_common4_caps_are_calibrated_but_selected_caps_remain_frozen():
    common = f63._candidate_caps(4)
    assert common == f63._calibrated_common4_caps()
    assert common.game_lanes(4, 4) == 4
    assert common.logical_cpu_count == 10
    assert f63._candidate_caps(8) == f63.ArenaExecutionCaps(
        per_game_wall_seconds=900.0,
        per_game_nodes=200_000,
        per_game_plies=80,
        max_stage_games=16,
        max_concurrent_games=10,
        stage_wall_seconds=7_200.0,
        logical_cpu_count=10,
    )
    assert f63._candidate_caps(32) == f63.ArenaExecutionCaps(
        per_game_wall_seconds=900.0,
        per_game_nodes=200_000,
        per_game_plies=80,
        max_stage_games=64,
        max_concurrent_games=10,
        stage_wall_seconds=28_800.0,
        logical_cpu_count=10,
    )


def test_r6_completed_game_carries_forward_without_mutating_source(tmp_path):
    compiled, _native, _profile = f63.f59._ruleset(f63.LABEL)
    source_manifest = json.loads(f63.R6_SOURCE_MANIFEST.read_text(encoding="utf-8"))
    openings = f63.generate_arena_openings(
        compiled, count=4, seed=630403, min_plies=2, max_plies=6
    )
    config = f63.ArenaConfig(
        pairs=4, nodes_per_move=2_000, max_depth=12, tt_megabytes=8,
        opening_seed=630403, opening_count=4, min_plies=2, max_plies=6, workers=4,
    )
    parent = SimpleNamespace(checkpoint_id=f63.GEN1_ID)
    candidate = SimpleNamespace(
        checkpoint_id=source_manifest["identity"]["child_checkpoint_id"]
    )
    source_before = f63.R6_SOURCE_GAME.read_bytes()
    destination = tmp_path / "calibrated"

    f63._carry_forward_r6_game(
        compiled, parent, candidate, config, openings, destination,
        stage_id="candidate-59011-common-4",
    )

    assert f63.R6_SOURCE_GAME.read_bytes() == source_before
    assert hashlib.sha256(source_before).hexdigest() == f63.R6_SOURCE_GAME_SHA256
    manifest = json.loads((destination / "manifest.json").read_text(encoding="utf-8"))
    imported = json.loads(
        (destination / "game-000000-owner-0.json").read_text(encoding="utf-8")
    )
    assert manifest["identity"]["execution_caps"]["per_game_plies"] == 512
    assert imported["identity_sha256"] == manifest["identity_sha256"]
    assert imported["game"]["plies"] == 72
    assert imported["game"]["result"] == "checkmate"
    assert imported["game_identity"]["hard_caps"]["per_game_nodes"] == 1_000_000
    assert imported["game_identity"]["node_budgets"] == {
        "parent": 2_000, "child": 2_000
    }


def test_r6_carry_forward_rejects_equal_or_tighter_caps(monkeypatch, tmp_path):
    compiled, _native, _profile = f63.f59._ruleset(f63.LABEL)
    source_manifest = json.loads(f63.R6_SOURCE_MANIFEST.read_text(encoding="utf-8"))
    openings = f63.generate_arena_openings(
        compiled, count=4, seed=630403, min_plies=2, max_plies=6
    )
    config = f63.ArenaConfig(
        pairs=4, nodes_per_move=2_000, max_depth=12, tt_megabytes=8,
        opening_seed=630403, opening_count=4, min_plies=2, max_plies=6, workers=4,
    )
    parent = SimpleNamespace(checkpoint_id=f63.GEN1_ID)
    candidate = SimpleNamespace(
        checkpoint_id=source_manifest["identity"]["child_checkpoint_id"]
    )
    monkeypatch.setattr(
        f63, "_candidate_caps",
        lambda _pairs: f63.ArenaExecutionCaps(
            per_game_wall_seconds=900.0,
            per_game_nodes=200_000,
            per_game_plies=80,
            max_stage_games=8,
            max_concurrent_games=8,
            stage_wall_seconds=3_600.0,
            logical_cpu_count=10,
        ),
    )
    with pytest.raises(RuntimeError, match="caps are not calibrated"):
        f63._carry_forward_r6_game(
            compiled, parent, candidate, config, openings, tmp_path / "reject",
            stage_id="candidate-59011-common-4",
        )


@pytest.mark.parametrize(
    "mutation",
    ["checkpoint", "opening", "owner", "search_budget", "depth", "tt", "telemetry"],
)
def test_r6_carry_forward_rejects_scientific_identity_changes(
    monkeypatch, tmp_path, mutation
):
    compiled, _native, _profile = f63.f59._ruleset(f63.LABEL)
    source_manifest = json.loads(f63.R6_SOURCE_MANIFEST.read_text(encoding="utf-8"))
    source_game = json.loads(f63.R6_SOURCE_GAME.read_text(encoding="utf-8"))
    if mutation == "checkpoint":
        source_manifest["identity"]["child_checkpoint_id"] = "changed-checkpoint"
        source_manifest["identity_sha256"] = f63.stable_sha256(source_manifest["identity"])
    elif mutation == "opening":
        source_game["game_identity"]["opening"]["final_position_key"] = "changed-opening"
    elif mutation == "owner":
        source_game["game"]["child_owner"] = 1
    elif mutation == "search_budget":
        source_game["game_identity"]["node_budgets"]["child"] = 1_000
    elif mutation == "depth":
        source_game["game_identity"]["max_depth"] = 11
    elif mutation == "tt":
        source_game["game_identity"]["tt_megabytes"] = 4
    else:
        source_game["game_identity"]["capture_search_metrics"] = False
    manifest_path = tmp_path / "manifest.json"
    game_path = tmp_path / "source-game.json"
    manifest_path.write_text(json.dumps(source_manifest), encoding="utf-8")
    game_path.write_text(json.dumps(source_game), encoding="utf-8")
    monkeypatch.setattr(f63, "R6_SOURCE_MANIFEST", manifest_path)
    monkeypatch.setattr(f63, "R6_SOURCE_GAME", game_path)
    monkeypatch.setattr(
        f63, "R6_SOURCE_MANIFEST_SHA256", hashlib.sha256(manifest_path.read_bytes()).hexdigest()
    )
    monkeypatch.setattr(
        f63, "R6_SOURCE_GAME_SHA256", hashlib.sha256(game_path.read_bytes()).hexdigest()
    )
    if mutation == "checkpoint":
        monkeypatch.setattr(f63, "R6_SOURCE_IDENTITY_SHA256", source_manifest["identity_sha256"])
    openings = f63.generate_arena_openings(
        compiled, count=4, seed=630403, min_plies=2, max_plies=6
    )
    config = f63.ArenaConfig(
        pairs=4, nodes_per_move=2_000, max_depth=12, tt_megabytes=8,
        opening_seed=630403, opening_count=4, min_plies=2, max_plies=6, workers=4,
    )
    parent = SimpleNamespace(checkpoint_id=f63.GEN1_ID)
    candidate = SimpleNamespace(
        checkpoint_id=source_game["game_identity"]["child_checkpoint_id"]
    )
    with pytest.raises(RuntimeError):
        f63._carry_forward_r6_game(
            compiled, parent, candidate, config, openings, tmp_path / "reject",
            stage_id="candidate-59011-common-4",
        )


def test_candidate_resume_source_has_no_teacher_stage_call():
    source = inspect.getsource(f63.run_candidate_resume)
    context_source = inspect.getsource(f63._resume_context)
    assert "_run_teacher_stage" not in source
    assert "_run_candidate_resume_stage" in source
    assert "validate_frozen_teacher_decision" in context_source
    assert "CANDIDATE_PATH" in context_source


def test_terminal_summary_accepts_candidate_only_resumable_result():
    result = {
        "teacher": {
            "status": "FROZEN_DECISION_ONLY",
            "decision_state": "PASS_LOCKED",
            "decision_sufficient": True,
        },
        "candidate_loop": {
            "status": "COMMON_INCOMPLETE_RESUMABLE",
            "candidates": [{"seed": 59011}],
        },
    }
    summary = f63._terminal_summary(result)
    assert summary["teacher_classification"] is None
    assert summary["teacher_decision_state"] == "PASS_LOCKED"
    assert summary["candidate_status"] == "COMMON_INCOMPLETE_RESUMABLE"
    assert summary["candidate_classification"] is None
    assert json.dumps(summary, sort_keys=True)


@pytest.mark.parametrize(
    ("stage", "expected"),
    [
        ({"status": "INCOMPLETE", "decision_state": "PASS_LOCKED"}, "RUN_32"),
        ({"status": "COMPLETE", "decision_state": "PASS_LOCKED"}, "RUN_32"),
        ({"status": "INCOMPLETE", "decision_state": "FAIL_LOCKED"}, "FAIL_LOCKED"),
        ({"status": "COMPLETE", "decision_state": "FAIL_LOCKED"}, "FAIL_LOCKED"),
        ({"status": "PAUSED", "decision_state": "UNRESOLVED"}, "INCONCLUSIVE_RESUMABLE"),
        ({"status": "INCOMPLETE", "decision_state": "UNRESOLVED"}, "INCONCLUSIVE_RESUMABLE"),
        ({"status": "COMPLETE", "decision_state": "UNRESOLVED"}, "RUN_32"),
    ],
)
def test_selected_eight_continuation_is_decision_aware(stage, expected):
    assert f63._selected_eight_continuation(stage) == expected


def test_candidate_resume_freezes_all_identities_before_first_arena(monkeypatch, tmp_path):
    compiled = object()
    gen1 = type("Checkpoint", (), {"checkpoint_id": f63.GEN1_ID})()
    checkpoints = {
        59011: type("Checkpoint", (), {"checkpoint_id": "candidate-59011"})(),
        59012: type("Checkpoint", (), {"checkpoint_id": "candidate-59012"})(),
        59013: type("Checkpoint", (), {"checkpoint_id": "candidate-59013"})(),
    }
    identities = {
        seed: {"checkpoint_id": checkpoint.checkpoint_id}
        for seed, checkpoint in checkpoints.items()
    }
    persisted_identity = {
        "gen2_checkpoint_id": "candidate-59012",
        "training": {"records_sha256": f63.F62_RECORDS_SHA},
    }
    monkeypatch.setattr(f63.f59, "_ruleset", lambda _label: (compiled, object(), object()))
    monkeypatch.setattr(f63, "_load_gen1", lambda _compiled: gen1)
    monkeypatch.setattr(
        f63,
        "validate_frozen_teacher_decision",
        lambda _compiled: {
            "artifact": {
                "authorizes_candidate_branch": True,
                "original_teacher_identity_sha256": "teacher-id",
            },
            "bound": type("Bound", (), {
                "decision_state": "PASS_LOCKED",
                "decision_sufficient": True,
                "strength_estimate_complete": False,
            })(),
        },
    )
    monkeypatch.setattr(
        f63,
        "_load_f62_training_summary",
        lambda _compiled, _gen1: (object(), {"records_sha256": f63.F62_RECORDS_SHA}, checkpoints[59012], persisted_identity),
    )
    monkeypatch.setattr(
        f63,
        "_fit_candidate",
        lambda _compiled, _gen1, _summary, _provenance, seed: (
            checkpoints[seed], identities[seed]
        ),
    )
    writes = []
    monkeypatch.setattr(f63, "_atomic_json", lambda path, payload: writes.append((path, payload)))
    monkeypatch.setattr(f63, "CANDIDATE_PATH", tmp_path / "candidates.json")
    arena_calls = []

    def fake_stage(*args, **kwargs):
        arena_calls.append((args, kwargs))
        return {
            "status": "COMPLETE",
            "mean_pair_score": 0.5,
            "game_wins": 1,
            "game_losses": 1,
            "bootstrap_low": 0.0,
        }

    monkeypatch.setattr(f63, "_run_candidate_stage", fake_stage)
    result = f63.run_candidate_resume(stage="common-4")
    assert result["candidate_loop"]["status"] == "COMMON_COMPLETE"
    candidate_write_index = next(
        index for index, (path, _payload) in enumerate(writes)
        if path == f63.CANDIDATE_PATH
    )
    assert candidate_write_index == 0
    assert len(arena_calls) == 3
    assert all(
        writes[candidate_write_index][1]["candidates"][index]["checkpoint_id"]
        for index in range(3)
    )
