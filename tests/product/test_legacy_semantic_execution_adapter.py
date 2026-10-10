"""Behavioral contracts for the opt-in validated legacy-to-semantic adapter."""
from collections import Counter
from dataclasses import replace

import pytest

from conftest import T, king_type, make_ruleset, sq
from generic_chess import (GeneratorConfig, generate_game, initial_state, legal_actions,
                           apply_action, compile_legacy_ruleset_for_semantic_execution)
from generic_chess.core.actions import DropMove
from generic_chess.core.movement import LeapAtom, RayAtom
from generic_chess.core.search_runtime import SearchPathRuntime
from generic_chess.rules.compiler import compile_ruleset_for_execution, compile_semantic_ruleset
from generic_chess.rules.ir import CompiledSemanticRuleset
from generic_chess.rules.schema import ruleset_to_dict
from generic_chess.rules.validation import RuleValidationError


def visible(action):
    return (getattr(action, "from_square", None), action.to_square,
            getattr(action, "promotion_target_id", None),
            getattr(action, "base_type_id", None))


@pytest.mark.parametrize("seed", range(2026101101, 2026101105))
def test_generated_initial_children_preserve_visible_actions_and_positions(seed):
    game = generate_game(GeneratorConfig(seed=seed, board_size=6,
                         setup_preset="free_random", movement_symmetry="none", allow_hybrid=True))
    ordinary = compile_ruleset_for_execution(game.ruleset)
    semantic = compile_legacy_ruleset_for_semantic_execution(game.ruleset)
    assert not isinstance(ordinary, CompiledSemanticRuleset)
    assert semantic.ruleset_fingerprint == ordinary.ruleset_fingerprint
    assert semantic.ir.capabilities.new_ir_core_executable
    a, b = initial_state(ordinary), initial_state(semantic)
    assert a.position == b.position
    aa, bb = legal_actions(a, ordinary), legal_actions(b, semantic)
    assert Counter(map(visible, aa)) == Counter(map(visible, bb))
    by_visible = {visible(action): action for action in aa}
    for action in bb:
        x = apply_action(a, by_visible[visible(action)], ordinary)
        y = apply_action(b, action, semantic)
        assert x.position == y.position
        assert x.terminal_status == y.terminal_status
        assert x.history[-1].gave_check == y.history[-1].gave_check
    # Different identity encodings must not be copied across compiled representations.
    assert a.history[0].position_key != b.history[0].position_key
    with pytest.raises(RuleValidationError, match="NO_SEMANTIC_ACTIONS"):
        compile_semantic_ruleset(game.ruleset)


def test_capture_promotion_hand_drop_and_runtime_restore():
    rules = make_ruleset(4, [king_type(), T("P", LeapAtom((1, 1)),
                          is_promotable=True, targets=("Q",)), T("Q", RayAtom((1, 0)))],
        lines=[".p.k", "P...", "....", "K..."],
        promotion={"P": ([(sq(0, 2), sq(1, 3))], [sq(1, 3)])})
    old = compile_ruleset_for_execution(rules)
    new = compile_legacy_ruleset_for_semantic_execution(ruleset_to_dict(rules))
    a, b = initial_state(old), initial_state(new)
    key = (sq(0, 2), sq(1, 3), "Q", None)
    aa = next(x for x in legal_actions(a, old) if visible(x) == key)
    bb = next(x for x in legal_actions(b, new) if visible(x) == key)
    a, b = apply_action(a, aa, old), apply_action(b, bb, new)
    assert a.position == b.position
    assert b.position.hands[0].count("P") == 1
    reply_key = visible(legal_actions(a, old)[0])
    a = apply_action(a, next(x for x in legal_actions(a, old) if visible(x) == reply_key), old)
    b = apply_action(b, next(x for x in legal_actions(b, new) if visible(x) == reply_key), new)
    drops = [x for x in legal_actions(b, new) if getattr(x, "base_type_id", None) == "P"]
    assert drops
    action = drops[0]
    expected = apply_action(a, DropMove("P", action.to_square), old)
    runtime = SearchPathRuntime.from_state(b, new)
    before_history = tuple(runtime.history)
    runtime.push(action)
    assert runtime.position == expected.position
    runtime.pop()
    assert runtime.position == b.position
    assert runtime.ply_count == b.ply_count
    assert runtime.terminal_status == b.terminal_status
    assert tuple(runtime.history) == before_history
    assert runtime.depth == 0
    assert runtime.history_reconstruction_attempts == 1
    assert runtime.history_witness_misses == 0


