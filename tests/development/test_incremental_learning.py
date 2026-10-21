"""Opt-in incremental TDLeaf: independent arithmetic and real rule authority."""
from dataclasses import replace
from math import tanh

import chess
import pytest

from generic_chess.core.pieces import Piece
from generic_chess.learning.incremental import (
    AlphaBeta, BudgetEnd, ChessEnv, FixedScaleSessionEnv, Model,
    NonScoringTerminal, Receipt, SessionChoice, TDLeafEpisode, compile_channels,
    play_episode,
)
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.schema import RuleDeclaration, RuleNoProgressDraw
from generic_chess.session.session import GameSession
from scripts.generic_proof_fixtures import krk_ruleset
from rule_semantics_ir_fixtures import weird_rulesets


def declaration_session(outcome):
    board = [None] * 16
    for square, piece in ((1, Piece(0, 'K', 'K')), (3, Piece(1, 'K', 'K')),
                          (8, Piece(0, 'R', 'R'))):
        board[square] = piece
    rules = replace(krk_ruleset(4),
                    initial_position=tuple(tuple(board[y:y + 4]) for y in range(0, 16, 4)),
                    declarations=(RuleDeclaration('claim', 0, require_not_in_check=False,
                                                  failure_outcome=outcome),))
    return GameSession(compile_ruleset_for_execution(rules))


@pytest.mark.parametrize('outcome', [-1, 0, 1, None])
@pytest.mark.parametrize('lam', [0.0, 0.95, 1.0])
def test_episode_update_matches_independent_forward_lambda_return(outcome, lam):
    model = Model([1., 0.7, 1.2])
    learner = TDLeafEpisode(eta=.05, lam=lam)
    scores = [1.2, -2.3, 1_000_000.]
    phis = [(0., 2., -1.), (1., -.5, 3.), None]
    predictions = [tanh(s / 10.) for s in scores]
    gradients = [model.gradient(p) if p is not None else (0., 0., 0.) for p in phis]
    initial = model.weights[:]
    for score, phi in zip(scores, phis):
        receipt = Receipt(None, score, phi, phi is None, (), 1, True, 0, 0., 'test')
        learner.observe(model, receipt)
        assert model.weights == initial  # No update within a frozen episode.
    errors = [predictions[i + 1] - predictions[i] for i in range(2)]
    if outcome is not None:
        errors.append(outcome - predictions[-1])
    expected = [initial[j] + .05 * sum(gradients[i][j] * sum(
        lam ** (k - i) * errors[k] for k in range(i, len(errors)))
        for i in range(len(errors))) for j in range(3)]
    expected[0] = 1.
    stats = learner.finish(model, outcome)
    assert model.weights == pytest.approx(expected, abs=1e-15)
    assert stats['samples'] == len(errors)
    assert stats['censored'] is (outcome is None)
    if outcome is None:
        assert stats['terminal_credit_l1'] == 0.


def test_chess_actual_mate_trajectory_learns_with_fixed_unit():
    env = ChessEnv(chess.Board('7k/p7/5KQ1/8/8/8/8/8 b - - 0 1'))
    model, learner = Model([1.] * 5), TDLeafEpisode(eta=.1)
    for ply in range(3):
        if env.terminal() is not None:
            break
        before = env.record()
        receipt = AlphaBeta(1, 0).search(env, model, seed=ply)
        assert env.record() == before and receipt.complete
        learner.observe(model, receipt)
        env.push(receipt.action)
    assert env.terminal() == 1
    assert learner.finish(model, env.terminal())['changed']
    assert model.weights[0] == 1. and model.weights[4] > 1.


@pytest.mark.parametrize('outcome,expected', [('WIN', 1), ('LOSS', -1),
                                            ('RESTART', None), ('NO_CONTEST', None)])
def test_all_owned_declarations_keep_their_actual_meaning(outcome, expected):
    env = FixedScaleSessionEnv(declaration_session(outcome), unit_type='R')
    before = env.record()
    choice = next(c for c in env.actions() if c.kind == 'DECLARATION')
    env.push(choice)
    assert env.replay().record() == env.record()
    if expected is None:
        with pytest.raises(NonScoringTerminal):
            env.terminal()
    else:
        assert env.terminal() == expected
    env.pop()
    assert env.record() == before and env.terminal() is None


def test_search_cancellation_restores_full_history_and_has_no_training_sample():
    env = FixedScaleSessionEnv(declaration_session('WIN'), unit_type='R')
    model = Model([1.] * len(env.names))
    before, weights = env.record(), model.weights[:]
    polls = 0

    def cancel():
        nonlocal polls
        polls += 1
        if polls >= 3:
            raise BudgetEnd('STOPPED_USER')

    receipt = AlphaBeta(5, 0).search(env, model, nodes=4096, cancel=cancel)
    assert not receipt.complete and receipt.reason == 'STOPPED_USER'
    assert receipt.action is None and receipt.samples == ()
    assert env.record() == before and env.stack == [] and model.weights == weights
    learner = TDLeafEpisode()
    learner.observe(model, receipt)
    assert learner.finish(model, None)['samples'] == 0 and model.weights == weights


