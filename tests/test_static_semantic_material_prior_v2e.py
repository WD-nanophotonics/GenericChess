from fractions import Fraction
from pathlib import Path
import ast
import sys

from generic_chess.rules.compiler import compile_semantic_ruleset
from generic_chess.rules.schema import RuleSquareRef
from generic_chess.rules.standard_shogi import build_standard_shogi_ruleset
from generic_chess.rules.western_chess import build_western_chess_ruleset
from scripts.audit_static_semantic_material_prior_v2c import _event_measure_factory, _token_state_ledger
from scripts.audit_static_semantic_material_prior_v2e import (
    _add_transition_event,
    _transition_events,
    canonical_removed_effect_identity,
    solve_transition_values,
)
from scripts.audit_static_semantic_material_prior_v2d import resolve_removed_square

ROOT = Path(__file__).resolve().parents[1]


def _event(options, probability=Fraction(1), **extra):
    return {"allowed_resulting_types": tuple(options), "probability": probability, **extra}


def test_no_transition_has_zero_premium_and_preserves_b0():
    base = {"A": Fraction(7, 3)}
    result = solve_transition_values(base, {"A": []}, area=8)
    assert result["acyclic"]
    assert result["transition_premiums"]["A"] == 0
    assert result["transition_values_b1"]["A"] == base["A"]


def test_optional_equal_higher_and_lower_destinations():
    equal = solve_transition_values({"A": Fraction(2), "B": Fraction(2)},
        {"A": [_event(("A", "B")), _event(("A", "B"))]}, area=1)
    higher = solve_transition_values({"A": Fraction(2), "B": Fraction(5)},
        {"A": [_event(("A", "B")), _event(("A", "B"))]}, area=1)
    lower = solve_transition_values({"A": Fraction(5), "B": Fraction(2)},
        {"A": [_event(("A", "B")), _event(("A", "B"))]}, area=1)
    assert equal["transition_premiums"]["A"] == 0
    assert higher["transition_premiums"]["A"] == 3
    assert lower["transition_premiums"]["A"] == 0


def test_forced_lower_transition_keeps_negative_delta_without_clipping():
    result = solve_transition_values({"A": Fraction(5), "B": Fraction(2)},
        {"A": [_event(("B",)), _event(("B",))]}, area=1)
    event = result["evaluated_events"]["A"][0]
    assert event["signed_delta"] == -3
    assert result["transition_premiums"]["A"] == -3
    assert result["transition_values_b1"]["A"] == 2


def test_multiple_destinations_use_max_not_sum_and_inferior_option_changes_nothing():
    base = {"A": Fraction(1), "B": Fraction(5), "C": Fraction(3), "D": Fraction(7)}
    with_inferior = solve_transition_values(base, {"A": [
        _event(("A", "B", "C")), _event(("A", "B", "C"))]}, area=1)
    with_superior = solve_transition_values(base, {"A": [
        _event(("A", "B", "D")), _event(("A", "B", "D"))]}, area=1)
    assert with_inferior["transition_premiums"]["A"] == 4
    assert with_superior["transition_premiums"]["A"] >= with_inferior["transition_premiums"]["A"]
    assert with_inferior["evaluated_events"]["A"][0]["selected_v_after"] == 5


def test_transition_descriptions_deduplicate_and_capture_quiet_classes_stay_distinct():
    groups = {}
    key = (0, 12, 20, "empty", "quiet", ())
    cube = ((20, ("empty",)),)
    for name in ("promote_rule", "duplicate_promote_rule"):
        _add_transition_event(groups, key, cube, allowed_types=("P", "Q", "R"),
            pattern_name=name, forced=False, promotion_mode="inherit_compiled_masks")
    assert len(groups) == 1
    assert len(set(groups[key]["cubes"])) == 1
    assert groups[key]["option_sets"] == {("P", "Q", "R")}
    capture_key = (0, 12, 20, "enemy", "capture", ((20, "remove_from_game"),))
    _add_transition_event(groups, capture_key, ((20, ("enemy",)),), allowed_types=("Q", "R"),
        pattern_name="capture_promote", forced=True, promotion_mode="inherit_compiled_masks")
    assert len(groups) == 2


