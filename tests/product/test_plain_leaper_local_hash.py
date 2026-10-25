"""Certified footprints must equal the full component oracle and Core history."""
from dataclasses import replace

import pytest

from scripts import leaper_design as L
from generic_chess.core import search_runtime as R
from generic_chess.core.identity import RuntimeHash
from generic_chess.core.movement import RayAtom
from generic_chess.core.pieces import Piece
from generic_chess.core.semantic_executor import semantic_engine_for
from generic_chess.core.coordinates import Square
from generic_chess.session.session import GameSession


def runtime(session, enabled=True, **kwargs):
    return R.SearchPathRuntime.from_state(session.state, session.compiled,
        history_witnesses=session._search_witnesses,
        use_plain_leaper_local_hash=enabled, **kwargs)


@pytest.mark.parametrize('cached', [False, True])
@pytest.mark.parametrize('masks', [(1, 2), (5, 9), (17, 31)])
def test_exact_hash_history_and_undo_across_real_core_transitions(masks, cached):
    c = L.compile_rule(L.definition(*masks))
    s = GameSession(c)
    fast, base = runtime(s, use_cached_position_identity_hash=cached), runtime(s, False)
    roots = (fast.runtime_hash, fast.search_key())
    saved = [s.state]
    branches = 0
    for step in range(12):
        assert fast.legal_actions() == base.legal_actions() == s.legal_actions()
        actions = s.legal_actions()
        if not actions:
            break
        for a in actions:
            before = fast.runtime_hash, fast.search_key()
            with fast.pushed(a), base.pushed(a):
                branches += 1
                assert fast.runtime_hash == base.runtime_hash == R._full_runtime_hash(fast.position, c)
                assert fast.position == base.position
                assert fast.search_key() == base.search_key()
                assert fast.terminal_status == base.terminal_status
                assert fast.occurrence_count() == base.occurrence_count()
            assert (fast.runtime_hash, fast.search_key()) == before
        chosen = actions[(7 * step) % len(actions)]
        s.submit(chosen)
        fast.push(chosen)
        base.push(chosen)
        saved.append(s.state)
        assert fast.position == s.state.position
        assert fast.terminal_status == s.state.terminal_status
        if s.state.terminal_status.is_terminal:
            break
    assert branches > 0 and fast.semantic_local_hash_updates > 0
    assert fast.semantic_full_diff_fallbacks == 0
    assert base.semantic_local_hash_updates == 0
    for expected in reversed(saved[:-1]):
        fast.pop()
        base.pop()
        assert fast.position == expected.position
        assert fast.terminal_status == expected.terminal_status
        assert fast.runtime_hash == R._full_runtime_hash(fast.position, c)
        assert fast.search_key() == base.search_key()
    assert (fast.runtime_hash, fast.search_key()) == roots
    fast.assert_balanced()


def test_capture_footprint_matches_existing_transition_write_tracker():
    rule = L.definition(1, 2)
    board = [None] * 16
    for i, owner, tid in [(0, 0, 'K'), (15, 1, 'K'), (5, 0, 'A'), (6, 1, 'A')]:
        board[i] = Piece(owner, tid, tid)
    rule = replace(rule, initial_position=tuple(tuple(board[i:i+4]) for i in range(0, 16, 4)))
    c = L.compile_rule(rule)
    s = GameSession(c)
    r = runtime(s)
    a = next(a for a in r.legal_actions()
             if a.from_square == Square(1, 1) and a.to_square == Square(2, 1))
    semantic, binding = r._bindings[a]
    writes = set()
    child = semantic_engine_for(c)._transition(r.position, semantic, binding, written_squares=writes)
    assert writes == {5, 6}
    with r.pushed(a):
        assert r.position == child
        assert r.runtime_hash == R._full_runtime_hash(child, c)
        assert sum(p is not None for p in child.board) == 3