def test_generic_qsearch_is_rejected_before_touching_session():
    env = FixedScaleSessionEnv(declaration_session('LOSS'), unit_type='R')
    before = env.record()
    with pytest.raises(ValueError, match='qdepth=0'):
        AlphaBeta(1, 1).search(env, Model([1.] * len(env.names)))
    assert env.record() == before and env.stack == []


def test_promotion_drop_auxiliary_and_history_survive_library_adapter():
    fixtures = weird_rulesets()
    board = [[None] * 8 for _ in range(8)]
    for owner, type_id, file, rank in (
        (0, 'K', 4, 0), (1, 'K', 7, 7), (0, 'R', 0, 0),
        (0, 'R', 0, 1), (0, 'R', 0, 2), (0, 'R', 1, 1),
        (1, 'R', 1, 3), (1, 'R', 1, 4)):
        board[rank][file] = Piece(owner, type_id, type_id)
    rules = replace(fixtures[2], initial_position=tuple(map(tuple, board)),
                    semantic_actions=(fixtures[1].semantic_actions[0], fixtures[2].semantic_actions[0]),
                    drop_allowed={'R': ((True,) * 64, (True,) * 64),
                                  'TP': ((False,) * 64, (False,) * 64)})
    env = FixedScaleSessionEnv(GameSession(compile_ruleset_for_execution(rules)), unit_type='R')
    assert env.names == (('board', 'R'), ('board', 'TP'), ('hand', 'R'), ('hand', 'TP'))
    route = (((1, 1), (1, 3), False), ((7, 7), (6, 7), False),
             ((1, 3), (1, 4), False), ((6, 7), (5, 7), False),
             ((0, 0), (1, 1), True), ((5, 7), (4, 7), False),
             (None, (0, 0), False), ((4, 7), (3, 7), False))
    for ply in range(9):
        assert env.replay().record() == env.record()
        quantities = dict(zip(env.names, env.features()))
        if ply == 5:
            assert quantities[('board', 'TP')] == 1
            assert dict(env.session.state.position.aux_state)[(0, -1)] == 1
        if ply == 6:
            assert dict(env.session.state.position.aux_state)[(0, -1)] == 0
        if ply == 8:
            assert env.session.state.position.hands[0].count('R') == 1
            break
        source, target, semantic = route[ply]
        candidates = []
        for choice in env.actions():
            action = choice.action
            if choice.kind != 'ACTION' or (action.to_square.file, action.to_square.rank) != target:
                continue
            hit = hasattr(action, 'base_type_id') if source is None else (
                hasattr(action, 'from_square') and
                (action.from_square.file, action.from_square.rank) == source and
                action.pattern_id.startswith('sem_') == semantic)
            if hit:
                candidates.append(choice)
        choice, = candidates
        before = env.record()
        env.push(choice)
        env.replay()
        env.pop()
        assert env.record() == before
        env.push(choice)


def test_failed_push_is_atomic_and_invalid_numerics_are_rejected():
    env = FixedScaleSessionEnv(declaration_session('WIN'), unit_type='R')
    before = env.record()
    with pytest.raises(ValueError, match='mixed'):
        env.push(SessionChoice('ACTION', declaration_id='claim'))
    assert env.record() == before and env.stack == []
    for scale in (float('nan'), float('inf'), -1., 0.):
        with pytest.raises(ValueError):
            Model([1., 1.], scale=scale)
    with pytest.raises(ValueError, match='outcome'):
        TDLeafEpisode().finish(Model([1., 1.]), .5)


def test_episode_checks_real_terminal_after_last_allowed_move():
    env = ChessEnv(chess.Board('7k/8/5KQ1/8/8/8/8/8 w - - 0 1'))
    model, opponent = Model([1.] * 5), Model([1.] * 5)
    result = play_episode(env, model, opponent=opponent, horizon=1, depth=1)
    assert result.outcome == 1 and result.ending == 'ACTUAL_TERMINAL'
    assert result.plies == result.queries == 1 and result.update is None


def test_stopped_episode_starts_no_query_and_censored_episode_has_no_draw_target():
    env = ChessEnv()
    model, opponent = Model([1.] * 5), Model([1.] * 5)
    before = env.record()

    def stopped():
        raise BudgetEnd('STOPPED_USER')

    result = play_episode(env, model, opponent=opponent, learner=TDLeafEpisode(), cancel=stopped)
    assert result.queries == result.nodes == result.plies == 0
    assert result.outcome is None and result.update['censored']
    assert env.record() == before
    result = play_episode(env, model, opponent=opponent, learner=TDLeafEpisode(),
                          max_nodes=1, horizon=8)
    assert result.nodes == 1 and result.outcome is None and result.plies == 0
    assert result.update['samples'] == 0 and env.record() == before


def test_search_non_scoring_terminal_keeps_cost_but_never_creates_a_target():
    env = FixedScaleSessionEnv(declaration_session('NO_CONTEST'), unit_type='R')
    model = Model([1.] * len(env.names))
    before = env.record()
    result = play_episode(env, model, opponent=Model(model.weights), learner=TDLeafEpisode())
    assert result.outcome is None and result.nodes > 0 and result.queries == 1
    assert result.update['samples'] == 0 and env.record() == before
