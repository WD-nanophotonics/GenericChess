"""A caller's checkpoint failure must not become an illegal candidate."""

import pytest

from generic_chess import build_builtin_ruleset, compile_ruleset_for_execution
from generic_chess.core.semantic_executor import semantic_engine_for
from generic_chess.core.transition import initial_state


@pytest.mark.parametrize("game", ("western_chess", "standard_shogi"))
def test_s3_trial_preserves_checkpoint_runtime_error(game):
    compiled = compile_ruleset_for_execution(build_builtin_ruleset(game))
    engine = semantic_engine_for(compiled)
    position = initial_state(compiled).position
    action, binding = next(engine.iter_legal_action_bindings(position))
    pattern = next(p for p in engine._patterns if p.pattern_id == action.pattern_id)
    fault = RuntimeError("caller checkpoint failure")

    def checkpoint():
        raise fault

    with pytest.raises(RuntimeError) as caught:
        engine._trial_child_if_s3_legal(pattern, position, action, binding,
                                      checkpoint=checkpoint)
    assert caught.value is fault
    assert engine._trial_child_if_s3_legal(pattern, position, action, binding) is not None


def test_s3_transition_failure_still_rejects_candidate(monkeypatch):
    compiled = compile_ruleset_for_execution(build_builtin_ruleset("western_chess"))
    engine = semantic_engine_for(compiled)
    position = initial_state(compiled).position
    action, binding = next(engine.iter_legal_action_bindings(position))
    pattern = next(p for p in engine._patterns if p.pattern_id == action.pattern_id)

    def invalid(*_args, **_kwargs):
        raise RuntimeError("unexecutable effect")

    monkeypatch.setattr(engine, "_transition", invalid)
    assert engine._trial_child_if_s3_legal(pattern, position, action, binding) is None
    assert engine._trial_child_if_s3_legal(pattern, position, action, binding,
                                         checkpoint=lambda: None) is None