def test_exact_repetition_draw_keeps_full_history():
    rule = L.definition(1, 2)
    board = [None] * 16
    board[0], board[15] = Piece(0, 'K', 'K'), Piece(1, 'K', 'K')
    rule = replace(rule, piece_types=(rule.piece_types[0],), drop_allowed={},
        initial_position=tuple(tuple(board[i:i+4]) for i in range(0, 16, 4)))
    c = L.compile_rule(rule)
    s = GameSession(c)
    r = runtime(s)
    cycle = [(0, 1), (15, 14), (1, 0), (14, 15)]
    for turn in range(12):
        source, target = cycle[turn % 4]
        a = next(a for a in s.legal_actions() if
            a.from_square == Square(source % 4, source // 4)
            and a.to_square == Square(target % 4, target // 4))
        s.submit(a)
        r.push(a)
        assert r.position == s.state.position
        assert r.runtime_hash == R._full_runtime_hash(r.position, c)
        assert r.terminal_status == s.state.terminal_status
    assert s.state.terminal_status.is_terminal
    assert r.occurrence_count() == 4
    assert r.semantic_local_hash_updates == 12
    for _ in range(12):
        r.pop()
    r.assert_balanced()


def test_actual_ray_and_enabled_drop_rules_keep_full_fallback():
    rule = L.definition(1, 2)
    ray = replace(rule, piece_types=rule.piece_types[:2] +
        (replace(rule.piece_types[2], movement_atoms=(RayAtom((1, 0)),)),))
    drops = replace(rule, drop_allowed={**rule.drop_allowed, 'A': ((True,) * 16,) * 2})
    for candidate in (ray, drops):
        c = L.compile_rule(candidate)
        assert R._plain_leaper_hash_patterns(c) is None
        r = runtime(GameSession(c))
        with r.pushed(r.legal_actions()[0]):
            assert r.runtime_hash == R._full_runtime_hash(r.position, c)
        assert r.semantic_local_hash_updates == 0
        assert r.semantic_full_diff_fallbacks == 1


@pytest.mark.parametrize('kind', ['effect', 'trigger', 'slot', 'promotion'])
def test_unknown_or_nonlocal_ir_options_fail_closed(kind):
    c = L.compile_rule(L.definition(1, 2))
    ir = c.ir
    if kind == 'effect':
        p = ir.patterns[0]
        ir = replace(ir, patterns=(replace(p, effects=p.effects + p.effects),) + ir.patterns[1:])
    elif kind == 'trigger':
        ir = replace(ir, triggers=(object(),))
    elif kind == 'slot':
        ir = replace(ir, aux_slots=(object(),))
    else:
        ir = replace(ir, patterns=(replace(ir.patterns[0], explicit_promotion_type='A'),) + ir.patterns[1:])
    class Changed:
        def __getattr__(self, name):
            return ir if name == 'ir' else getattr(c, name)
    assert R._plain_leaper_hash_patterns(Changed()) is None


def test_foreign_aux_data_does_not_use_local_hash():
    c = L.compile_rule(L.definition(1, 2))
    s = GameSession(c)
    r = runtime(s)
    a = r.legal_actions()[0]
    parent = replace(r.position, aux_state=(((99, -1), True),))
    child = replace(r.position, aux_state=(((99, -1), 1),))
    assert R._plain_leaper_local_hash(parent, child, a, c, r.runtime_hash,
        r._plain_leaper_hash_patterns) is None


def test_forced_collisions_and_failure_rollback_keep_original_guards(monkeypatch):
    c = L.compile_rule(L.definition(1, 2))
    s = GameSession(c)
    r = runtime(s, hash_override=RuntimeHash(1, 1))
    with r.pushed(r.legal_actions()[0]):
        assert r.runtime_hash == RuntimeHash(1, 1)
    assert r.semantic_local_hash_updates == 0
    r = runtime(s)
    before = r.runtime_hash, r.search_key(), tuple(r.history)
    def fail(*args, **kwargs):
        raise RuntimeError('post-hash snapshot failure')
    monkeypatch.setattr(R.RuntimeCountsSnapshot, 'updated', fail)
    with pytest.raises(RuntimeError, match='post-hash snapshot failure'):
        r.push(r.legal_actions()[0])
    assert (r.runtime_hash, r.search_key(), tuple(r.history)) == before
    r.assert_balanced()


@pytest.mark.parametrize('cached', [False, True])
@pytest.mark.parametrize('native', [False, True])
@pytest.mark.parametrize('tt', [False, True])
def test_actual_player_and_retained_tt_keep_exact_decisions(native, tt, cached):
    from generic_chess.ai.alphabeta.player import AlphaBetaPlayer
    from generic_chess.ai.alphabeta.tuning import SearchTuning
    from generic_chess.ai.limits import SearchLimits
    c = L.compile_rule(L.definition(5, 9))
    s = GameSession(c)
    for step in range(4):
        s.submit(s.legal_actions()[step % len(s.legal_actions())])
    before = s.state, s.to_record(), s._search_witnesses
    players = [AlphaBetaPlayer(c, use_disk_cache=False, use_tt=tt,
        use_native_semantic_legality=native,
        use_native_semantic_availability=native, use_native_semantic_check=native,
        tuning=SearchTuning(use_pvs=True, use_plain_leaper_local_hash=enabled,
            use_cached_position_identity_hash=cached and enabled))
        for enabled in (False, True)]
    # Repeat on each retained player to exercise warm exact-history TT reuse.
    for _ in range(2):
        decisions = [p.choose_action(s, SearchLimits(max_depth=3,
            max_nodes=20000, max_time_seconds=5)) for p in players]
        a, b = decisions
        for name in ('action', 'score', 'principal_variation', 'nodes', 'qnodes',
                     'completed_depth', 'termination_reason', 'tt_hits', 'tt_cutoffs'):
            assert getattr(a, name) == getattr(b, name), name
        assert a.completed_depth == 3
        assert a.runtime_semantic_local_hash_updates == 0
        assert b.runtime_semantic_local_hash_updates > 0
        assert b.runtime_semantic_full_diff_fallbacks == 0
        for d in decisions:
            assert d.runtime_pushes == d.runtime_pops
            assert d.runtime_depth_balanced
        assert (s.state, s.to_record(), s._search_witnesses) == before


def test_cancel_after_actual_local_hash_update_rolls_back(monkeypatch):
    from generic_chess.ai.alphabeta.player import AlphaBetaPlayer
    from generic_chess.ai.alphabeta.tuning import SearchTuning
    from generic_chess.ai.cancellation import CancellationToken
    from generic_chess.ai.limits import SearchLimits
    c = L.compile_rule(L.definition(1, 2))
    s = GameSession(c)
    token = CancellationToken()
    original = R.SearchPathRuntime.push
    def push(self, *args, **kwargs):
        result = original(self, *args, **kwargs)
        token.cancel()
        return result
    monkeypatch.setattr(R.SearchPathRuntime, 'push', push)
    p = AlphaBetaPlayer(c, use_disk_cache=False,
        tuning=SearchTuning(use_plain_leaper_local_hash=True))
    before = s.state, s.to_record(), s._search_witnesses
    d = p.choose_action(s, SearchLimits(max_depth=5, max_nodes=20000,
        max_time_seconds=5), cancel_token=token)
    assert d.termination_reason == 'cancelled'
    assert d.runtime_semantic_local_hash_updates == 1
    assert d.runtime_pushes == d.runtime_pops == 1
    assert (s.state, s.to_record(), s._search_witnesses) == before


def test_rectangular_carrier_and_mismatched_shape_decline():
    c = L.compile_rule(L.definition(1, 2))
    class Rectangular:
        board_size = None
        def __getattr__(self, name):
            return getattr(c, name)
    assert R._plain_leaper_hash_patterns(Rectangular()) is None
    r = runtime(GameSession(c))
    a = r.legal_actions()[0]
    rectangular = replace(r.position, board_width=8, board_height=2)
    assert R._plain_leaper_local_hash(rectangular, rectangular, a, c,
        r.runtime_hash, r._plain_leaper_hash_patterns) is None



@pytest.mark.parametrize('cached', [False, True])
def test_real_local_hash_component_collisions_keep_exact_history_keys(monkeypatch, cached):
    # Unlike hash_override, this actually executes the certified local updater.
    monkeypatch.setattr(R, '_component_token', lambda *args: RuntimeHash(7, 7))
    c = L.compile_rule(L.definition(1, 2))
    r = runtime(GameSession(c), use_cached_position_identity_hash=cached)
    actions = r.legal_actions()
    keys = []
    hashes = []
    for a in actions[:2]:
        with r.pushed(a):
            hashes.append(r.runtime_hash)
            keys.append(r.search_key())
            assert r.runtime_hash == R._full_runtime_hash(r.position, c)
    assert r.semantic_local_hash_updates == 2
    assert hashes[0] == hashes[1]
    assert keys[0].position_key != keys[1].position_key
    assert keys[0].repetition != keys[1].repetition
    assert keys[0] != keys[1]
    r.assert_balanced()


def test_flag_changes_can_reuse_existing_exact_tt():
    from generic_chess.ai.alphabeta.player import AlphaBetaPlayer
    from generic_chess.ai.alphabeta.tuning import SearchTuning
    from generic_chess.ai.limits import SearchLimits
    c = L.compile_rule(L.definition(5, 9))
    s = GameSession(c)
    players = [AlphaBetaPlayer(c, use_disk_cache=False,
        tuning=SearchTuning(use_pvs=True)) for _ in range(2)]
    limits = SearchLimits(max_depth=3, max_nodes=20000, max_time_seconds=5)
    for enabled, cached in ((False, False), (True, False),
                            (False, True), (True, True), (False, False)):
        players[1]._tuning = replace(players[1]._tuning,
            use_plain_leaper_local_hash=enabled,
            use_cached_position_identity_hash=cached)
        a, b = [p.choose_action(s, limits) for p in players]
        for field in ('action', 'score', 'principal_variation', 'nodes', 'qnodes',
                      'tt_hits', 'tt_cutoffs', 'completed_depth', 'termination_reason'):
            assert getattr(a, field) == getattr(b, field), field
        assert b.runtime_pushes == b.runtime_pops



def test_cached_identity_is_lazy_and_dict_interoperable_with_exact_base():
    c = L.compile_rule(L.definition(1, 2))
    s = GameSession(c)
    a = R.RuntimePositionIdentity(s.state.position)
    b = R._CachedRuntimePositionIdentity(s.state.position)
    assert b._cached_hash is None
    assert a == b and b == a
    assert hash(a) == hash(b) == hash(b)
    assert b._cached_hash == hash(s.state.position)
    assert {a: 'same'}[b] == {b: 'same'}[a]
    foreign = replace(s.state.position, aux_state=(((99, -1), True),))
    other = replace(foreign, aux_state=(((99, -1), 1),))
    assert R._CachedRuntimePositionIdentity(foreign) != R.RuntimePositionIdentity(other)


def test_cached_only_keeps_component_hash_path_and_declines_mixed_rules():
    c = L.compile_rule(L.definition(1, 2))
    r = runtime(GameSession(c), False, use_cached_position_identity_hash=True)
    assert isinstance(r.current_identity, R._CachedRuntimePositionIdentity)
    with r.pushed(r.legal_actions()[0]):
        assert isinstance(r.current_identity, R._CachedRuntimePositionIdentity)
        assert r.runtime_hash == R._full_runtime_hash(r.position, c)
    assert r.semantic_local_hash_updates == 0
    assert r.semantic_full_diff_fallbacks == 1
    rule = L.definition(1, 2)
    mixed = replace(rule, piece_types=rule.piece_types[:2] +
        (replace(rule.piece_types[2], movement_atoms=(RayAtom((1, 0)),)),))
    c = L.compile_rule(mixed)
    r = runtime(GameSession(c), use_cached_position_identity_hash=True)
    assert type(r.current_identity) is R.RuntimePositionIdentity
    assert not r._cache_position_identity_hash



def test_cached_zero_python_hash_and_component_collisions_keep_exact_keys(monkeypatch):
    monkeypatch.setattr(R.Position, '__hash__', lambda self: 0)
    monkeypatch.setattr(R, '_component_token', lambda *args: RuntimeHash(0, 0))
    c = L.compile_rule(L.definition(1, 2))
    r = runtime(GameSession(c), use_cached_position_identity_hash=True)
    keys = []
    for a in r.legal_actions()[:2]:
        with r.pushed(a):
            assert hash(r.current_identity) == hash(r.current_identity) == 0
            assert r.current_identity._cached_hash == 0
            keys.append(r.search_key())
    assert keys[0].runtime_hash == keys[1].runtime_hash
    assert hash(keys[0].position_key) == hash(keys[1].position_key) == 0
    assert keys[0] != keys[1]
    assert len({keys[0]: 'first', keys[1]: 'second'}) == 2
    r.assert_balanced()
