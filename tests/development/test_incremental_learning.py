"""Opt-in incremental TDLeaf: independent arithmetic and real rule authority."""
from dataclasses import replace
from math import tanh

import chess
import pytest

from generic_chess.core.pieces import Piece
from generic_chess.learning.incremental import (
    AlphaBeta, BudgetEnd, ChessEnv, FixedScaleSessionEnv, Model,
    NonScoringTerminal, Receipt, SessionChoice, TDLeafEpisode, compile_channels,
    play_episode, completed_depth_search,
)
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.schema import RuleDeclaration, RuleNoProgressDraw
from generic_chess.session.session import GameSession
from scripts.generic_proof_fixtures import krk_ruleset
from rule_semantics_ir_fixtures import weird_rulesets


def test_iterative_retains_only_complete_shallow_target_and_pays_partial_work():
    env = ChessEnv()
    model = Model([1.] * 5)
    before = env.record()
    shallow = AlphaBeta(1, 0).search(env, model, nodes=100, seed=42)
    receipt = completed_depth_search(env, model, depth=2, nodes=30, seed=42)
    assert receipt.complete and receipt.completed_depth == 1
    assert receipt.attempted_depth == 2
    assert receipt.nodes == 30 == sum(a.nodes for a in receipt.attempts)
    assert [(a.depth, a.complete) for a in receipt.attempts] == [(1, True), (2, False)]
    assert receipt.action == shallow.action and receipt.value == shallow.value
    assert receipt.pv_phi == shallow.pv_phi and receipt.samples == shallow.samples
    assert env.record() == before
    learner = TDLeafEpisode()
    learner.observe(model, receipt)
    assert len(learner.rows) == 1
    assert learner.finish(model, None)['samples'] == 0  # No fabricated final draw.


@pytest.mark.parametrize('nodes,complete,depth', [(1, False, 0), (21, True, 1), (1000, True, 2)])
def test_iterative_node_boundary_and_completed_depth(nodes, complete, depth):
    env = ChessEnv()
    receipt = completed_depth_search(env, Model([1.] * 5), nodes=nodes, seconds=10)
    assert receipt.complete is complete and receipt.completed_depth == depth
    assert receipt.nodes <= nodes
    assert receipt.nodes == sum(a.nodes for a in receipt.attempts)
    if not complete:
        assert receipt.action is receipt.value is receipt.pv_phi is None
        assert receipt.samples == ()


def test_iterative_stop_after_d1_discards_fallback_and_restores_history():
    env = ChessEnv()
    before = env.record()
    calls = 0

    def stop():
        nonlocal calls
        calls += 1
        if calls >= 5:  # During the second search, after D1 completed.
            raise BudgetEnd('STOPPED_USER')

    receipt = completed_depth_search(env, Model([1.] * 5), cancel=stop)
    assert not receipt.complete and receipt.reason == 'STOPPED_USER'
    assert receipt.completed_depth == 0 and receipt.action is None
    assert receipt.attempts[0].complete and receipt.nodes >= 21
    assert env.record() == before


def test_iterative_does_not_hide_non_scoring_deeper_branch(monkeypatch):
    from generic_chess.learning import incremental
    calls = 0

    def search(self, env, model, **kwargs):
        nonlocal calls
        calls += 1
        if calls == 1:
            return Receipt('legal', 1., (1.,), False, (), 3, True, 0, .1,
                           'complete', 1, 1)
        assert kwargs['nodes'] == 7
        return Receipt(None, None, None, False, (), 2, False, 0, .1,
                       'Non-scoring terminal is not W/L/D: neutral', 0, 2)

    monkeypatch.setattr(incremental.AlphaBeta, 'search', search)
    receipt = completed_depth_search(None, Model([1.]), nodes=10)
    assert not receipt.complete and receipt.nodes == 5
    assert receipt.action is receipt.value is None and not receipt.samples


