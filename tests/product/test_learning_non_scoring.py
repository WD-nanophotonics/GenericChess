"""Actual non-scoring Session results must not become TD or arena draws."""
from dataclasses import replace
from types import SimpleNamespace

import pytest
from conftest import make_ruleset, king_type, T
from generic_chess.core.movement import RayAtom
from generic_chess.learning import selfplay
from generic_chess.learning.arena import ArenaGameResult, ArenaPairResult
from generic_chess.learning.material import LearnableMaterialCheckpoint
from generic_chess.learning.tdleaf import TDLeafConfig, tdleaf_update
from generic_chess.learning.trajectory import TrainingTrajectory
from generic_chess.rules.compiler import compile_legacy_ruleset_for_semantic_execution
from generic_chess.rules.schema import RuleDeclaration
from generic_chess.session.session import GameSession


def _compiled(outcome):
    rule = make_ruleset(
        4, [king_type(), T("R", RayAtom((0, 1)), RayAtom((0, -1)))],
        lines=["...k", "....", "R...", "K..."],
    )
    return compile_legacy_ruleset_for_semantic_execution(replace(
        rule, declarations=(RuleDeclaration(
            "claim", 0, require_not_in_check=False, failure_outcome=outcome
        ),),
    ))


def _checkpoint(compiled):
    return LearnableMaterialCheckpoint(
        ruleset_fingerprint=compiled.ruleset_fingerprint,
        board_weights={"R": 1.0}, hand_weights={"R": 1.0}, value_scale=10.,
    )


def _arena(result, owner=0):
    return ArenaGameResult(
        pair=0, opening_id="opening", opening_position_key="root",
        child_owner=owner, winner=result.winner, result=result.status.value,
        plies=0, actions=(), final_position_key="final",
        declaration_id=result.declaration_id,
    )


@pytest.mark.parametrize("outcome,expected", [
    ("WIN", 1.), ("LOSS", -1.), ("RESTART", None), ("NO_CONTEST", None),
])
def test_real_declaration_selfplay_carrier_and_arena(outcome, expected, monkeypatch):
    compiled = _compiled(outcome)
    checkpoint = _checkpoint(compiled)

    class Declare:
        def __init__(self, *args, **kwargs):
            pass

        def search(self, session, limits):
            return SimpleNamespace(
                principal_variation=(), completed_depth=0, declaration_id="claim"
            )

    # Only engine choice is stubbed. Collection executes the real declaration,
    # Session result mapping and trajectory creation; no native library needed.
    monkeypatch.setattr(selfplay, "SemanticSearchEngine", Declare)
    trajectory, = selfplay.collect_self_play(
        compiled, None, checkpoint, selfplay.SelfPlayConfig(games=1, max_depth=1)
    )
    session = GameSession(compiled)
    session.declare("claim")
    assert trajectory.terminal == session.result.status.value == "declaration"
    assert trajectory.winner == session.result.winner
    restored = TrainingTrajectory.from_dict(trajectory.to_dict())
    assert restored.trajectory_id == trajectory.trajectory_id

    game = _arena(session.result)
    pair = ArenaPairResult(0, "opening", game, _arena(session.result, 1))
    if expected is None:
        with pytest.raises(ValueError, match="non-scoring"):
            _ = restored.terminal_z
        with pytest.raises(ValueError, match="non-scoring"):
            tdleaf_update([restored], checkpoint, TDLeafConfig(alpha=.01))
        assert game.child_points is None and not game.is_scoring_result
        assert pair.child_pair_score is None
    else:
        assert restored.terminal_z == expected
        assert game.child_points == (1. if expected > 0 else 0.)
        assert pair.child_pair_score == .5


@pytest.mark.parametrize("terminal", ["no_contest", "declaration"])
def test_non_scoring_cannot_be_coerced_by_truncation_bootstrap(terminal):
    trajectory = TrainingTrajectory(
        ruleset_fingerprint="fp", generation=0, game_seed=1,
        initial_position_key="root", actions=(), search_nodes=1,
        search_max_depth=1, points=(), terminal=terminal, winner=None,
        type_ids=(), truncated=True, bootstrap_value=.25,
    )
    with pytest.raises(ValueError, match="non-scoring"):
        _ = trajectory.terminal_z


def test_real_rule_draw_still_scores_and_legacy_payload_is_unchanged():
    # Keep the draw control free from any declaration.
    compiled = compile_legacy_ruleset_for_semantic_execution(
        make_ruleset(4, [king_type()], lines=["...k", "....", "....", "K..."],
                     max_ply=1)
    )
    session = GameSession(compiled)
    session.submit(session.legal_actions()[0])
    assert session.result.winner is None and session.result.status.value == "max_ply"
    trajectory = TrainingTrajectory(
        ruleset_fingerprint=compiled.ruleset_fingerprint, generation=0,
        game_seed=1, initial_position_key="root", actions=(), search_nodes=1,
        search_max_depth=1, points=(), terminal=session.result.status.value,
        winner=None, type_ids=(),
    )
    before = trajectory.to_dict()
    restored = TrainingTrajectory.from_dict(before)
    assert restored.to_dict() == before
    assert restored.trajectory_id == trajectory.trajectory_id
    assert restored.terminal_z == 0.
    assert _arena(session.result).child_points == .5
