"""Thin diagnostic cannot silently pretend Native calls poll internally."""
import pytest
from scripts.root_bound_diagnostic import root_search
from tests.development.test_bounded_root_scheduler import ChangingHorizon


class PollingBoard(ChangingHorizon):
    semantic_checkpoint_supported = True
    checkpoint = None

    def actions(self):
        if self.checkpoint is not None:
            self.checkpoint()
        return super().actions()

    def push(self, move):
        if self.checkpoint is not None:
            self.checkpoint()
        super().push(move)


def test_callback_restored_on_completed_and_semantic_abort(monkeypatch):
    from scripts import root_bound_diagnostic as diagnostic
    board=PollingBoard();old=lambda:None;board.checkpoint=old
    r=root_search(board,2,cooperative=True)
    assert r['completed_depth']==2 and r['work']['semantic_polls']>0
    assert board.checkpoint is old and board.restored()
    clock=[0.]
    monkeypatch.setattr(diagnostic,'perf_counter',lambda:clock[0])
    actions=board.actions
    def timed_actions():
        clock[0]=2.
        return actions()
    board.actions=timed_actions
    r=root_search(board,2,seconds=1,cooperative=True)
    assert r['exit_cause']=='time_limit' and r['completed_depth']==0
    assert board.restored() and board.checkpoint is old


def test_attribute_without_semantic_support_is_rejected():
    board=ChangingHorizon();board.checkpoint=None
    with pytest.raises(ValueError,match='internal semantic'):
        root_search(board,2,cooperative=True)
    assert board.checkpoint is None and board.restored()


def test_live_cancel_and_node_precedence():
    class Token:
        def is_cancelled(self):return True
    board=PollingBoard()
    r=root_search(board,2,node_limit=0,seconds=0,cooperative=True,cancellation=Token())
    assert r['exit_cause']=='node_budget'
    r=root_search(board,2,node_limit=100,seconds=0,cooperative=True,cancellation=Token())
    assert r['exit_cause']=='cancelled' and board.checkpoint is None
