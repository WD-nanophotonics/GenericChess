"""Actual-source terminal/history controls; algebra controls are labelled."""
from copy import deepcopy
from dataclasses import replace
import gzip,json
from pathlib import Path
import pytest
from generic_chess.core.actions import action_to_dict
from scripts.leaper_truth_compatibility import bind_context,action_coverage,Context,compare_contexts
from scripts.leaper_terminal_frontier import terminal_frontier

@pytest.fixture(scope='module')
def controls():
    return json.loads(gzip.decompress(Path('tests/fixtures/terminal_frontier_source_controls.json.gz').read_bytes()))

def test_all_rule_horizon_children_are_actual_draw_not_unknown(controls):
    item=controls['max_ply_control'];ctx=bind_context(item['rule'],item['record'])
    before=ctx.identity.copy();result=terminal_frontier(ctx)
    assert ctx.identity==before and ctx.session.state.ply_count==95
    assert result['root_WDL_outer_bounds']==[0,0]
    assert result['Core_terminal_children']==result['ordinary_legal_actions']>1
    assert all(x['wdl_bounds']==[0,0] for x in result['children'])
    assert all(x['regret_bounds']==[0,0] for x in result['action_bounds'])

def mate_parent(controls):
    c=controls['mate_control'];record=deepcopy(c['ends'][1]);record['actions'].pop()
    return c['rule'],record,bind_context(c['rule'],record)

def test_real_terminal_win_labels_fixed_seat_not_child_to_move(controls):
    rule,record,ctx=mate_parent(controls)
    result=terminal_frontier(ctx,value_seat=0)
    assert ctx.session.state.position.side_to_move==1
    assert result['root_WDL_outer_bounds']==[-1,-1]
    mate=next(x for x in result['children']if x['terminal']['status']=='checkmate')
    assert mate['terminal']['winner']==1 and mate['wdl_bounds']==[-1,-1]
    won=next(x for x in result['action_bounds']if x['action']==mate['action'])
    assert won['regret_bounds']==[0,0]
    draw=next(x for x in result['children']if x['terminal']['status']=='stalemate')
    draw_action=next(x for x in result['action_bounds']if x['action']==draw['action'])
    assert draw['wdl_bounds']==[0,0] and draw_action['regret_bounds']==[1,1]
    unknown=[x for x in result['children']if x['truth']=='UNKNOWN_ONGOING']
    assert unknown and all(x['wdl_bounds']==[-1,1]for x in unknown)

def test_value_seat_reversal_preserves_actor_regret(controls):
    rule,record,ctx=mate_parent(controls)
    a=terminal_frontier(ctx,value_seat=0);b=terminal_frontier(ctx,value_seat=1)
    assert a['root_WDL_outer_bounds']==[-1,-1]and b['root_WDL_outer_bounds']==[1,1]
    assert [x['regret_bounds']for x in a['action_bounds']]==[x['regret_bounds']for x in b['action_bounds']]

def test_external_resignation_cannot_be_a_rule_truth_parent(controls):
    item=controls['max_ply_control'];record=deepcopy(item['record']);record['resigned_by']=1
    ctx=bind_context(item['rule'],record)
    with pytest.raises(ValueError,match='external Session'):terminal_frontier(ctx)

def test_actual_terminal_parent_is_rejected(controls):
    c=controls['mate_control'];ctx=bind_context(c['rule'],c['ends'][1])
    with pytest.raises(ValueError,match='ongoing parent'):terminal_frontier(ctx)

@pytest.mark.parametrize('seat',[True,-1,2,'0'])
def test_ambiguous_value_seat_is_rejected(seat,controls):
    item=controls['max_ply_control'];ctx=bind_context(item['rule'],item['record'])
    with pytest.raises(ValueError,match='seat'):terminal_frontier(ctx,value_seat=seat)

def test_incomplete_or_duplicate_context_frontier_fails_closed(controls):
    item=controls['max_ply_control'];ctx=bind_context(item['rule'],item['record'])
    with pytest.raises(ValueError,match='frontier differs'):
        terminal_frontier(replace(ctx,legal_actions=ctx.legal_actions[:-1]))

