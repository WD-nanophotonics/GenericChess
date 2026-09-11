"""Contract tests for the F81-R2 audit and cap corrective."""

from pathlib import Path
from types import SimpleNamespace

import pytest

from generic_chess.learning import arena as arena_module
from generic_chess.learning.arena import ArenaCapHit, ArenaConfig, ArenaExecutionCaps, _play_one_game
from scripts import f81_r2_time_budget_cap_corrective as f81r2


ROOT = Path(__file__).resolve().parents[1]


def test_f81_r2_audit_is_zero_compute_and_fixed_scope():
    source = (ROOT / "scripts" / "f81_r2_time_budget_cap_corrective.py").read_text(encoding="utf-8")
    assert f81r2.WORK_ORDER == "GENERICCHESS-F81-R2-TIME-BUDGET-CAP-CORRECTIVE"
    assert f81r2.BASELINE_SHA == "55c7bbcccb21d78d0398e0deecbfd5301e059392"
    assert "generate_arena_openings" not in source
    assert "CAP_LIKE_REASONS" in source
    assert "time_budget" in source
    assert "run_corrective" in source


def test_f81_r2_audit_requires_all_frozen_games_and_tracks_provenance():
    source = (ROOT / "scripts" / "f81_r2_time_budget_cap_corrective.py").read_text(encoding="utf-8")
    assert "expected exactly sixteen F81-R1 game files" in source
    assert "progress_sha256" in source
    assert "contaminated_pair_indices" in source
    assert "root_window_pruning" in source
    assert "termination_reason_counts" in source
    assert "f81_r1_time_cap_audit.json" in source


def test_native_time_budget_is_an_arena_cap_before_action(monkeypatch):
    action = object()

    class FakeSession:
        def __init__(self, _compiled):
            self.state = SimpleNamespace(position=SimpleNamespace(side_to_move=0))
            self.result = SimpleNamespace(status=SimpleNamespace(value="ongoing"))

        def submit(self, _action):
            raise AssertionError("time-budget cap must stop before action submission")

        def legal_actions(self):
            return [action]

    class FakeEngine:
        def search(self, _session, _limits):
            return SimpleNamespace(
                action=action,
                declaration_id=None,
                elapsed_seconds=0.0,
                nodes=1,
                qnodes=0,
                score=0,
                completed_depth=0,
                selective_depth=0,
                termination_reason="time_budget",
                used_fallback=False,
            )

    monkeypatch.setattr(arena_module, "GameSession", FakeSession)
    monkeypatch.setattr(arena_module, "_engine_for", lambda *args: FakeEngine())
    monkeypatch.setattr(arena_module, "position_identity_key", lambda *_args: "key")
    with pytest.raises(ArenaCapHit, match="per_game_wall_seconds"):
        _play_one_game(
            SimpleNamespace(ruleset_fingerprint="rules-v1"), None,
            SimpleNamespace(), SimpleNamespace(),
            opening=SimpleNamespace(actions=(), index=0, final_position_key="key"),
            child_owner=0,
            config=ArenaConfig(pairs=1, nodes_per_move=17, max_depth=3),
            execution_caps=ArenaExecutionCaps(per_game_wall_seconds=1.0),
        )
