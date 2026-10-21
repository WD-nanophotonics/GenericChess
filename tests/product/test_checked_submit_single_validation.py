"""Observed duplicate semantic membership work and its full-state safety boundary."""
from dataclasses import replace

import pytest

from generic_chess.core.errors import IllegalActionError
from generic_chess.core.semantic_executor import SemanticEngine, semantic_engine_for, _semantic_public_action
from generic_chess.core.transition import apply_action, legal_successors
from generic_chess.rules.compiler import compile_semantic_ruleset
from generic_chess.rules.western_chess import build_western_chess_ruleset
from generic_chess.session.session import GameSession


def test_checked_submit_resolves_parent_legality_once_and_keeps_full_child(monkeypatch):
    compiled = compile_semantic_ruleset(build_western_chess_ruleset())
    session = GameSession(compiled)
    parent = session.state
    action, expected = legal_successors(parent, compiled)[0]
    original = SemanticEngine.iter_legal_action_bindings
    parent_enumerations = []

    def observed(self, position, *args, **kwargs):
        if position is parent.position:
            parent_enumerations.append(position)
        yield from original(self, position, *args, **kwargs)

    monkeypatch.setattr(SemanticEngine, 'iter_legal_action_bindings', observed)
    child = apply_action(parent, action, compiled)
    assert child == expected
    assert len(parent_enumerations) == 1
    assert session.state is parent
    assert not session.history


def test_checked_submit_rejects_real_max_ply_parent_with_playable_position():
    compiled = compile_semantic_ruleset(replace(
        build_western_chess_ruleset(), max_ply=1,
        automatic_adjudications=(), declarations=(),
    ))
    session = GameSession(compiled)
    session.submit(session.legal_actions()[0])
    assert session.result.status.value == 'max_ply'
    replayed = GameSession.replay(compiled, session.to_record())
    assert replayed.state == session.state
    engine = semantic_engine_for(compiled)
    still_legal = tuple(engine.iter_legal_actions(session.state.position))
    assert still_legal
    action = _semantic_public_action(engine, still_legal[0])
    before = (session.state, session.history, session.to_record(), session._search_witnesses)
    with pytest.raises(IllegalActionError, match='cannot apply an action to a terminal state'):
        apply_action(session.state, action, compiled)
    assert before == (session.state, session.history, session.to_record(), session._search_witnesses)
