"""F25 product-surface and historical-parity contracts for Standard Shogi."""

from __future__ import annotations

import json
import subprocess
import sys
import uuid
from pathlib import Path

from generic_chess import (
    build_builtin_ruleset,
    build_standard_shogi_ruleset,
    compile_ruleset_for_execution,
    builtin_ruleset_names,
)
from generic_chess.ai.alphabeta.player import AlphaBetaPlayer
from generic_chess.ai.limits import SearchLimits
from generic_chess.cli.play import _resolve_action_input
from generic_chess.rules.compiler import compile_semantic_ruleset
from generic_chess.rules.schema import compute_fingerprint, ruleset_to_dict
from generic_chess.rules.serialization import deserialize_ruleset, serialize_ruleset
from generic_chess.session.serialization import deserialize_game_record, serialize_game_record
from generic_chess.session.session import GameSession


ROOT = Path(__file__).resolve().parents[2]


def test_product_builder_matches_historical_semantic_gameplay_fields():
    from generic_chess.learning.shogi_semantic_rules import build_semantic_shogi_ruleset

    product = build_standard_shogi_ruleset()
    historical = build_semantic_shogi_ruleset()
    product_data = ruleset_to_dict(product, include_metadata=False)
    historical_data = ruleset_to_dict(historical, include_metadata=False)
    assert {
        key: value
        for key, value in product_data.items()
        if key not in {"declarations", "automatic_adjudications"}
    } == historical_data
    assert compute_fingerprint(historical) == "5b3d04eda31a342b729fc9af8a04cdde13c796646b2b37024891f8c99703c345"
    assert compute_fingerprint(product) == "ac987c3ffe75d8fa885ba787c1aa7cf60e92205465bf056b12b2989674007635"
    assert product.metadata["nyugyoku_supported"] is True
    assert product.metadata["move_500_no_contest_supported"] is True
    assert product.automatic_adjudications[0].trigger_ply == 500


def test_catalog_contains_exact_productized_builtins():
    assert builtin_ruleset_names() == ("western_chess", "standard_shogi")
    assert build_builtin_ruleset("standard_shogi") == build_standard_shogi_ruleset()


def test_raw_semantic_and_execution_dispatcher_have_same_initial_behavior():
    product = build_standard_shogi_ruleset()
    raw = compile_semantic_ruleset(product)
    dispatched = compile_ruleset_for_execution(product)
    from generic_chess.core.semantic_executor import semantic_engine_for

    raw_engine = semantic_engine_for(raw)
    dispatched_engine = semantic_engine_for(dispatched)
    raw_position = raw_engine._initial_position()
    dispatched_position = dispatched_engine._initial_position()
    assert raw.ruleset_fingerprint == dispatched.ruleset_fingerprint
    assert raw_engine.legal_actions(raw_position) == dispatched_engine.legal_actions(dispatched_position)
    assert raw_engine.terminal_result(raw_position, 0, ()) == dispatched_engine.terminal_result(dispatched_position, 0, ())


def test_product_curated_contracts_match_historical_semantic_authority():
    from generic_chess.learning.shogi_rules import curated_parity_cases, sfen_to_gc_state

    product = compile_ruleset_for_execution(build_standard_shogi_ruleset())
    historical = compile_semantic_ruleset(
        __import__(
            "generic_chess.learning.shogi_semantic_rules",
            fromlist=["build_semantic_shogi_ruleset"],
        ).build_semantic_shogi_ruleset()
    )
    for case in curated_parity_cases():
        product_state = sfen_to_gc_state(product, case["sfen"])
        historical_state = sfen_to_gc_state(historical, case["sfen"])
        from generic_chess.core.movegen import legal_actions

        assert {str(a) for a in legal_actions(product_state, product)} == {
            str(a) for a in legal_actions(historical_state, historical)
        }, case["id"]


