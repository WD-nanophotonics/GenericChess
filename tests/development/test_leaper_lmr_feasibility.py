import inspect
import pytest
from scripts import leaper_design as L
from scripts.leaper_lmr_feasibility import LateQuietReduction, transform
from generic_chess.ai.alphabeta import search as S
from generic_chess.ai.alphabeta.player import AlphaBetaPlayer
from generic_chess.ai.alphabeta.tuning import SearchTuning
from generic_chess.ai.limits import SearchLimits


def fixture():
    c = L.compile_rule(L.definition(1, 8))
    return c, L.GameSession(c)


def test_disabled_transform_preserves_real_core_action_value_work_and_state():
    c, s = fixture()
    before = L.record_value(s.to_record())
    limits = SearchLimits(max_depth=4, max_nodes=20000)
    def run():
        return AlphaBetaPlayer(c, use_disk_cache=False, tuning=SearchTuning(use_pvs=True)).choose_action(s, limits)
    a = run()
    with LateQuietReduction(False) as policy:
        b = run()
    for key in ('action', 'score', 'completed_depth', 'nodes', 'qnodes', 'principal_variation', 'tt_hits', 'tt_cutoffs'):
        assert getattr(a, key) == getattr(b, key)
    assert not policy.counts
    assert L.record_value(s.to_record()) == before


def test_source_contract_and_exception_restore():
    original = S.negamax
    transform(inspect.getsource(original))
    with pytest.raises(RuntimeError, match='injected'):
        with LateQuietReduction():
            raise RuntimeError('injected')
    assert S.negamax is original
    assert not hasattr(S, '_research_lmr')


def test_live_cancellation_does_not_mutate_complete_history_or_leave_patch():
    c, s = fixture()
    before = L.record_value(s.to_record())
    class Cancel:
        def is_cancelled(self):
            return True
    original = S.negamax
    with LateQuietReduction():
        d = AlphaBetaPlayer(c, use_disk_cache=False, tuning=SearchTuning(use_pvs=True)).choose_action(
            s, SearchLimits(max_depth=8, max_nodes=10000), cancel_token=Cancel())
    assert d.termination_reason == 'cancelled'
    assert L.record_value(s.to_record()) == before
    assert S.negamax is original