def test_repetition_draw_survives_semantic_replay_with_own_key_namespace():
    rules = make_ruleset(4, [king_type()], repetition_limit=3)
    arms = [compile_ruleset_for_execution(rules), compile_legacy_ruleset_for_semantic_execution(rules)]
    states = [initial_state(c) for c in arms]
    cycle = [(sq(0, 0), sq(0, 1)), (sq(3, 0), sq(3, 1)),
             (sq(0, 1), sq(0, 0)), (sq(3, 1), sq(3, 0))]
    for source, target in cycle * 2:
        for i, c in enumerate(arms):
            action = next(x for x in legal_actions(states[i], c)
                          if getattr(x, "from_square", None) == source and x.to_square == target)
            states[i] = apply_action(states[i], action, c)
        assert states[0].position == states[1].position
        assert states[0].terminal_status == states[1].terminal_status
        assert sorted(n for _, n in states[0].repetition_counts) == sorted(n for _, n in states[1].repetition_counts)
    assert states[1].terminal_status.is_terminal
    assert states[1].terminal_status.winner is None
    runtime = SearchPathRuntime.from_state(states[1], arms[1])
    assert runtime.history_witness_misses == 0
    assert runtime.terminal_status == states[1].terminal_status


def test_adapter_retains_schema_validation_and_rejects_semantic_dsl():
    from generic_chess.rules.western_chess import build_western_chess_ruleset
    with pytest.raises(RuleValidationError):
        compile_legacy_ruleset_for_semantic_execution(build_western_chess_ruleset())
    with pytest.raises(RuleValidationError):
        compile_legacy_ruleset_for_semantic_execution(replace(make_ruleset(4, [king_type()]), repetition_limit=0))


@pytest.mark.parametrize("seed", [2026101101, 2026101103])
def test_default_rule_profile_and_dynamic_evaluation_keep_legacy_metadata(seed):
    from generic_chess.ai.evaluation import EvaluationConfig, EvaluationProfileCache, Evaluator
    game = generate_game(GeneratorConfig(seed=seed, board_size=6,
                         setup_preset="free_random", movement_symmetry="none", allow_hybrid=True))
    arms = [game.compiled_ruleset, compile_legacy_ruleset_for_semantic_execution(game.ruleset)]
    cfg = EvaluationConfig(dynamic_mobility_weight=1, anchor_escape_weight=1,
                           promotion_potential_weight=1)
    profiles = [EvaluationProfileCache(use_disk=False).get_or_build(c, cfg)[0] for c in arms]
    assert profiles[0] == profiles[1]
    evaluators = [Evaluator(c, profile, cfg) for c, profile in zip(arms, profiles)]
    states = [initial_state(c) for c in arms]
    assert evaluators[0].evaluate(states[0]) == evaluators[1].evaluate(states[1])
    bb = {visible(a): a for a in legal_actions(states[1], arms[1])}
    for action in legal_actions(states[0], arms[0]):
        x = apply_action(states[0], action, arms[0])
        y = apply_action(states[1], bb[visible(action)], arms[1])
        assert evaluators[0].evaluate(x) == evaluators[1].evaluate(y)


def test_overlapping_atoms_keep_typed_identity_and_reject_ambiguous_coordinate_action():
    from generic_chess.core.actions import BoardMove, action_to_dict, action_from_dict
    from generic_chess.core.errors import IllegalActionError
    rules = make_ruleset(4, [king_type(), T("P", LeapAtom((1, 0)), RayAtom((1, 0)))],
                         lines=["...k", "....", ".P..", "K..."])
    old = compile_ruleset_for_execution(rules)
    new = compile_legacy_ruleset_for_semantic_execution(rules)
    a, b = initial_state(old), initial_state(new)
    coordinate = BoardMove(sq(1, 1), sq(2, 1))
    expected = apply_action(a, coordinate, old)
    duplicates = [x for x in legal_actions(b, new) if visible(x) == visible(coordinate)]
    assert len(duplicates) == 2
    assert len({x.geometry_id for x in duplicates}) == 2
    for action in duplicates:
        assert action_from_dict(action_to_dict(action)) == action
        child = apply_action(b, action, new)
        assert child.position == expected.position
        runtime = SearchPathRuntime.from_state(child, new)
        assert runtime.history_witness_misses == 0
    with pytest.raises(IllegalActionError, match="ambiguous"):
        apply_action(b, coordinate, new)


