"""F50B2A semantic Native no-TT search contract."""

import pytest

from generic_chess.ai.cancellation import CancellationToken
from generic_chess.native import native_available
from generic_chess.native.compiler import compile_native_semantic_rules
from generic_chess.native.semantic import (
    fixed_depth_search,
    make_checked,
    pack_position,
    snapshot,
    public_action,
    semantic_iterative_search,
)
from generic_chess.rules.compiler import compile_semantic_ruleset
from generic_chess.rules.western_chess import build_western_chess_ruleset


def _initial():
    semantic = compile_semantic_ruleset(build_western_chess_ruleset())
    native = compile_native_semantic_rules(semantic)
    ids = {type_id: index for index, type_id in enumerate(native.type_ids)}
    board = [
        None if piece is None else [
            ids[piece.base_type_id], ids[piece.current_type_id],
            piece.owner, int(piece.promoted),
        ]
        for row in semantic.support.initial_position
        for piece in row
    ]
    position = pack_position(native, {
        "side": 0,
        "ply": 0,
        "board": board,
        "hands": [[0] * len(ids), [0] * len(ids)],
        "aux_state": (),
    })
    return semantic, native, position


@pytest.mark.skipif(not native_available(), reason="native extension unavailable")
def test_no_tt_iterative_matches_semantic_fixed_depth_and_pv():
    _semantic, native, position = _initial()
    fixed = fixed_depth_search(native, position, 2)
    result = semantic_iterative_search(native, position, 2)
    assert result["tt_status"] == "NOT_STARTED"
    assert result["completed_depth"] == 2
    assert result["score"] == fixed["score"]
    assert result["best_action"] == fixed["best_action"]
    assert result["principal_variation"] == fixed["principal_variation"]
    assert result["nodes"] >= result["completed_depth"]
    assert result["principal_variation"]
    assert public_action(native, result["best_action"])


@pytest.mark.skipif(not native_available(), reason="native extension unavailable")
@pytest.mark.parametrize("budget", [0, 1, 2, 16, 64, 500])
def test_node_budget_is_bounded_and_fallback_is_deterministic(budget):
    _semantic, native, position = _initial()
    first = semantic_iterative_search(native, position, 3, max_nodes=budget)
    second = semantic_iterative_search(native, position, 3, max_nodes=budget)
    volatile = {"elapsed_nanoseconds", "elapsed_seconds"}
    assert {key: value for key, value in first.items() if key not in volatile} == {
        key: value for key, value in second.items() if key not in volatile
    }
    assert first["nodes"] <= budget
    assert first["termination_reason"] in {"node_budget", "completed"}
    assert first["best_action"] is not None


@pytest.mark.skipif(not native_available(), reason="native extension unavailable")
def test_time_budget_and_pre_cancelled_search_fail_closed_with_root_fallback():
    _semantic, native, position = _initial()
    timed = semantic_iterative_search(native, position, 4, max_time_seconds=0.0)
    assert timed["termination_reason"] == "time_budget"
    assert timed["used_fallback"] is True
    assert timed["completed_depth"] == 0
    token = CancellationToken()
    token.cancel()
    cancelled = semantic_iterative_search(native, position, 4, cancel_token=token)
    assert cancelled["termination_reason"] == "cancelled"
    assert cancelled["used_fallback"] is True
    assert cancelled["completed_depth"] == 0


@pytest.mark.skipif(not native_available(), reason="native extension unavailable")
def test_evaluator_profiles_are_bound_per_search_without_ruleset_recompile():
    _semantic, native, position = _initial()
    zero = {type_id: 0 for type_id in native.type_ids}
    values = {type_id: index + 1 for index, type_id in enumerate(native.type_ids)}
    first = semantic_iterative_search(native, position, 1, board_values=zero, hand_values=zero)
    second = semantic_iterative_search(native, position, 1, board_values=values, hand_values=values)
    assert first["ruleset_fingerprint"] == second["ruleset_fingerprint"] == native.fingerprint
    assert first["evaluator_config_hash"] != second["evaluator_config_hash"]
    with pytest.raises(ValueError):
        semantic_iterative_search(native, position, 1, board_values=(0,), hand_values=(0,))


@pytest.mark.skipif(not native_available(), reason="native extension unavailable")
def test_search_preserves_root_and_pv_replays_through_semantic_runtime():
    _semantic, native, position = _initial()
    before = snapshot(native, position)
    result = semantic_iterative_search(native, position, 3)
    assert snapshot(native, position) == before
    replay = position
    for action in result["principal_variation"]:
        replay = make_checked(native, replay, action)
    assert len(result["principal_variation"]) <= result["completed_depth"]
    assert result["principal_variation"]
    assert snapshot(native, position) == before


@pytest.mark.skipif(not native_available(), reason="native extension unavailable")
def test_package_export_keeps_iterative_entrypoint_semantic_and_experimental():
    from generic_chess.native import iterative_search

    _semantic, native, position = _initial()
    assert iterative_search is semantic_iterative_search
    result = iterative_search(native, position, 1)
    assert result["tt_status"] == "NOT_STARTED"


@pytest.mark.skipif(not native_available(), reason="native extension unavailable")
def test_zero_depth_uses_safe_root_fallback_without_recursing_state():
    _semantic, native, position = _initial()
    before = snapshot(native, position)
    result = semantic_iterative_search(native, position, 0)
    assert result["completed_depth"] == 0
    assert result["used_fallback"] is True
    assert result["principal_variation"] == ()
    assert public_action(native, result["best_action"])
    assert snapshot(native, position) == before
