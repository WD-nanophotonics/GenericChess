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
    ACTION_TRACE_SCHEMA,
    HORIZON_AWARE_PREP_SCHEMA,
    PREP_SCHEMA,
    StrengthResponsePrep,
    measure_strength_response,
    prepare_strength_response,
)
from generic_chess.benchmark.strength_response import _depth_ceiling_stats


def test_depth_ceiling_fraction_uses_only_the_strong_budget_role():
    telemetry = [{"engine_role": "parent", "completed_depth": 8}, {"engine_role": "child", "completed_depth": 8}, {"engine_role": "child", "completed_depth": 3}]
    assert _depth_ceiling_stats(telemetry, 8) == (3, 2)
    assert _depth_ceiling_stats(telemetry, 8, engine_role="child") == (2, 1)


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
    one = {
        key: {"pair_scores": [value] * 6, "search_nodes": 6 * budget}
        for key, budget in (
            ("4x-vs-1x", 1280),
            ("16x-vs-4x", 5120),
            ("16x-vs-1x", 20480),
        )
    }
    return {tape: {key: dict(row) for key, row in one.items()} for tape in (
        "tape-11", "tape-22", "tape-33"
    )}


def _r5_prep():
    return prepare_strength_response(
        SimpleNamespace(ruleset_fingerprint="rules-v1"),
        evaluator_identity="eval-v1",
        candidate_fingerprint="candidate-v1",
        pair_count=2,
        max_depth=8,
        max_ply=20,
        tape_seeds=(11, 22, 33),
        bootstrap_resamples=100,
        schema=HORIZON_AWARE_PREP_SCHEMA,
    )


def _r5_summaries(*, horizon_hit=False, child_depths=(3, 3, 3)):
    rows = {}
    for tape in ("tape-11", "tape-22", "tape-33"):
        rows[tape] = {}
        for matchup in ("4x-vs-1x", "16x-vs-4x", "16x-vs-1x"):
            games = []
            for index in range(2):
                games.append({
                    "pair_index": index,
                    "child_owner": index % 2,
                    "termination_status": "max_ply" if horizon_hit and matchup == "16x-vs-1x" and index == 0 else "draw",
                    "actual_plies": 20 if horizon_hit and matchup == "16x-vs-1x" and index == 0 else 7,
                    "opening_position_key": f"{tape}-opening-{index}",
                    "final_position_key": f"{tape}-{matchup}-{index}",
                    "actions": [{"kind": "board", "from": [0, 0], "to": [0, 1], "promotion_target_id": None}],
                })
            metric_rows = [
                {"engine_role": "parent", "completed_depth": 8},
                *[{"engine_role": "child", "completed_depth": depth} for depth in child_depths],
            ]
            rows[tape][matchup] = {"pair_scores": [0.7, 0.7], "games": games, "metrics": metric_rows}
    return rows


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
    assert result.matchups["16x-vs-1x"]["pair_scores"] == [0.7] * 18
    assert result.compute_usage["arena_games"] == 108
    assert set(result.tape_results) == {"tape-11", "tape-22", "tape-33"}
    assert result.behavior_descriptors["search_response_monotonicity"]["value"] is True


def test_depth_censoring_and_mixed_tape_are_deferred():
    summaries = _summaries()
    summaries["tape-11"]["16x-vs-1x"]["depth_censored"] = True
    result = measure_strength_response(prep=_prep(), summaries=summaries)
    assert result.layer_d_status == "DEFER"
    assert result.reason_codes == ("DEPTH_CENSORED",)

    mixed = _summaries()
    mixed["tape-11"]["16x-vs-1x"]["pair_scores"] = [0.4] * 6
    result = measure_strength_response(prep=_prep(), summaries=mixed)
    assert result.layer_d_status == "DEFER"
    assert result.reason_codes == ("MIXED_TAPE_RESPONSE",)


def test_r5_child_only_ceiling_and_horizon_gates_are_frozen_and_role_aware():
    prep = _r5_prep()
    assert prep.child_ceiling_gate_fraction == prep.horizon_hit_gate_fraction == 0.5
    # The parent hit is deliberately ignored; one child hit in three is below
    # the child-only ceiling gate and remains a diagnostic, not censorship.
    result = measure_strength_response(
        prep=prep, summaries=_r5_summaries(child_depths=(8, 3, 3))
    )
    assert result.layer_d_status == "PASS"
    assert result.behavior_descriptors["high_budget_ceiling_hit_fraction"]["value"] == pytest.approx(1 / 3)

    horizon = measure_strength_response(
        prep=prep, summaries=_r5_summaries(horizon_hit=True)
    )
    assert horizon.layer_d_status == "DEFER"
    assert horizon.reason_codes == ("HORIZON_CENSORED",)
    assert horizon.behavior_descriptors["strongest_vs_weakest_horizon_hit_fraction"]["value"] == 0.5

    explicit = _r5_summaries(horizon_hit=True)
    explicit["tape-11"]["16x-vs-1x"]["depth_censored"] = True
    result = measure_strength_response(prep=prep, summaries=explicit)
    assert result.reason_codes == ("DEPTH_CENSORED",)
    assert result.behavior_descriptors["explicit_censor_flags_present"]["value"] is True


