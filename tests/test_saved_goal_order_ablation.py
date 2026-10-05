import hashlib,json
from pathlib import Path
from types import SimpleNamespace
from scripts.public_goal_intervals import observe
from scripts.saved_contact_proof_graph import SavedContactProofGraph
ROOT=Path(__file__).resolve().parents[1];DATA=ROOT/'docs/research/data'
def inputs():
    return [json.loads((DATA/f'{name}_20261005.json').read_text()) for name in
        ('chess_pinned_queen_mate','chess_pinned_queen_continuation','contact_depth2_dominance')]

def test_common_graph_and_unknown_frontiers_never_become_material_labels():
    graphs=[SavedContactProofGraph(*inputs(),name) for name in ('contact','unit','zero')]
    assert graphs[0].states==graphs[1].states==graphs[2].states
    assert graphs[0].full_actions==graphs[1].full_actions==graphs[2].full_actions
    assert len(graphs[0].states)==49 and len(graphs[0].full_actions)==8
    for graph in graphs:
        for node in graph.states:
            for action in graph.full_actions.get(node,()):
                child=graph.successor(node,action)
                if child not in graph.states:
                    t=graph.terminal(child);assert t.unresolved and t.winner is None
        result=observe((),graph,depth=2,max_transitions=64,max_visits=256,clock=lambda:0)
        assert result['interval']==(-1,1) and result['public_materializations']==0

def test_frozen_depth3_order_results_and_common_interior_order():
    raw=json.loads((DATA/'saved_goal_order_ablation_20261005.json').read_text())
    expected={'contact':((1,1),22),'unit':((1,1),40),'zero':((-1,1),64)}
    for name,(interval,cost) in expected.items():
        graph=SavedContactProofGraph(*inputs(),name)
        result=observe((),graph,depth=3,max_transitions=64,max_visits=256,clock=lambda:0)
        assert result['interval']==interval and result['transitions']==cost
        row=next(row for row in raw['rows'] if row['method']==name and row['depth']==3)
        assert list(result['interval'])==row['observation']['interval']
        for node,actions in graph.full_actions.items():
            if node:assert list(graph.actions(node,lambda:None))==sorted(actions)
    assert raw['complete'] and raw['public_transitions']==raw['source_queries']==0
    for name,pin in raw['source_sha256'].items():assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==pin

def test_permuted_root_order_does_not_change_complete_cached_goal_proof():
    graph=SavedContactProofGraph(*inputs(),'zero')
    orders=[graph.root_order,tuple(reversed(graph.root_order))]
    for order in orders:
        graph.root_order=order
        result=observe((),graph,depth=3,max_transitions=128,max_visits=256,clock=lambda:0)
        assert result['interval']==(1,1)
