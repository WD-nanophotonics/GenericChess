import pytest

from generic_chess.core.semantic_executor import SemanticEngine
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.standard_shogi import build_standard_shogi_ruleset
from generic_chess.rules.western_chess import build_western_chess_ruleset

from scripts.rule_option_entropy_prior import choice_entropy, measure_piece


def test_option_entropy_is_maximum_entropy_of_uniform_action_choices():
    assert choice_entropy(0) == 0.0
    assert choice_entropy(1) == 1.0
    assert choice_entropy(3) == 2.0


def test_piece_ledger_is_read_from_the_executable_semantic_engine():
    compiled = compile_ruleset_for_execution(build_western_chess_ruleset())
    engine = SemanticEngine(compiled)
    ledger = measure_piece(compiled, engine, "N")

    assert ledger.type_id == "N"
    assert ledger.board_sample_count_per_owner == (62, 62)
    assert ledger.final_score_bits == ledger.board_mode_entropy_bits
    assert ledger.drop_owner_entropy_bits is None
    assert ledger.mean_quiet_actions > 0
    assert ledger.mean_capture_actions > 0


def test_shogi_hand_mode_and_promoted_type_use_rule_declared_states():
    compiled = compile_ruleset_for_execution(build_standard_shogi_ruleset())
    engine = SemanticEngine(compiled)

    base = measure_piece(compiled, engine, "P")
    promoted = measure_piece(compiled, engine, "TP")

    assert base.base_type_id == "P"
    assert base.drop_owner_entropy_bits is not None
    assert base.final_score_bits == pytest.approx(
        (base.board_mode_entropy_bits + sum(base.drop_owner_entropy_bits) / 2) / 2
    )
    assert promoted.base_type_id == "P"
    assert promoted.drop_owner_entropy_bits is None
