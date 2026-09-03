"""H50B2E persistent semantic search and learning re-entry contracts."""

from dataclasses import replace

import pytest

from generic_chess.ai.cancellation import CancellationToken
from generic_chess.ai.evaluation.config import EvaluationConfig
from generic_chess.ai.evaluation.profile import build_ruleset_profile
from generic_chess.ai.limits import SearchLimits
from generic_chess.core.identity import position_identity_key
from generic_chess.core.position import HistoryRecord
from generic_chess.learning.material import LearnableMaterialCheckpoint
from generic_chess.learning.selfplay import SelfPlayConfig, collect_self_play
from generic_chess.native import SemanticSearchEngine, native_available
from generic_chess.native.compiler import compile_native_semantic_rules
from generic_chess.native.semantic import pack_position, snapshot
from generic_chess.rules.compiler import compile_ruleset_for_execution, compile_semantic_ruleset
from generic_chess.rules.standard_shogi import build_standard_shogi_ruleset
from generic_chess.rules.western_chess import build_western_chess_ruleset
from generic_chess.session.session import GameSession


pytestmark = pytest.mark.skipif(
    not native_available(), reason="native extension unavailable"
)


def _western():
    compiled = compile_semantic_ruleset(build_western_chess_ruleset())
    native = compile_native_semantic_rules(compiled)
    return compiled, native


def _search_limits(**kwargs):
    return SearchLimits(quiescence_max_depth=0, **kwargs)


def test_persistent_engine_reuses_tt_and_next_root_history():
    compiled, native = _western()
    session = GameSession(compiled)
    engine = SemanticSearchEngine(compiled, native, tt_megabytes=1)
    cold = engine.search(session, _search_limits(max_depth=1, max_nodes=200))
    info_after_cold = engine.tt_info()
    warm = engine.search(session, _search_limits(max_depth=1, max_nodes=200))
    assert cold.action == warm.action
    assert warm.tt_hits > 0
    assert info_after_cold["occupied_entries"] > 0
    assert engine.tt_info()["generation"] > info_after_cold["generation"]

    assert cold.action is not None
    session.submit(cold.action)
    next_root = engine.search(session, _search_limits(max_depth=1, max_nodes=200))
    assert next_root.action is not None
    assert next_root.tt_hits > 0


def test_checkpoint_rebind_replaces_evaluator_and_clears_tt_without_rule_recompile():
    compiled, native = _western()
    legacy = compile_ruleset_for_execution(build_western_chess_ruleset())
    profile = build_ruleset_profile(legacy, EvaluationConfig())
    parent = LearnableMaterialCheckpoint.from_profile(compiled, profile)
    child = parent.child_checkpoint(
        board_weights={key: value * 0.9 for key, value in parent.board_weights.items()},
        hand_weights={key: value * 0.9 for key, value in parent.hand_weights.items()},
        games_seen_delta=0,
        positions_seen_delta=0,
        training_updates_delta=1,
        training_config_hash="h50b2e",
        training_seed=1,
    )
    engine = SemanticSearchEngine(compiled, native, checkpoint=parent, tt_megabytes=1)
    engine.search(GameSession(compiled), _search_limits(max_depth=1, max_nodes=200))
    assert engine.tt_info()["occupied_entries"] > 0
    engine.bind_checkpoint(child)
    assert engine.checkpoint_id == child.checkpoint_id
    assert engine.ruleset_fingerprint == compiled.ruleset_fingerprint
    assert engine.tt_info()["occupied_entries"] == 0


def test_history_context_prevents_cross_path_tt_reuse():
    compiled, native = _western()
    session = GameSession(compiled)
    from generic_chess.native.adapter import pack_semantic_search_position

    first = pack_semantic_search_position(compiled, native, session)
    words = snapshot(native, first)["history"][0]
    board = [
        None if piece is None else [
            native.type_ids.index(piece.base_type_id),
            native.type_ids.index(piece.current_type_id),
            piece.owner,
            int(piece.promoted),
        ]
        for piece in session.state.position.board
    ]
    hands = [[0] * len(native.type_ids), [0] * len(native.type_ids)]
    second = pack_position(native, {
        "side": 0,
        "ply": 1,
        "board": board,
        "hands": hands,
        "history": [(*words, 255, 0), (*words, 0, 0)],
        "aux_state": (),
    })
    engine = SemanticSearchEngine(compiled, native, tt_megabytes=1)
    module = __import__("generic_chess.native", fromlist=["_module"])._module()
    module.semantic_engine_search(engine._capsule, first, 1, 200, None, None)
    different_path = dict(module.semantic_engine_search(
        engine._capsule, second, 1, 200, None, None
    ))
    assert different_path["tt_hits"] == 0