def test_iterative_time_allowance_is_shared_and_partial_cost_paid(monkeypatch):
    from generic_chess.learning import incremental
    clock = [0.]
    allowances = []

    def search(self, env, model, **kwargs):
        allowances.append(kwargs['seconds'])
        clock[0] += .6 if self.depth == 1 else .4
        if self.depth == 1:
            return Receipt('legal', 1., (1.,), False, (), 3, True, 0, .6,
                           'complete', 1, 1)
        return Receipt(None, None, None, False, (), 2, False, 0, .4,
                       'resource limit', 0, 2)

    monkeypatch.setattr(incremental.time, 'perf_counter', lambda: clock[0])
    monkeypatch.setattr(incremental.AlphaBeta, 'search', search)
    receipt = completed_depth_search(None, Model([1.]), seconds=1.)
    assert allowances == pytest.approx([1., .4])
    assert receipt.complete and receipt.completed_depth == 1
    assert receipt.seconds == 1. and receipt.nodes == 5


@pytest.mark.parametrize('color', [0, 1])
def test_episode_keeps_opponent_search_fixed_across_candidate_modes(color):
    queries = []
    env = ChessEnv()
    model = Model([1.] * 5)
    result = play_episode(env, model, opponent=Model([1.] * 5),
                          learner_color=color, horizon=2, depth=2, iterative=True,
                          opponent_depth=1, opponent_iterative=False,
                          on_query=lambda ply, actor, r: queries.append((actor, r)))
    assert result.plies == 2
    for actor, receipt in queries:
        if actor == color:
            assert receipt.completed_depth == 2
            assert [a.depth for a in receipt.attempts] == [1, 2]
        else:
            assert receipt.completed_depth == 1 and not receipt.attempts


@pytest.mark.parametrize('iterative', [False, True])
def test_stop_after_receipt_before_commit_withholds_action_and_observation(iterative):
    env = ChessEnv()
    initial = env.record()
    stopped = False

    def cancel():
        if stopped:
            raise BudgetEnd('STOPPED_USER')

    def callback(ply, actor, receipt):
        nonlocal stopped
        assert receipt.complete
        stopped = True

    model = Model([1.] * 5)
    result = play_episode(env, model, opponent=Model([1.] * 5),
                          learner=TDLeafEpisode(), iterative=iterative,
                          cancel=cancel, on_query=callback)
    assert result.ending == 'STOPPED_USER' and result.outcome is None
    assert result.queries == 1 and result.nodes > 0 and result.plies == 0
    assert result.update['observed_searches'] == 0 and result.update['samples'] == 0
    assert env.record() == initial


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
        if ply in (5, 6, 8):
            # Compare the actual post-promotion/drop/aux histories through the
            # shared Core search path and the public session reference.
            model = Model([1.] * len(env.names))
            before = env.record()
            env.use_runtime = False
            reference = AlphaBeta(1, 0).search(env, model, nodes=8192, seconds=10, seed=ply)
            env.use_runtime = True
            current = AlphaBeta(1, 0).search(env, model, nodes=8192, seconds=10, seed=ply)
            assert reference.complete and current.complete
            assert (reference.action, reference.value, reference.pv_phi,
                    reference.pv_terminal, reference.samples, reference.nodes) == (
                    current.action, current.value, current.pv_phi,
                    current.pv_terminal, current.samples, current.nodes)
            assert env.record() == before
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


@pytest.mark.parametrize('candidate_color', [0, 1])
def test_perpetual_loss_trains_actual_player0_return_with_full_history(candidate_color):
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
    class ObservedTDLeaf(TDLeafEpisode):
        def finish(self, model, outcome):
            self.actual_target = outcome
            return super().finish(model, outcome)

    learner = ObservedTDLeaf()
    result = play_episode(env, model, opponent=Model([1.] * 4),
        learner=learner, learner_color=candidate_color, horizon=2, depth=1, seed=0)
    assert result.ending == 'ACTUAL_TERMINAL' and result.outcome == -1
    assert env.session.result.status is SessionStatus.PERPETUAL_CHECK
    assert env.session.result.winner == 1 and result.plies == 2
    assert len(env.record()['actions']) == 8 and len(before['actions']) == 6
    prediction = tanh(.7 / 10.)
    expected = .7 + .05 * (-1 - prediction) * (1 - prediction ** 2) / 10.
    assert learner.actual_target == -1  # Never invert the target for candidate1.
    expected = expected if candidate_color == 0 else .7  # Candidate1 already sees terminal PV.
    assert model.weights == pytest.approx([1., expected, 1., 1.], abs=1e-15)
    assert not result.update['censored']
    if candidate_color == 0:
        assert result.update['terminal_credit_l1'] > 0
    else:
        assert result.update['terminal_credit_l1'] == 0
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


