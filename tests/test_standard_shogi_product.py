"""F25 product-surface and historical-parity contracts for Standard Shogi."""

from __future__ import annotations

import json
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


ROOT = Path(__file__).resolve().parents[1]


def test_product_builder_matches_historical_semantic_gameplay_fields():
    from generic_chess.learning.shogi_semantic_rules import build_semantic_shogi_ruleset

    product = build_standard_shogi_ruleset()
    historical = build_semantic_shogi_ruleset()
    assert ruleset_to_dict(product, include_metadata=False) == ruleset_to_dict(
        historical, include_metadata=False
    )
    assert compute_fingerprint(product) == compute_fingerprint(historical)
    assert product.metadata["nyugyoku_supported"] is False


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
