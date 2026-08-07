"""Rule-semantics architecture boundary tests (Phase 1.9A-1).

These tests lock the *current* ownership boundaries so a future Rule IR
phase cannot silently cross them: session/UI/learning never own legality,
attack never depends on full legal move generation, terminal uses the
first-legal scan, the action model is single-source/single-destination,
and the native hot path has no Python runtime callbacks.
"""

from pathlib import Path

import pytest

from generic_chess.core.actions import BoardMove, DropMove
from generic_chess.core.coordinates import Square
from generic_chess.core.keys import position_key
from generic_chess.core.position import Hands, Position
from generic_chess.core.pieces import Piece
from generic_chess.rules.compiled import CompiledRuleSet
from generic_chess.rules.schema import RuleSet


ROOT = Path(__file__).resolve().parent.parent
PKG = ROOT / "generic_chess"
NATIVE_C = PKG / "_native"


def _read(rel: str) -> str:
    return (PKG / rel).read_text(encoding="utf-8", errors="ignore")


def test_session_imports_only_core_public_semantics():
    source = _read("session/session.py")
    for forbidden in ("native", "ai.", "learning", "rules.compiler", "rules.schema"):
        assert forbidden not in source, f"session imports forbidden layer: {forbidden}"
    for required in ("legal_actions", "apply_action", "initial_state", "position_key"):
        assert required in source


def test_generator_does_not_import_native_or_search():
    for path in (PKG / "generation").rglob("*.py"):
        source = path.read_text(encoding="utf-8", errors="ignore")
        for forbidden in ("native", "ai.search", "ai.engine", "_native"):
            assert forbidden not in source, f"{path.name} imports {forbidden}"


def test_native_headers_have_no_game_name_symbols():
    tokens = (
        "PAWN",
        "SHOGI",
        "XIANGQI",
        "CANNON",
        "NIFU",
        "CASTL",
        "EN_PASSANT",
        "UCHIFUZUME",
        "ROOK",
        "BISHOP",
    )
    for path in NATIVE_C.glob("*.h"):
        source = path.read_text(encoding="utf-8", errors="ignore")
        for token in tokens:
            assert token not in source, f"{path.name} contains game token {token}"


def test_no_python_runtime_call_in_native_c():
    markers = ("PyObject_Call", "PyEval_", "PyCallable")
    for path in NATIVE_C.glob("*.c"):
        source = path.read_text(encoding="utf-8", errors="ignore")
        for marker in markers:
            assert marker not in source, f"{path.name} contains {marker}"


def test_compiled_ruleset_is_frozen_derived_no_runtime_state():
    import dataclasses

    assert dataclasses.is_dataclass(CompiledRuleSet)
    assert CompiledRuleSet.__dataclass_params__.frozen is True
    fields = {f.name for f in dataclasses.fields(CompiledRuleSet)}
    runtime_state = {"side_to_move", "hands", "ply", "history", "repetition_counts"}
    assert not (fields & runtime_state)
    expected = {
        "ruleset_fingerprint",
        "board_size",
        "piece_types",
        "types_by_id",
        "initial_position",
        "initial_entity_count",
        "leap_targets",
        "ray_paths",
        "empty_mobility",
        "empty_forward_mobility",
        "drop_allowed",
        "promotion_allowed",
        "promotion_forced",
        "repetition_limit",
        "max_ply",
        "stalemate_result",
    }
    assert fields == expected


def test_rule_schema_field_set_is_frozen():
    import dataclasses

    fields = {f.name for f in dataclasses.fields(RuleSet)}
    assert fields == {
        "schema_version",
        "board_size",
        "piece_types",
        "initial_position",
        "drop_allowed",
        "promotion_allowed",
        "promotion_forced",
        "repetition_limit",
        "max_ply",
        "stalemate_result",
        "semantic_actions",  # additive Phase 1.9B-1 high-level DSL (legacy empty)
        "semantic_dsl_version",  # Phase 1.9B-1.5 explicit DSL version axis
        "metadata",
    }


def test_attack_never_depends_on_legal_move_generation():
    attacks = _read("core/attacks.py")
    assert "legal_actions_from_position" not in attacks
    assert "movegen" not in attacks
    movegen = _read("core/movegen.py")
    assert "attacks" in movegen  # legal depends on attack, not the reverse


def test_terminal_uses_first_legal_scan_not_full_legal_actions():
    terminal = _read("core/terminal.py")
    assert "has_legal_action" in terminal
    assert "legal_actions_from_position" not in terminal


def test_position_key_identity_includes_semantic_fields():
    from generic_chess.rules.compiler import compile_ruleset
    from generic_chess.rules.schema import RuleSet
    from generic_chess.core.pieces import PieceType
    from generic_chess.core.movement import LeapAtom

    n = 4
    king = PieceType("K", "K", (LeapAtom((1, 0)),), is_anchor=True)
    rows = []
    for rank in range(n):
        row = []
        for file in range(n):
            if (rank, file) == (0, 0):
                row.append(Piece(0, "K", "K"))
            elif (rank, file) == (n - 1, n - 1):
                row.append(Piece(1, "K", "K"))
            else:
                row.append(None)
        rows.append(tuple(row))
    ruleset = RuleSet(
        board_size=n,
        piece_types=(king,),
        initial_position=tuple(rows),
    )
    compiled = compile_ruleset(ruleset)
    empty = tuple(None for _ in range(n * n))
    p0 = Position(
        board=empty,
        hands=(Hands.empty(), Hands.empty()),
        side_to_move=0,
        ruleset_fingerprint=compiled.ruleset_fingerprint,
    )
    p1 = Position(
        board=empty,
        hands=(Hands.empty(), Hands.empty()),
        side_to_move=1,
        ruleset_fingerprint=compiled.ruleset_fingerprint,
    )
    with_hand = Position(
        board=empty,
        hands=(Hands((("P", 1),)), Hands.empty()),
        side_to_move=0,
        ruleset_fingerprint=compiled.ruleset_fingerprint,
    )
    assert position_key(p0, compiled) == position_key(p0, compiled)
    assert position_key(p0, compiled) != position_key(p1, compiled)
    assert position_key(p0, compiled) != position_key(with_hand, compiled)


def test_action_model_is_single_source_single_destination():
    move = BoardMove(Square(1, 1), Square(1, 2))
    assert move.promotion_target_id is None
    assert move.from_square == Square(1, 1)
    assert move.to_square == Square(1, 2)
    drop = DropMove("P", Square(2, 2))
    assert drop.base_type_id == "P"
    # The current model has exactly one destination and no off-target
    # capture field (documented constraint for the Rule IR phase).
    assert set(BoardMove.__dataclass_fields__) == {
        "from_square",
        "to_square",
        "promotion_target_id",
    }
    assert set(DropMove.__dataclass_fields__) == {"base_type_id", "to_square"}