def test_stale_snapshot_after_real_session_submit_is_rejected(controls):
    c=controls['mate_control'];ctx=bind_context(c['rule'],c['initial'])
    ctx.session.submit(ctx.session.legal_actions()[0])
    with pytest.raises(ValueError,match='snapshot'):terminal_frontier(ctx)

def test_same_board_clock_different_history_never_reuses_context(controls):
    c=controls['history_alias'];a,b=[bind_context(c['rule'],r)for r in c['ends']]
    ra,rb=terminal_frontier(a),terminal_frontier(b)
    assert a.identity['position_sha256']==b.identity['position_sha256']
    assert a.identity['ply']==b.identity['ply']
    assert a.identity['history_sha256']!=b.identity['history_sha256']
    assert ra['context']!=rb['context']
    assert ra['root_WDL_outer_bounds']==rb['root_WDL_outer_bounds']==[-1,1]
    # This controls identity, not a claim that the two true values differ.

def test_horizon_relaxation_does_not_transplant_the_old_zero(controls):
    from generic_chess.rules.schema import ruleset_from_dict,compute_fingerprint
    c=controls['max_ply_control'];old=bind_context(c['rule'],c['record'])
    rule=deepcopy(c['rule']);rule['max_ply']=97
    record=deepcopy(c['record']);record['ruleset_fingerprint']=compute_fingerprint(ruleset_from_dict(rule))
    new=bind_context(rule,record);out=terminal_frontier(new)
    assert compare_contexts(old,new)['status']=='INCOMPATIBLE'
    assert old.identity['position_sha256']!=new.identity['position_sha256'] # rule fingerprint is part of Position
    assert out['ongoing_children']>0 and out['root_WDL_outer_bounds']!=[0,0]

def algebra(count):
    return Context(None,dict(side_to_move=0,terminal=dict(status='ongoing',winner=None)),
                   tuple(dict(kind='abstract',index=i)for i in range(count)))

def test_algebra_only_unknown_absolute_value_can_be_weakly_optimal():
    c=algebra(3)
    labels=[dict(action=a,wdl_bounds=[-1,-1])for a in c.legal_actions[1:]]
    row=action_coverage(c,labels)['rows'][0]
    assert row['wdl_bounds']==[-1,1]and row['regret_bounds']==[0,0]

def test_algebra_only_one_draw_and_one_unknown_have_regret_at_most_one():
    c=algebra(2);r=action_coverage(c,[dict(action=c.legal_actions[0],wdl_bounds=[0,0])])
    assert r['frontier_bounds']==[0,1]
    assert [x['regret_bounds']for x in r['rows']]==[[0,1],[0,1]]


def test_mate_precedence_survives_a_simultaneous_rule_ply_limit(controls):
    from generic_chess.rules.schema import ruleset_from_dict,compute_fingerprint
    c=controls['mate_control'];record=deepcopy(c['ends'][1]);record['actions'].pop()
    rule=deepcopy(c['rule']);rule['max_ply']=len(record['actions'])+1
    record['ruleset_fingerprint']=compute_fingerprint(ruleset_from_dict(rule))
    ctx=bind_context(rule,record);result=terminal_frontier(ctx)
    mate=next(x for x in result['children']if x['terminal']['status']=='checkmate')
    assert mate['ply']==rule['max_ply']and mate['terminal']['winner']==1
    assert mate['wdl_bounds']==[-1,-1]and result['root_WDL_outer_bounds']==[-1,-1]
    assert result['ongoing_children']==0
    assert any(x['terminal']['status']=='max_ply'for x in result['children'])

def test_root_snapshot_tampering_cannot_misattribute_terminal_facts(controls):
    item=controls['max_ply_control'];ctx=bind_context(item['rule'],item['record'])
    identity=dict(ctx.identity);identity['record_sha256']='f'*64
    with pytest.raises(ValueError,match='snapshot'):
        terminal_frontier(replace(ctx,identity=identity))


