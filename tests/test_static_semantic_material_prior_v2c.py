from collections import Counter
from dataclasses import replace
from fractions import Fraction
from itertools import permutations
from pathlib import Path
import ast
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from generic_chess.core.pieces import Piece
from generic_chess.rules.compiler import compile_semantic_ruleset
from generic_chess.rules.standard_shogi import build_standard_shogi_ruleset
from generic_chess.rules.western_chess import build_western_chess_ruleset
from scripts.audit_static_semantic_material_prior_v2c import (
    OCCUPANCY_STATES,
    _board_count_pmf,
    _pmf_stats,
    _source_joint_counts,
    _token_state_ledger,
    audit_ruleset_v2c,
    finite_population_union_probability,
)
from tests.test_static_semantic_material_prior_v2a import _synthetic


def test_finite_population_union_matches_explicit_enumeration_and_unions_events():
    labels = ("empty", "own", "enemy")
    assignments = list(permutations(labels))  # one of each label on three squares
    cube_eox = (((0, ("empty",)), (1, ("own",)), (2, ("enemy",))),)
    enumerated = Fraction(sum(row == labels for row in assignments), len(assignments))
    computed = finite_population_union_probability(
        cube_eox, empty_count=1, own_count=1, enemy_count=1,
    )
    assert enumerated == computed == Fraction(1, 6)

    empty_at_zero = ((0, ("empty",)),)
    own_at_zero = ((0, ("own",)),)
    assert finite_population_union_probability(
        [empty_at_zero, own_at_zero], empty_count=1, own_count=1, enemy_count=1,
    ) == Fraction(2, 3)


def test_inventory_and_source_conditioned_pmf_are_exact_for_chess_and_shogi():
    cases = (
        (build_western_chess_ruleset(), 2, 30, Fraction(17), Fraction(15, 2), Fraction(35, 2), Fraction(29, 4)),
        (build_standard_shogi_ruleset(), 2, 38, Fraction(21), Fraction(19, 2), Fraction(43, 2), Fraction(37, 4)),
    )
    for rules, anchors, optional, mean, variance, source_mean, source_variance in cases:
        ledger = _token_state_ledger(compile_semantic_ruleset(rules))
        assert ledger["complete"]
        assert ledger["anchor_token_count"] == anchors
        assert ledger["optional_token_count"] == optional
        pmf = _pmf_stats(_board_count_pmf(ledger))
        source_pmf = _pmf_stats(_board_count_pmf(ledger, source_conditioned=True))
        assert pmf["mass_exact"] == source_pmf["mass_exact"] == "1/1"
        assert Fraction(pmf["mean_exact"]) == mean
        assert Fraction(pmf["variance_exact"]) == variance
        assert Fraction(source_pmf["mean_exact"]) == source_mean
        assert Fraction(source_pmf["variance_exact"]) == source_variance
        for source_is_anchor in (True, False):
            for owner in (0, 1):
                joint = _source_joint_counts(ledger, owner, source_is_anchor=source_is_anchor)
                assert sum(joint.values(), Fraction(0)) == 1
                assert all(sum(counts) == ledger["board_square_count"] - 1 for counts in joint)
                occupied_mean = sum(Fraction(own + enemy) * mass for (empty, own, enemy), mass in joint.items())
                expected = (mean if source_is_anchor else source_mean) - 1
                assert occupied_mean == expected
                for label_index, label in enumerate(OCCUPANCY_STATES):
                    event = (((0, (label,)),),)
                    for counts in joint:
                        probability = finite_population_union_probability(
                            event, empty_count=counts[0], own_count=counts[1], enemy_count=counts[2]
                        )
                        assert probability == Fraction(counts[label_index], ledger["board_square_count"] - 1)