def test_alternate_initial_setup_survives_search_play_and_full_replay():
    from generic_chess.rules.schema import RuleInitialSetupOption
    from generic_chess.session.result import SessionStatus

    rules = krk_ruleset(4)
    board = [None] * 16
    for index, piece in ((1, Piece(0, 'K', 'K')), (3, Piece(1, 'K', 'K')),
                         (8, Piece(0, 'R', 'R'))):
        board[index] = piece
    alternate = tuple(tuple(board[i:i + 4]) for i in range(0, 16, 4))
    rules = replace(rules, initial_setup_options=(RuleInitialSetupOption('mate', alternate),))
    compiled = compile_ruleset_for_execution(rules)
    env = FixedScaleSessionEnv(GameSession(compiled, initial_setup_key='mate'), unit_type='R')
    before = env.record()
    assert before['schema_version'] == 3 and before['initial_setup_key'] == 'mate'
    result = play_episode(env, Model([1., 1.]), opponent=Model([1., 1.]),
                          horizon=1, depth=1)
    assert result.outcome == 1 and env.session.result.status is SessionStatus.CHECKMATE
    assert env.record()['initial_setup_key'] == 'mate'
    assert env.replay().record() == env.record()
    assert FixedScaleSessionEnv(GameSession(compiled), unit_type='R').record() != before


def test_real_pass_action_can_end_the_shared_episode_by_rule_draw():
    from generic_chess.core.actions import PassAction
    from generic_chess.rules.schema import RuleConsecutiveActionAdjudication
    from generic_chess.session.result import SessionStatus

    board = [None] * 16
    for index, piece in ((0, Piece(0, 'K', 'K')), (15, Piece(1, 'K', 'K')),
                         (14, Piece(1, 'R', 'R'))):
        board[index] = piece
    rules = replace(krk_ruleset(4), pass_enabled=True,
        consecutive_action_adjudications=(RuleConsecutiveActionAdjudication('pass', 1, 'DRAW'),),
        initial_position=tuple(tuple(board[i:i + 4]) for i in range(0, 16, 4)))
    env = FixedScaleSessionEnv(GameSession(compile_ruleset_for_execution(rules)), unit_type='R')
    result = play_episode(env, Model([1., 1.]), opponent=Model([1., 1.]),
                          learner=TDLeafEpisode(), horizon=1, depth=1)
    assert result.outcome == 0 and result.ending == 'ACTUAL_TERMINAL'
    assert env.session.result.status is SessionStatus.ACTION_CLASS_DRAW
    assert isinstance(env.session.to_record().actions[-1], PassAction)
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
    # The shared player can commit an already authoritative WIN without
    # needing a scalar comparison or an invented search observation.
    model = Model([1., 1.])
    result = play_episode(env, model, opponent=Model([1., 1.]),
                          learner=TDLeafEpisode(), horizon=1)
    assert result.outcome == 1 and result.ending == 'ACTUAL_TERMINAL'
    assert result.plies == 1 and result.queries == result.nodes == 0
    assert result.update['observed_searches'] == result.update['samples'] == 0
    assert model.weights == [1., 1.] and env.replay().record() == env.record()


def test_winning_declaration_belongs_to_actor_and_keeps_player0_outcome():
    rules = replace(krk_ruleset(4), declarations=(
        RuleDeclaration('win1', 1, require_not_in_check=False, failure_outcome='WIN'),
        RuleDeclaration('neutral1', 1, require_not_in_check=False, failure_outcome='NO_CONTEST')))
    env = FixedScaleSessionEnv(GameSession(compile_ruleset_for_execution(rules)), unit_type='R')
    assert env.player() == 0 and env.winning_declaration() is None
    result = play_episode(env, Model([1., 1.]), opponent=Model([1., 1.]),
                          learner=TDLeafEpisode(), learner_color=1, horizon=2, depth=1)
    assert result.outcome == -1 and env.session.result.winner == 1
    assert result.plies == 2 and result.queries == 1
    assert result.update['observed_searches'] == 0 and not result.update['censored']
    assert env.session.to_record().declaration.declaration_id == 'win1'
    assert env.replay().record() == env.record()


