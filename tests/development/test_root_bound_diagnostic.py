"""Canonical true ties, inferior bounds and interrupted exact verification."""
import pytest
from native_test_helpers import requires_native
from scripts.root_bound_diagnostic import root_search

class Tree:
    def __init__(self, same=False):
        self.stack=[]
        self.values={'b':(100,100),'a':(100,100 if same else 0)}
    def actions(self):
        if not self.stack:return [('b','b'),('a','a')]
        if len(self.stack)==1:return [('first',0),('second',1)]
        return []
    def push(self,m):self.stack.append(m)
    def pop(self):self.stack.pop()
    def terminal(self,ply):return None
    def evaluate(self):return self.values[self.stack[0]][self.stack[1]]
    def restored(self):return not self.stack

@pytest.mark.parametrize('reverse',[False,True])
@pytest.mark.parametrize('same',[False,True])
def test_verified_selection_matches_exact_root_with_traversal_independent_tie(reverse,same):
    full=root_search(Tree(same),2,mode='full',reverse=reverse)
    verified=root_search(Tree(same),2,mode='verified',reverse=reverse)
    assert (verified['move'],verified['score'])==(full['move'],full['score'])
    assert verified['move']==('a' if same else 'b')
    assert verified['bound']=='EXACT' and verified['completed_depth']==2

def test_equal_bound_reproduces_wrong_canonical_replacement_and_is_repaired():
    unsafe=root_search(Tree(),2,mode='unsafe')
    verified=root_search(Tree(),2,mode='verified')
    assert unsafe['move']=='a' and unsafe['score']==100
    assert verified['move']=='b' and verified['score']==100
    assert verified['candidates'][-1]['bound']=='UPPER'
    assert verified['candidates'][-1]['exact_score']==0

def test_interruption_during_verification_keeps_exact_incumbent_and_marks_incomplete():
    complete=root_search(Tree(),2,mode='verified')
    cap=complete['candidates'][-1]['verification_start_nodes']
    result=root_search(Tree(),2,mode='verified',node_limit=cap)
    assert result['move']=='b' and result['score']==100 and result['bound']=='EXACT'
    assert result['completed_depth']==0 and result['reason']=='budget'
    assert result['work']['nodes']==cap
    assert not result['candidates'][-1]['installed']

@pytest.mark.parametrize('cap',range(1,10))
def test_original_shared_node_cap_is_not_extended(cap):
    result=root_search(Tree(True),2,node_limit=cap)
    assert result['work']['nodes']<=cap and result['root_restored']
    if result['completed_depth']:
        assert result['move']=='a' and result['score']==100


@pytest.mark.parametrize('reverse',[False,True])
@requires_native
def test_full_native_ep_interior_order_changes_bound_but_not_verified_exact_choice(reverse):
    from generic_chess import build_builtin_ruleset,compile_ruleset_for_execution
    from scripts.search_backend_comparison import CoreBoard,CASES,VALUES
    from scripts.native_backend_bridge import NativeBoard
    compiled=compile_ruleset_for_execution(build_builtin_ruleset('western_chess'))
    def run(mode):
        board=NativeBoard(CoreBoard(CASES[3],compiled),VALUES['chess'])
        return root_search(board,3,mode=mode,reverse=reverse,
                           reverse_interior=True,canonical_key=int)
    full,verified=run('full'),run('verified')
    assert (verified['move'],verified['score'])==(full['move'],full['score'])==('f1d3',100)
    assert verified['bound']=='EXACT' and verified['completed_depth']==3
    if not reverse:
        unsafe=run('unsafe')
        assert (unsafe['move'],unsafe['score'])==('f1e2',100)
        entry=next(x for x in verified['candidates'] if x['label']=='f1e2')
        assert entry['bound']=='UPPER' and entry['exact_score']==0 and not entry['installed']
