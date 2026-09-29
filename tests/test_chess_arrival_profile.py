"""Checks for the bounded topology-only arrival diagnostic."""

import sys
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from audit_chess_arrival_profile import arrival_histogram, audit  # noqa: E402


def test_arrival_histogram_counts_shortest_paths_and_unreachable_pairs():
    # 0 -> 1 -> 2; source 2 cannot leave. Each source-target pair occurs once.
    assert arrival_histogram([(0, 1), (1, 2)], 3) == [3, 2, 1, 3]


def test_frozen_chess_topology_has_bishop_knight_deadline_crossover():
    pieces = audit()["pieces"]
    bishop = pieces["B"]["cumulative_fraction_including_source"]
    knight = pieces["N"]["cumulative_fraction_including_source"]
    assert bishop == ["1/64", "39/256", "1/2"]
    assert knight == ["1/64", "25/256", "185/512", "377/512", "979/1024", "1023/1024", "1"]
    assert pieces["B"]["unreachable_pair_count"] == 4096
    assert pieces["N"]["unreachable_pair_count"] == 0