def test_chess_owner_survives_but_shogi_owner_prior_is_explicit_and_symmetric():
    chess = _token_state_ledger(compile_semantic_ruleset(build_western_chess_ruleset()))
    shogi = _token_state_ledger(compile_semantic_ruleset(build_standard_shogi_ruleset()))
    assert chess["owner_model"] == "initial_owner_persists"
    assert chess["owner_model_is_rule_unique"] is True
    assert all(row.get("capture_disposition") == "remove_from_game"
               for row in chess["token_types"].values() if not row["anchor"])
    assert shogi["owner_model"] == "maximum_entropy_symmetric_owner_given_board_state"
    assert shogi["owner_model_is_rule_unique"] is False
    assert all(row.get("capture_disposition") == "capture_to_hand"
               for row in shogi["token_types"].values() if not row["anchor"])
    for ledger in (chess, shogi):
        own0 = _source_joint_counts(ledger, 0, source_is_anchor=False)
        own1 = _source_joint_counts(ledger, 1, source_is_anchor=False)
        assert own0 == own1


def test_promotion_and_hand_reentry_are_token_preserving_and_ledgered():
    chess = _token_state_ledger(compile_semantic_ruleset(build_western_chess_ruleset()))
    shogi = _token_state_ledger(compile_semantic_ruleset(build_standard_shogi_ruleset()))
    assert chess["token_types"]["P"]["promotion_targets"] == ["Q", "R", "B", "N"]
    assert chess["token_types"]["P"]["persistence_state"] == "board_or_removed"
    assert shogi["token_types"]["P"]["persistence_state"] == "board_or_hand"
    assert all(set(row["drop_effect_pairs"]) == {(1, 1)} for row in shogi["token_types"].values() if not row["anchor"])
    assert all(row["persistence_state"] == "board_or_removed" for row in chess["token_types"].values() if not row["anchor"])


def _synthetic_with_optional_tokens(*, shapes=((1, 0), (0, 1)), relations=("empty", "enemy")):
    rules, _compiled = _synthetic(shapes=shapes, relations=relations)
    rows = [list(row) for row in rules.initial_position]
    rows[2][2] = Piece(0, "X", "X", False)
    rows[5][5] = Piece(1, "X", "X", False)
    return replace(rules, initial_position=tuple(tuple(row) for row in rows))


def test_v2c_source_conditioning_owner_mirror_and_rule_renaming():
    rules = _synthetic_with_optional_tokens()
    compiled = compile_semantic_ruleset(rules)
    baseline = audit_ruleset_v2c(compiled)
    assert baseline["coverage_complete"]
    value = baseline["ledger"]["X"]["v2c_exact"]

    mirrored_position = tuple(tuple(
        replace(piece, owner=1 - piece.owner) if piece is not None else None for piece in row
    ) for row in rules.initial_position)
    mirrored = compile_semantic_ruleset(replace(rules, initial_position=mirrored_position))
    assert audit_ruleset_v2c(mirrored)["ledger"]["X"]["v2c_exact"] == value

    renamed_types = tuple(replace(row, type_id="Y") if row.type_id == "X" else row for row in rules.piece_types)
    renamed_actions = tuple(replace(row, type_ids=tuple("Y" if tid == "X" else tid for tid in row.type_ids))
                            for row in rules.semantic_actions)
    renamed_position = tuple(tuple(
        replace(piece, base_type_id="Y", current_type_id="Y")
        if piece is not None and piece.current_type_id == "X" else piece for piece in row
    ) for row in rules.initial_position)
    renamed = compile_semantic_ruleset(replace(
        rules, piece_types=renamed_types, semantic_actions=renamed_actions,
        initial_position=renamed_position, drop_allowed={"Y": rules.drop_allowed["X"]},
    ))
    assert audit_ruleset_v2c(renamed)["ledger"]["Y"]["v2c_exact"] == value


def test_candidate_calculation_has_no_human_reference_or_transport_imports():
    from scripts import audit_static_semantic_material_prior_v2c as candidate

    tree = ast.parse(Path(candidate.__file__).read_text(encoding="utf-8"))
    imported = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            imported.append(node.module or "")
    assert not any("validate_static_material" in name or name.startswith("tests.fixtures")
                   or "transport_efficiency" in name for name in imported)
