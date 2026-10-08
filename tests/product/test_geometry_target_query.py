"""Target probes retain the compiled all-endpoint geometry contract."""

import pytest

from generic_chess.rules.ir import (
    CompiledGeometry,
    geometry_candidates,
    geometry_paths_to,
)


@pytest.mark.parametrize("kind,min_steps", [("leap", None), ("ray", 1),
                                           ("ray", 2), ("ray", 5)])
def test_target_query_matches_all_endpoint_contract(kind, min_steps):
    geometry = CompiledGeometry(
        "target-probe", kind, min_steps=min_steps,
        paths={"0": {0: (1, 2, 3, 2), 1: ()},
               "1": {0: (7, 6, 5), 1: (4,)}},
    )
    for owner in ("0", "1", "absent"):
        for source in (0, 1, 8):
            candidates = geometry_candidates(geometry, owner, source)
            for target in range(9):
                expected = tuple(path for endpoint, path in candidates
                                 if endpoint == target)
                assert tuple(geometry_paths_to(geometry, owner, source, target)) == expected


def test_target_query_preserves_duplicate_prefixes_and_minimum_distance():
    geometry = CompiledGeometry(
        "repeated-target", "ray", min_steps=2,
        paths={"0": {0: (1, 2, 3, 2)}},
    )
    assert tuple(geometry_paths_to(geometry, "0", 0, 1)) == ()
    assert tuple(geometry_paths_to(geometry, "0", 0, 2)) == ((1,), (1, 2, 3))


def test_target_query_uses_rectangular_flat_indices_without_direction_guessing():
    geometry = CompiledGeometry(
        "rectangular-ray", "ray", min_steps=2,
        paths={"0": {0: (7, 14, 21)}, "1": {21: (14, 7, 0)}},
    )
    assert tuple(geometry_paths_to(geometry, "0", 0, 14)) == ((7,),)
    assert tuple(geometry_paths_to(geometry, "1", 21, 0)) == ((14, 7),)
    assert tuple(geometry_paths_to(geometry, "1", 21, 14)) == ()
