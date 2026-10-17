"""Session terminals remain authoritative when their Core GameState is ongoing."""
from dataclasses import replace

import pytest

from conftest import make_ruleset, king_type, T
from generic_chess.core.errors import RuleSetMismatchError
from generic_chess.core.movement import LeapAtom
from generic_chess.rules.schema import (
    RuleDeclaration, RuleDeclarationOutcomeBand, RuleWeightedMaterialMetric,
)
from generic_chess.rules.compiler import (
    compile_ruleset, compile_legacy_ruleset_for_semantic_execution,
)
from generic_chess.session.session import GameSession
from generic_chess.ai.alphabeta.player import AlphaBetaPlayer
from generic_chess.ai.cancellation import CancellationToken
from generic_chess.ai.evaluation.config import MATE_SCORE
from generic_chess.ai.limits import SearchLimits


def rules(kind, owner=0):
    rule = make_ruleset(4, [king_type(), T('P', LeapAtom((0, 1)))],
                        lines=['K...', '.P..', '..p.', '...k'])
    if kind != 'RESIGNATION':
        rule = replace(rule, declarations=(RuleDeclaration(
            declaration_id='done', owner=owner, require_not_in_check=False,
            weighted_metric=RuleWeightedMaterialMetric(weights={'K': 1}),
            outcome_bands=(RuleDeclarationOutcomeBand(1, kind),)),))
    return rule


def finish(session, kind, owner):
    if owner:
        session.submit(session.legal_actions()[0])
    assert session.state.position.side_to_move == owner
    if kind == 'RESIGNATION':
        session.resign()
    else:
        session.declare('done')
    assert not session.state.terminal_status.is_terminal
    assert session.legal_actions() == ()


class UnusedEvaluator:
    def evaluate(self, state):
        raise AssertionError('finished session evaluated')


@pytest.mark.parametrize('kind', ['RESIGNATION', 'WIN', 'LOSS', 'RESTART', 'NO_CONTEST'])
@pytest.mark.parametrize('owner', [0, 1])
@pytest.mark.parametrize('cancelled', [False, True])
@pytest.mark.parametrize('compiler', [compile_ruleset, compile_legacy_ruleset_for_semantic_execution])
def test_finished_session_and_record_replay_return_terminal_without_search(
        monkeypatch, kind, owner, cancelled, compiler):
    import generic_chess.ai.alphabeta.player as module
    c = compiler(rules(kind, owner))
    session = GameSession(c)
    finish(session, kind, owner)
    player = AlphaBetaPlayer(c, evaluator_override=UnusedEvaluator(),
                             use_disk_cache=False, use_native_semantic_legality=False)
    def forbidden(*args, **kwargs):
        raise AssertionError('finished session entered search or mutated TT')
    monkeypatch.setattr(module, 'run_root_search', forbidden)
    monkeypatch.setattr(player._tt, 'clear', forbidden)
    token = CancellationToken()
    if cancelled:
        token.cancel()
    for current in (session, GameSession.replay(c, session.to_record())):
        before = current.state, current.to_record(), current._search_witnesses
        result = current.result
        d = player.choose_action(current, SearchLimits(
            max_depth=2, max_nodes=0 if cancelled else 256,
            max_time_seconds=0 if cancelled else 1), cancel_token=token)
        expected = (0 if result.winner is None else
                    MATE_SCORE if result.winner == owner else -MATE_SCORE)
        assert (d.action, d.declaration, d.principal_variation) == (None, None, ())
        assert d.choice_kind == 'TERMINAL'
        assert d.termination_reason == 'terminal_position'
        assert d.result_source == 'terminal' and d.score == expected
        assert (d.nodes, d.qnodes, d.completed_depth, d.evaluation_calls) == (0, 0, 0, 0)
        assert d.native_legality_calls == 0 and d.runtime_depth_balanced is None
        assert player._tt_q_depths is None
        assert before == (current.state, current.to_record(), current._search_witnesses)


@pytest.mark.parametrize('kind', ['RESIGNATION', 'WIN'])
def test_finished_session_shortcut_keeps_ruleset_mismatch_rejection(kind):
    c = compile_legacy_ruleset_for_semantic_execution(rules(kind))
    other = compile_legacy_ruleset_for_semantic_execution(replace(rules(kind), max_ply=513))
    session = GameSession(c)
    finish(session, kind, 0)
    player = AlphaBetaPlayer(other, evaluator_override=UnusedEvaluator(),
                             use_disk_cache=False, use_native_semantic_legality=False)
    with pytest.raises(RuleSetMismatchError):
        player.choose_action(session, SearchLimits(max_depth=1))