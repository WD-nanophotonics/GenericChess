"""Bounded topology-only Chess bishop/knight arrival diagnostic."""

import hashlib
import json
from collections import deque
from fractions import Fraction
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TOPOLOGY = ROOT / ".generic_chess_flow/static-material-domain-fragmentation-topology.json"


def arrival_histogram(edges, area):
    adjacent = [[] for _ in range(area)]
    for source, target in edges:
        adjacent[source].append(target)
    histogram = [0] * (area + 1)
    for source in range(area):
        distance = {source: 0}
        pending = deque([source])
        while pending:
            vertex = pending.popleft()
            for target in adjacent[vertex]:
                if target not in distance:
                    distance[target] = distance[vertex] + 1
                    pending.append(target)
        for hops in distance.values():
            histogram[hops] += 1
        histogram[area] += area - len(distance)  # unreachable sentinel
    return histogram


def audit():
    raw = TOPOLOGY.read_bytes()
    document = json.loads(raw)
    chess = document["rulesets"]["western_chess"]
    area = chess["board_area"]
    result = {"source_sha256": hashlib.sha256(raw).hexdigest(), "board_area": area, "pieces": {}}
    for piece in ("B", "N"):
        histograms = [
            arrival_histogram(chess["pieces"][piece]["owner_graphs"][str(owner)]["directed_edges"], area)
            for owner in (0, 1)
        ]
        assert histograms[0] == histograms[1], "Chess owner arrival histograms differ"
        histogram = [sum(rows[k] for rows in histograms) for k in range(area + 1)]
        assert sum(histogram) == 2 * area * area
        cumulative = 0
        curve = []
        for hops in range(area):
            cumulative += histogram[hops]
            curve.append(str(Fraction(cumulative, 2 * area * area)))
        result["pieces"][piece] = {
            "exact_hop_histogram": {str(k): count for k, count in enumerate(histogram[:-1]) if count},
            "unreachable_pair_count": histogram[-1],
            "cumulative_fraction_including_source": curve[:max(k for k, v in enumerate(histogram[:-1]) if v) + 1],
        }
    return result


if __name__ == "__main__":
    print(json.dumps(audit(), indent=2))
