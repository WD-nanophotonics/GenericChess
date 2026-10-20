"""Finite adapter/learner contract witnesses, not Generic strength evaluation."""
from dataclasses import replace
import importlib.util
from pathlib import Path
import json

import pytest

from generic_chess.core.pieces import Piece
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.session.session import GameSession
from generic_chess.session.session import SessionRecordError
from generic_chess.session.serialization import serialize_game_record, deserialize_game_record
from results.dev_aux.task2492.learning import Model
from results.dev_aux.task2492.episode import TDLeafEpisode
from results.dev_aux.task2511.generic import NonScoringTerminal
from results.dev_aux.task2511.test_generic import session as declaration_session
from results.dev_aux.task2621.fixed_scale import (
    FixedScaleSessionEnv, compile_channels, unchanged_learner, unchanged_model)


def semantic_rules():
    # Existing repository fixture, loaded from its explicit own-checkout path.
    path = Path(__file__).resolve().parents[3] / "tests/rule_semantics_ir_fixtures.py"
    spec = importlib.util.spec_from_file_location("gc2621_semantic_fixtures", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    fixtures = module.weird_rulesets()
    board = [[None] * 8 for _ in range(8)]
    for owner, type_id, file, rank in (
        (0, "K", 4, 0), (1, "K", 7, 7), (0, "R", 0, 0),
        (0, "R", 0, 1), (0, "R", 0, 2), (0, "R", 1, 1),
        (1, "R", 1, 3), (1, "R", 1, 4)):
        board[rank][file] = Piece(owner, type_id, type_id)
    return replace(fixtures[2], initial_position=tuple(map(tuple, board)),
        semantic_actions=(fixtures[1].semantic_actions[0], fixtures[2].semantic_actions[0]),
        drop_allowed={"R": ((True,) * 64, (True,) * 64),
                      "TP": ((False,) * 64, (False,) * 64)})


def test_exact_model_and_learner_classes_keep_the_same_fixed_scale():
    model = unchanged_model([1., .7, 1.2, .9, 1.3, 1.1])
    learner = unchanged_learner()
    assert type(model) is Model and type(learner) is TDLeafEpisode
    assert model.fixed == 0 and model.scale == 10.
    model.apply([99., 0., 0., 0., 0., 0.])
    assert model.weights[0] == 1.
    assert learner.eta == .05 and learner.lam == .95


def test_no_hard_coded_dimension_or_silent_unknown_unit():
    compiled = compile_ruleset_for_execution(semantic_rules())
    names = compile_channels(compiled, unit_type="R")
    assert names == (("board", "R"), ("board", "TP"), ("hand", "R"), ("hand", "TP"))
    with pytest.raises(ValueError, match="unit type"):
        compile_channels(compiled)  # No invented P coordinate for this R/TP fixture.


def test_real_promotion_base_hand_auxiliary_expiry_and_full_history_route():
    env = FixedScaleSessionEnv(GameSession(compile_ruleset_for_execution(semantic_rules())), unit_type="R")
    route = (((1, 1), (1, 3), False), ((7, 7), (6, 7), False),
             ((1, 3), (1, 4), False), ((6, 7), (5, 7), False),
             ((0, 0), (1, 1), True), ((5, 7), (4, 7), False),
             (None, (0, 0), False), ((4, 7), (3, 7), False))
    for ply in range(9):
        assert env.replay().record() == env.record()
        quantities = dict(zip(env.names, env.features()))
        if ply == 5:
            assert quantities[("board", "TP")] == 1
            assert dict(env.session.state.position.aux_state)[(0, -1)] == 1
        if ply == 6:
            assert dict(env.session.state.position.aux_state)[(0, -1)] == 0
        if ply == 8:
            assert env.session.state.position.hands[0].count("R") == 1
            break
        source, target, semantic = route[ply]
        matches = []
        for choice in env.actions():
            if choice.kind != "ACTION":
                continue
            action = choice.action
            if (action.to_square.file, action.to_square.rank) != target:
                continue
            if source is None:
                hit = hasattr(action, "base_type_id")
            else:
                hit = (hasattr(action, "from_square")
                       and (action.from_square.file, action.from_square.rank) == source
                       and action.pattern_id.startswith("sem_") == semantic)
            if hit:
                matches.append(choice)
        choice, = matches
        before, state = env.record(), env.session.state
        env.push(choice)
        env.replay()
        env.pop()
        assert env.record() == before and env.session.state == state
        env.push(choice)


@pytest.mark.parametrize("outcome", ["RESTART", "NO_CONTEST"])
def test_non_scoring_terminal_remains_unknown_not_a_draw(outcome):
    session = declaration_session(outcome)
    env = FixedScaleSessionEnv(session, unit_type="R")
    before = env.record()
    choice = next(choice for choice in env.actions() if choice.kind == "DECLARATION")
    env.push(choice)
    with pytest.raises(NonScoringTerminal):
        env.terminal()
    assert env.replay().record() == env.record()
    env.pop()
    assert env.record() == before and env.terminal() is None


@pytest.mark.parametrize("outcome", ["WIN", "RESTART", "NO_CONTEST", "LOSS"])
def test_all_rule_supported_declaration_outcomes_roundtrip_authoritatively(outcome):
    session = declaration_session(outcome)
    session.declare("claim")
    record = session.to_record()
    parsed = deserialize_game_record(serialize_game_record(record))
    replayed = GameSession.replay(session.compiled, parsed)
    assert parsed == record and replayed.to_record() == record
    assert replayed.result == session.result


def test_unknown_label_and_rule_inconsistent_no_contest_are_still_rejected():
    session = declaration_session("WIN")
    session.declare("claim")
    payload = json.loads(serialize_game_record(session.to_record()))
    payload["declaration"]["outcome"] = "invented_reward"
    with pytest.raises(SessionRecordError, match="INVALID_OUTCOME"):
        deserialize_game_record(json.dumps(payload))
    payload["declaration"]["outcome"] = "NO_CONTEST"
    record = deserialize_game_record(json.dumps(payload))
    with pytest.raises(SessionRecordError, match="authoritative assessment"):
        GameSession.replay(session.compiled, record)
