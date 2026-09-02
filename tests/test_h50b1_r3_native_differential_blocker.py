"""Regression coverage for the H50B1-R3 Native promotion correction."""

import pytest

from generic_chess.core.semantic_executor import semantic_engine_for, semantic_public_actions
from generic_chess.learning.shogi_rules import sfen_to_gc_state
from generic_chess.native.compiler import compile_native_semantic_rules
from generic_chess.native import native_available
from generic_chess.native.semantic import make_checked
from scripts.audit_f13_native_action_delivers_check import certified_semantic_shogi
from scripts.audit_h50b1_r3_native_differential import _native_position, _same_public_actions


@pytest.mark.skipif(not native_available(), reason="native extension unavailable")
def test_h50b1_r4_promoted_piece_public_action_identity_is_closed():
    compiled = certified_semantic_shogi()
    native_rules = compile_native_semantic_rules(compiled)
    position = sfen_to_gc_state(compiled, "8k/7+P1/9/9/9/9/9/9/4K4 b - 1").position
    native_position = _native_position(native_rules, position)
    engine = semantic_engine_for(compiled)

    python_actions, native_raw = _same_public_actions(
        engine, compiled, native_rules, position, native_position
    )
    assert all(action.promotion_target_id is None for action in python_actions)
    assert all(
        ((raw >> 16) & 0xFF) == 0xFF
        for raw in native_raw
        if ((raw >> 8) & 0xFF) == 64
    )
    next(action for action in python_actions if action.to_square.rank == 8)
    raw = next(
        raw for raw in native_raw
        if ((raw >> 8) & 0xFF) == 64 and (raw & 0xFF) == 73
    )
    assert make_checked(native_rules, native_position, raw)
    tp_index = native_rules.type_ids.index("TP")
    forged = (raw & ~(0xFF << 16)) | (tp_index << 16)
    with pytest.raises(ValueError, match="not valid|illegal|invalid|rejected"):
        make_checked(native_rules, native_position, forged)
