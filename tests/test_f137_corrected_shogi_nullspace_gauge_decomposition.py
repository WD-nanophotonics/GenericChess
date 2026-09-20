from types import SimpleNamespace

import numpy as np

from generic_chess.rules.compiler import compile_semantic_ruleset
from generic_chess.rules.standard_shogi import build_standard_shogi_ruleset
from scripts.f135_corrected_shogi_oracle_schema_rebaseline import CorrectedShogiFrozenBasisV2
from scripts.f137_corrected_shogi_nullspace_gauge_decomposition import (
    F137_BASELINE,
    TYPES,
    _canonical_gauges,
    _split_indices,
)


def test_f137_baseline_and_frozen_split_contract():
    assert F137_BASELINE == "08f5eb079f6614c834792356ee4d97c1e0786540"
    splits = _split_indices()
    assert (splits["train"].start, splits["train"].stop) == (0, 3000)
    assert (splits["dev"].start, splits["dev"].stop) == (3000, 3750)
    assert (splits["holdout"].start, splits["holdout"].stop) == (3750, 4500)


def test_f137_canonical_gauges_are_schema_defined_and_independent_of_svd():
    compiled = compile_semantic_ruleset(build_standard_shogi_ruleset())
    basis = CorrectedShogiFrozenBasisV2("standard_shogi", compiled)
    pack = {
        "active": np.ones(len(basis.names), dtype=bool),
        "feature_scale": np.ones(len(basis.names), dtype=np.float64),
        "design": {"train": np.zeros((2, len(basis.names) + 1), dtype=np.float64)},
    }
    gauges, definitions = _canonical_gauges(basis, pack)
    assert gauges.shape == (len(basis.names) + 1, len(TYPES))
    assert all(definitions[type_id]["active_occupancy_coordinate_count"] == 81 for type_id in TYPES)
    assert all(definitions[type_id]["omitted_occupancy_coordinate_count"] == 0 for type_id in TYPES)
    assert np.allclose(np.linalg.norm(gauges, axis=0), np.sqrt(82.0))
    assert np.allclose(gauges[-1], 0.0)
