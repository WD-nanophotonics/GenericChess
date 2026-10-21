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


def declaration_session(outcome, extra_declarations=()):
    board = [None] * 16
    for square, piece in ((1, Piece(0, 'K', 'K')), (3, Piece(1, 'K', 'K')),
                          (8, Piece(0, 'R', 'R'))):
        board[square] = piece
    rules = replace(krk_ruleset(4),
                    initial_position=tuple(tuple(board[y:y + 4]) for y in range(0, 16, 4)),
                    declarations=(RuleDeclaration('claim', 0, require_not_in_check=False,
                                                  failure_outcome=outcome),) + extra_declarations)
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


def test_perpetual_loss_trains_actual_player0_return_with_full_history():
    # This is a played history, not a state-only repetition-count mock. A
    # dummy fixed P unit leaves R free so the sign of the actual update is visible.
    from generic_chess.core.movement import LeapAtom
    from generic_chess.session.result import SessionStatus

    rules = krk_ruleset(4)
    dummy = replace(rules.piece_types[1], type_id='P', movement_atoms=(LeapAtom((0, 1)),))
    board = [None] * 16
    for index, piece in ((0, Piece(0, 'K', 'K')), (15, Piece(1, 'K', 'K')),
                         (2, Piece(0, 'R', 'R'))):
        board[index] = piece
    rules = replace(rules, piece_types=rules.piece_types + (dummy,),
        drop_allowed={**rules.drop_allowed, 'P': ((False,) * 16,) * 2},
        repetition_policy='continuous_check_loss',
        initial_position=tuple(tuple(board[i:i + 4]) for i in range(0, 16, 4)))
    session = GameSession(compile_ruleset_for_execution(rules))
    for source, target in (((2, 0), (3, 0)), ((3, 3), (2, 3)),
                           ((3, 0), (2, 0)), ((2, 3), (3, 3)),
                           ((2, 0), (3, 0)), ((3, 3), (2, 3))):
        session.submit(next(a for a in session.legal_actions()
                            if (a.from_square.file, a.from_square.rank) == source
                            and (a.to_square.file, a.to_square.rank) == target))
    env = FixedScaleSessionEnv(session, unit_type='P')
    before = env.record()
    model = Model([1., .7, 1., 1.])
    result = play_episode(env, model, opponent=Model([1.] * 4),
        learner=TDLeafEpisode(), learner_color=0, horizon=2, depth=1, seed=0)
    assert result.ending == 'ACTUAL_TERMINAL' and result.outcome == -1
    assert env.session.result.status is SessionStatus.PERPETUAL_CHECK
    assert env.session.result.winner == 1 and result.plies == 2
    assert len(env.record()['actions']) == 8 and len(before['actions']) == 6
    prediction = tanh(.7 / 10.)
    expected = .7 + .05 * (-1 - prediction) * (1 - prediction ** 2) / 10.
    assert model.weights == pytest.approx([1., expected, 1., 1.], abs=1e-15)
    assert result.update['terminal_credit_l1'] > 0 and not result.update['censored']
    assert env.replay().record() == env.record()
    assert FixedScaleSessionEnv(session, unit_type='P').record() == before


def test_actual_no_progress_draw_is_distinct_from_external_horizon():
    from generic_chess.session.result import SessionStatus

    rules = replace(krk_ruleset(4), no_progress_draw=RuleNoProgressDraw(1, True))
    env = FixedScaleSessionEnv(GameSession(compile_ruleset_for_execution(rules)), unit_type='R')
    result = play_episode(env, Model([1., 1.]), opponent=Model([1., 1.]),
                          learner=TDLeafEpisode(), horizon=1, depth=1)
    assert result.outcome == 0 and result.ending == 'ACTUAL_TERMINAL'
    assert env.session.result.status is SessionStatus.NO_PROGRESS_DRAW
    assert not result.update['censored'] and env.replay().record() == env.record()


