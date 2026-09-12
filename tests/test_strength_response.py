from types import SimpleNamespace

import pytest

from generic_chess.benchmark.qualification import (
    GateOutcome,
    MetricEvidence,
    QualificationReport,
    STATUS_PASS,
    reduce_qualification_status,
)
from generic_chess.benchmark.strength_response import (
    PREP_SCHEMA,
    StrengthResponsePrep,
    measure_strength_response,
    prepare_strength_response,
)


def _prep():
    return prepare_strength_response(
        SimpleNamespace(ruleset_fingerprint="rules-v1"),
        evaluator_identity="eval-v1",
        candidate_fingerprint="candidate-v1",
        pair_count=6,
        max_depth=8,
        tape_seeds=(11, 22, 33),
        bootstrap_resamples=100,
    )


def _summaries(value=0.7):
    return {
        key: {"pair_scores": [value] * 6, "search_nodes": 6 * budget}
        for key, budget in (
            ("4x-vs-1x", 1280),
            ("16x-vs-4x", 5120),
            ("16x-vs-1x", 20480),
        )
    }


def test_prep_is_result_free_and_freezes_protocol_identity():
    prep = _prep()
    assert prep.schema == PREP_SCHEMA
    assert prep.budget_ladder == (256, 1024, 4096)
    assert prep.prep_fingerprint == prepare_strength_response(
        SimpleNamespace(ruleset_fingerprint="rules-v1"),
        evaluator_identity="eval-v1",
        candidate_fingerprint="candidate-v1",
        pair_count=6,
        max_depth=8,
        tape_seeds=(11, 22, 33),
        bootstrap_resamples=100,
    ).prep_fingerprint
    assert "matchups" not in prep.to_dict()


def test_clean_monotone_curve_passes_and_preserves_pair_level_evidence():
    result = measure_strength_response(
        prep=_prep(), summaries=_summaries(), compiled=None
    )
    assert result.layer_d_status == "PASS"
    assert result.reason_codes == ()
    assert result.matchups["16x-vs-1x"]["pair_scores"] == [0.7] * 6
    assert result.compute_usage["arena_games"] == 36
    assert result.behavior_descriptors["search_response_monotonicity"]["value"] is True


def test_depth_censoring_and_mixed_tape_are_deferred():
    summaries = _summaries()
    summaries["16x-vs-1x"]["depth_censored"] = True
    result = measure_strength_response(prep=_prep(), summaries=summaries)
    assert result.layer_d_status == "DEFER"
    assert result.reason_codes == ("DEPTH_CENSORED",)

    mixed = _summaries()
    mixed["16x-vs-1x"]["pair_scores"] = [0.9, 0.9, 0.9, 0.4, 0.9, 0.9]
    result = measure_strength_response(prep=_prep(), summaries=mixed)
    assert result.layer_d_status == "DEFER"
    assert result.reason_codes == ("MIXED_TAPE_RESPONSE",)


def test_result_rejects_incomplete_or_mismatched_prep():
    with pytest.raises(ValueError, match="exactly pair_count"):
        bad = _summaries()
        bad["4x-vs-1x"]["pair_scores"] = [0.7]
        measure_strength_response(prep=_prep(), summaries=bad)
    with pytest.raises(ValueError, match="does not match PREP"):
        measure_strength_response(
            prep=_prep(),
            opening_corpus=SimpleNamespace(
                corpus_id="different", openings=(), to_dict=lambda: {}
            ),
            summaries=_summaries(),
        )


def _base_report():
    gates = (GateOutcome("base", STATUS_PASS, "EMPIRICAL_GATE", "ok"),)
    layers = {key: STATUS_PASS for key in ("A", "B", "C", "D", "E")}
    return QualificationReport(
        ruleset_fingerprint="rules-v1",
        provenance={},
        experiment_identity="base",
        qualification_target="PLAYABILITY",
        required_layers=("A", "B", "C"),
        blocking_layers=("A", "C"),
        non_blocking_layers=("B",),
        non_blocking_gate_names=(),
        measurement_status=STATUS_PASS,
        calibration_expectation_status=STATUS_PASS,
        layers=layers,
        raw_diagnostics={},
        hard_gates=gates,
        integrity_gates=gates,
        qualification_gates=gates,
        reason_codes=(),
        layer_reasons={},
        fail_defer_reasons=(),
        compute_usage={},
        behavior_descriptors={"base": MetricEvidence(True, "GENERICCHESS_SPECIFIC")},
        overall_status=reduce_qualification_status(
            layers, required_layers=("A", "B", "C"), integrity_gates=gates,
            qualification_gates=gates, blocking_layers=("A", "C"),
        ),
    )


def test_layer_d_is_diagnostic_unless_skill_bearing_target_is_selected():
    result = measure_strength_response(prep=_prep(), summaries=_summaries())
    report = _base_report().with_strength_response(result)
    assert report.qualification_target == "PLAYABILITY"
    assert report.layers["D"] == "PASS"
    assert "D" not in report.blocking_layers

    skill = _base_report().with_strength_response(
        result, qualification_target="SKILL_BEARING"
    )
    assert skill.qualification_target == "SKILL_BEARING"
    assert "D" in skill.required_layers
    assert "D" in skill.blocking_layers
    assert skill.raw_diagnostics["strength_response"]["schema"] == "generic-chess-strength-response-v1"
