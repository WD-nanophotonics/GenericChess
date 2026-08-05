"""Empty-board directed movement graph metrics."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass

from ...core.coordinates import index_to_square
from ...core.movement import MovementAtom, atom_targets


@dataclass(frozen=True, slots=True)
class MovementGraphMetrics:
    average_out_degree: float
    reachable_pair_ratio: float
    average_shortest_path: float | None
    diameter: int | None
    largest_component_ratio: float


_EXACT_THRESHOLD = 1024
_SAMPLE_SOURCES = 64


def build_movement_graph(n: int, atoms: tuple[MovementAtom, ...]) -> tuple[list[list[int]], int]:
    """Adjacency list (owner-relative orientation, player 0)."""
    adj: list[list[int]] = [[] for _ in range(n * n)]
    for idx in range(n * n):
        square = index_to_square(idx, n)
        seen: set[int] = set()
        for atom in atoms:
            for target in atom_targets(n, 0, square, atom):
                tidx = target.rank * n + target.file
                if tidx not in seen:
                    seen.add(tidx)
                    adj[idx].append(tidx)
    return adj, n * n


def _bfs(adj: list[list[int]], source: int, node_count: int) -> tuple[int, int, int]:
    """Return (reachable_count, path_sum, max_distance) from source."""
    dist = {source: 0}
    queue = deque([source])
    while queue:
        node = queue.popleft()
        for nxt in adj[node]:
            if nxt not in dist:
                dist[nxt] = dist[node] + 1
                queue.append(nxt)
    reachable = len(dist) - 1
    path_sum = sum(d for d in dist.values() if d > 0)
    max_dist = max(dist.values())
    return reachable, path_sum, max_dist


def graph_metrics(n: int, atoms: tuple[MovementAtom, ...]) -> MovementGraphMetrics:
    adj, node_count = build_movement_graph(n, atoms)
    total_edges = sum(len(neighbors) for neighbors in adj)
    average_out_degree = total_edges / node_count if node_count else 0.0

    exact = node_count <= _EXACT_THRESHOLD
    sources = range(node_count) if exact else sorted(
        {int(round(i * (node_count - 1) / (_SAMPLE_SOURCES - 1))) for i in range(_SAMPLE_SOURCES)}
    )
    sources = [s for s in sources if s < node_count]

    reachable_sum = 0
    path_sum_total = 0
    pair_count = 0
    diameter = 0
    for source in sources:
        reachable, path_sum, max_dist = _bfs(adj, source, node_count)
        reachable_sum += reachable
        pair_count += reachable
        path_sum_total += path_sum
        diameter = max(diameter, max_dist)
    reachable_pair_ratio = reachable_sum / (len(sources) * (node_count - 1)) if len(sources) and node_count > 1 else 0.0
    average_shortest_path = path_sum_total / pair_count if pair_count else None

    # Largest SCC ratio (exact for small graphs).
    largest_component_ratio = _largest_scc_ratio(adj, node_count) if exact else 0.0
    return MovementGraphMetrics(
        average_out_degree=average_out_degree,
        reachable_pair_ratio=reachable_pair_ratio,
        average_shortest_path=average_shortest_path,
        diameter=diameter if pair_count else None,
        largest_component_ratio=largest_component_ratio,
    )


def _largest_scc_ratio(adj: list[list[int]], node_count: int) -> float:
    index = 0
    stack: list[int] = []
    on_stack = [False] * node_count
    indices = [-1] * node_count
    lowlink = [0] * node_count
    largest = 0

    def strongconnect(v: int) -> None:
        nonlocal index, largest
        indices[v] = index
        lowlink[v] = index
        index += 1
        stack.append(v)
        on_stack[v] = True
        for w in adj[v]:
            if indices[w] == -1:
                strongconnect(w)
                lowlink[v] = min(lowlink[v], lowlink[w])
            elif on_stack[w]:
                lowlink[v] = min(lowlink[v], indices[w])
        if lowlink[v] == indices[v]:
            component = []
            while True:
                w = stack.pop()
                on_stack[w] = False
                component.append(w)
                if w == v:
                    break
            largest = max(largest, len(component))

    for v in range(node_count):
        if indices[v] == -1:
            strongconnect(v)
    return largest / node_count if node_count else 0.0
