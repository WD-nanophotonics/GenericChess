"""F50B2A semantic Native no-TT search contract."""

from dataclasses import replace

import pytest

from generic_chess.ai.cancellation import CancellationToken
from generic_chess.native import native_available
from generic_chess.native.compiler import compile_native_semantic_rules
from generic_chess.native.semantic import (
    fixed_depth_search,
    guarded_actions,
    make_checked,
    pack_position,
    public_action,
    root_parallel_search,
    semantic_iterative_search,
    search_runtime_sizes,
    snapshot,
    terminal_status,
)
from generic_chess.rules.compiler import compile_semantic_ruleset
from generic_chess.rules.standard_shogi import build_standard_shogi_ruleset
from generic_chess.rules.western_chess import build_western_chess_ruleset


def _initial():
    semantic = compile_semantic_ruleset(build_western_chess_ruleset())
    native = compile_native_semantic_rules(semantic)
    return semantic, native, _pack_initial(semantic, native)


def _pack_initial(semantic, native, *, side=0, ply=0, history=None):
    ids = {type_id: index for index, type_id in enumerate(native.type_ids)}
    board = [
        None if piece is None else [
            ids[piece.base_type_id], ids[piece.current_type_id],
            piece.owner, int(piece.promoted),
        ]
        for row in semantic.support.initial_position
        for piece in row
    ]
    payload = {
        "side": side,
        "ply": ply,
        "board": board,
        "hands": [[0] * len(ids), [0] * len(ids)],
        "aux_state": (),
    }
    if history is not None:
        payload["history"] = [list(entry) for entry in history]
    return pack_position(native, payload)


def _declaration_free_shogi():
    semantic = compile_semantic_ruleset(
        replace(build_standard_shogi_ruleset(), declarations=())
    )
    native = compile_native_semantic_rules(semantic)
    return semantic, native


def _semantic_mate(king_file=2):
    """Return a standard-semantic-rule mate-in-one position."""
    n = 8
    semantic = compile_semantic_ruleset(build_western_chess_ruleset())
    native = compile_native_semantic_rules(semantic)
    ids = {type_id: index for index, type_id in enumerate(native.type_ids)}
    board = [None] * (n * n)
    for row, column, owner, type_id in (
        (0, 0, 1, "K"), (0, king_file, 0, "K"),
        (4, 1, 0, "R"), (1, 5, 0, "R"),
    ):
        index = row * n + column
        board[index] = [ids[type_id], ids[type_id], owner, 0]
    position = pack_position(native, {
        "side": 0, "ply": 0, "board": board,
        "hands": [[0] * len(ids), [0] * len(ids)], "aux_state": (),
    })
    return semantic, native, position


def _continuous_history(native, position, checker):
    words = snapshot(native, position)["history"][0]
    return (
        (*words, 255, 0),
        (*words, checker, 1),
        (*words, 1 - checker, 0),
        (*words, checker, 1),
    )


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


@pytest.mark.skipif(not native_available(), reason="native extension unavailable")
@pytest.mark.parametrize(
    "checker,side,sign", ((0, 0, -1), (0, 1, 1), (1, 0, 1), (1, 1, -1))
)
def test_continuous_check_winner_is_scored_for_both_owners(checker, side, sign):
    semantic, native = _declaration_free_shogi()
    fresh = _pack_initial(semantic, native, side=side)
    position = _pack_initial(
        semantic, native, side=side,
        history=_continuous_history(native, fresh, checker),
    )
    assert terminal_status(native, position) == {
        "status": "perpetual_check", "winner": 1 - checker,
    }
    result = semantic_iterative_search(native, position, 1)
    assert result["score"] * sign > 0
    assert result["best_action"] is None
    assert result["principal_variation"] == ()


