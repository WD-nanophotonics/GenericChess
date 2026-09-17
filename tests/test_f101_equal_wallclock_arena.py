"""F101 intentional per-move wall-clock arena contracts."""

from pathlib import Path
from types import SimpleNamespace

import pytest

from generic_chess.ai.evaluation.config import EvaluationConfig
from generic_chess.ai.limits import SearchLimits
from generic_chess.learning import arena as arena_module
from generic_chess.learning.arena import (
    ArenaCapHit,
    ArenaConfig,
    ArenaExecutionCaps,
    _game_progress_identity_for,
    _play_one_game,
)
from generic_chess.learning.material import LearnableMaterialCheckpoint
from generic_chess.native import SemanticSearchEngine, native_available
from generic_chess.native.compiler import compile_native_semantic_rules
from generic_chess.rules.compiler import compile_ruleset_for_execution, compile_semantic_ruleset
from generic_chess.rules.western_chess import build_western_chess_ruleset
from generic_chess.session.session import GameSession


ROOT = Path(__file__).resolve().parents[1]


def test_timed_arena_passes_intentional_budget_and_accepts_time_budget(monkeypatch):
    action = object()
    captured = []

    class FakeSession:
        def __init__(self, _compiled):
            self.state = SimpleNamespace(position=SimpleNamespace(side_to_move=0))
            self.result = SimpleNamespace(
                status=SimpleNamespace(value="ongoing"), winner=None,
            )

        def legal_actions(self):
            return [action]

        def submit(self, submitted):
            assert submitted is action
            self.result.status.value = "checkmate"
            self.result.winner = 0

    class FakeEngine:
        def search(self, _session, limits):
            captured.append(limits)
            return SimpleNamespace(
                action=action, declaration_id=None, elapsed_seconds=1.0,
                nodes=17, qnodes=0, score=0, completed_depth=2,
                selective_depth=2, termination_reason="time_budget",
                used_fallback=False,
            )

    monkeypatch.setattr(arena_module, "GameSession", FakeSession)
    monkeypatch.setattr(arena_module, "_engine_for", lambda *args, **kwargs: FakeEngine())
    monkeypatch.setattr(arena_module, "position_identity_key", lambda *_args: "key")
    game = _play_one_game(
        SimpleNamespace(ruleset_fingerprint="rules-v1"), None,
        SimpleNamespace(), SimpleNamespace(),
        opening=SimpleNamespace(actions=(), index=0, final_position_key="key"),
        child_owner=0,
        config=ArenaConfig(
            pairs=1, nodes_per_move=17, max_depth=3, move_time_seconds=1.0,
        ),
        capture_search_metrics=True,
    )

    assert game.result == "checkmate"
    assert captured[0].max_time_seconds == pytest.approx(1.0)
    assert game.search_metrics[0]["timing_mode"] == "per_move_search_time"
    assert game.search_metrics[0]["time_budget_termination"] is True
    assert game.search_metrics[0]["search_wall_seconds"] >= 0.0
    assert game.search_metrics[0]["wall_budget_overshoot_seconds"] >= 0.0


def test_timed_arena_keeps_hard_time_limit_distinct(monkeypatch):
    action = object()

    class FakeSession:
        def __init__(self, _compiled):
            self.state = SimpleNamespace(position=SimpleNamespace(side_to_move=0))
            self.result = SimpleNamespace(status=SimpleNamespace(value="ongoing"))

        def legal_actions(self):
            return [action]

        def submit(self, _action):
            raise AssertionError("hard timeout must not submit a searched action")

    class FakeEngine:
        def search(self, _session, _limits):
            return SimpleNamespace(
                action=action, declaration_id=None, elapsed_seconds=1.0,
                nodes=1, qnodes=0, score=0, completed_depth=0,
                selective_depth=0, termination_reason="time_limit",
                used_fallback=False,
            )

    monkeypatch.setattr(arena_module, "GameSession", FakeSession)
    monkeypatch.setattr(arena_module, "_engine_for", lambda *args, **kwargs: FakeEngine())
    monkeypatch.setattr(arena_module, "position_identity_key", lambda *_args: "key")
    with pytest.raises(ArenaCapHit, match="per_game_wall_seconds"):
        _play_one_game(
            SimpleNamespace(ruleset_fingerprint="rules-v1"), None,
            SimpleNamespace(), SimpleNamespace(),
            opening=SimpleNamespace(actions=(), index=0, final_position_key="key"),
            child_owner=0,
            config=ArenaConfig(
                pairs=1, nodes_per_move=17, max_depth=3, move_time_seconds=1.0,
            ),
            execution_caps=ArenaExecutionCaps(per_game_wall_seconds=2.0),
        )