def test_winning_declaration_never_bypasses_stop_after_assessment():
    env = FixedScaleSessionEnv(declaration_session('WIN'), unit_type='R')
    before = env.record()
    polls = 0

    def stop():
        nonlocal polls
        polls += 1
        if polls == 2:
            raise BudgetEnd('STOPPED_USER')

    result = play_episode(env, Model([1., 1.]), opponent=Model([1., 1.]),
                          learner=TDLeafEpisode(), horizon=1, cancel=stop)
    assert result.outcome is None and result.ending == 'STOPPED_USER'
    assert result.nodes == result.queries == result.plies == 0
    assert env.record() == before and result.update['observed_searches'] == 0


def test_winning_declaration_never_bypasses_deadline_after_assessment(monkeypatch):
    from generic_chess.learning import incremental

    env = FixedScaleSessionEnv(declaration_session('WIN'), unit_type='R')
    before = env.record()
    calls = 0

    def clock():
        nonlocal calls
        calls += 1
        return 0. if calls <= 2 else 2.

    monkeypatch.setattr(incremental.time, 'perf_counter', clock)
    result = play_episode(env, Model([1., 1.]), opponent=Model([1., 1.]),
                          learner=TDLeafEpisode(), horizon=1, seconds=1.)
    assert result.outcome is None and result.ending == 'TIME_CAP_UNKNOWN'
    assert result.nodes == result.queries == result.plies == 0 and env.record() == before


def test_known_win_does_not_resume_an_exhausted_episode_node_budget():
    rules = replace(krk_ruleset(4), declarations=(
        RuleDeclaration('win1', 1, require_not_in_check=False, failure_outcome='WIN'),))
    env = FixedScaleSessionEnv(GameSession(compile_ruleset_for_execution(rules)), unit_type='R')
    model = Model([1., 1.])
    probe = AlphaBeta(1, 0).search(env, model, seed=0)
    assert probe.complete
    result = play_episode(env, model, opponent=Model([1., 1.]),
                          horizon=2, depth=1, max_nodes=probe.nodes, seed=0)
    assert result.nodes == probe.nodes and result.queries == result.plies == 1
    assert result.outcome is None and result.ending == 'NODE_CAP_UNKNOWN'
    assert env.winning_declaration().declaration_id == 'win1'
    assert env.session.to_record().declaration is None


def test_capture_then_known_win_trains_from_actual_outcome_without_neutral_label():
    from generic_chess.rules.schema import RuleWeightedMaterialMetric, RuleDeclarationOutcomeBand

    board = [None] * 16
    for index, piece in ((1, Piece(0, 'K', 'K')), (3, Piece(1, 'K', 'K')),
                         (4, Piece(0, 'R', 'R')), (8, Piece(1, 'R', 'R'))):
        board[index] = piece
    declarations = tuple(RuleDeclaration(name, 0, require_not_in_check=False,
        weighted_metric=RuleWeightedMaterialMetric(weights={'R': 1}, include_hands=True),
        outcome_bands=(RuleDeclarationOutcomeBand(2, outcome),), failure_outcome='LOSS')
        for name, outcome in (('win', 'WIN'), ('neutral', 'NO_CONTEST')))
    rules = replace(krk_ruleset(4), capture_disposition='capture_to_hand',
        drop_allowed={'R': ((True,) * 16,) * 2}, declarations=declarations,
        initial_position=tuple(tuple(board[i:i + 4]) for i in range(0, 16, 4)))
    env = FixedScaleSessionEnv(GameSession(compile_ruleset_for_execution(rules)), unit_type='R')
    assert env.winning_declaration() is None
    model = Model([1., 1.])
    receipts = []
    result = play_episode(env, model, opponent=Model([1., 1.]),
        learner=TDLeafEpisode(), learner_color=0, horizon=3, depth=1,
        on_query=lambda ply, actor, receipt: receipts.append((actor, receipt)))
    assert result.outcome == 1 and result.plies == 3 and result.queries == 2
    assert len(receipts) == 2 and receipts[0][1].pv_phi == (1, 1)
    assert not receipts[0][1].pv_terminal
    assert result.update['observed_searches'] == result.update['samples'] == 1
    prediction = tanh(2. / 10.)
    expected = 1. + .05 * (1. - prediction) * (1. - prediction ** 2) / 10.
    assert model.weights == pytest.approx([1., expected], abs=1e-15)
    assert env.session.to_record().declaration.declaration_id == 'win'
    assert env.replay().record() == env.record()


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


