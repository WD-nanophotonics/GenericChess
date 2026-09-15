from __future__ import annotations

import numpy as np

from scripts import f88_f87_update_damping_arena2 as f88


def test_f88_uses_frozen_identities_and_registered_arena2_corpus():
    _allocation, compiled, _native, parent, raw, corpus = f88._load_context()
    assert parent.checkpoint_id == f88.PARENT_ID
    assert raw.checkpoint_id == f88.RAW_F87_ID
    assert corpus.corpus_id == "6eca12faa0981e1c71f637eae7f66ee4a053193a752fbe592d2b0edafbdffd2a"
    assert tuple(opening.index for opening in corpus.openings) == (0, 1)
    parent.validate_ruleset(compiled)


def test_f88_interpolates_only_the_three_trainable_blocks_with_distinct_ids():
    _allocation, _compiled, _native, parent, raw, _corpus = f88._load_context()
    parent_model = f88.CompactNonlinearResidual.from_dict(parent.compact_nonlinear)
    raw_model = f88.CompactNonlinearResidual.from_dict(raw.compact_nonlinear)
    candidates = [f88.build_candidate(parent, raw, alpha) for alpha in f88.ALPHAS]
    assert candidates[0][0].checkpoint_id != candidates[1][0].checkpoint_id
    assert candidates[0][1]["candidate_model_sha256"] != candidates[1][1]["candidate_model_sha256"]
    for alpha, (candidate, metadata) in zip(f88.ALPHAS, candidates):
        model = f88.CompactNonlinearResidual.from_dict(candidate.compact_nonlinear)
        expected_hidden = np.asarray(parent_model.hidden_weights) + alpha * (np.asarray(raw_model.hidden_weights) - np.asarray(parent_model.hidden_weights))
        expected_bias = np.asarray(parent_model.hidden_bias) + alpha * (np.asarray(raw_model.hidden_bias) - np.asarray(parent_model.hidden_bias))
        expected_output = np.asarray(parent_model.output_weights) + alpha * (np.asarray(raw_model.output_weights) - np.asarray(parent_model.output_weights))
        np.testing.assert_allclose(model.hidden_weights, expected_hidden)
        np.testing.assert_allclose(model.hidden_bias, expected_bias)
        np.testing.assert_allclose(model.output_weights, expected_output)
        assert candidate.board_weights == parent.board_weights
        assert candidate.hand_weights == parent.hand_weights
        assert candidate.dynamic_weights == parent.dynamic_weights
        assert candidate.spatial_occupancy_weights == parent.spatial_occupancy_weights
        assert candidate.localized_control_weights == parent.localized_control_weights
        assert metadata["parameter_delta_norms"]["hidden_weights"] > 0.0