def draw_option_nodes(controls):
    from generic_chess.core.transition import apply_action
    from generic_chess.core.actions import action_from_dict
    from scripts.research_record import record_value
    c=controls['one_sided_control'];ctx=bind_context(c['rule'],c['record'])
    child=apply_action(ctx.session.state,action_from_dict(c['selected_terminal_action']),ctx.session.compiled)
    assert child.terminal_status.is_terminal and child.terminal_status.winner is None
    nodes=[{'state':record_value(ctx.session.state),'children':[{'action':c['selected_terminal_action'],'state':record_value(child)}]},
           {'state':record_value(child),'children':[]}]
    return ctx,nodes

def test_real_one_terminal_draw_proves_only_a_lower_bound(controls):
    from scripts.leaper_truth_compatibility import verify_bound_tree
    ctx,nodes=draw_option_nodes(controls)
    result=verify_bound_tree(ctx,nodes,0,direction='lower',value_seat=ctx.session.state.position.side_to_move)
    assert result['wdl_bounds']==[0,1]
    assert result['counts']['existential_nodes']==1 and result['counts']['selected_apply_calls']==1
    assert result['counts']['full_frontier_enumerations']==0

def test_real_one_draw_cannot_be_forged_into_an_upper_bound(controls):
    from scripts.leaper_truth_compatibility import verify_bound_tree
    ctx,nodes=draw_option_nodes(controls)
    with pytest.raises(ValueError,match='missing a legal defense'):
        verify_bound_tree(ctx,nodes,0,direction='upper',value_seat=ctx.session.state.position.side_to_move)

def test_real_selected_draw_cannot_be_called_a_complete_draw_tree(controls):
    from scripts.leaper_truth_compatibility import verify_saved_tree
    ctx,nodes=draw_option_nodes(controls)
    for n in nodes:n['value']=0
    with pytest.raises(ValueError,match='exact legal frontier'):
        verify_saved_tree(ctx,nodes,value_seat=ctx.session.state.position.side_to_move)

def test_outer_authority_distinguishes_absolute_value_and_relative_optimality(controls):
    c=controls['mate_control'];ctx=bind_context(c['rule'],c['initial'])
    r=terminal_frontier(ctx)
    assert all(x['absolute_WDL_authority']in ('CORE_TERMINAL','UNKNOWN_ONGOING')for x in r['action_bounds'])
    assert all(x['relative_WDL_optimality']in ('PROVED_OPTIMAL','PROVED_SUBOPTIMAL','UNKNOWN')for x in r['action_bounds'])


def multi_step_example(controls):
    c=controls['multi_step_bound_control']
    return c,bind_context(c['rule'],c['record'])

def test_source_contained_four_edge_stalemate_strategy_is_a_bound_not_draw(controls):
    from scripts.leaper_truth_compatibility import verify_bound_tree
    c,ctx=multi_step_example(controls)
    proof=verify_bound_tree(ctx,c['nodes'],c['bound'],direction=c['direction'],value_seat=0)
    assert ctx.identity['ply']==28 and proof['wdl_bounds']==[-1,0]
    assert proof['counts']['nodes']==5 and proof['counts']['edges']==4
    assert proof['counts']['universal_nodes']==2 and proof['counts']['generated_successors']==2
    assert proof['counts']['existential_nodes']==2
    assert c['nodes'][-1] # exact leaf outcome is checked by Core, not numeric annotations

def test_multistep_source_certificate_cannot_change_its_bound_direction(controls):
    from scripts.leaper_truth_compatibility import verify_bound_tree
    c,ctx=multi_step_example(controls)
    with pytest.raises(ValueError,match='missing a legal defense'):
        verify_bound_tree(ctx,c['nodes'],0,direction='lower',value_seat=0)

