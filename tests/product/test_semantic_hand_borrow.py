"""Preserve accepted hand normalization and ordered trial effects."""
from dataclasses import replace

import pytest

from generic_chess import build_builtin_ruleset, compile_ruleset_for_execution
from generic_chess.core.position import Hands
from generic_chess.core.pieces import Piece
from generic_chess.core import semantic_executor as sem
from generic_chess.core.transition import initial_state
from generic_chess.rules.ir import CompiledEffect, CompiledSquareRef, CompiledTypeRef


def quiet():
    compiled = compile_ruleset_for_execution(build_builtin_ruleset("western_chess"))
    engine = sem.semantic_engine_for(compiled)
    parent = initial_state(compiled).position
    action, binding = next(engine.iter_legal_action_bindings(parent))
    return engine, parent, action, binding


@pytest.mark.parametrize("counts", [(), (("P", 1), ("R", 2)),
    (("R", 2), ("P", 1)), (("R", 1), ("P", 0), ("R", 2)), []])
@pytest.mark.parametrize("owner", [0, 1])
def test_quiet_transition_preserves_dict_sorted_normalization(counts, owner):
    engine, parent, action, binding = quiet()
    hands = list(parent.hands)
    hands[owner] = Hands(counts)
    parent = replace(parent, hands=tuple(hands))
    child = engine._transition(parent, action, binding)
    assert child.hands[owner] == Hands(tuple(sorted(dict(counts).items())))
    assert parent.hands[owner].counts == counts
    assert child.hands[1-owner] == parent.hands[1-owner]
    # No mutable storage may be shared with another trial or an exported child.
    a = sem._WorkingPosition(parent, engine.support)
    b = sem._WorkingPosition(parent, engine.support)
    exported = a.to_position(parent.aux_state, parent.ruleset_fingerprint)
    a.set_piece(action.target, Piece(1-owner, "P", "Q", promoted=True))
    sem._apply_effect(CompiledEffect("remove",
        square_ref=CompiledSquareRef("target"), piece_owner="opponent",
        disposition="capture_to_hand"), a, engine.support, (), parent,
        replace(binding, actor_owner=owner))
    assert b.to_position(parent.aux_state, parent.ruleset_fingerprint) == exported
    assert exported.hands[owner] == Hands(tuple(sorted(dict(counts).items())))


def ordered_capture():
    engine, parent, action, binding = quiet()
    board = list(parent.board)
    board[action.target] = Piece(1, "P", "Q", promoted=True)
    parent = replace(parent, board=tuple(board))
    effects = (
        CompiledEffect("remove", square_ref=CompiledSquareRef("target"),
                       piece_owner="opponent", disposition="capture_to_hand"),
        CompiledEffect("remove_from_hand", piece_type_ref=CompiledTypeRef("explicit", "P")),
        CompiledEffect("move", from_ref=CompiledSquareRef("source"),
                       to_ref=CompiledSquareRef("target")),
    )
    pattern = replace(binding.pattern, effects=effects)
    binding = replace(binding, pattern=pattern)
    return engine, parent, action, binding


def test_capture_promoted_base_then_consume_in_same_transition():
    engine, parent, action, binding = ordered_capture()
    child = engine._transition(parent, action, binding)
    assert child.hands == parent.hands == (Hands(), Hands())
    assert child.board[action.source] is None
    assert child.board[action.target] == parent.board[action.source]
    assert parent.board[action.target] == Piece(1, "P", "Q", promoted=True)
    bad = replace(binding, pattern=replace(binding.pattern, effects=binding.pattern.effects[1:]))
    with pytest.raises(RuntimeError, match="insufficient hand"):
        engine._transition(parent, action, bad)
    assert engine._transition(parent, action, binding) == child


@pytest.mark.parametrize("tracked", [False, True])
def test_cancel_after_hand_capture_preserves_fault_and_sibling(monkeypatch, tracked):
    engine, parent, action, binding = ordered_capture()
    expected = engine._transition(parent, action, binding)
    captured = False
    original = sem._apply_effect
    fault = RuntimeError("caller after actual hand capture")

    def observe(effect, *args):
        nonlocal captured
        original(effect, *args)
        if effect.kind == "remove":
            captured = True

    def checkpoint():
        if captured:
            raise fault

    monkeypatch.setattr(sem, "_apply_effect", observe)
    with pytest.raises(RuntimeError) as caught:
        engine._trial_child_if_s3_legal(binding.pattern, parent, action, binding,
            checkpoint=checkpoint, safety=(sem._OwnAnchorSafety(parent, 0, sem._own_anchor(parent, engine.support, 0),
                frozenset(range(len(parent.board))), False) if tracked else None))
    assert caught.value is fault
    assert parent.hands == (Hands(), Hands())
    assert parent.board[action.target] == Piece(1, "P", "Q", promoted=True)
    monkeypatch.setattr(sem, "_apply_effect", original)
    assert engine._transition(parent, action, binding) == expected


@pytest.mark.parametrize("counts", [None, 0, False])
def test_invalid_falsy_hand_retains_original_constructor_failure(counts):
    engine, parent, _, _ = quiet()
    parent = replace(parent, hands=(Hands(counts), Hands()))
    with pytest.raises(TypeError):
        sem._WorkingPosition(parent, engine.support)
