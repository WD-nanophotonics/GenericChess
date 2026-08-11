"""Deterministic R1.2 cooperative semantic-search contracts."""

from __future__ import annotations

import pytest

from generic_chess.ai.alphabeta.player import AlphaBetaPlayer
from generic_chess.ai.alphabeta.tuning import SearchTuning
from generic_chess.ai.evaluation.cache import EvaluationProfileCache
from generic_chess.ai.evaluation.config import EvaluationConfig
from generic_chess.ai.limits import SearchLimits
from generic_chess.core.lazy_transitions import (
    iter_legal_successor_handles,
    materialize_legal_successor,
)
from generic_chess.core.movegen import iter_legal_actions, legal_actions
from generic_chess.core.semantic_executor import SemanticEngine
from generic_chess.core.position import GameState
from generic_chess.core.transition import apply_action, initial_state
from generic_chess.learning.round5_corrective_r1 import SearchSemanticCompiled
from generic_chess.learning.shogi_rules import sfen_to_gc_state
from generic_chess.learning.shogi_semantic_rules import build_semantic_shogi_ruleset
from generic_chess.rules.compiler import compile_semantic_ruleset
from generic_chess.session.session import GameSession

from rule_semantics_ir_fixtures import cannon_ruleset, castling_ruleset
from test_semantic_executor import _cannon_position


class ProbeAbort(Exception):
    pass


def _cannon_engine_and_position():
    engine = SemanticEngine(compile_semantic_ruleset(cannon_ruleset()))
    return engine, _cannon_position(engine, enemy_file=2, screen=True)


@pytest.mark.parametrize("fixture", [cannon_ruleset, castling_ruleset])
def test_streaming_legal_actions_matches_full_semantic_order(fixture):
    compiled = compile_semantic_ruleset(fixture())
    engine = SemanticEngine(compiled)
    position = initial_state(compiled).position

    full = engine.legal_actions(position)
    streamed = tuple(engine.iter_legal_actions(position))

    assert streamed == full


def test_semantic_candidate_and_s3_work_is_cooperatively_abortable():
    engine, position = _cannon_engine_and_position()
    original = position
    calls = 0

    def checkpoint():
        nonlocal calls
        calls += 1
        if calls >= 8:
            raise ProbeAbort

    with pytest.raises(ProbeAbort):
        tuple(engine.iter_legal_actions(position, checkpoint=checkpoint))
    assert calls == 8
    assert position == original


def test_s3_reply_existence_query_accepts_caller_abort():
    engine, position = _cannon_engine_and_position()
    calls = 0

    def checkpoint():
        nonlocal calls
        calls += 1
        if calls >= 6:
            raise ProbeAbort

    with pytest.raises(ProbeAbort):
        engine._exists_s3_reply(position, checkpoint=checkpoint)
    assert calls == 6


def test_semantic_handles_stream_without_child_materialization():
    engine, position = _cannon_engine_and_position()
    compiled = engine.semantic
    state = GameState(
        position=position,
        ply_count=0,
        repetition_counts=(),
        terminal_status=engine.terminal_result(position, 0, (), ()),
        history=(),
    )
    handles = iter_legal_successor_handles(state, compiled)
    first = next(handles)
    assert first.materialized is False
    child, _ = materialize_legal_successor(state, first, compiled)
    assert first.materialized is True
    assert child.position.side_to_move == 1 - position.side_to_move
    direct = apply_action(state, first.action, compiled)
    assert child == direct


@pytest.fixture(scope="module")
def certified_compiled():
    semantic = compile_semantic_ruleset(build_semantic_shogi_ruleset())
    assert semantic.ruleset_fingerprint == (
        "5b3d04eda31a342b729fc9af8a04cdde13c796646b2b37024891f8c99703c345"
    )
    return SearchSemanticCompiled(
        ir=semantic.ir,
        _legacy_compiled=semantic._legacy_compiled,
        support=semantic.support,
    )


@pytest.mark.parametrize("seconds", [0.10, 0.25, 0.50, 1.00])
def test_certified_semantic_time_budget_returns_legal_action(certified_compiled, seconds):
    compiled = certified_compiled
    state = sfen_to_gc_state(
        compiled,
        "lnsgkgsnl/1r5b1/p1ppppppp/9/9/9/P1PPPPPPP/1B5R1/LNSGKGSNL b - 1",
    )
    session = GameSession(compiled)
    session._state = state
    cfg = EvaluationConfig()
    player = AlphaBetaPlayer(
        compiled,
        evaluation_config=cfg,
        profile_cache=EvaluationProfileCache(use_disk=False),
        use_disk_cache=False,
        tuning=SearchTuning(use_root_tactical=True),
    )
    decision = player.choose_action(
        session,
        SearchLimits(max_depth=64, max_time_seconds=seconds, quiescence_max_depth=0),
    )

    assert decision.action in legal_actions(session.state, compiled)
    assert decision.time_to_first_legal_action is not None
    assert decision.time_to_first_legal_action <= decision.elapsed_seconds
    assert decision.elapsed_seconds <= seconds + max(0.050, seconds * 0.05)
