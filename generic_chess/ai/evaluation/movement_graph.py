"""Empty-board directed movement graph metrics."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass

from ...core.coordinates import BoardShape, _shape, index_to_square
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


def build_movement_graph(n: int | BoardShape, atoms: tuple[MovementAtom, ...]) -> tuple[list[list[int]], int]:
    """Adjacency list (owner-relative orientation, player 0)."""
    shape = _shape(n)
    adj: list[list[int]] = [[] for _ in range(shape.area)]
    for idx in range(shape.area):
        square = index_to_square(idx, shape)
        seen: set[int] = set()
        for atom in atoms:
            for target in atom_targets(shape, 0, square, atom):
                tidx = target.rank * shape.width + target.file
                if tidx not in seen:
                    seen.add(tidx)
                    adj[idx].append(tidx)
    return adj, shape.area


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


def _bfs_bitset(neighbors: list[int], source: int, node_count: int) -> tuple[int, int, int]:
    """Exact shortest-distance layers on a bounded, directed movement graph."""
    seen = frontier = 1 << source
    reachable = path_sum = depth = 0
    while frontier:
        targets = 0
        while frontier:
            bit = frontier & -frontier
            targets |= neighbors[bit.bit_length() - 1]
            frontier ^= bit
        frontier = targets & ~seen
        if not frontier:
            break
        depth += 1
        count = frontier.bit_count()
        reachable += count
        path_sum += depth * count
        seen |= frontier
        if reachable == node_count - 1:
            break
    return reachable, path_sum, depth


def graph_metrics(n: int | BoardShape, atoms: tuple[MovementAtom, ...]) -> MovementGraphMetrics:
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
    # Graph construction deduplicates each adjacency list. Limit the extra
    # bitset storage to the existing exact-analysis bound (at most128KiB bits).
    # Larger graphs retain the original sampled-source/list traversal.
    bitsets = [sum(1 << target for target in row) for row in adj] if exact else None
    for source in sources:
        reachable, path_sum, max_dist = (
            _bfs_bitset(bitsets, source, node_count) if bitsets is not None
            else _bfs(adj, source, node_count)
        )
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

    # Explicit DFS frames preserve Tarjan's traversal without consuming one
    # Python call frame per square (a supported32x32 graph can exceed1000).
    for root in range(node_count):
        if indices[root] != -1:
            continue
        indices[root] = lowlink[root] = index
        index += 1
        stack.append(root)
        on_stack[root] = True
        frames = [(root, iter(adj[root]))]
        while frames:
            v, neighbors = frames[-1]
            try:
                w = next(neighbors)
            except StopIteration:
                if lowlink[v] == indices[v]:
                    size = 0
                    while True:
                        w = stack.pop()
                        on_stack[w] = False
                        size += 1
                        if w == v:
                            break
                    largest = max(largest, size)
                frames.pop()
                if frames:
                    parent = frames[-1][0]
                    lowlink[parent] = min(lowlink[parent], lowlink[v])
                continue
            if indices[w] == -1:
                indices[w] = lowlink[w] = index
                index += 1
                stack.append(w)
                on_stack[w] = True
                frames.append((w, iter(adj[w])))
            elif on_stack[w]:
                lowlink[v] = min(lowlink[v], indices[w])
    return largest / node_count if node_count else 0.0
