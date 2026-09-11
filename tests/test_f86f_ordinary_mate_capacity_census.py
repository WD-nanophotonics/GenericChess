"""F86F bounded ordinary-piece mate-capacity census contracts."""

import json
from pathlib import Path

from generic_chess.core.attacks import is_in_check
from generic_chess.core.movegen import has_legal_action
from generic_chess.core.pieces import Piece
from generic_chess.core.position import Hands, Position
from generic_chess.rules.compiler import compile_ruleset
from generic_chess.rules.schema import ruleset_from_dict

ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS = ROOT / "artifacts" / "f86f_mate_capacity"


def _load(name):
    return json.loads((ARTIFACTS / name).read_text(encoding="utf-8"))


def test_f86f_census_covers_four_frozen_cells_without_truncation():
    payload = _load("census.json")
    profiles = payload["profiles"]
    assert len(profiles) == 4
    assert {(row["sample_id"], row["cell"]) for row in profiles} == {
        (sample, cell) for sample in ("V4-3", "V5-3") for cell in ("ORTHO4_CURRENT", "FULL8_CURRENT")
    }
    assert payload["total_checked_position_count"] == 1593
    assert payload["total_candidate_position_count"] == 1593
    assert payload["total_checked_position_count"] <= 8192
    assert payload["any_truncation"] is False
    assert all(row["checked_position_count"] <= 2048 for row in profiles)
    assert all(row["truncation"] is False for row in profiles)


def test_f86f_geometric_and_engine_results_are_recorded_exactly():
    payload = _load("census.json")
    by_key = {(row["sample_id"], row["cell"]): row for row in payload["profiles"]}
    assert by_key[("V4-3", "ORTHO4_CURRENT")]["geometric_full_net_anchor_fraction"] == 5 / 16
    assert by_key[("V4-3", "ORTHO4_CURRENT")]["engine_validated_mate_exists"] is True
    assert by_key[("V4-3", "FULL8_CURRENT")]["geometric_full_net_anchor_fraction"] == 1 / 16
    assert by_key[("V4-3", "FULL8_CURRENT")]["engine_validated_mate_exists"] is False
    assert by_key[("V5-3", "ORTHO4_CURRENT")]["geometric_full_net_anchor_fraction"] == 7 / 25
    assert by_key[("V5-3", "ORTHO4_CURRENT")]["engine_validated_mate_exists"] is True
    assert by_key[("V5-3", "FULL8_CURRENT")]["geometric_full_net_anchor_fraction"] == 1 / 25
    assert by_key[("V5-3", "FULL8_CURRENT")]["engine_validated_mate_exists"] is True
    assert all(
        "full_material_validated_mate_position_count_by_attacker_count" in row
        and "minimum_validated_ordinary_attackers_distribution" not in row
        for row in by_key.values()
    )
    examples = _load("examples.json")["examples"]
    assert len(examples) == 9
    assert all(len(example["ordinary"]) == 3 for example in examples)


def test_f86f_scope_and_routing_are_fail_closed():
    payload = _load("census.json")
    assert payload["routing"]["labels"] == ["STRIPPED_ANCHOR_MATE_CAPACITY_EXISTS"]
    assert set(payload["routing"]["by_sample_cell"]) == {
        "V4-3:ORTHO4_CURRENT",
        "V4-3:FULL8_CURRENT",
        "V5-3:ORTHO4_CURRENT",
        "V5-3:FULL8_CURRENT",
    }
    assert payload["real_games"] == 0
    assert payload["teacher_search_compute"] == 0
    assert payload["f85_actual_compute"] == 0
    assert payload["default_generator_changed"] is False
    assert payload["no_ruleset_replacement"] is True


def test_f86f_canonical_examples_revalidate_through_core():
    examples = _load("examples.json")["examples"]
    selected = [
        next(example for example in examples if example["sample_id"] == "V4-3" and example["cell"] == "ORTHO4_CURRENT"),
        next(example for example in examples if example["sample_id"] == "V5-3" and example["cell"] == "FULL8_CURRENT"),
    ]
    for example in selected:
        if example["cell"] == "ORTHO4_CURRENT":
            payload = json.loads((ROOT / "artifacts/f86e_anchor_placement_ablation/counterfactual_rulesets.json").read_text(encoding="utf-8"))
            row = next(item for item in payload["rows"] if item["sample_id"] == example["sample_id"] and item["cell"] == example["cell"])
        else:
            payload = json.loads((ROOT / "artifacts/f86d_mobility_ablation/counterfactual_rulesets.json").read_text(encoding="utf-8"))
            row = next(item for item in payload["rows"] if item["sample_id"] == example["sample_id"] and item["profile"] == "A_FULL_ANCHOR")
        ruleset = ruleset_from_dict(row["ruleset"])
        compiled = compile_ruleset(ruleset)
        anchor_type = next(piece_type.type_id for piece_type in compiled.piece_types if piece_type.is_anchor)
        n = compiled.board_size
        board = [None] * (n * n)
        defender = example["defender_anchor"]
        attacker = example["attacker_anchor"]
        defender_index = defender[1] * n + defender[0]
        attacker_index = attacker[1] * n + attacker[0]
        board[defender_index] = Piece(1, anchor_type, anchor_type)
        board[attacker_index] = Piece(0, anchor_type, anchor_type)
        for ordinary in example["ordinary"]:
            square = ordinary["square"]
            board[square[1] * n + square[0]] = Piece(0, ordinary["type_id"], ordinary["type_id"])
        position = Position(
            board=tuple(board),
            hands=(Hands.empty(), Hands.empty()),
            side_to_move=1,
            ruleset_fingerprint=compiled.ruleset_fingerprint,
        )
        assert not is_in_check(position, 0, compiled)
        assert is_in_check(position, 1, compiled)
        assert not has_legal_action(position, compiled)