@pytest.mark.parametrize('outcome', ['RESTART', 'NO_CONTEST'])
def test_neutral_declaration_can_still_hide_a_real_win_without_inventing_utility(outcome):
    # Explicitly preserve this conservative limitation; it is not a complete
    # player for a game whose non-scoring actions have no W/L/D utility.
    session = declaration_session('WIN', (
        RuleDeclaration('neutral', 0, require_not_in_check=False, failure_outcome=outcome),))
    env = FixedScaleSessionEnv(session, unit_type='R')
    before = env.record()
    win = next(a for a in env.actions() if a.declaration_id == 'claim')
    env.push(win)
    assert env.terminal() == 1
    env.pop()
    receipt = AlphaBeta(1, 0).search(env, Model([1., 1.]), seed=0)
    assert not receipt.complete and receipt.action is None and receipt.value is None
    assert receipt.nodes > 0 and receipt.samples == () and env.record() == before


@pytest.mark.parametrize('opening_cost', [.25, .75])
def test_runner_charges_opening_time_and_uses_training_deadline(monkeypatch, tmp_path, opening_cost):
    """A slow opening must consume its phase budget before search starts."""
    import json
    from pathlib import Path
    from types import SimpleNamespace
    from generic_chess.learning.incremental import EpisodeResult
    from scripts import incremental_learning as runner

    clock = [0.]
    calls = []

    class OpeningEnv:
        names = (('board', 'R'), ('hand', 'R'))

        def __init__(self, *args, **kwargs):
            self.moves = 0

        def terminal(self):
            return None

        def actions(self):
            return (0,)

        def push(self, action):
            self.moves += 1
            clock[0] += opening_cost

        def replay(self):
            return self

        def record(self):
            return dict(moves=self.moves)

    def episode(env, model, **kwargs):
        training = kwargs['learner'] is not None
        calls.append((training, clock[0], kwargs['seconds']))
        if training:
            # seed0 constructs eight opening plies. The original runner passed
            # five seconds here after spending two, and its cancel ignored5s.
            assert clock[0] == 2. and kwargs['seconds'] == 3.
            clock[0] = 5.
            with pytest.raises(BudgetEnd, match='TRAIN_TIME_CAP'):
                kwargs['cancel']()
        return EpisodeResult(None, 'TRAIN_TIME_CAP' if training else 'HORIZON_UNKNOWN',
                             0, 0, 0, 0., {'changed': False} if training else None)

    state = tmp_path / '.local_agent'
    state.mkdir()
    for name in ('rollout', 'advisor', 'slack'):
        (state / (name + '.json')).write_text('{}')
    monkeypatch.setattr(runner, 'ROOT', tmp_path)
    monkeypatch.setattr(runner, 'perf_counter', lambda: clock[0])
    monkeypatch.setattr(runner, 'FixedScaleSessionEnv', OpeningEnv)
    monkeypatch.setattr(runner, 'play_episode', episode)
    monkeypatch.setattr(runner.subprocess, 'check_output', lambda *a, **k: 'a' * 40 + '\n')
    rules = Path(__file__).resolve().parents[2] / 'docs/research/data/incremental_semantic_pilot_20261021.json'
    args = SimpleNamespace(rules=rules, output=tmp_path / 'run', unit='R', seed=0,
        seconds=10., train_episodes=1, eval_pairs=1, train_nodes=100,
        eval_nodes=100, horizon=2, depth=1, query_nodes=100, game_nodes=100)
    result = runner.run(args)
    if opening_cost == .25:
        assert calls[0][0] and result['training_episodes'] == 1
        assert result['training_phase_seconds'] == 5.
    else:
        assert not any(training for training, _, _ in calls)
        assert result['training_episodes'] == 0
        assert result['training_phase_seconds'] >= 5.
    # Wall-clock guards can finish an already-running atomic operation late;
    # they must never start a query using stale pre-opening remaining time.
    assert all(start < 10. and seconds <= 10. - start for _, start, seconds in calls)
    saved = json.loads((args.output / 'summary.json').read_text())
    assert saved['evaluation_UNKNOWN'] == saved['evaluation_slots']
    assert saved['missing_evaluation_slots'] + saved['evaluation_slots'] == 4
