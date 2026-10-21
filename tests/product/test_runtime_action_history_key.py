"""Consecutive action adjudication must survive exact-history TT reuse."""
from dataclasses import replace

import pytest

from generic_chess.ai.alphabeta.player import AlphaBetaPlayer
from generic_chess.ai.alphabeta.tuning import SearchTuning
from generic_chess.ai.limits import SearchLimits
from generic_chess.core.actions import PassAction, SemanticBoardMove
from generic_chess.core.identity import search_state_identity
from generic_chess.core.pieces import Piece, PieceType
from generic_chess.core.search_runtime import RuntimeHistoryContext, SearchPathRuntime
from generic_chess.core.terminal import TerminalStatus
from generic_chess.rules.compiler import compile_semantic_ruleset
from generic_chess.rules.schema import (
    RuleConsecutiveActionAdjudication, RuleGeometrySpec, RuleSemanticAction,
)
from generic_chess.session.session import GameSession
from rule_semantics_ir_fixtures import _king_type, _semantic_ruleset


def pair(policy=True):
    rows = [[None] * 5 for _ in range(5)]
    rows[0][0] = Piece(0, 'K', 'K')
    rows[4][4] = Piece(1, 'K', 'K')
    rows[1][1] = Piece(0, 'A', 'A')
    rows[3][3] = Piece(1, 'A', 'A')
    noop = RuleSemanticAction(
        name='board_noop', type_ids=('A',),
        geometry=RuleGeometrySpec(kind='leap', offset=(1, 0)),
        target_relation='empty', effects=(), composition='augment',
    )
    rules = replace(
        _semantic_ruleset((_king_type(), PieceType('A', 'A', ())), (noop,),
                          n=5, rows=tuple(tuple(row) for row in rows)),
        pass_enabled=True, repetition_limit=20,
        consecutive_action_adjudications=(
            (RuleConsecutiveActionAdjudication('pass', 2, 'DRAW'),) if policy else ()
        ),
    )
    compiled = compile_semantic_ruleset(rules)
    left, right = GameSession(compiled), GameSession(compiled)
    left.submit(PassAction())
    right.submit(next(a for a in right.legal_actions()
                      if isinstance(a, SemanticBoardMove) and a.pattern_id.startswith('sem_')))
    assert left.state.position == right.state.position
    assert left.state.ply_count == right.state.ply_count
    assert left.state.repetition_counts == right.state.repetition_counts
    return compiled, left, right


@pytest.mark.parametrize('collide', [False, True])
def test_identical_positions_with_different_future_draws_have_distinct_keys(monkeypatch, collide):
    if collide:
        monkeypatch.setattr(RuntimeHistoryContext, '_record_digest',
                            staticmethod(lambda *_args: bytes(16)))
    compiled, left, right = pair()
    runtimes = [SearchPathRuntime(s.state, compiled, history_witnesses=s._search_witnesses)
                for s in (left, right)]
    assert all(rt.tt_eligible for rt in runtimes)
    assert runtimes[0].search_key() != runtimes[1].search_key()
    assert search_state_identity(left.state, compiled) != search_state_identity(right.state, compiled)
    statuses = []
    for runtime in runtimes:
        before = runtime.search_key()
        with runtime.pushed(PassAction()):
            statuses.append(runtime.terminal_status.status)
        runtime.assert_balanced()
        assert runtime.search_key() == before
    assert statuses == [TerminalStatus.ACTION_CLASS_DRAW, TerminalStatus.ONGOING]


@pytest.mark.parametrize('collide', [False, True])
def test_warm_public_search_does_not_reuse_the_other_action_history(monkeypatch, collide):
    if collide:
        monkeypatch.setattr(RuntimeHistoryContext, '_record_digest',
                            staticmethod(lambda *_args: bytes(16)))
    compiled, left, right = pair()

    class ConstantLeaf:
        def evaluate(self, state):
            return 7

    def player():
        return AlphaBetaPlayer(compiled, evaluator_override=ConstantLeaf(),
                               use_disk_cache=False, use_native_semantic_legality=False,
                               tuning=SearchTuning(use_root_tactical=False))

    limits = SearchLimits(max_depth=1, quiescence_max_depth=0, quiescence_hard_max_depth=0)
    shared = player()
    assert shared.choose_action(left, limits).score == 0
    warm = shared.choose_action(right, limits)
    cold = player().choose_action(right, limits)
    assert warm.score == cold.score == -7
    assert warm.action == cold.action
    assert warm.principal_variation == cold.principal_variation


def test_irrelevant_action_signatures_do_not_disable_plain_history_reuse():
    compiled, left, right = pair(False)
    runtimes = [SearchPathRuntime(s.state, compiled, history_witnesses=s._search_witnesses)
                for s in (left, right)]
    assert runtimes[0].search_key() == runtimes[1].search_key()
    assert search_state_identity(left.state, compiled) == search_state_identity(right.state, compiled)
    for runtime in runtimes:
        with runtime.pushed(PassAction()):
            assert runtime.terminal_status.status is TerminalStatus.ONGOING
        runtime.assert_balanced()
