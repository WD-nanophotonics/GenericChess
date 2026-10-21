"""Accepted evaluator profiles must not outrank rule wins in fixed/probe search."""
import pytest

from native_test_helpers import requires_native
from generic_chess.native import _module
from generic_chess.native.compiler import NativeUnsupportedRuleError
from generic_chess.native.semantic import (probe_search, fixed_depth_search,
    semantic_iterative_search, snapshot, make_checked, terminal_status, pack_position)
from generic_chess.core.position import Hands, Position
from generic_chess.core.pieces import Piece
from generic_chess.core.semantic_executor import SemanticEngine
from test_h50b2a_semantic_native_search import _semantic_mate
from test_native_semantic_probe_search import _packed_actions

pytestmark = requires_native


@pytest.mark.parametrize("entry", [probe_search, fixed_depth_search])
@pytest.mark.parametrize("rook_value", [-1_000_000, 1_000_000])
def test_accepted_large_profiles_choose_core_verified_mate(entry, rook_value):
    semantic, native, packed = _semantic_mate()
    before = snapshot(native, packed)
    position = Position(tuple(None if p is None else Piece(p[2],
        native.type_ids[p[0]], native.type_ids[p[1]], bool(p[3]))
        for p in before["board"]), (Hands.empty(), Hands.empty()),
        before["side"], semantic.support.ruleset_fingerprint)
    engine = SemanticEngine(semantic)
    legal = _packed_actions(semantic, position, native)
    winning = {raw for raw, action in legal.items()
        if engine.terminal_result(engine.apply(position, action), 1, ()).winner == 0}
    assert winning
    values = {tid: rook_value if tid == "R" else 0 for tid in native.type_ids}
    result = entry(native, packed, 1, board_values=values, hand_values=values)
    assert result["score"] == 100_000_000
    assert result["best_action"] == min(winning)
    assert result["principal_variation"] == (result["best_action"],)
    child = make_checked(native, packed, result["best_action"])
    assert terminal_status(native, child) == {"status": "checkmate", "winner": 0}
    terminal = entry(native, child, 0, board_values=values, hand_values=values)
    assert terminal["score"] == -100_000_000
    assert terminal["best_action"] is None and terminal["principal_variation"] == ()
    assert snapshot(native, packed) == before


@pytest.mark.parametrize("entry", [probe_search, fixed_depth_search])
@pytest.mark.parametrize("sign", [-1, 1])
def test_large_hand_ordinary_scores_keep_existing_saturation(entry, sign):
    from rule_semantics_ir_fixtures import nifu_ruleset
    from generic_chess.rules.compiler import compile_semantic_ruleset
    from generic_chess.native.compiler import compile_native_semantic_rules
    semantic = compile_semantic_ruleset(nifu_ruleset())
    native = compile_native_semantic_rules(semantic)
    ids = {tid: i for i, tid in enumerate(native.type_ids)}
    board = [None if p is None else [ids[p.base_type_id], ids[p.current_type_id],
        p.owner, int(p.promoted)] for row in semantic.support.initial_position for p in row]
    hands = [[0] * len(ids) for _ in range(2)]
    hands[0][ids["P"]] = 100
    packed = pack_position(native, {"side": 0, "ply": 0, "board": board,
        "hands": hands, "aux_state": ()})
    before = snapshot(native, packed)
    values = {tid: sign * 1_000_000 if tid == "P" else 0 for tid in ids}
    assert terminal_status(native, packed)["status"] == "ongoing"
    result = entry(native, packed, 0, board_values=values, hand_values=values)
    assert result["score"] == sign * 90_000_000
    assert result["best_action"] is None
    assert snapshot(native, packed) == before


@pytest.mark.parametrize("entry", [probe_search, fixed_depth_search])
def test_stale_fixed_probe_kernel_is_explicitly_rejected(entry, monkeypatch):
    _semantic, native, packed = _semantic_mate()
    kernel = _module()
    caps = kernel.native_capabilities()
    monkeypatch.setattr(kernel, "native_capabilities", lambda: {k: v
        for k, v in caps.items() if k != "semantic_fixed_depth_terminal_dominance"})
    with pytest.raises(NativeUnsupportedRuleError, match="terminal score band"):
        entry(native, packed, 1)
    # The already-correct production path does not require this compatibility fix.
    assert semantic_iterative_search(native, packed, 1)["score"] == 99_999_999
