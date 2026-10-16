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
@pytest.mark.parametrize("dynamic", (None, (2, 3, 5)))
def test_inline_localized_leaf_keeps_real_child_aux_and_nested_reply_semantics(
    builder, position_for, owner, dynamic,
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
        if dynamic is not None:
            expected += (1 if owner == 0 else -1) * sum(
                w * value for w, value in zip(dynamic, reference_features(compiled, position)))
        expected = max(-90000000, min(90000000, expected))
        assert native.evaluate(
            rules, packed, board_values=zero_material, hand_values=zero_material,
            localized_control_values=weights, dynamic_values=dynamic,
        ) == expected
    assert native.snapshot(rules, packed) == before


@pytest.mark.parametrize("builder,position_for", S4_CASES)
@pytest.mark.parametrize("owner", (0, 1))
@pytest.mark.parametrize("horizon", (2, 512))
def test_public_spatial_getter_preserves_s4_and_occupancy(
    builder, position_for, owner, horizon,
):
    from generic_chess.learning.features import (
        localized_control_features, spatial_occupancy_features,
    )
    compiled = compile_semantic_ruleset(replace(builder(), max_ply=horizon))
    position = replace(position_for(compiled.support), side_to_move=owner)
    rules = compile_native_semantic_rules(compiled)
    packed = native.pack_current_position(rules, position, ply_count=0)
    before = native.snapshot(rules, packed)
    expected = spatial_occupancy_features(position, rules.type_ids)
    actual = native.spatial_features(rules, packed)
    assert actual["occupancy"] == tuple(
        value for side in (0, 1) for type_id in rules.type_ids
        for value in expected[f"{side}:{type_id}"]
    )
    assert actual["localized_control"] == localized_control_features(position, compiled)
    assert native.snapshot(rules, packed) == before


@pytest.mark.parametrize("prefix", (1023, 1024))
def test_public_spatial_getter_preserves_history_capacity(prefix):
    from test_native_q_history_deferral import cycle
    from generic_chess.learning.features import localized_control_features
    session = cycle(max_ply=2048, repetition=10000, prefix=prefix)
    rules = compile_native_semantic_rules(session.compiled)
    packed = pack_semantic_search_position(session.compiled, rules, session)
    before = native.snapshot(rules, packed)
    if prefix == 1024:
        with pytest.raises(NotImplementedError, match="history capacity"):
            native.spatial_features(rules, packed)
    else:
        assert native.spatial_features(rules, packed)["localized_control"] == (
            localized_control_features(session.state.position, session.compiled)
        )
    assert native.snapshot(rules, packed) == before
