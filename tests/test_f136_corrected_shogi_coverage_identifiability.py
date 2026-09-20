import numpy as np

from generic_chess.rules.compiler import compile_semantic_ruleset
from generic_chess.rules.standard_shogi import build_standard_shogi_ruleset
from scripts.f136_corrected_shogi_coverage_identifiability import (
    BASELINE,
    CORRECTED_ORACLE_SHA,
    FEATURE_NAME_SHA,
    FAMILY_ORDER,
    CorrectedShogiFrozenBasisV2,
    _corr,
    _feature_family,
    _gate,
)


def test_f136_constants_bind_to_f135_baseline_and_schema():
    compiled = compile_semantic_ruleset(build_standard_shogi_ruleset())
    basis = CorrectedShogiFrozenBasisV2("standard_shogi", compiled)
    assert BASELINE == "f63eaaffa4c143342fa3d11c05447e8766974a4a"
    assert basis.oracle_weight_sha256 == CORRECTED_ORACLE_SHA
    from scripts.f122_reverse_benchmark_known_evaluator_system_identification import _json_sha
    assert _json_sha(basis.names) == FEATURE_NAME_SHA
    assert len(basis.names) == 1086


def test_f136_family_mapping_and_gate_are_authoritative():
    assert _feature_family("material_diff:P") == "material"
    assert _feature_family("occupancy_diff:P:0:0") == "occupancy/PST"
    assert _feature_family("hand_diff:P") == "hand"
    assert _feature_family("legal_drop_count_diff:R") == "legal-drop counts"
    assert tuple(FAMILY_ORDER) == ("material", "occupancy/PST", "hand", "mobility", "king escape", "king-zone pressure", "current check", "promotion potential", "legal-drop counts", "mean legal-drop mobility")
    assert _gate({"normalized_rmse": 0.05, "r2": 0.99, "pearson": 0.995})
    assert not _gate({"normalized_rmse": 0.050001, "r2": 0.99, "pearson": 0.995})


def test_f136_correlation_handles_constant_vectors():
    assert _corr(np.asarray([1.0, 1.0]), np.asarray([0.0, 1.0])) == 0.0
    assert np.isclose(_corr(np.asarray([1.0, 2.0, 3.0]), np.asarray([2.0, 4.0, 6.0])), 1.0)
