"""Unused source coordinates may be omitted only on canonical square input."""
import pytest
from generic_chess import build_builtin_ruleset, compile_ruleset_for_execution
from generic_chess.core import attacks
from generic_chess.core.coordinates import BoardShape, index_to_square, Square
from generic_chess.session.session import GameSession

def sample():
    compiled = compile_ruleset_for_execution(build_builtin_ruleset("western_chess"))
    return compiled._legacy_compiled, GameSession(compiled).state.position

class Extent:
    def __init__(self, compiled, extent):
        self.compiled = compiled
        self.board_size = extent
    def __getattr__(self, key):
        return getattr(self.compiled, key)

def test_canonical_maps_equal_independent_scalar_without_unused_source_conversion(monkeypatch):
    compiled, position = sample()
    expected = [frozenset(Square(file, rank) for rank in range(8) for file in range(8)
                         if attacks.is_square_attacked(position, Square(file, rank), side, compiled))
                for side in (0, 1)]
    def unused(*args):
        raise AssertionError("unused source Square allocated")
    monkeypatch.setattr(attacks, "index_to_square", unused)
    assert [attacks.pseudo_attacks(position, side, compiled) for side in (0, 1)] == expected

def test_shape_extent_keeps_original_source_conversion(monkeypatch):
    compiled, position = sample()
    expected = attacks.pseudo_attacks(position, 0, compiled)
    calls = []
    def observed(index, extent):
        calls.append((index, extent))
        return index_to_square(index, extent)
    monkeypatch.setattr(attacks, "index_to_square", observed)
    assert attacks.pseudo_attacks(position, 0, Extent(compiled, BoardShape(8, 8))) == expected
    assert len(calls) == sum(p is not None and p.owner == 0 for p in position.board)

@pytest.mark.parametrize("extent", [0, True, None])
def test_invalid_extent_keeps_original_required_error(extent):
    compiled, position = sample()
    with pytest.raises((TypeError, ValueError)):
        attacks.pseudo_attacks(position, 0, Extent(compiled, extent))
