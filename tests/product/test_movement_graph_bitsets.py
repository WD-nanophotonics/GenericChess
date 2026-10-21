"""Exact directed-distance layers and original large-graph sampling contract."""
import random

import pytest

from generic_chess.ai.evaluation import movement_graph as mg
from generic_chess.core.coordinates import BoardShape
from generic_chess.core.movement import LeapAtom, RayAtom


@pytest.mark.parametrize("count", [1, 2, 3, 7, 16, 31, 64])
def test_bitset_distances_match_queue_reference_on_directed_disconnected_graphs(count):
    rng = random.Random(20261015 + count)
    for density in [0, .03, .2, 1]:
        adj = [[target for target in range(count) if rng.random() < density] for _ in range(count)]
        masks = [sum(1 << target for target in row) for row in adj]
        for source in range(count):
            assert mg._bfs_bitset(masks, source, count) == mg._bfs(adj, source, count)


@pytest.mark.parametrize("shape,atoms", [
    (BoardShape(4, 4), ()),
    (BoardShape(5, 9), (LeapAtom((0, 1)),)),
    (BoardShape(8, 8), (RayAtom((1, 1)), RayAtom((-1, -1)))),
    (BoardShape(16, 16), (RayAtom((1, 0)), RayAtom((-1, 0)))),
    (BoardShape(32, 32), tuple(RayAtom(d) for d in ((1, 0), (-1, 0), (0, 1), (0, -1)))),
])
def test_complete_metrics_equal_list_reference_at_exact_boundary(shape, atoms, monkeypatch):
    observed = mg.graph_metrics(shape, atoms)
    adj, count = mg.build_movement_graph(shape, atoms)
    monkeypatch.setattr(mg, "_bfs_bitset", lambda masks, source, size: mg._bfs(adj, source, count))
    assert observed == mg.graph_metrics(shape, atoms)


def test_sampled_graph_uses_original_sources_without_quadratic_bitsets(monkeypatch):
    calls = []
    original = mg._bfs
    def counted(adj, source, count):
        calls.append(source)
        return original(adj, source, count)
    def forbidden(*args):
        raise AssertionError("sampled large graph must retain list traversal")
    monkeypatch.setattr(mg, "_bfs", counted)
    monkeypatch.setattr(mg, "_bfs_bitset", forbidden)
    result = mg.graph_metrics(BoardShape(33, 32), (LeapAtom((0, 1)),))
    assert len(calls) == len(set(calls)) == 64
    assert calls[0] == 0 and calls[-1] == 1055
    assert result.largest_component_ratio == 0