@pytest.mark.parametrize("policy", ["pass_pair", "no_progress", "max_ply"])
def test_history_adjudication_and_pass_keep_core_authority(policy):
    from generic_chess.core.actions import PassAction
    from generic_chess.core.search_runtime import _full_runtime_hash
    from generic_chess.core.terminal import TerminalStatus
    from generic_chess.rules.schema import RuleConsecutiveActionAdjudication, RuleNoProgressDraw
    rules = replace(make_ruleset(4, [king_type()], repetition_limit=20), pass_enabled=True)
    if policy == "pass_pair":
        # The second pass also reaches repetition: action-class priority matters.
        rules = replace(rules, repetition_limit=2, consecutive_action_adjudications=(
            RuleConsecutiveActionAdjudication("pass", 2, "DRAW"),))
        steps, expected = 2, TerminalStatus.ACTION_CLASS_DRAW
    elif policy == "no_progress":
        rules = replace(rules, no_progress_draw=RuleNoProgressDraw(4, True))
        steps, expected = 4, TerminalStatus.NO_PROGRESS_DRAW
    else:
        rules = replace(rules, max_ply=3)
        steps, expected = 3, TerminalStatus.MAX_PLY
    arms = [compile_ruleset_for_execution(rules), compile_legacy_ruleset_for_semantic_execution(rules)]
    states = [initial_state(c) for c in arms]
    assert not arms[1].ir.capabilities.native_executable
    for ply in range(steps):
        for i, c in enumerate(arms):
            state = states[i]
            assert PassAction() in legal_actions(state, c)
            if policy == "no_progress":
                # Compilation/Core execution does not remove the existing
                # search path-state restriction.
                with pytest.raises(NotImplementedError, match="path-state identity"):
                    SearchPathRuntime.from_state(state, c)
                states[i] = apply_action(state, PassAction(), c)
                continue
            runtime = SearchPathRuntime.from_state(state, c)
            before = (runtime.position, runtime.search_key(), tuple(runtime.history), runtime.terminal_status)
            runtime.push(PassAction())
            child = apply_action(state, PassAction(), c)
            assert runtime.position == child.position
            assert runtime.terminal_status == child.terminal_status
            assert runtime.runtime_hash == _full_runtime_hash(child.position, c)
            runtime.pop()
            assert (runtime.position, runtime.search_key(), tuple(runtime.history), runtime.terminal_status) == before
            states[i] = child
        assert states[0].position == states[1].position
        assert states[0].terminal_status == states[1].terminal_status
    assert states[1].terminal_status.status is expected
    assert all(not record.gave_check for record in states[1].history)


def test_alternate_setup_typed_session_record_and_history_replay():
    from generic_chess.core.history_provenance import reconstruct_history_provenance
    from generic_chess.rules.schema import RuleInitialSetupOption
    from generic_chess.session.serialization import deserialize_game_record, serialize_game_record
    from generic_chess.session.session import GameSession
    types = [king_type(), T("P", LeapAtom((1, 0)))]
    base = make_ruleset(4, types, lines=["...k", "....", ".P..", "K..."])
    alternate = make_ruleset(4, types, lines=["...k", "....", "P...", "K..."])
    rules = replace(base, initial_setup_options=(RuleInitialSetupOption("p-file-a", alternate.initial_position),))
    old = compile_ruleset_for_execution(rules)
    new = compile_legacy_ruleset_for_semantic_execution(rules)
    a, b = initial_state(old, "p-file-a"), initial_state(new, "p-file-a")
    assert a.position == b.position
    assert b.position != initial_state(new).position
    session = GameSession(new, "p-file-a")
    for _ in range(3):
        session.submit(session.legal_actions()[0])
    record = deserialize_game_record(serialize_game_record(session.to_record()))
    assert record.schema_version == 3
    assert record.initial_setup_key == "p-file-a"
    replayed = GameSession.replay(new, record)
    assert replayed.state == session.state
    assert replayed.history == session.history
    assert reconstruct_history_provenance(replayed.state, new).status == "verified"
    runtime = SearchPathRuntime.from_state(replayed.state, new)
    assert runtime.history_witness_misses == 0
    with pytest.raises(ValueError, match="unknown initial setup"):
        initial_state(new, "missing")
