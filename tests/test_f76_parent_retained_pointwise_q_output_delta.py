"""Contract tests for the F76 pointwise-Q output correction."""

import json
from pathlib import Path

import numpy as np

from scripts import f76_parent_retained_pointwise_q_output_delta as f76


ROOT = Path(__file__).resolve().parents[1]


def test_f76_scope_and_frozen_identity_contract():
    assert f76.WORK_ORDER == "GENERICCHESS-F76-PARENT-RETAINED-POINTWISE-Q-OUTPUT-DELTA"
    assert f76.PARENT_SHA == "e680f6ab09b15cc13520d8655b7100a1540b8134"
    assert f76.GEN1_ID == "d0e6a02482bb316e657ec6ef5c4f9379e6e7946d2da1a9a38647175567aecab4"
    assert f76.FIT_ROOT_COUNT == 48
    assert f76.DEVELOPMENT_ROOT_COUNT == 20
    assert f76.REGULARIZATION == 1e-3
    assert f76.NODES == 2_048
    assert f76.MAX_DEPTH == 12
    assert f76.TT_MEGABYTES == 8


def test_pointwise_delta_is_deterministic_and_improves_weighted_objective():
    rows = [[
        {
            "hidden": np.asarray([1.0, 0.0]),
            "target_residual": 2.0,
            "parent_residual": 0.0,
            "parent_total": 0.0,
            "action_key": "a",
        },
        {
            "hidden": np.asarray([0.0, 1.0]),
            "target_residual": -1.0,
            "parent_residual": 0.0,
            "parent_total": 0.0,
            "action_key": "b",
        },
    ]]
    first, first_summary = f76._fit_pointwise_delta(rows, 2, 1.0, 1e-3)
    second, second_summary = f76._fit_pointwise_delta(rows, 2, 1.0, 1e-3)
    assert np.array_equal(first, second)
    assert first_summary == second_summary
    assert first_summary["objective_after"] < first_summary["objective_before"]


def test_pointwise_targets_subtract_parent_residual_before_scaling():
    rows = [[
        {
            "hidden": np.asarray([1.0]),
            "target_residual": 5.0,
            "parent_residual": 2.0,
            "parent_total": 0.0,
            "action_key": "a",
        }]
    ]
    delta, _summary = f76._fit_pointwise_delta(rows, 1, 2.0, 1e-9)
    assert np.isclose(delta[0], 1.5, atol=1e-6)


def test_durable_candidate_descriptor_is_compact_and_identity_bound():
    payload = json.loads(
        (ROOT / "artifacts" / "f76_parent_retained_pointwise_q" / "candidate.json").read_text(
            encoding="utf-8"
        )
    )
    assert payload["source_commit"] == f76.PARENT_SHA
    assert payload["parent_checkpoint_id"] == f76.GEN1_ID
    assert payload["child_checkpoint_id"] == "efe6bcf97198a75badae0989720e3a5c05889c0d9f3babbe92c472d686724ffd"
    assert payload["f74_delta_cosine"] < 0.995
    assert len(payload["raw_delta"]) == 32
    assert len(payload["final_output_weights"]) == 32