def test_capturing_promoted_piece_demotes_to_base_hand_and_can_be_dropped():
    from generic_chess.core.actions import action_is_board, action_is_drop
    from generic_chess.core.coordinates import Square
    from generic_chess.core.movegen import legal_actions
    from generic_chess.core.pieces import Piece
    from generic_chess.core.position import GameState, HistoryRecord
    from generic_chess.core.search_runtime import SearchPathRuntime
    from generic_chess.core.transition import apply_action
    from generic_chess.learning.shogi_rules import sfen_to_gc_state

    compiled = compile_ruleset_for_execution(build_standard_shogi_ruleset())
    state = sfen_to_gc_state(compiled, "8k/9/9/4+p4/4P4/9/9/9/K8 b - 1")
    root_key = state.repetition_counts[0][0]
    state = GameState(
        position=state.position,
        ply_count=state.ply_count,
        repetition_counts=state.repetition_counts,
        terminal_status=state.terminal_status,
        history=(HistoryRecord(root_key, -1, "", False),),
    )
    capture = next(
        action
        for action in legal_actions(state, compiled)
        if action_is_board(action)
        and action.from_square == Square(4, 4)
        and action.to_square == Square(4, 5)
    )
    victim_square = 5 * 9 + 4
    source_square = 4 * 9 + 4
    victim = state.position.board[victim_square]
    assert victim is not None
    assert (victim.base_type_id, victim.current_type_id, victim.promoted) == (
        "P", "TP", True
    )

    runtime = SearchPathRuntime.from_state(state, compiled)
    public_actions = frozenset(legal_actions(state, compiled))
    before_actions = frozenset(runtime.legal_actions())
    assert before_actions == public_actions
    before = (
        runtime.position,
        runtime.ply_count,
        runtime.terminal_status,
        tuple(runtime.history),
        runtime.repetition_counts,
        runtime.runtime_hash,
        runtime._history_context,
        runtime.search_key(),
        runtime._history_complete,
        runtime.history_witness_misses,
        before_actions,
    )
    capture_child = apply_action(state, capture, compiled)
    runtime.push(capture)
    assert runtime.position == capture_child.position
    assert runtime.position.board[source_square] is None
    assert runtime.position.board[victim_square] == Piece(0, "P", "P")
    assert runtime.position.hands[0] == state.position.hands[0].add("P")
    assert runtime.position.hands[0].count("TP") == state.position.hands[0].count("TP")
    assert runtime.position.hands[1] == state.position.hands[1]
    assert runtime.position.side_to_move == 1
    assert runtime.ply_count == state.ply_count + 1
    assert runtime.position.aux_state == state.position.aux_state
    assert all(
        runtime.position.board[index] == state.position.board[index]
        for index in range(len(state.position.board))
        if index not in (source_square, victim_square)
    )
    assert not any(
        action_is_drop(action)
        for action in legal_actions(capture_child, compiled)
    )
    runtime.pop()
    runtime.assert_balanced()
    after = (
        runtime.position,
        runtime.ply_count,
        runtime.terminal_status,
        tuple(runtime.history),
        runtime.repetition_counts,
        runtime.runtime_hash,
        runtime._history_context,
        runtime.search_key(),
        runtime._history_complete,
        runtime.history_witness_misses,
        frozenset(runtime.legal_actions()),
    )
    assert after == before

    state = capture_child
    assert state.position.hands[0].count("P") == 1
    assert state.position.hands[0].count("TP") == 0

    reply = next(
        action for action in legal_actions(state, compiled) if action_is_board(action)
    )
    state = apply_action(state, reply, compiled)
    drop = next(
        action
        for action in legal_actions(state, compiled)
        if action_is_drop(action) and action.base_type_id == "P"
    )
    drop_target = drop.to_square.rank * 9 + drop.to_square.file
    assert state.position.board[drop_target] is None
    runtime = SearchPathRuntime.from_state(state, compiled)
    public_actions = frozenset(legal_actions(state, compiled))
    before_actions = frozenset(runtime.legal_actions())
    assert before_actions == public_actions
    before = (
        runtime.position,
        runtime.ply_count,
        runtime.terminal_status,
        tuple(runtime.history),
        runtime.repetition_counts,
        runtime.runtime_hash,
        runtime._history_context,
        runtime.search_key(),
        runtime._history_complete,
        runtime.history_witness_misses,
        before_actions,
    )
    drop_child = apply_action(state, drop, compiled)
    runtime.push(drop)
    assert runtime.position == drop_child.position
    assert runtime.position.hands[0] == state.position.hands[0].remove("P")
    assert runtime.position.hands[1] == state.position.hands[1]
    placed_by_runtime = runtime.position.board[drop_target]
    assert placed_by_runtime is not None
    assert (
        placed_by_runtime.owner,
        placed_by_runtime.base_type_id,
        placed_by_runtime.current_type_id,
        placed_by_runtime.promoted,
    ) == (0, "P", "P", False)
    assert all(
        runtime.position.board[index] == state.position.board[index]
        for index in range(len(state.position.board))
        if index != drop_target
    )
    assert runtime.position.side_to_move == 1
    assert runtime.ply_count == state.ply_count + 1
    assert runtime.position.aux_state == state.position.aux_state
    runtime.pop()
    runtime.assert_balanced()
    after = (
        runtime.position,
        runtime.ply_count,
        runtime.terminal_status,
        tuple(runtime.history),
        runtime.repetition_counts,
        runtime.runtime_hash,
        runtime._history_context,
        runtime.search_key(),
        runtime._history_complete,
        runtime.history_witness_misses,
        frozenset(runtime.legal_actions()),
    )
    assert after == before

    state = drop_child

    assert state.position.hands[0].count("P") == 0
    placed = state.position.board[drop.to_square.rank * 9 + drop.to_square.file]
    assert placed is not None
    assert (placed.base_type_id, placed.current_type_id, placed.promoted) == (
        "P", "P", False
    )