def test_unconfigured_arena_path_keeps_unbounded_search_limit(monkeypatch):
    action = object()
    captured = []

    class FakeSession:
        def __init__(self, _compiled):
            self.state = SimpleNamespace(position=SimpleNamespace(side_to_move=0))
            self.result = SimpleNamespace(
                status=SimpleNamespace(value="ongoing"), winner=None,
            )

        def legal_actions(self):
            return [action]

        def submit(self, _action):
            self.result.status.value = "checkmate"

    class FakeEngine:
        def search(self, _session, limits):
            captured.append(limits)
            return SimpleNamespace(
                action=action, declaration_id=None, elapsed_seconds=0.0,
                nodes=1, qnodes=0, score=0, completed_depth=1,
                selective_depth=1, termination_reason="node_budget",
                used_fallback=False,
            )

    monkeypatch.setattr(arena_module, "GameSession", FakeSession)
    monkeypatch.setattr(arena_module, "_engine_for", lambda *args, **kwargs: FakeEngine())
    monkeypatch.setattr(arena_module, "position_identity_key", lambda *_args: "key")
    _play_one_game(
        SimpleNamespace(ruleset_fingerprint="rules-v1"), None,
        SimpleNamespace(), SimpleNamespace(),
        opening=SimpleNamespace(actions=(), index=0, final_position_key="key"),
        child_owner=0,
        config=ArenaConfig(pairs=1, nodes_per_move=17, max_depth=3),
    )
    assert captured[0].max_time_seconds is None


def test_timing_mode_and_budget_are_bound_to_game_identity():
    config = ArenaConfig(
        pairs=1, nodes_per_move=17, max_depth=3, move_time_seconds=1.0,
    )
    identity = _game_progress_identity_for(
        {
            "stage_id": "f101",
            "arena_id": "arena",
            "parent_checkpoint_id": "parent",
            "child_checkpoint_id": "child",
            "ordering_checkpoint_id": "ordering",
        },
        config,
        ArenaExecutionCaps(logical_cpu_count=1),
        {"final_position_key": "opening"},
        0,
        0,
        capture_search_metrics=True,
    )
    assert identity["timing_mode"] == "per_move_search_time"
    assert identity["move_time_seconds"] == pytest.approx(1.0)


@pytest.mark.skipif(not native_available(), reason="native extension unavailable")
def test_timed_search_returns_legal_actions_for_both_ordering_modes():
    ruleset = build_western_chess_ruleset()
    compiled = compile_semantic_ruleset(ruleset)
    native = compile_native_semantic_rules(compiled)
    legacy = compile_ruleset_for_execution(ruleset)
    from generic_chess.ai.evaluation.profile import build_ruleset_profile

    profile = build_ruleset_profile(legacy, EvaluationConfig())
    parent = LearnableMaterialCheckpoint.from_profile(compiled, profile)
    ordering = parent.child_checkpoint(
        board_weights={key: value * 0.9 for key, value in parent.board_weights.items()},
        hand_weights={key: value * 0.9 for key, value in parent.hand_weights.items()},
        games_seen_delta=0, positions_seen_delta=0, training_updates_delta=1,
        training_config_hash="f101-timed-ordering", training_seed=101,
    )
    for ordering_checkpoint in (None, ordering):
        session = GameSession(compiled)
        engine = SemanticSearchEngine(
            compiled, native, checkpoint=parent,
            ordering_checkpoint=ordering_checkpoint, tt_megabytes=1,
        )
        result = engine.search(
            session,
            SearchLimits(max_depth=64, max_time_seconds=0.01, quiescence_max_depth=0),
            root_window_pruning=False,
        )
        assert result.action in session.legal_actions()
        assert result.termination_reason == "time_budget"
