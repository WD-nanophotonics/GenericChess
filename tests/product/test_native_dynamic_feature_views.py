"""Derived features keep exact legal bindings while discarding trial identity."""
from dataclasses import replace
import random

import pytest

from generic_chess.core.semantic_executor import SemanticEngine
from generic_chess.native import native_available
from generic_chess.native.adapter import pack_semantic_search_position
from generic_chess.native.compiler import compile_native_semantic_rules
from generic_chess.native.mirror import expected_snapshot
from generic_chess.native import semantic as native
from generic_chess.rules.compiler import compile_semantic_ruleset
from generic_chess.session.session import GameSession
from phase19c1_native_semantic_fixtures import semantic_corpus
import phase19b3_s4_fixtures as s4

pytestmark = pytest.mark.skipif(not native_available(), reason="Native unavailable")


def reference_features(compiled, position):
    engine = SemanticEngine(compiled)
    counts = []
    for owner in (0, 1):
        view = replace(position, side_to_move=owner)
        actions = engine.legal_actions(view)
        promotions = sum(a.promotion_target_id is not None for a in actions)
        anchor_moves = sum(
            a.source is not None
            and compiled.support.type_metadata[
                view.board[a.source].current_type_id
            ].is_anchor
            for a in actions
        )
        counts.append((len(actions), promotions,
                       anchor_moves - 10 * int(engine.in_check(view, owner))))
    return tuple(a - b for a, b in zip(*counts))


@pytest.mark.parametrize("name,compiled", semantic_corpus(), ids=lambda x: x if isinstance(x, str) else None)
def test_dynamic_counts_match_core_through_complete_sessions(name, compiled):
    session = GameSession(compiled)
    rules = compile_native_semantic_rules(compiled)
    rng = random.Random(22001 + sum(map(ord, name)))
    for _ in range(4):
        state = session.state
        witnesses = session._search_witnesses
        packed = pack_semantic_search_position(compiled, rules, session)
        before = native.snapshot(rules, packed)
        assert native.dynamic_features(rules, packed) == reference_features(
            compiled, state.position)
        assert native.snapshot(rules, packed) == before
        assert session.state is state and session._search_witnesses is witnesses
        if state.terminal_status.is_terminal:
            break
        actions = session.legal_actions()
        if not actions:
            break
        session.submit(rng.choice(sorted(actions, key=repr)))


S4_CASES = (
    (s4.opponent_checked_perspective_ruleset,
     s4.opponent_checked_reply_checked_position),
    (s4.nested_s4_option_b_ruleset, s4.nested_s4_option_b_position),
    (s4.full_child_state_ruleset, s4.full_child_state_position),
    (s4.multiple_replies_ruleset, s4.multiple_replies_position),
    (s4.restricted_finish_ruleset, s4.restricted_finish_position),
    (s4.forbidden_no_reply_drop_ruleset, s4.forbidden_no_reply_drop_position),
)


@pytest.mark.parametrize("builder,position_for", S4_CASES)
@pytest.mark.parametrize("owner", (0, 1))
def test_dynamic_counts_keep_real_child_aux_and_nested_reply_semantics(
    builder, position_for, owner,
):
    # A specification Position fixture, not a claimed reachable game history.
    compiled = compile_semantic_ruleset(builder())
    position = replace(position_for(compiled.support), side_to_move=owner)
    rules = compile_native_semantic_rules(compiled)
    payload = dict(expected_snapshot(position, rules, compiled), ply=0)
    payload["board"] = [None if p is None else list(p) for p in payload["board"]]
    payload["hands"] = [list(h) for h in payload["hands"]]
    packed = native.pack_position(rules, payload)
    before = native.snapshot(rules, packed)
    assert native.dynamic_features(rules, packed) == reference_features(compiled, position)
    assert native.snapshot(rules, packed) == before

@pytest.mark.parametrize("builder,position_for", S4_CASES)
@pytest.mark.parametrize("owner", (0, 1))
def test_inline_localized_leaf_keeps_real_child_aux_and_nested_reply_semantics(
    builder, position_for, owner,
):
    from generic_chess.learning.features import localized_control_features

    # Exercise the actual leaf consumer, not the separate public vector getter.
    compiled = compile_semantic_ruleset(builder())
    position = replace(position_for(compiled.support), side_to_move=owner)
    rules = compile_native_semantic_rules(compiled)
    payload = dict(expected_snapshot(position, rules, compiled), ply=0)
    payload["board"] = [None if p is None else list(p) for p in payload["board"]]
    payload["hands"] = [list(h) for h in payload["hands"]]
    packed = native.pack_position(rules, payload)
    before = native.snapshot(rules, packed)
    zero_material = (0,) * len(rules.type_ids)
    control = localized_control_features(position, compiled)
    for weights in (
        (1, 0, 0, 0, 0, 0, 0, 0, -1),
        (1000000, 0, 0, 0, 0, 0, 0, 0, -1000000),
    ):
        expected = (1 if owner == 0 else -1) * sum(
            w * value for w, value in zip(weights, control))
        expected = max(-90000000, min(90000000, expected))
        assert native.evaluate(
            rules, packed, board_values=zero_material, hand_values=zero_material,
            localized_control_values=weights,
        ) == expected
    assert native.snapshot(rules, packed) == before
