"""Random-play system invariants with fixed seeds."""

import random

from generic_chess.core.movegen import legal_actions_from_position
from generic_chess.core.transition import apply_action, initial_state
from generic_chess.generation.config import GeneratorConfig
from generic_chess.generation.generator import generate_game
from generic_chess.rules.serialization import deserialize_ruleset, serialize_ruleset
from generic_chess.rules.compiler import compile_ruleset


def _count_entities(position):
    return sum(1 for p in position.board if p is not None) + sum(
        h.total() for h in position.hands
    )


def _assert_invariants(state, compiled, initial_count):
    pos = state.position
    assert _count_entities(pos) == initial_count
    for player in (0, 1):
        anchors = [
            p
            for p in pos.board
            if p is not None
            and p.owner == player
            and compiled.types_by_id[p.current_type_id].is_anchor
        ]
        assert len(anchors) == 1
    # Anchors never enter the hands.
    for player in (0, 1):
        for tid, _count in pos.hands[player].counts:
            assert not compiled.types_by_id[tid].is_anchor


def _run_game(seed, plies=60):
    game = generate_game(GeneratorConfig(seed=seed))
    compiled = game.compiled_ruleset
    initial_count = compiled.initial_entity_count
    state = initial_state(compiled)
    rng = random.Random(seed + 1000)
    _assert_invariants(state, compiled, initial_count)
    for _ in range(plies):
        if state.terminal_status.is_terminal:
            break
        actions = legal_actions_from_position(state.position, compiled)
        assert actions, "non-terminal state must have legal actions"
        state = apply_action(state, rng.choice(actions), compiled)
        _assert_invariants(state, compiled, initial_count)
        assert not any(
            p is not None and compiled.types_by_id[p.current_type_id].is_anchor
            and p.promoted
            for p in state.position.board
        )
    return game, state


def test_random_games_preserve_invariants():
    for seed in range(1, 5):
        _run_game(seed, plies=60)


def test_serialization_stable_during_play():
    game = generate_game(GeneratorConfig(seed=6))
    text = serialize_ruleset(game.ruleset)
    rt = deserialize_ruleset(text)
    compiled_rt = compile_ruleset(rt)
    assert compiled_rt.ruleset_fingerprint == game.compiled_ruleset.ruleset_fingerprint


def test_no_anchor_captured_during_random_play():
    game = generate_game(GeneratorConfig(seed=7))
    compiled = game.compiled_ruleset
    state = initial_state(compiled)
    initial_anchors = sum(
        1
        for p in state.position.board
        if p is not None and compiled.types_by_id[p.current_type_id].is_anchor
    )
    rng = random.Random(7)
    for _ in range(80):
        if state.terminal_status.is_terminal:
            break
        actions = legal_actions_from_position(state.position, compiled)
        state = apply_action(state, rng.choice(actions), compiled)
        now = sum(
            1
            for p in state.position.board
            if p is not None and compiled.types_by_id[p.current_type_id].is_anchor
        )
        assert now == initial_anchors


def test_same_seed_reproduces_full_game():
    _, s1 = _run_game(42, plies=30)
    _, s2 = _run_game(42, plies=30)
    assert s1.position == s2.position
    assert s1.ply_count == s2.ply_count