def test_declaration_decision_is_selected_and_decoded_generically():
    from test_generic_declaration_semantics import _claim_position, _claim_ruleset

    compiled = compile_semantic_ruleset(_claim_ruleset())
    native = compile_native_semantic_rules(compiled)
    position = _claim_position(compiled)
    key = str(position_identity_key(position, compiled))
    session = GameSession(compiled)
    session._state = replace(
        session.state,
        position=position,
        ply_count=0,
        repetition_counts=((key, 1),),
        history=(HistoryRecord(key, -1, "", False),),
    )
    session._search_history_witnesses = (position,)
    zero_values = (0,) * len(native.type_ids)
    result = SemanticSearchEngine(
        compiled,
        native,
        board_values=zero_values,
        hand_values=zero_values,
        tt_megabytes=1,
    ).search(
        session, _search_limits(max_depth=1, max_nodes=100)
    )
    assert result.action is None
    assert result.declaration_id == "opaque_claim"
    assert result.decision_line == ("opaque_claim",)
    assert result.principal_variation == ()


def test_no_contest_declaration_is_a_neutral_terminal_decision():
    from test_generic_declaration_semantics import _claim_position, _claim_ruleset
    from generic_chess.rules.schema import RuleDeclarationOutcomeBand

    ruleset = replace(
        _claim_ruleset(),
        declarations=tuple(
            replace(
                declaration,
                outcome_bands=(RuleDeclarationOutcomeBand(7, "NO_CONTEST"),),
            )
            for declaration in _claim_ruleset().declarations
        ),
    )
    compiled = compile_semantic_ruleset(ruleset)
    native = compile_native_semantic_rules(compiled)
    position = _claim_position(compiled)
    key = str(position_identity_key(position, compiled))
    session = GameSession(compiled)
    session._state = replace(
        session.state,
        position=position,
        ply_count=0,
        repetition_counts=((key, 1),),
        history=(HistoryRecord(key, -1, "", False),),
    )
    session._search_history_witnesses = (position,)
    zero_values = (0,) * len(native.type_ids)
    result = SemanticSearchEngine(
        compiled,
        native,
        board_values=zero_values,
        hand_values=zero_values,
        tt_megabytes=1,
    ).search(
        session, _search_limits(max_depth=1, max_nodes=100)
    )
    assert result.action is None
    assert result.declaration_id == "opaque_claim"
    assert result.score == 0
    assert result.decision_line == ("opaque_claim",)


def test_cancel_and_node_budget_remain_bounded_on_persistent_engine():
    compiled, native = _western()
    engine = SemanticSearchEngine(compiled, native, tt_megabytes=1)
    limited = engine.search(GameSession(compiled), _search_limits(max_depth=4, max_nodes=1))
    assert limited.nodes <= 1
    assert limited.termination_reason in {"node_budget", "completed"}
    token = CancellationToken()
    token.cancel()
    cancelled = engine.search(
        GameSession(compiled), _search_limits(max_depth=4), cancel_token=token
    )
    assert cancelled.termination_reason == "cancelled"
    assert cancelled.action is not None


def test_learning_selfplay_selects_semantic_engine_for_semantic_rulesets(monkeypatch):
    from generic_chess.learning import selfplay as selfplay_module

    ruleset = replace(build_western_chess_ruleset(), max_ply=2, declarations=())
    compiled = compile_semantic_ruleset(ruleset)
    legacy = compile_ruleset_for_execution(ruleset)
    profile = build_ruleset_profile(legacy, EvaluationConfig())
    checkpoint = LearnableMaterialCheckpoint.from_profile(compiled, profile)
    native = compile_native_semantic_rules(compiled)
    seen = []
    real_engine = SemanticSearchEngine

    class SpyEngine(real_engine):
        def __init__(self, *args, **kwargs):
            seen.append(True)
            super().__init__(*args, **kwargs)

    monkeypatch.setattr(selfplay_module, "SemanticSearchEngine", SpyEngine)
    trajectories = collect_self_play(
        compiled,
        native,
        checkpoint,
        SelfPlayConfig(games=1, nodes_per_move=20, max_depth=1, epsilon=1.0, tt_megabytes=1),
    )
    assert seen
    assert len(trajectories) == 1
    assert len(trajectories[0].actions) == 2