def test_reference_syntax_aliases_for_same_removed_square_union_to_one_transition():
    source, target, width = 12, 20, 8
    refs = (RuleSquareRef(kind="target"),
            RuleSquareRef(kind="offset_from_target", offset=(0, 0)))
    resolved = [resolve_removed_square(ref, owner=0, source=source, target=target,
        path=(), area_width=width) for ref in refs]
    assert resolved == [target, target]
    identities = [canonical_removed_effect_identity(((square, "capture_to_hand", repr(ref)),))
                  for square, ref in zip(resolved, refs)]
    assert identities[0] == identities[1] == ((target, "capture_to_hand"),)

    groups = {}
    physical_key = (0, source, target, "enemy", "capture", identities[0])
    cube = ((target, ("enemy",)),)
    for name, ref in zip(("capture_by_target_ref", "capture_by_zero_offset_ref"), refs):
        _add_transition_event(groups, physical_key, cube, allowed_types=("P", "Q"),
            pattern_name=name, forced=True, promotion_mode="inherit_compiled_masks",
            effect_square_refs=(repr(ref),))
    assert len(groups) == 1
    assert len(set(groups[physical_key]["cubes"])) == 1
    assert len(groups[physical_key]["effect_square_refs"]) == 2
    different_square_identity = ((target + 1, "capture_to_hand"),)
    different_square_key = (0, source, target, "enemy", "capture", different_square_identity)
    _add_transition_event(groups, different_square_key, cube, allowed_types=("P", "Q"),
        pattern_name="different_removed_square", forced=True, promotion_mode="inherit_compiled_masks")
    assert len(groups) == 2

    result = solve_transition_values({"P": Fraction(1), "Q": Fraction(5)},
        {"P": [_event(("Q",), Fraction(1, 2))]}, area=1)
    assert result["transition_premiums"]["P"] == 1


def test_two_level_dag_propagates_downstream_b1_in_reverse_topological_order():
    base = {"A": Fraction(1), "B": Fraction(2), "C": Fraction(4)}
    events = {"A": [_event(("A", "B")), _event(("A", "B"))],
              "B": [_event(("B", "C")), _event(("B", "C"))], "C": []}
    result = solve_transition_values(base, events, area=1)
    assert result["acyclic"]
    assert result["reverse_topological_order"] == ["C", "B", "A"]
    assert result["transition_values_b1"] == {"A": 4, "B": 4, "C": 4}
    assert result["transition_premiums"] == {"A": 3, "B": 2, "C": 0}
    assert result["evaluated_events"]["A"][0]["destination_capabilities_b0_or_b1"]["B"] == 4


def test_cycle_fails_closed_without_an_implicit_discount():
    result = solve_transition_values({"A": Fraction(1), "B": Fraction(2)},
        {"A": [_event(("B",))], "B": [_event(("A",))]}, area=1)
    assert not result["acyclic"]
    assert set(result["cycle"]) == {"A", "B"}
    assert "transition_premiums" not in result


def test_renaming_types_and_mirroring_owner_event_rows_preserve_averaged_values():
    base = {"P": Fraction(1), "Q": Fraction(5)}
    events = {"P": [_event(("P", "Q"), owner=0), _event(("P", "Q"), owner=1)], "Q": []}
    original = solve_transition_values(base, events, area=1)
    renamed = solve_transition_values({"x": base["P"], "y": base["Q"]},
        {"x": [_event(("x", "y"), owner=1), _event(("x", "y"), owner=0)], "y": []}, area=1)
    assert original["transition_values_b1"]["P"] == renamed["transition_values_b1"]["x"]
    assert original["transition_premiums"]["P"] == renamed["transition_premiums"]["x"]


def test_chess_pawn_and_shogi_pawn_transitions_are_derived_from_compiled_rules():
    chess = compile_semantic_ruleset(build_western_chess_ruleset())
    chess_ledger = _token_state_ledger(chess)
    chess_events = _transition_events(chess, "P", _event_measure_factory(chess_ledger, chess, "P"))
    assert chess_events["coverage_complete"]
    assert chess_events["events"]
    alternatives = {destination for event in chess_events["events"] for destination in event["allowed_resulting_types"]}
    assert {"Q", "R", "B", "N"} <= alternatives
    assert all(event["forced"] and "P" not in event["allowed_resulting_types"]
               for event in chess_events["events"])

    shogi = compile_semantic_ruleset(build_standard_shogi_ruleset())
    shogi_ledger = _token_state_ledger(shogi)
    shogi_events = _transition_events(shogi, "P", _event_measure_factory(shogi_ledger, shogi, "P"))
    assert shogi_events["coverage_complete"]
    assert "TP" in {destination for event in shogi_events["events"] for destination in event["allowed_resulting_types"]}


def test_candidate_contains_no_reference_transport_or_validation_imports():
    tree = ast.parse((ROOT / "scripts/audit_static_semantic_material_prior_v2e.py").read_text(encoding="utf-8"))
    imported = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            imported.append(node.module or "")
    assert not any("validate_static_material" in name or name.startswith("tests.fixtures")
                   or "transport_efficiency" in name or "xiangqi" in name.lower() for name in imported)
