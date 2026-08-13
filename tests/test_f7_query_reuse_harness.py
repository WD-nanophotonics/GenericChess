"""H7A tests for exact query identity and bounded probe isolation."""

from dataclasses import replace

from generic_chess.core.position import Hands, Position
from scripts.audit_f7_attack_query_reuse import (
    BoundedExactAttackCache,
    exact_query_key,
)


def _position(aux_state=(), side=0):
    return Position(
        board=(None, None, None, None),
        hands=(Hands.empty(), Hands.empty()),
        side_to_move=side,
        ruleset_fingerprint="fp",
        aux_state=aux_state,
    )


def test_f7_exact_query_identity_includes_all_position_semantics():
    left = _position(aux_state=(((1, -1), 0),))
    equal_copy = replace(left)
    different_aux = _position(aux_state=(((1, -1), 1),))
    different_side = _position(side=1, aux_state=(((1, -1), 0),))
    assert exact_query_key(left, 2, 1) == exact_query_key(equal_copy, 2, 1)
    assert exact_query_key(left, 2, 1) != exact_query_key(different_aux, 2, 1)
    assert exact_query_key(left, 2, 1) != exact_query_key(different_side, 2, 1)
    assert exact_query_key(left, 2, 1) != exact_query_key(left, 3, 1)
    assert exact_query_key(left, 2, 1) != exact_query_key(left, 2, 0)


def test_f7_bounded_cache_requires_exact_key_and_observes_checkpoint_on_hit():
    cache = BoundedExactAttackCache(max_entries=2)
    position = _position()
    checks = []
    calls = []

    def compute():
        calls.append(1)
        return True

    checkpoint = lambda: checks.append(None)
    assert cache.get_or_compute(position, 0, 1, compute, checkpoint)
    assert cache.get_or_compute(replace(position), 0, 1, compute, checkpoint)
    assert calls == [1]
    assert len(checks) == 2
    assert cache.hits == 1
    assert cache.misses == 1


def test_f7_bounded_cache_eviction_prevents_unbounded_growth():
    cache = BoundedExactAttackCache(max_entries=2)
    for square in range(4):
        cache.get_or_compute(_position(), square, 0, lambda square=square: square)
    assert cache.peak == 2
    assert len(cache.entries) == 2
    assert cache.evictions == 2
