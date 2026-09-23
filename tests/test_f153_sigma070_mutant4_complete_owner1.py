import ast
import json
from pathlib import Path

from scripts import f153_sigma070_mutant4_complete_owner1 as owner1
from scripts import f149_shogi_material_score_race_deep_openings as race
from tools.generic_chess_flow import _validate_resource_envelope


ROOT = Path(owner1.__file__).resolve().parents[1]
ENVELOPE = ROOT / ".generic_chess_flow/compute-plans/f153-sigma070-mutant4-complete-owner1-envelope.json"


def test_one_game_envelope_is_exactly_derived_from_saved_opening():
    envelope = json.loads(ENVELOPE.read_text(encoding="utf-8"))
    _validate_resource_envelope(envelope)
    assert owner1.MAX_GAMES_NEW == envelope["maximum_games"] == 1
    assert owner1.MAX_CONCURRENT_GAMES == envelope["maximum_concurrent_games"] == 1
    assert owner1.OPENING_PLIES == envelope["opening_plies"] == 21
    assert owner1.MAX_TOTAL_PLIES == envelope["maximum_total_plies_including_opening"] == 128
    assert owner1.MAX_SEARCHED_PLIES == envelope["maximum_searched_plies"] == 107
    assert owner1.MAX_NODES_PER_MOVE == envelope["nodes_per_move"] == 1000
    assert owner1.MAX_NODES == envelope["maximum_nodes"] == 107_000
    assert owner1.MAX_GAME_SECONDS == envelope["maximum_game_wall_seconds"] == 420
    assert envelope["external_hard_wall_seconds"] == 420


def test_saved_owner0_evidence_hash_and_semantic_replay_are_exact():
    if not owner1.HISTORICAL_GAME_PATH.is_file():
        import pytest
        pytest.skip("ignored Heavy evidence is only available in the active workspace")
    raw, normalized = owner1._load_owner0()
    assert normalized["source_sha256"] == owner1.HISTORICAL_GAME_SHA256
    assert raw["terminal_cause"] == "repetition"
    assert normalized["scores"] == [0, 0]
    assert normalized["decisive_reason"] == "score_draw"
    assert normalized["valid"] is True
    assert normalized["winner"] is None
    assert normalized["child_game_score"] == 0.5
    assert race.v2.pair_score([normalized]) is None
    assert race.v2.pair_score([normalized, dict(normalized)]) is None


def test_pair_classification_requires_the_real_distinct_owner1_result():
    owner0 = {
        "child_owner": 0, "winner": None, "decisive_reason": "score_draw", "valid": True,
        "mutant4_points": 0, "gen0_points": 0, "child_game_score": 0.5,
    }
    owner1_draw = {"child_owner": 1, "winner": None, "decisive_reason": "score_draw", "valid": True}
    owner1_win = {"child_owner": 1, "winner": 1, "decisive_reason": "score_tiebreak", "valid": True}
    owner1_loss = {"child_owner": 1, "winner": 0, "decisive_reason": "score_tiebreak", "valid": True}
    assert owner1._classify(owner0, owner1_draw) == ("FRESH_PAIR_MUTANT4_TIED", 0.5)
    assert owner1._classify(owner0, owner1_win) == ("FRESH_PAIR_MUTANT4_POSITIVE_SIGNAL", 0.75)
    assert owner1._classify(owner0, owner1_loss) == ("FRESH_PAIR_MUTANT4_NEGATIVE_SIGNAL", 0.25)
    assert owner1._classify(owner0, dict(owner1_draw, valid=False)) == (
        "FRESH_PAIR_MUTANT4_INCONCLUSIVE", None
    )


def test_runner_starts_only_owner1_and_has_no_opening_search_or_retry_loop():
    tree = ast.parse(Path(owner1.__file__).read_text(encoding="utf-8"))
    calls = {
        node.func.id if isinstance(node.func, ast.Name)
        else node.func.attr if isinstance(node.func, ast.Attribute)
        else ""
        for node in ast.walk(tree) if isinstance(node, ast.Call)
    }
    assert owner1.ROLE_OWNER == 1
    assert owner1.OPENING_ID == "7e04681975c54713539109e629d64d568aebf72547382db2f04faf53a920bda9"
    assert "play_capped_game" in calls
    assert "ProcessPoolExecutor" not in calls
    assert not any(isinstance(node, ast.While) for node in ast.walk(tree))
    assert "range" not in calls
