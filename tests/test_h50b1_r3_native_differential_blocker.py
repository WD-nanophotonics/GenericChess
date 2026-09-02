"""Regression detector for the H50B1-R3 Native promotion blocker."""

import pytest

from generic_chess.core.semantic_executor import semantic_engine_for
from generic_chess.learning.shogi_rules import sfen_to_gc_state
from generic_chess.native.compiler import compile_native_semantic_rules
from generic_chess.native import native_available
from scripts.audit_f13_native_action_delivers_check import certified_semantic_shogi
from scripts.audit_h50b1_r3_native_differential import _native_position, _same_public_actions


@pytest.mark.skipif(not native_available(), reason="native extension unavailable")
def test_h50b1_r3_promoted_piece_public_action_identity_is_blocked():
    compiled = certified_semantic_shogi()
    native_rules = compile_native_semantic_rules(compiled)
    position = sfen_to_gc_state(
        compiled, "8k/7+P1/9/9/9/9/9/9/4K4 b - 1"
    ).position
    native_position = _native_position(native_rules, position)
    engine = semantic_engine_for(compiled)

    with pytest.raises(AssertionError, match="public action identity differs"):
        _same_public_actions(
            engine, compiled, native_rules, position, native_position
        )
