"""Cheap contract tests for the F48 execution boundary."""

from __future__ import annotations

from scripts.f48_protocol import (
    RULESET_FINGERPRINTS,
    build_partition_plan,
    partition_id,
    preflight,
    recompute_selector,
)


def _ruleset(*, admissible: bool = True, leverage: bool = True, stability: bool = True):
    initial = {
        prior: {"holdout_vs_p0_teacher": {"agreement": 0.5 if prior != "P48-0" else 0.8}}
        for prior in ("P48-0", "P48-1", "P48-2", "P48-3")
    }
    learners = {}
    for learner in ("M48-0", "M48-1"):
        by_prior = {}
        for prior in initial:
            by_prior[prior] = {
                "generations": [
                    {
                        "holdout_teacher_agreement": {"agreement": 0.8 if prior == "P48-0" else 0.75},
                        "catastrophic_arena_regression": False,
                        "integrity_gates": True,
                        "arena_vs_p48_0": {"mean_pair_score": 0.6, "bootstrap_low": 0.55},
                    }
                ]
            }
        learners[learner] = {"by_prior": by_prior}
    return {
        "ruleset_id": "A_CANONICAL_WESTERN_CHESS",
        "ruleset_fingerprint": RULESET_FINGERPRINTS["A_CANONICAL_WESTERN_CHESS"],
        "prerequisites": {"admissible": admissible, "leverage_pass": leverage, "teacher_stability_pass": stability},
        "initial_competence": initial,
        "learners": learners,
    }


def test_partition_inventory_is_deterministic_and_unique():
    first = build_partition_plan()
    second = build_partition_plan()
    assert first == second
    ids = [row["partition_id"] for row in first]
    assert len(ids) == len(set(ids))
    assert partition_id(ruleset_id="A_CANONICAL_WESTERN_CHESS", phase="corpus") == "F48.A-CANONICAL-WESTERN-CHESS.none.none.G00.corpus"
    assert len(first) == 249
    assert all(row["phase"] in {"corpus", "leverage", "stability", "calibration", "initial", "training", "holdout", "arena"} for row in first)


def test_preflight_binds_authority_and_separates_holdout():
    plan = preflight()
    assert plan["status"] == "PASS"
    assert plan["baseline_sha"] == "dc1fe20964354b6494e90830408c8747018d6102"
    assert plan["authority"]["selected_h48b"]["index"] == 9
    assert plan["holdout_separation"] == {
        "holdout_in_training": False,
        "holdout_in_ranking": False,
        "holdout_in_arena_opening_generation": False,
        "mechanically_checked": True,
    }
    assert all(len(row["input_hash"]) == 64 for row in plan["partitions"])


def test_selector_terminal_prerequisite_paths():
    assert recompute_selector([_ruleset(admissible=False, leverage=False, stability=False)]) == "MIXED_OR_UNRESOLVED"
    assert recompute_selector([_ruleset(admissible=False, leverage=False, stability=True)]) == "MATERIAL_ONLY_LEVERAGE_INSUFFICIENT"
    assert recompute_selector([_ruleset(admissible=False, leverage=True, stability=False)]) == "SEARCH_ENGINE_LIMITS_LEARNING"


def test_selector_terminal_learning_paths():
    rows = [_ruleset(), _ruleset(), _ruleset()]
    assert recompute_selector(rows) == "COLD_START_RECOVERY_SUPPORTED"

    rows = [_ruleset(), _ruleset(), _ruleset()]
    for row in rows:
        for prior in ("P48-1", "P48-2", "P48-3"):
            row["learners"]["M48-1"]["by_prior"][prior]["generations"][0]["holdout_teacher_agreement"]["agreement"] = 0.5
        row["learners"]["M48-0"]["by_prior"]["P48-0"]["generations"][0]["holdout_teacher_agreement"]["agreement"] = 0.83
    assert recompute_selector(rows) == "TDLEAF_MATERIAL_RECOVERY_SUPPORTED"

    rows = [_ruleset(), _ruleset(), _ruleset()]
    for row in rows:
        for prior in ("P48-1", "P48-2", "P48-3"):
            row["learners"]["M48-0"]["by_prior"][prior]["generations"][0]["holdout_teacher_agreement"]["agreement"] = 0.5
        row["learners"]["M48-1"]["by_prior"]["P48-0"]["generations"][0]["holdout_teacher_agreement"]["agreement"] = 0.83
    assert recompute_selector(rows) == "SEARCH_AWARE_MATERIAL_EVOLUTION_SUPPORTED"

    rows = [_ruleset(), _ruleset(), _ruleset()]
    for row in rows:
        for learner in ("M48-0", "M48-1"):
            for prior in ("P48-1", "P48-2", "P48-3"):
                row["learners"][learner]["by_prior"][prior]["generations"][0]["holdout_teacher_agreement"]["agreement"] = 0.5
    assert recompute_selector(rows) == "LEARNING_DIRECTION_FAILURE"
