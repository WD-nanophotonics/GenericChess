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


@pytest.mark.parametrize("nested", [False, True])
@pytest.mark.parametrize("collision", [False, True])
def test_opaque_bridge_target_constructor_failure_preserves_original_state(
        monkeypatch, nested, collision):
    import inspect
    from dataclasses import fields
    from generic_chess.core import search_runtime as module
    from test_native_history import _cycle_ruleset, _session_at_ply

    compiled = _cycle_ruleset()
    session = _session_at_ply(compiled, 2 if nested else 3)
    public = session.state
    runtime = SearchPathRuntime.from_state(
        replace(public, history=()), compiled,
        hash_override=RuntimeHash(0, 0) if collision else None,
    )
    if nested:
        outer = runtime.legal_actions()[0]
        runtime.push(outer)
        public = dict(legal_successors(public, compiled))[outer]
    action = runtime.legal_actions()[0]
    expected = dict(legal_successors(public, compiled))[action]
    target = module._runtime_position_identity(expected.position, compiled)
    assert position_identity_key(expected.position, compiled) in runtime._opaque_imported_keys

    def actual_state():
        frames = tuple(tuple((field.name, tuple(getattr(frame, field.name).items())
                              if field.name == "bindings" else getattr(frame, field.name))
                             for field in fields(frame)) for frame in runtime._frames)
        return (occurrences(runtime), tuple(runtime._history), runtime.position,
                runtime.ply_count, runtime.terminal_status, runtime._identity,
                runtime.runtime_hash, runtime._snapshot, runtime._history_context,
                runtime._legal_cache, dict(runtime._bindings), frames,
                frozenset(runtime._opaque_imported_keys), dict(runtime._history_aliases))

    before = actual_state()
    original = module._Occurrence
    fault = MemoryError("one opaque target allocation")
    hits = 0

    def allocate(identity, count):
        nonlocal hits
        # Bind the fault to the migration constructor, not ordinary child add.
        caller = inspect.currentframe().f_back.f_code.co_name
        if caller == "_resolve_opaque_history_key" and identity == target:
            hits += 1
            if hits == 1:
                raise fault
        return original(identity, count)

    with monkeypatch.context() as patch:
        patch.setattr(module, "_Occurrence", allocate)
        with pytest.raises(MemoryError, match="one opaque target allocation") as caught:
            runtime.push(action)
    assert caught.value is fault
    assert hits == 1
    assert actual_state() == before
    # A preserved outer frame is intentionally live in the nested control.
    assert len(runtime._frames) == int(nested)
    assert runtime.pushes - runtime.pops == int(nested)
    with runtime.pushed(action):
        assert runtime.position == expected.position
        assert runtime.terminal_status == expected.terminal_status
        assert runtime.occurrence_count() == 2
    assert actual_state() == before
    if nested:
        runtime.pop()
    runtime.assert_balanced()


@pytest.mark.parametrize("inject", [False, True])
def test_opaque_bridge_comparison_is_completed_before_mutation(monkeypatch, inject):
    import sys
    from generic_chess.core import search_runtime as module
    from test_native_history import _cycle_ruleset, _session_at_ply

    compiled = _cycle_ruleset()
    public = _session_at_ply(compiled, 3).state
    action = next(iter(dict(legal_successors(public, compiled))))
    expected = dict(legal_successors(public, compiled))[action]
    key = position_identity_key(expected.position, compiled)
    reordered = tuple((k, n) for k, n in public.repetition_counts if k != key)
    reordered += tuple((k, n) for k, n in public.repetition_counts if k == key)
    assert dict(reordered) == dict(public.repetition_counts)
    runtime = SearchPathRuntime.from_state(
        replace(public, history=(), repetition_counts=reordered), compiled,
        hash_override=RuntimeHash(0, 0),
    )
    runtime.legal_actions()
    before = (occurrences(runtime), runtime.search_key(), tuple(runtime.history),
              frozenset(runtime._opaque_imported_keys), dict(runtime._history_aliases))
    original = module._Occurrence.__eq__
    fault = MemoryError("one old occurrence comparison allocation")
    reached = hits = 0

    def compare(self, other):
        nonlocal reached, hits
        if (sys._getframe(1).f_code.co_name == "_resolve_opaque_history_key"
                and self is not other and isinstance(other.identity, module._ImportedIdentity)
                and other.identity.external_key == key):
            reached += 1
            if inject and hits == 0:
                hits += 1
                raise fault
        return original(self, other)

    with monkeypatch.context() as patch:
        patch.setattr(module._Occurrence, "__eq__", compare)
        if inject:
            with pytest.raises(MemoryError) as caught:
                runtime.push(action)
            assert caught.value is fault and hits == 1
        else:
            with runtime.pushed(action):
                assert runtime.position == expected.position
                assert runtime.occurrence_count() == 2
    assert reached > 0
    assert (occurrences(runtime), runtime.search_key(), tuple(runtime.history),
            frozenset(runtime._opaque_imported_keys), dict(runtime._history_aliases)) == before
    rebuilt = runtime._snapshot_from_occurrences()
    assert rebuilt.items() == runtime._snapshot.items()
    assert rebuilt.digest == runtime._snapshot.digest
    with runtime.pushed(action):
        assert runtime.position == expected.position
        assert runtime.terminal_status == expected.terminal_status
        assert runtime.occurrence_count() == 2
    assert occurrences(runtime) == before[0]
    runtime.assert_balanced()
