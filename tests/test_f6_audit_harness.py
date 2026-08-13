"""H6A contract tests for target-directed semantic geometry."""

from __future__ import annotations

from generic_chess.rules.ir import geometry_candidates
from scripts.audit_f6_target_directed import (
    FINGERPRINT,
    compiled_geometry_cases,
    semantic_specs,
    target_directed_matches,
)


def test_f6_reuses_the_certified_four_prefix_corpus():
    assert [spec["id"] for spec in semantic_specs()] == [
        "semantic_prefix_0",
        "semantic_prefix_1",
        "semantic_prefix_2",
        "semantic_prefix_3",
    ]


def test_f6_geometry_cases_include_certified_and_generic_shapes():
    labels = {label for label, _gid, _geometry, _size in compiled_geometry_cases()}
    assert {f"semantic_prefix_{i}" for i in range(4)} <= labels
    assert "fixture_castling_min_steps" in labels
    assert "fixture_cannon" in labels
    assert "fixture_en_passant" in labels


def test_f6_candidate_matches_oracle_exactly_for_all_compiled_geometry():
    rows = 0
    for _label, _gid, geometry, board_size in compiled_geometry_cases():
        for owner in (0, 1):
            for source in range(board_size * board_size):
                for target in range(board_size * board_size):
                    baseline = tuple(
                        (candidate_target, candidate_path)
                        for candidate_target, candidate_path in geometry_candidates(
                            geometry, str(owner), source
                        )
                        if candidate_target == target
                    )
                    assert target_directed_matches(
                        geometry, owner, source, target
                    ) == baseline
                    rows += 1
    assert rows > 0


def test_f6_certified_fingerprint_is_frozen():
    assert FINGERPRINT == "5b3d04eda31a342b729fc9af8a04cdde13c796646b2b37024891f8c99703c345"
