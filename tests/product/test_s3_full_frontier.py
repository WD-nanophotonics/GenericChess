"""Full-frontier S3 observations retain complete rules and transaction/error boundaries."""
from dataclasses import replace
import json
from pathlib import Path
import types

import pytest
from generic_chess.core import semantic_executor as se
from generic_chess.core.errors import RuleSetMismatchError
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.serialization import deserialize_ruleset
from generic_chess.session.session import GameSession
from test_compiled_endpoint_fallback import DEFINITIONS

def engine_position(definition):
    compiled = compile_ruleset_for_execution(definition)
    return se.SemanticEngine(compiled), GameSession(compiled).state.position

@pytest.mark.parametrize("definition", DEFINITIONS)
def test_full_frontier_exact_order_child_and_complete_write_coverage(definition):
    compiled = compile_ruleset_for_execution(definition)
    session = GameSession(compiled)
    engine = se.SemanticEngine(compiled)
    for _ in range(4):
        position = session.state.position
        original = tuple(engine.iter_legal_action_bindings(position))
        optimized = tuple(engine.iter_legal_action_bindings(position, full_frontier=True))
        assert optimized == original
        for action, binding in original:
            written = set()
            child = engine._transition(position, action, binding, written_squares=written)
            assert child == engine._transition(position, action, binding)
            assert {i for i, (old, new) in enumerate(zip(position.board, child.board))
                    if old != new} <= written
        if not original or session.state.terminal_status.is_terminal:
            break
        session.submit(sorted(session.legal_actions(), key=repr)[0])

def counter(name):
    path = Path(__file__).parent / "fixtures" / ("s3_" + name + ".json")
    return engine_position(deserialize_ruleset(path.read_text(encoding="utf-8")))

@pytest.mark.parametrize("name", ["guard", "enemy_retype", "other_invariant"])
def test_real_complete_dsl_counterexamples_reject_unsafe_candidate(name, monkeypatch):
    engine, position = counter(name)
    original = tuple(engine.iter_legal_action_bindings(position))
    calls = []
    old = engine.in_check
    def check(pos, side, checkpoint=None):
        calls.append(pos)
        return old(pos, side, checkpoint=checkpoint)
    monkeypatch.setattr(engine, "in_check", check)
    optimized = tuple(engine.iter_legal_action_bindings(position, full_frontier=True))
    assert optimized == original
    assert all(action.actor_type != "B" for action, binding in optimized)
    if name == "guard":
        assert not engine._capture_reads_local_board()
        assert position not in calls
    if name == "enemy_retype":
        assert position in calls and any(p != position for p in calls)
    if name == "other_invariant":
        ctx = engine._own_anchor_safety(position, se._sources_by_owner_type(position), None)
        witness = next((a, b) for p in engine._patterns for a, b in engine._iter_candidates(p, position)
                       if a.source == 7 and a.target == 6)
        written = set()
        child = engine._transition(position, *witness, written_squares=written)
        assert ctx.unchanged(child, written, engine.support) and not ctx.checked
        assert engine.is_square_attacked(child, 3, 1)
        assert engine._trial_child_if_s3_legal(witness[1].pattern, position, *witness, safety=ctx) is None

def test_existence_and_filtered_calls_never_prepare(monkeypatch):
    engine, position = engine_position(DEFINITIONS[0])
    def forbidden(*args):
        raise AssertionError("existence prepared full frontier")
    monkeypatch.setattr(engine, "_own_anchor_safety", forbidden)
    assert engine.has_legal_action(position)
    assert tuple(engine.iter_legal_action_bindings(position, source=0, full_frontier=True)) == ()