def test_coupled_runner_shares_initial_and_seeds_but_not_profile_budgets(monkeypatch, tmp_path):
    import json
    from pathlib import Path
    from types import SimpleNamespace
    from generic_chess.learning.incremental import EpisodeResult
    from scripts import incremental_learning as runner

    clock, calls = [0.], []

    class Env:
        names = ('unit', 'other')
        def __init__(self, *a, **k): self.moves = []
        def terminal(self): return None
        def actions(self): return (0, 1)
        def push(self, a):
            self.moves.append(a)
            clock[0] += .01
        def replay(self): return self
        def record(self): return {'actions': list(self.moves)}

    def play(env, model, **kw):
        learner = kw['learner']
        calls.append((list(model.weights), kw['seed'], kw['learner_color'],
                      env.record(), kw['seconds'], learner is not None))
        kw['on_query'](0, kw['learner_color'], Receipt(None, None, None, False,
            (), kw['max_nodes'], False, 0, .1, 'NODE_CAP_UNKNOWN'))
        clock[0] += .1
        if learner is not None:
            model.weights[1] += learner.lam
        return EpisodeResult(None, 'NODE_CAP_UNKNOWN', 0, 1, kw['max_nodes'], .1,
                             {'changed': True} if learner is not None else None)

    state = tmp_path / '.local_agent'
    state.mkdir()
    for name in ('rollout', 'advisor', 'slack'):
        (state / (name + '.json')).write_text('{}')
    monkeypatch.setattr(runner, 'ROOT', tmp_path)
    monkeypatch.setattr(runner, 'perf_counter', lambda: clock[0])
    monkeypatch.setattr(runner, 'FixedScaleSessionEnv', Env)
    monkeypatch.setattr(runner, 'play_episode', play)
    monkeypatch.setattr(runner.subprocess, 'check_output', lambda *a, **k: 'a' * 40)
    rules = Path(__file__).resolve().parents[2] / 'docs/research/data/incremental_semantic_pilot_20261021.json'
    args = SimpleNamespace(rules=rules, output=tmp_path / 'run', unit='R', seed=19,
        seconds=10., train_episodes=2, eval_pairs=1, train_nodes=10, eval_nodes=10,
        train_seconds=1., eval_seconds=1., compare_lambda=1., td_lambda=.95,
        horizon=2, depth=1, query_nodes=10, game_nodes=10)
    result = runner.run(args)
    # Each arm pays its own10 nodes; each eval profile can play justONE slot.
    assert result['training_episodes'] == 2 and result['evaluation_slots'] == 3
    assert result['missing_evaluation_slots'] == 3
    assert result['status'] == 'PROFILE_CAPS_WITH_MISSING'
    assert calls[0][:4] == calls[1][:4]  # init, search seed, color and opening
    assert all(value == 10 for value in result['costs'].values())
    rows = [json.loads(s) for s in (args.output / 'episodes.jsonl').read_text().splitlines()]
    evaluation = [r for r in rows if r['phase'] == 'eval']
    assert [r['profile'] for r in evaluation] == ['lambda_a', 'lambda_b', 'initial']
    assert evaluation[-1]['weights'] == result['config']['initial_weights']
    assert evaluation[0]['start_record'] == evaluation[1]['start_record'] == evaluation[2]['start_record']
    assert calls[2][1:4] == calls[3][1:4] == calls[4][1:4]
    # Active-time accounting excludes the other profiles' work.
    assert all(0 < value < .2 for value in result['profile_seconds'].values())
    assert result['contrasts']['lambda_b-lambda_a'] == [-2., 2.]
