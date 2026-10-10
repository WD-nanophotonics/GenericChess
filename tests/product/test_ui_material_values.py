"""Human material policy is applied to real players without changing generic rules."""
from dataclasses import replace
import pytest

from generic_chess.ai.evaluation.config import EvaluationConfig
from generic_chess.ai.evaluation.evaluator import Evaluator
from generic_chess.ai.evaluation.profile import build_ruleset_profile
from generic_chess.core.pieces import Piece
from generic_chess.core.position import Hands
from generic_chess.rules.catalog import build_builtin_ruleset
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.serialization import serialize_ruleset, deserialize_ruleset
from generic_chess.ui.ai_backend import create_ui_player
from generic_chess.ui.controller import UIController
from generic_chess.ui.material_values import human_material_profile


@pytest.mark.parametrize("kind,expected", [
    ("western_chess", {"K":0,"P":1000,"N":3000,"B":3000,"R":5000,"Q":9000}),
    ("standard_shogi", {"K":0,"P":1000,"L":3000,"N":4000,"S":5000,"G":6000,
                        "B":8000,"R":10000,"TP":7000,"TL":6000,"TN":6000,"TS":6000,"TB":10000,"TR":12000})])
def test_player_uses_complete_fixed_table(kind, expected):
    compiled = compile_ruleset_for_execution(build_builtin_ruleset(kind))
    player = create_ui_player(compiled, use_disk_cache=False)
    profile = player.evaluation_profile
    assert dict(profile.board_value_by_type) == expected
    assert dict(profile.hand_value_by_base_type) == expected
    assert not player.use_native_semantic_legality
    assert profile.promotion_gain_by_type["P"] == (8000 if kind == "western_chess" else 6000)


@pytest.mark.parametrize("kind,tid,base,hand,expected", [
    ("western_chess", "Q", "P", None, 9000),
    ("standard_shogi", "TP", "P", "R", 17000),
    ("standard_shogi", "TR", "R", "P", 13000)])
def test_actual_evaluator_board_promotion_hands_and_perspective(kind, tid, base, hand, expected):
    ctrl = UIController()
    assert ctrl.new_game_from_builtin(kind)
    config = EvaluationConfig(dynamic_mobility_weight=0, anchor_escape_weight=0, promotion_potential_weight=0)
    profile = human_material_profile(ctrl.compiled, config)
    evaluator = Evaluator(ctrl.compiled, profile, config)
    board = [None] * len(ctrl.session.state.position.board)
    board[0] = Piece(owner=0, base_type_id=base, current_type_id=tid, promoted=base != tid)
    hands = (Hands(((hand, 1),)) if hand else Hands.empty(), Hands.empty())
    position = replace(ctrl.session.state.position, board=tuple(board), hands=hands, side_to_move=0)
    assert evaluator.evaluate(replace(ctrl.session.state, position=position)) == expected
    assert evaluator.evaluate(replace(ctrl.session.state, position=replace(position, side_to_move=1))) == -expected


@pytest.mark.parametrize("hybrid", [False, True])
def test_generated_prices_unchanged(hybrid):
    ctrl = UIController()
    assert ctrl.new_game(seed=42, hybrid=hybrid)
    player = create_ui_player(ctrl.compiled, use_disk_cache=False)
    original = build_ruleset_profile(ctrl.compiled, EvaluationConfig())
    assert player.evaluation_profile == original


@pytest.mark.parametrize("kind", ["western_chess", "standard_shogi"])
def test_import_identity_and_modified_rules(kind):
    rules = deserialize_ruleset(serialize_ruleset(build_builtin_ruleset(kind)))
    compiled = compile_ruleset_for_execution(rules)
    assert human_material_profile(compiled, EvaluationConfig()) is not None
    custom = compile_ruleset_for_execution(replace(rules, max_ply=rules.max_ply + 1))
    assert human_material_profile(custom, EvaluationConfig()) is None
    player = create_ui_player(custom, use_disk_cache=False)
    assert player.evaluation_profile == build_ruleset_profile(custom, EvaluationConfig())