def test_entry_validation_precedes_optional_observation(monkeypatch):
    engine, position = engine_position(DEFINITIONS[0])
    def forbidden(*args):
        raise AssertionError("preparation ran before entry validation")
    monkeypatch.setattr(engine, "_own_anchor_safety", forbidden)
    with pytest.raises(RuleSetMismatchError):
        tuple(engine.iter_legal_action_bindings(replace(position, ruleset_fingerprint="wrong"), full_frontier=True))
    for square in [-1, True, len(position.board)]:
        with pytest.raises(ValueError):
            tuple(engine.iter_legal_action_bindings(position, target=square, full_frontier=True))

@pytest.mark.parametrize("at", [1, 4, 16, 64, 256])
def test_full_frontier_cancel_recovery(at):
    engine, position = engine_position(DEFINITIONS[0])
    expected = tuple(engine.iter_legal_action_bindings(position))
    calls = 0
    def stop():
        nonlocal calls
        calls += 1
        if calls >= at:
            raise RuntimeError("caller cancel")
    with pytest.raises(RuntimeError, match="caller cancel"):
        tuple(engine.iter_legal_action_bindings(position, stop, full_frontier=True))
    assert tuple(engine.iter_legal_action_bindings(position, full_frontier=True)) == expected
    assert engine._postcondition_parent is None if hasattr(engine, "_postcondition_parent") else True

def test_optional_parent_error_declines_but_required_candidate_error_propagates(monkeypatch):
    engine, position = counter("other_invariant")
    def bad(*args, **kwargs):
        raise RuntimeError("binding fault")
    monkeypatch.setattr(engine, "_make_binding", bad)
    monkeypatch.setattr(engine, "_iter_candidates", types.MethodType(lambda self, *a, **kw: iter(()), engine))
    assert tuple(engine.iter_legal_action_bindings(position, full_frontier=True)) == ()
    monkeypatch.setattr(engine, "_iter_candidates", types.MethodType(se.SemanticEngine._iter_candidates, engine))
    with pytest.raises(RuntimeError, match="binding fault"):
        tuple(engine.iter_legal_action_bindings(position, full_frontier=True))

def test_interleaved_iterators_close_without_engine_parent_retention():
    compiled = compile_ruleset_for_execution(DEFINITIONS[0])
    session = GameSession(compiled)
    parent = session.state.position
    session.submit(sorted(session.legal_actions(), key=repr)[0])
    other = session.state.position
    engine = se.SemanticEngine(compiled)
    expected = tuple(engine.iter_legal_action_bindings(parent))
    expected_other = tuple(engine.iter_legal_action_bindings(other))
    a = engine.iter_legal_action_bindings(parent, full_frontier=True)
    b = engine.iter_legal_action_bindings(other, full_frontier=True)
    assert next(a) == expected[0] and next(b) == expected_other[0]
    assert not any(isinstance(v, (se._OwnAnchorSafety, type(parent))) for v in vars(engine).values())
    a.close()
    assert tuple(b) == expected_other[1:]
    assert tuple(engine.iter_legal_action_bindings(parent, full_frontier=True)) == expected

def test_required_child_check_error_not_declined(monkeypatch):
    engine, position = counter("enemy_retype")
    original = engine.in_check
    def fail_child(pos, side, checkpoint=None):
        if pos is not position:
            raise RuntimeError("required child check")
        return original(pos, side, checkpoint=checkpoint)
    monkeypatch.setattr(engine, "in_check", fail_child)
    with pytest.raises(RuntimeError, match="required child check"):
        tuple(engine.iter_legal_action_bindings(position, full_frontier=True))

def test_caller_runtimeerror_inside_optional_parent_observation_not_swallowed(monkeypatch):
    engine, position = counter("other_invariant")
    inside = False
    def observed(pos, side, checkpoint=None):
        nonlocal inside
        inside = True
        checkpoint()
    def stop():
        if inside:
            raise RuntimeError("caller within optional observation")
    monkeypatch.setattr(engine, "in_check", observed)
    with pytest.raises(RuntimeError, match="caller within optional"):
        tuple(engine.iter_legal_action_bindings(position, stop, full_frontier=True))
