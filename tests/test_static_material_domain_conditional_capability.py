from fractions import Fraction
import json

from generic_chess.rules.compiler import compile_semantic_ruleset
from scripts.audit_static_material_domain_conditional_capability import (
    _domain_table,
    OUTPUT,
    main,
    _source_c_by_square,
    _source_u_by_square,
)
from scripts.audit_static_semantic_material_prior_v2c import (
    _event_measure_factory,
    _token_state_ledger,
    audit_ruleset_v2c,
)
from scripts.audit_static_semantic_material_prior_v2d import _capture_rows
from tests.test_static_semantic_material_prior_v2c import _synthetic_with_optional_tokens


def test_equal_domains_identical_capability_factor_exactly():
    result = _domain_table(4, [Fraction(2)] * 4, [Fraction(3)] * 4, [[0, 1], [2, 3]])
    assert result["domain_size_weighted_b_bar_exact"] == "5/1"
    assert result["d_exact"] == "1/2"
    assert result["j_exact"] == result["fct_exact"] == "5/2"
    assert result["factorization_error_exact"] == "0/1"


def test_unequal_domains_with_capability_coupling_show_exact_nonfactorization():
    local = [Fraction(1), Fraction(5), Fraction(5), Fraction(5)]
    result = _domain_table(4, local,
                           [Fraction(0)] * 4, [[0], [1, 2, 3]])
    assert result["domain_size_weighted_b_bar_exact"] == "4/1"
    assert result["d_exact"] == "5/8"
    assert result["j_exact"] == "23/8"
    assert result["fct_exact"] == "5/2"
    assert result["factorization_error_exact"] == "-3/8"
    assert result["r_joint_exact"] == "23/32"
    domain = [0, 1, 1, 1]
    enumerated_j = sum((local[source] for source in range(4) for target in range(4)
                        if domain[source] == domain[target]), Fraction(0)) / 16
    assert enumerated_j == Fraction(result["j_exact"])


def test_unequal_domains_constant_capability_satisfy_owner_factorization():
    result = _domain_table(4, [Fraction(5)] * 4, [Fraction(0)] * 4, [[0], [1, 2, 3]])
    assert result["j_exact"] == result["fct_exact"] == "25/8"
    assert result["factorization_error_exact"] == "0/1"


def test_domain_permutation_and_singleton_domains_preserve_aggregates():
    u = [Fraction(1), Fraction(2), Fraction(4), Fraction(7)]
    c = [Fraction(0), Fraction(1), Fraction(2), Fraction(3)]
    original = _domain_table(4, u, c, [[0], [1, 2, 3]])
    permuted = _domain_table(4, u, c, [[1, 2, 3], [0]])
    for key in ("domain_size_weighted_u_bar_exact", "domain_size_weighted_c_bar_exact",
                "domain_size_weighted_b_bar_exact", "j_exact", "fct_exact",
                "factorization_error_exact", "d_exact"):
        assert original[key] == permuted[key]
    assert sorted(original["domains"][i]["size"] for i in range(2)) == [1, 3]


def test_owner_mirror_preserves_owner_averaged_joint_diagnostic():
    u = [Fraction(1), Fraction(2), Fraction(4), Fraction(7)]
    c = [Fraction(0), Fraction(1), Fraction(2), Fraction(3)]
    components = [[0], [1, 2, 3]]
    original = _domain_table(4, u, c, components)
    mirrored_u = list(reversed(u))
    mirrored_c = list(reversed(c))
    mirrored_components = [[3], [0, 1, 2]]
    mirrored = _domain_table(4, mirrored_u, mirrored_c, mirrored_components)
    for key in ("domain_size_weighted_u_bar_exact", "domain_size_weighted_c_bar_exact",
                "domain_size_weighted_b_bar_exact", "j_exact", "fct_exact",
                "factorization_error_exact", "d_exact"):
        assert original[key] == mirrored[key]


def test_source_option_and_capture_decomposition_reproduce_synthetic_v2c_v2d():
    compiled = compile_semantic_ruleset(_synthetic_with_optional_tokens())
    token_ledger = _token_state_ledger(compiled)
    u = _source_u_by_square(compiled, "X", token_ledger)
    v2c = audit_ruleset_v2c(compiled)
    reconstructed_u = sum((sum(rows, Fraction(0)) for rows in u["u_by_owner_source"].values()), Fraction(0)) / (2 * 64)
    assert u["coverage_complete"]
    assert reconstructed_u == Fraction(v2c["ledger"]["X"]["v2c_exact"])

    measure = _event_measure_factory(token_ledger, compiled, "X")
    capture_rows = _capture_rows(compiled, "X", measure)
    c = _source_c_by_square(capture_rows, 64)
    reconstructed_c = sum((sum(rows, Fraction(0)) for rows in c["c_by_owner_source"].values()), Fraction(0)) / (2 * 64)
    assert c["coverage_complete"]
    assert reconstructed_c == Fraction(capture_rows["capture_affordance_exact"])


def test_real_frozen_baselines_reconstruct_without_reference_or_score_change():
    assert main() == 0
    result = json.loads(OUTPUT.read_text(encoding="utf-8"))
    assert result["classification"] == "STATIC_MATERIAL_DOMAIN_CONDITIONAL_CAPABILITY_FACTORABLE"
    assert result["coverage_complete"]
    assert result["reconstruction_complete"]
    assert result["human_reference_imported"] is False
    assert result["v2d_residuals_imported"] is False
    assert result["material_formula_modified"] is False
    assert result["score_validation_performed"] is False
    assert result["v2e_transition_value_used"] is False
    assert result["transport_efficiency_used"] is False
    assert result["transition_bearing_domain_payoff_assigned"] is False
    assert all(row["u_reconstruction_exact"] and row["c_reconstruction_exact"]
               and row["b0_reconstruction_exact"]
               for ruleset in result["rulesets"].values()
               for row in ruleset["types"].values())
    assert all(row["joint_measure_status"] == "NOT_APPLICABLE_TRANSITION_BEARING_TYPE"
               for ruleset in result["rulesets"].values()
               for row in ruleset["types"].values() if not row["terminal_current_type"])
    assert all("j_exact" not in owner["domain_conditioned"]
               and "fct_exact" not in owner["domain_conditioned"]
               and "r_joint_exact" not in owner["domain_conditioned"]
               for ruleset in result["rulesets"].values()
               for row in ruleset["types"].values() if not row["terminal_current_type"]
               for owner in row["owner_graphs"].values())
    assert all(row["factorization_error_exact"] == "0/1"
               for ruleset in result["rulesets"].values()
               for row in ruleset["types"].values() if row["terminal_current_type"])