def test_product_shogi_optional_and_forced_promotion_actions():
    from generic_chess.core.actions import action_is_board
    from generic_chess.core.coordinates import Square
    from generic_chess.core.movegen import legal_actions
    from generic_chess.core.transition import apply_action
    from generic_chess.learning.shogi_rules import sfen_to_gc_state

    compiled = compile_ruleset_for_execution(build_standard_shogi_ruleset())
    optional_state = sfen_to_gc_state(
        compiled, "8k/9/9/4P4/9/9/9/9/K8 b - 1"
    )
    optional_moves = [
        action
        for action in legal_actions(optional_state, compiled)
        if action_is_board(action)
        and action.from_square == Square(4, 5)
        and action.to_square == Square(4, 6)
    ]
    assert {action.promotion_target_id for action in optional_moves} == {None, "TP"}
    promoted_state = apply_action(
        optional_state,
        next(action for action in optional_moves if action.promotion_target_id == "TP"),
        compiled,
    )
    promoted_piece = promoted_state.position.board[6 * 9 + 4]
    assert promoted_piece is not None
    assert (
        promoted_piece.base_type_id,
        promoted_piece.current_type_id,
        promoted_piece.promoted,
    ) == ("P", "TP", True)

    forced_state = sfen_to_gc_state(
        compiled, "8k/4P4/9/9/9/9/9/9/K8 b - 1"
    )
    forced_moves = [
        action
        for action in legal_actions(forced_state, compiled)
        if action_is_board(action)
        and action.from_square == Square(4, 7)
        and action.to_square == Square(4, 8)
    ]
    assert {action.promotion_target_id for action in forced_moves} == {"TP"}


def test_standard_shogi_optional_promotion_runtime_push_pop_roundtrip():
    from generic_chess.core.actions import action_is_board
    from generic_chess.core.coordinates import Square
    from generic_chess.core.movegen import legal_actions
    from generic_chess.core.position import GameState, HistoryRecord
    from generic_chess.core.search_runtime import SearchPathRuntime
    from generic_chess.core.transition import apply_action
    from generic_chess.learning.shogi_rules import sfen_to_gc_state

    compiled = compile_ruleset_for_execution(build_standard_shogi_ruleset())
    state = sfen_to_gc_state(compiled, "8k/9/9/4P4/9/9/9/9/K8 b - 1")
    root_key = state.repetition_counts[0][0]
    state = GameState(
        position=state.position,
        ply_count=state.ply_count,
        repetition_counts=state.repetition_counts,
        terminal_status=state.terminal_status,
        history=(HistoryRecord(root_key, -1, "", False),),
    )
    actions = [
        action
        for action in legal_actions(state, compiled)
        if action_is_board(action)
        and action.from_square == Square(4, 5)
        and action.to_square == Square(4, 6)
    ]
    assert {action.promotion_target_id for action in actions} == {None, "TP"}
    promote = next(action for action in actions if action.promotion_target_id == "TP")
    runtime = SearchPathRuntime.from_state(state, compiled)
    before_actions = frozenset(runtime.legal_actions())
    assert before_actions == frozenset(legal_actions(state, compiled))
    before = (
        runtime.position,
        runtime.ply_count,
        runtime.terminal_status,
        tuple(runtime.history),
        runtime.repetition_counts,
        runtime.runtime_hash,
        runtime._history_context,
        runtime.search_key(),
        runtime._history_complete,
        runtime.history_witness_misses,
        before_actions,
    )

    child = apply_action(state, promote, compiled)
    runtime.push(promote)
    assert runtime.position == child.position
    assert runtime.position.board[5 * 9 + 4] is None
    promoted_piece = runtime.position.board[6 * 9 + 4]
    assert promoted_piece is not None
    assert (
        promoted_piece.owner,
        promoted_piece.base_type_id,
        promoted_piece.current_type_id,
        promoted_piece.promoted,
    ) == (0, "P", "TP", True)
    assert runtime.position.side_to_move == 1
    assert runtime.ply_count == state.ply_count + 1
    runtime.pop()
    runtime.assert_balanced()
    after = (
        runtime.position,
        runtime.ply_count,
        runtime.terminal_status,
        tuple(runtime.history),
        runtime.repetition_counts,
        runtime.runtime_hash,
        runtime._history_context,
        runtime.search_key(),
        runtime._history_complete,
        runtime.history_witness_misses,
        frozenset(runtime.legal_actions()),
    )
    assert after == before


