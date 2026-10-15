"""A finite movement graph must not depend on the Python call-stack limit."""
import pytest
from generic_chess.ai.evaluation.movement_graph import _largest_scc_ratio, graph_metrics
from generic_chess.core.movement import RayAtom

@pytest.mark.parametrize("n", [1024, 2048])
@pytest.mark.parametrize("closed", [False, True])
def test_deep_path_and_cycle_scc(n, closed):
    adj = [[i+1] if i+1 < n else ([0] if closed else []) for i in range(n)]
    assert _largest_scc_ratio(adj, n) == (1.0 if closed else 1/n)


def test_large_sccs_with_one_way_bridge_stay_separate():
    n = 2048
    adj = [[(i//1024)*1024 + (i+1)%1024] for i in range(n)]
    adj[0].append(1024)
    assert _largest_scc_ratio(adj, n) == .5


def test_supported_32_board_rook_graph_is_one_component():
    metrics = graph_metrics(32, tuple(RayAtom(d) for d in ((1,0),(-1,0),(0,1),(0,-1))))
    assert metrics.largest_component_ratio == 1.0
    assert metrics.reachable_pair_ratio == 1.0
    assert metrics.diameter == 2