def test_multistep_source_certificate_requires_every_continuation(controls):
    from scripts.leaper_truth_compatibility import verify_bound_tree
    c,ctx=multi_step_example(controls)
    nodes=deepcopy(c['nodes'])
    leaf=next(n for n in nodes if not n['children']);nodes.remove(leaf)
    with pytest.raises(ValueError,match='missing bound-certificate continuation'):
        verify_bound_tree(ctx,nodes,0,direction='upper',value_seat=0)

def test_multistep_source_certificate_rejects_false_terminal_state(controls):
    from scripts.leaper_truth_compatibility import verify_bound_tree
    c,ctx=multi_step_example(controls)
    nodes=deepcopy(c['nodes'])
    leaf=next(n for n in nodes if not n['children'])
    leaf['state']['terminal_status']['winner']=0
    with pytest.raises(ValueError):
        verify_bound_tree(ctx,nodes,0,direction='upper',value_seat=0)


def run_partial_fixture(controls,monkeypatch,frontiers=None):
    from scripts import propagate_pvs_terminal_bounds as module
    c=controls['partial_graph_control']
    monkeypatch.setattr(module,'git_bytes',lambda path:gzip.compress(json.dumps(c['games']).encode(),mtime=0))
    return module.propagate(deepcopy(c['frontiers'])if frontiers is None else frontiers)

def test_checked_source_edges_tighten_bounds_without_new_state_expansion(controls,monkeypatch):
    r=run_partial_fixture(controls,monkeypatch)
    earliest=min(r['contexts'],key=lambda x:x['ply'])
    assert earliest['ply']==28 and earliest['derived_bounds']==[-1,0]
    assert r['new_Core_successor_expansions']==0
    assert r['unexpanded_nonterminal_children']>0
    assert all(lo<=0<=hi for lo,hi in (x['derived_bounds']for x in r['contexts']))
    assert r['exact_roots_after']==0 # a drawing strategy is not exact root DRAW

def root_only_graph(controls):
    f=deepcopy(controls['partial_graph_control']['frontiers'])
    key=min(f['contexts'],key=lambda k:f['contexts'][k]['context']['ply'])
    f['contexts']={key:f['contexts'][key]};f['queries']=[q for q in f['queries']if q['context_sha256']==key]
    f['distinct_full_contexts']=1
    return f

def test_missing_source_continuations_stay_unknown_not_draw(controls,monkeypatch):
    f=root_only_graph(controls)
    r=run_partial_fixture(controls,monkeypatch,f)
    assert r['contexts'][0]['derived_bounds']==[-1,1]
    assert r['tightened_distinct_roots']==0

def test_ongoing_source_child_numeric_metadata_is_not_a_terminal_label(controls,monkeypatch):
    f=root_only_graph(controls)
    for row in f['contexts'].values():
        assert row['Core_terminal_children']==0
        for child in row['children']:child['wdl_bounds']=[0,0]
    r=run_partial_fixture(controls,monkeypatch,f)
    assert r['contexts'][0]['derived_bounds']==[-1,1]

def test_linked_source_full_state_mismatch_is_rejected(controls,monkeypatch):
    f=deepcopy(controls['partial_graph_control']['frontiers'])
    last=max(f['contexts'].values(),key=lambda x:x['context']['ply'])
    last['context']['state_sha256']='0'*64
    with pytest.raises(ValueError,match='full state/clock differs'):
        run_partial_fixture(controls,monkeypatch,f)


def horizon_child_action_proofs(controls):
    from generic_chess.core.transition import legal_successors
    from generic_chess.session.serialization import deserialize_game_record
    from scripts.research_record import record_value
    c=controls['max_ply_control'];child_ctx=bind_context(c['rule'],c['record'])
    parent_record=deepcopy(c['record']);parent_record['actions'].pop()
    parent=bind_context(c['rule'],parent_record)
    action=action_to_dict(deserialize_game_record(json.dumps(c['record'])).actions[-1])
    edges=[];leaves=[]
    for move,end in legal_successors(child_ctx.session.state,child_ctx.session.compiled):
        assert end.terminal_status.is_terminal and end.terminal_status.winner is None
        state=record_value(end);edges.append({'action':action_to_dict(move),'state':state})
        leaves.append({'state':state,'children':[]})
    root={'state':record_value(child_ctx.session.state),'children':edges}
    all_nodes=[root,*leaves]
    one_nodes=[{'state':root['state'],'children':edges[:1]},leaves[0]]
    return parent,action,all_nodes,one_nodes

