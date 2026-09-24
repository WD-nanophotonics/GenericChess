from dataclasses import replace
from fractions import Fraction
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.audit_static_semantic_material_prior_v2a import (
    _group_probability,
    audit_ruleset_v2a,
    evaluate_density_polynomial,
    integrate_density_polynomial,
    union_probability_polynomial,
)
from scripts.audit_static_semantic_material_prior_v2b import audit_ruleset_v2b
from scripts.audit_static_semantic_material_prior_v2a import event_probability
from tests.test_static_semantic_material_prior_v2a import _cube, _synthetic


@pytest.mark.parametrize("rho", [Fraction(0), Fraction(2, 3), Fraction(1, 2), Fraction(40, 81)])
def test_fixed_density_equals_direct_polynomial_evaluation(rho):
    cube = _cube(path=(1, 2), target=("empty",))
    polynomial = union_probability_polynomial([cube])
    _, fixed_total = _group_probability({"event": {"cubes": [cube]}}, Fraction(1), fixed_rho=rho)
    assert fixed_total == evaluate_density_polynomial(polynomial, rho)


def test_rho_two_thirds_reproduces_v2_and_v2a_default_stays_phase_averaged():
    _, compiled = _synthetic()
    v2a = audit_ruleset_v2a(compiled)
    fixed = audit_ruleset_v2a(compiled, fixed_at_rho_max=True)
    assert v2a["density_model"]["rho_distribution"] == "Uniform[0,rho_max]"
    assert v2a["ledger"]["X"]["v2a_raw_exact"] != fixed["ledger"]["X"]["v2b_raw_exact"]
    assert fixed["density_model"]["rho_reference"] == "rho_max"
    assert fixed["human_metrics_computed"] is False
    assert fixed["ledger"]["X"]["fixed_three_label_reproduction"]["absolute_difference"] < 1e-12


def test_zero_density_is_empty_board_limit_for_supported_quiet_leap():
    cube = _cube()
    poly = union_probability_polynomial([cube])
    assert evaluate_density_polynomial(poly, Fraction(0)) == 1


def test_increasing_density_does_not_increase_nonzero_ray_clearance():
    cube = _cube(path=(1, 2, 3))
    assert evaluate_density_polynomial(union_probability_polynomial([cube]), Fraction(1, 2)) < evaluate_density_polynomial(
        union_probability_polynomial([cube]), Fraction(1, 4)
    )


def test_leap_has_only_endpoint_occupancy_and_candidate_has_exact_components():
    leap = _cube()
    assert union_probability_polynomial([leap]) == (Fraction(1), Fraction(-1))
    assert event_probability(leap, Fraction(1, 2)) == Fraction(3, 4)
    _, compiled = _synthetic()
    row = audit_ruleset_v2b(compiled)["ledger"]["X"]
    assert row["v2b_raw_exact"]
    assert set(row["components_exact"]) == {
        "quiet", "capture", "ray_path_attenuation", "source_restriction_excluded_raw",
        "immediate_promotion_branch_mass", "held_drop",
    }


def test_rename_owner_mirror_and_added_successor_preserve_v2b_invariants():
    from generic_chess.rules.compiler import compile_semantic_ruleset

    rules, base_compiled = _synthetic()
    base = audit_ruleset_v2b(base_compiled)["ledger"]["X"]["v2b_raw_exact"]
    renamed_types = tuple(replace(row, type_id="Y") if row.type_id == "X" else row for row in rules.piece_types)
    renamed_actions = tuple(replace(row, type_ids=("Y",)) for row in rules.semantic_actions)
    renamed = compile_semantic_ruleset(replace(
        rules, piece_types=renamed_types, semantic_actions=renamed_actions,
        drop_allowed={"Y": rules.drop_allowed["X"]},
    ))
    assert audit_ruleset_v2b(renamed)["ledger"]["Y"]["v2b_raw_exact"] == base

    mirrored_position = tuple(tuple(
        replace(piece, owner=1 - piece.owner) if piece is not None else None for piece in row
    ) for row in rules.initial_position)
    mirrored = compile_semantic_ruleset(replace(rules, initial_position=mirrored_position))
    assert audit_ruleset_v2b(mirrored)["ledger"]["X"]["v2b_raw_exact"] == base

    extra_rules, expanded = _synthetic(shapes=((1, 0), (0, 1)), relations=("empty", "enemy"))
    del extra_rules
    expanded_value = audit_ruleset_v2b(expanded)["ledger"]["X"]["v2b_fixed_rho_max_board_intrinsic"]
    base_value = audit_ruleset_v2b(base_compiled)["ledger"]["X"]["v2b_fixed_rho_max_board_intrinsic"]
    assert expanded_value >= base_value


def test_real_chess_and_shogi_use_only_executable_inventory_density():
    from generic_chess.rules.compiler import compile_semantic_ruleset
    from generic_chess.rules.standard_shogi import build_standard_shogi_ruleset
    from generic_chess.rules.western_chess import build_western_chess_ruleset

    for rules in (build_western_chess_ruleset(), build_standard_shogi_ruleset()):
        result = audit_ruleset_v2b(compile_semantic_ruleset(rules))
        assert result["inventory_bound"]["complete"]
        assert result["density_model"]["human_metric_search_used"] is False
        assert result["human_metrics_computed"] is False
        assert all(row["v2b_raw_exact"] for row in result["ledger"].values())

    chess = audit_ruleset_v2b(compile_semantic_ruleset(build_western_chess_ruleset()))
    pawn = chess["ledger"]["P"]
    assert Fraction(*map(int, pawn["v2b_raw_exact"].split("/"))) > 0
    assert pawn["promotion_transitions"]
    assert pawn["v2b_coverage"] == "COMPLETE"


def test_candidate_module_does_not_import_human_reference_data():
    from scripts import audit_static_semantic_material_prior_v2b as candidate

    source = Path(candidate.__file__).read_text(encoding="utf-8").lower()
    assert "f40_material_prior_audit" not in source
    assert "human reference" not in source