@pytest.mark.skipif(not native_available(), reason="native extension unavailable")
def test_repetition_and_no_contest_terminal_scores_are_neutral():
    semantic, native = _declaration_free_shogi()
    fresh = _pack_initial(semantic, native)
    words = snapshot(native, fresh)["history"][0]
    repetition = _pack_initial(semantic, native, history=(
        (*words, 255, 0), (*words, 0, 0), (*words, 1, 0), (*words, 0, 0),
    ))
    assert terminal_status(native, repetition)["status"] == "repetition"
    assert semantic_iterative_search(native, repetition, 1)["score"] == 0
    history = [(1, 2, 3, 4, 255, 0)]
    history.extend(
        (index + 10, index + 20, index + 30, index + 40, index % 2, 0)
        for index in range(1, 501)
    )
    no_contest = _pack_initial(semantic, native, ply=500, history=history)
    assert terminal_status(native, no_contest)["status"] == "no_contest"
    result = semantic_iterative_search(native, no_contest, 1)
    assert result["score"] == 0
    assert result["best_action"] is None


@pytest.mark.skipif(not native_available(), reason="native extension unavailable")
def test_declaration_bearing_rulesets_fail_closed_but_shogi_without_them_executes():
    semantic = compile_semantic_ruleset(build_standard_shogi_ruleset())
    native = compile_native_semantic_rules(semantic)
    with pytest.raises(ValueError, match="declaration-bearing rulesets"):
        semantic_iterative_search(native, _pack_initial(semantic, native), 1)
    clear_semantic, clear_native = _declaration_free_shogi()
    result = semantic_iterative_search(
        clear_native, _pack_initial(clear_semantic, clear_native), 1
    )
    assert result["best_action"] is not None


@pytest.mark.skipif(not native_available(), reason="native extension unavailable")
def test_runtime_size_measurement_exposes_copy_pressure_without_legacy_aliasing():
    sizes = search_runtime_sizes()
    assert sizes["position_bytes"] > 50_000
    assert sizes["undo_bytes"] >= sizes["position_bytes"]
    assert sizes["max_ply"] >= 1_000


@pytest.mark.skipif(not native_available(), reason="native extension unavailable")
def test_experimental_root_parallel_search_matches_one_position_reference():
    _semantic, native, position = _initial()
    before = snapshot(native, position)
    reference = semantic_iterative_search(native, position, 2)
    parallel = root_parallel_search(native, position, 2, workers=4)
    assert parallel["mode"] == "ROOT_PARALLEL_EXPERIMENTAL"
    assert (parallel["score"], parallel["best_action"], parallel["principal_variation"]) == (
        reference["score"], reference["best_action"], reference["principal_variation"],
    )
    assert snapshot(native, position) == before


@pytest.mark.skipif(not native_available(), reason="native extension unavailable")
def test_root_parallel_preserves_mate_in_one_score_and_state():
    semantic, native, position = _semantic_mate()
    before = snapshot(native, position)
    reference = semantic_iterative_search(native, position, 2)
    assert reference["score"] == 99_999_999
    assert reference["principal_variation"]
    for workers in (1, 2, 4):
        parallel = root_parallel_search(native, position, 2, workers=workers)
        assert (parallel["score"], parallel["best_action"], parallel["principal_variation"]) == (
            reference["score"], reference["best_action"], reference["principal_variation"],
        )
    assert snapshot(native, position) == before


@pytest.mark.skipif(not native_available(), reason="native extension unavailable")
def test_root_parallel_preserves_deeper_terminal_score_parity():
    semantic, native, position = _semantic_mate()
    first_action = min(action for action in guarded_actions(native, position)
                       if terminal_status(native, make_checked(native, position, action))["status"] == "ongoing")
    child = make_checked(native, position, first_action)
    reference = semantic_iterative_search(native, child, 2)
    assert len(reference["principal_variation"]) >= 2
    parallel = root_parallel_search(native, child, 2, workers=4)
    assert (parallel["score"], parallel["best_action"], parallel["principal_variation"]) == (
        reference["score"], reference["best_action"], reference["principal_variation"],
    )
