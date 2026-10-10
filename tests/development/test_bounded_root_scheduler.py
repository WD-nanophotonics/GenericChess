"""Completed iteration, fallback and literal deadline behavior of shared caller."""
from scripts.bounded_root_scheduler import iterative_root_search
from scripts.root_bound_diagnostic import root_search

class ChangingHorizon:
    def __init__(self): self.path=[]
    def actions(self):
        if not self.path:return [('b','b'),('a','a')]
        if len(self.path)==1:return [('x','x'),('y','y')]
        return []
    def push(self,move):self.path.append(move)
    def pop(self):self.path.pop()
    def restored(self):return not self.path
    def terminal(self,ply):
        if len(self.path)==2:return {'a':5,'b':3}[self.path[0]]
        return None
    def evaluate(self):return {'a':0,'b':-1}[self.path[0]]

def test_shared_cap_keeps_last_complete_iteration_not_partial_candidate():
    low=iterative_root_search(ChangingHorizon(),seconds=30,node_limit=4,max_depth=2)
    full=iterative_root_search(ChangingHorizon(),seconds=30,node_limit=100,max_depth=2)
    assert low['move']=='b' and low['completed_depth']==1 and low['score']==1
    assert low['work']['nodes']==4 and low['exit_cause']=='node_budget'
    assert low['pv_labels']==['b'] and low['root_restored']
    assert full['move']=='a' and full['score']==5 and full['completed_depth']==2
    assert full['pv_labels']==['a','x'] and full['root_restored']

def test_preparation_overrun_uses_legal_fallback_without_search_or_fake_depth():
    result=iterative_root_search(ChangingHorizon(),seconds=0,node_limit=100,max_depth=2)
    assert result['used_fallback'] and result['move']=='b' and result['score'] is None
    assert result['completed_depth']==0 and result['work']['nodes']==0
    assert result['exit_cause']=='time_limit' and result['pv_labels']==['b']
    assert result['caller_seconds']>=result['budgeted_seconds']


def test_searched_frontier_labels_skip_only_independent_replay():
    for nodes in (4, 100):
        replay = iterative_root_search(ChangingHorizon(), seconds=30,
            node_limit=nodes, max_depth=2)
        captured = iterative_root_search(ChangingHorizon(), seconds=30,
            node_limit=nodes, max_depth=2, validate_pv=False)
        for key in ('move', 'score', 'pv_labels', 'completed_depth', 'work'):
            assert captured[key] == replay[key]
        assert replay['pv_validation'] == 'independent_replay'
        assert captured['pv_validation'] == 'searched_frontiers'
        assert captured['root_restored'] and captured['validation_seconds'] >= 0

def test_deadline_during_child_unwinds_board_and_reports_actual_cause(monkeypatch):
    from scripts import root_bound_diagnostic as diagnostic
    board=ChangingHorizon();clock={'now':0.}
    original=board.terminal
    def terminal(ply):
        result=original(ply)
        if ply==2:clock['now']=2.
        return result
    board.terminal=terminal
    monkeypatch.setattr(diagnostic,'perf_counter',lambda:clock['now'])
    result=root_search(board,2,seconds=1,node_limit=100)
    assert result['completed_depth']==0 and result['reason']=='budget'
    assert result['exit_cause']=='time_limit' and result['root_restored']
    assert result['work']['nodes']<100 and result['action'] is None