def test_an_ongoing_child_can_have_exact_zero_from_a_separate_certificate(controls):
    from scripts.leaper_truth_compatibility import verify_action_bound
    parent,action,all_nodes,one_nodes=horizon_child_action_proofs(controls)
    lower=verify_action_bound(parent,action,all_nodes,0,direction='lower',value_seat=0)
    upper=verify_action_bound(parent,action,one_nodes,0,direction='upper',value_seat=0)
    assert lower['wdl_bounds']==[0,1] and upper['wdl_bounds']==[-1,0]
    intersection=[max(lower['wdl_bounds'][0],upper['wdl_bounds'][0]),min(lower['wdl_bounds'][1],upper['wdl_bounds'][1])]
    assert intersection==[0,0]
    assert parent.identity['ply']==94 and parent.identity['terminal']['status']=='ongoing'
    coverage=action_coverage(parent,[dict(action=action,wdl_bounds=intersection)])
    selected=next(r for r in coverage['rows']if r['action']==action)
    assert selected['wdl_bounds']==[0,0]
    assert selected['regret_bounds']==[0,1] # exact Q=0 is not proved optimal at this root.

def test_child_certificate_does_not_label_another_action_at_the_same_parent(controls):
    from scripts.leaper_truth_compatibility import verify_action_bound
    parent,action,all_nodes,one_nodes=horizon_child_action_proofs(controls)
    other=next(a for a in parent.legal_actions if a!=action)
    with pytest.raises(ValueError):
        verify_action_bound(parent,other,all_nodes,0,direction='lower',value_seat=0)


def test_non_horizon_strategy_can_be_rechecked_but_not_silently_transferred(controls):
    from scripts.verify_terminal_frontier_proofs import replay_bound_with_horizon
    c=controls['multi_step_bound_control']
    result=replay_bound_with_horizon(c['rule'],c['record'],c['nodes'],0,'upper',97)
    assert result['default_context_attribution']['status']=='INCOMPATIBLE'
    assert result['source_rule_fingerprint']!=result['target_context']['ruleset_fingerprint']
    assert result['status']=='NEW_TARGET_RULE_CERTIFICATE_VERIFIED'
    assert result['target_verified_bound']['wdl_bounds']==[-1,0]
    assert result['target_selected_apply_calls']==4 and result['new_missing_continuations_generated']==0

def test_horizon_certificate_with_new_ongoing_leaves_stays_unknown(controls):
    from generic_chess.core.transition import legal_successors
    from scripts.research_record import record_value
    from scripts.verify_terminal_frontier_proofs import replay_bound_with_horizon
    c=controls['max_ply_control'];ctx=bind_context(c['rule'],c['record'])
    edges=[];leaves=[]
    for action,child in legal_successors(ctx.session.state,ctx.session.compiled):
        assert child.terminal_status.is_terminal and child.terminal_status.winner is None
        state=record_value(child);edges.append({'action':action_to_dict(action),'state':state})
        leaves.append({'state':state,'children':[]})
    nodes=[{'state':record_value(ctx.session.state),'children':edges},*leaves]
    # At seat1 to move, seat0's lower bound needs all replies, so all source
    # DRAW leaves matter; they cannot be guessed after the limit changes.
    result=replay_bound_with_horizon(c['rule'],c['record'],nodes,0,'lower',97)
    assert result['status']=='UNKNOWN_TARGET_CERTIFICATE_NOT_COMPLETE'
    assert result['target_verified_bound']is None
    assert result['target_unresolved_leaves']
    assert result['new_missing_continuations_generated']==0
