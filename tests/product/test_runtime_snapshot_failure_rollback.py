"""A pre-history snapshot failure must not leak a repetition occurrence."""
import pytest
from dataclasses import replace

from generic_chess import build_builtin_ruleset, compile_ruleset_for_execution
from generic_chess.core.identity import RuntimeHash, position_identity_key
from generic_chess.core.search_runtime import RuntimeCountsSnapshot, SearchPathRuntime
from generic_chess.core.transition import legal_successors
from generic_chess.session.session import GameSession


def occurrences(runtime):
    # Inspect the actual mutable table, not the restored persistent snapshot or
    # the root-only compatibility projection, which can conceal a leaked child.
    # A bridge can move an opaque entry within a collision bucket. Compare all
    # entries/counts including multiplicity, independently of list order.
    return {key: tuple(sorted(((entry.identity, entry.count) for entry in bucket),
                            key=lambda value: repr(value[0])))
            for key, bucket in runtime._occurrences.items()}


@pytest.mark.parametrize("game", ["western_chess", "standard_shogi"])
@pytest.mark.parametrize("collision", [False, True])
def test_snapshot_failure_rolls_back_child_before_history_append(monkeypatch, game, collision):
    compiled = compile_ruleset_for_execution(build_builtin_ruleset(game))
    session = GameSession(compiled)
    # Include a complete public history; both the history and occurrence table
    # must survive repeated failures before any new history record is appended.
    session.submit(session.legal_actions()[0])
    root = session.state
    runtime = SearchPathRuntime.from_state(
        root, compiled, history_witnesses=session._search_witnesses,
        hash_override=RuntimeHash(1, 1) if collision else None,
    )
    action = runtime.legal_actions()[0]
    expected = dict(legal_successors(root, compiled))[action]
    before = occurrences(runtime)
    before_key = runtime.search_key()
    before_history = tuple(runtime._history)
    original = RuntimeCountsSnapshot.updated

    def fail(*args, **kwargs):
        raise RuntimeError("injected snapshot allocation failure")

    monkeypatch.setattr(RuntimeCountsSnapshot, "updated", fail)
    for _ in range(2):
        with pytest.raises(RuntimeError, match="snapshot allocation failure"):
            runtime.push(action)
        assert occurrences(runtime) == before
        assert tuple(runtime._history) == before_history
        assert runtime.position is root.position
        assert runtime.search_key() == before_key
        runtime.assert_balanced()

    monkeypatch.setattr(RuntimeCountsSnapshot, "updated", original)
    with runtime.pushed(action):
        assert runtime.position == expected.position
        assert runtime.terminal_status == expected.terminal_status
        assert runtime.occurrence_count() == dict(expected.repetition_counts)[
            position_identity_key(expected.position, compiled)]
    assert occurrences(runtime) == before
    runtime.assert_balanced()


@pytest.mark.parametrize("opaque", [False, True])
@pytest.mark.parametrize("collision", [False, True])
@pytest.mark.parametrize("failure_stage", ["snapshot", "terminal"])
def test_failure_preserves_existing_child_count_without_double_decrement(
        monkeypatch, opaque, collision, failure_stage):
    from test_native_history import _cycle_ruleset, _session_at_ply

    compiled = _cycle_ruleset()
    session = _session_at_ply(compiled, 3)
    root = replace(session.state, history=()) if opaque else session.state
    runtime = SearchPathRuntime.from_state(
        root, compiled,
        history_witnesses=None if opaque else session._search_witnesses,
        hash_override=RuntimeHash(0, 0) if collision else None,
    )
    action = runtime.legal_actions()[0]
    expected = dict(legal_successors(root, compiled))[action]
    child_key = position_identity_key(expected.position, compiled)
    assert dict(root.repetition_counts)[child_key] == 1
    before = (occurrences(runtime), tuple(runtime._history), runtime._snapshot,
              frozenset(runtime._opaque_imported_keys), dict(runtime._history_aliases))

    def fail(*args, **kwargs):
        raise MemoryError("injected child count boundary")

    with monkeypatch.context() as patch:
        if failure_stage == "snapshot":
            patch.setattr(RuntimeCountsSnapshot, "updated", fail)
        else:
            patch.setattr("generic_chess.core.search_runtime.terminal_from_search_runtime", fail)
        with pytest.raises(MemoryError, match="child count boundary"):
            runtime.push(action)
    after = (occurrences(runtime), tuple(runtime._history), runtime._snapshot,
             frozenset(runtime._opaque_imported_keys), dict(runtime._history_aliases))
    assert after == before
    assert runtime.position is root.position
    runtime.assert_balanced()
    with runtime.pushed(action):
        assert runtime.occurrence_count() == 2
        assert runtime.terminal_status == expected.terminal_status
    assert occurrences(runtime) == before[0]
    assert runtime._snapshot == before[2]
    assert frozenset(runtime._opaque_imported_keys) == before[3]
    assert runtime._history_aliases == before[4]
    runtime.assert_balanced()