def test_r5_action_trace_is_stable_and_binds_identity_without_affecting_result():
    first = measure_strength_response(prep=_r5_prep(), summaries=_r5_summaries())
    second = measure_strength_response(prep=_r5_prep(), summaries=_r5_summaries())
    first_trace = first.behavior_descriptors["action_trace_contract"]["value"]
    second_trace = second.behavior_descriptors["action_trace_contract"]["value"]
    assert first.layer_d_status == second.layer_d_status == "PASS"
    assert first_trace["schema"] == ACTION_TRACE_SCHEMA
    assert len(first_trace["action_traces"]) == 18
    assert first_trace["action_traces"] == second_trace["action_traces"]
    record = first_trace["action_traces"][0]
    assert record["tape_id"] == record["opening_corpus_id"]
    assert record["budget_roles"] == {"parent_nodes_per_move": 256, "child_nodes_per_move": 1024}
    assert record["actions"] and record["action_trace_sha256"]


def test_result_rejects_incomplete_or_mismatched_prep():
    with pytest.raises(ValueError, match="exactly pair_count"):
        bad = _summaries()
        bad["tape-11"]["4x-vs-1x"]["pair_scores"] = [0.7]
        measure_strength_response(prep=_prep(), summaries=bad)
    with pytest.raises(ValueError, match="do not match PREP"):
        measure_strength_response(
            prep=_prep(),
            opening_corpora=[
                SimpleNamespace(corpus_id=identity, openings=(), to_dict=lambda: {})
                for identity in ("different", "tape-22", "tape-33")
            ],
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


def test_deferred_layer_d_keeps_legacy_report_status_but_blocks_skill_target():
    summaries = _summaries()
    summaries["tape-11"]["16x-vs-1x"]["pair_scores"] = [0.4] * 6
    result = measure_strength_response(prep=_prep(), summaries=summaries)
    report = _base_report().with_strength_response(result)
    assert result.layer_d_status == "DEFER"
    assert report.overall_status == STATUS_PASS
    skill = _base_report().with_strength_response(
        result, qualification_target="SKILL_BEARING"
    )
    assert skill.overall_status == "DEFER"


def test_mapping_prep_fingerprint_is_tamper_evident():
    payload = _prep().to_dict()
    payload["evaluator_identity"] = "different-evaluator"
    with pytest.raises(ValueError, match="fingerprint"):
        measure_strength_response(prep=payload, summaries=_summaries())


def test_real_runner_requires_identical_checkpoint_and_evaluator_identity():
    compiled = SimpleNamespace(ruleset_fingerprint="rules-v1")
    parent = SimpleNamespace(
        checkpoint_id="candidate-v1", ruleset_fingerprint="rules-v1",
        evaluator_version="eval-v1",
    )
    child = SimpleNamespace(
        checkpoint_id="candidate-v2", ruleset_fingerprint="rules-v1",
        evaluator_version="eval-v1",
    )
    with pytest.raises(ValueError, match="checkpoint identity must be identical"):
        measure_strength_response(
            compiled, None, parent, child, _prep(), summaries=_summaries()
        )


def test_real_runner_consumes_three_corpora_for_each_of_three_matchups():
    corpora = [
        SimpleNamespace(corpus_id=identity, openings=(), to_dict=lambda: {})
        for identity in ("corpus-a", "corpus-b", "corpus-c")
    ]
    prep = prepare_strength_response(
        SimpleNamespace(ruleset_fingerprint="rules-v1"),
        evaluator_identity="eval-v1",
        candidate_fingerprint="candidate-v1",
        opening_corpora=corpora,
        pair_count=6,
        tape_seeds=(11, 22, 33),
        bootstrap_resamples=100,
    )
    calls = []

    def fake_runner(_compiled, _rules, _parent, _child, config, corpus, **_kwargs):
        calls.append((corpus.corpus_id, config.parent_nodes_per_move, config.child_nodes_per_move))
        return {"pair_scores": [0.75] * 6}

    checkpoint = SimpleNamespace(
        checkpoint_id="candidate-v1", ruleset_fingerprint="rules-v1",
        evaluator_version="eval-v1",
    )
    result = measure_strength_response(
        SimpleNamespace(ruleset_fingerprint="rules-v1"), None,
        checkpoint, checkpoint, prep, opening_corpora=corpora,
        arena_runner=fake_runner,
    )
    assert len(calls) == 9
    assert {row[0] for row in calls} == {"corpus-a", "corpus-b", "corpus-c"}
    assert result.compute_usage["arena_tapes"] == 3
    assert result.layer_d_status == "PASS"


def test_a_or_c_failure_short_circuits_layer_d_runner():
    report = _base_report()
    report.layers["A"] = "FAIL"
    calls = []
    result = measure_strength_response(
        prep=_prep(),
        summaries=_summaries(),
        base_report=report,
        arena_runner=lambda *args, **kwargs: calls.append(args),
    )
    assert result.reason_codes == ("PREREQUISITE_A_C_NOT_PASS",)
    assert calls == []
