"""Recompute the exact published pilot/V2C decomposition."""

import json
from fractions import Fraction
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_frozen_board_components_identify_what_first_action_service_added():
    pilot = json.loads((ROOT / "docs/research/data/first_action_service_chess_shogi_preref.json").read_text())
    v2c = json.loads((ROOT / ".generic_chess_flow/static-semantic-material-prior-v2c-board.json").read_text())
    assert not pilot["human_reference_imported"]
    assert not v2c["human_reference_imported"]
    ratios = {
        game: {
            piece: Fraction(raw) / Fraction(v2c["rulesets"][game]["ledger"][piece]["v2c_exact"])
            for piece, raw in data["raw_board_exact"].items()
        }
        for game, data in pilot["rulesets"].items()
    }
    assert ratios["western_chess"] == {
        "B": Fraction(1, 2),
        "N": 1,
        "P": Fraction(306183, 321404),
        "Q": 1,
        "R": 1,
    }
    assert len(ratios["standard_shogi"]) == 13
    assert set(ratios["standard_shogi"].values()) == {1}