def test_standard_shogi_capture_promotion_runtime_push_pop_roundtrip():
    from generic_chess.core.actions import action_is_board
    from generic_chess.core.coordinates import Square
    from generic_chess.core.movegen import legal_actions
    from generic_chess.core.pieces import Piece
    from generic_chess.core.position import GameState, HistoryRecord
    from generic_chess.core.search_runtime import SearchPathRuntime
    from generic_chess.core.transition import apply_action
    from generic_chess.learning.shogi_rules import sfen_to_gc_state

    compiled = compile_ruleset_for_execution(build_standard_shogi_ruleset())
    state = sfen_to_gc_state(
        compiled, "8k/9/4+p4/4P4/9/9/9/9/K8 b - 1"
    )
    root_key = state.repetition_counts[0][0]
    state = GameState(
        position=state.position,
        ply_count=state.ply_count,
        repetition_counts=state.repetition_counts,
        terminal_status=state.terminal_status,
        history=(HistoryRecord(root_key, -1, "", False),),
    )
    actions = [
        action
        for action in legal_actions(state, compiled)
        if action_is_board(action)
        and action.from_square == Square(4, 5)
        and action.to_square == Square(4, 6)
    ]
    assert {action.promotion_target_id for action in actions} == {None, "TP"}
    capture_promote = next(
        action for action in actions if action.promotion_target_id == "TP"
    )
    source_square = 5 * 9 + 4
    target_square = 6 * 9 + 4
    victim = state.position.board[target_square]
    assert victim == Piece(1, "P", "TP", promoted=True)

    runtime = SearchPathRuntime.from_state(state, compiled)
    before_actions = frozenset(runtime.legal_actions())
    assert before_actions == frozenset(legal_actions(state, compiled))
    before = (
        runtime.position,
        runtime.ply_count,
        runtime.terminal_status,
        tuple(runtime.history),
        runtime.repetition_counts,
        runtime.runtime_hash,
        runtime._history_context,
        runtime.search_key(),
        runtime._history_complete,
        runtime.history_witness_misses,
        before_actions,
    )

    child = apply_action(state, capture_promote, compiled)
    runtime.push(capture_promote)
    assert runtime.position == child.position
    assert runtime.position.board[source_square] is None
    mover = runtime.position.board[target_square]
    assert mover == Piece(0, "P", "TP", promoted=True)
    assert runtime.position.hands[0] == state.position.hands[0].add("P")
    assert runtime.position.hands[0].count("TP") == 0
    assert runtime.position.hands[1] == state.position.hands[1]
    assert runtime.position.side_to_move == 1
    assert runtime.ply_count == state.ply_count + 1
    runtime.pop()
    runtime.assert_balanced()
    after = (
        runtime.position,
        runtime.ply_count,
        runtime.terminal_status,
        tuple(runtime.history),
        runtime.repetition_counts,
        runtime.runtime_hash,
        runtime._history_context,
        runtime.search_key(),
        runtime._history_complete,
        runtime.history_witness_misses,
        frozenset(runtime.legal_actions()),
    )
    assert after == before


def test_product_shogi_record_replay_and_alphabeta_smoke():
    compiled = compile_ruleset_for_execution(build_standard_shogi_ruleset())
    session = GameSession(compiled)
    action = session.legal_actions()[0]
    session.submit(action)
    record = deserialize_game_record(serialize_game_record(session.to_record()))
    replayed = GameSession.replay(compiled, record)
    assert replayed.state == session.state
    assert replayed.history[-1].action == session.history[-1].action
    decision = AlphaBetaPlayer(compiled, use_disk_cache=False).choose_action(
        replayed,
        SearchLimits(max_nodes=512, max_depth=8, quiescence_max_depth=4, quiescence_hard_max_depth=8),
    )
    assert decision.action in replayed.legal_actions()


def test_standard_shogi_cli_smoke_renders_9x9_and_30_initial_actions():
    proc = subprocess.run(
        [sys.executable, "-m", "generic_chess.cli.play", "--builtin-ruleset", "standard_shogi"],
        cwd=ROOT,
        input="quit\n",
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    assert proc.returncode == 0, proc.stderr
    header = next(line for line in proc.stdout.splitlines() if line.lstrip().startswith("a "))
    assert all(letter in header for letter in "abcdefghi")
    assert "legal actions:" in proc.stdout
    assert sum(
        line.split(".", 1)[0].strip().isdigit()
        for line in proc.stdout.splitlines()
        if "." in line
    ) >= 30
