"""Ranked saved-history inference, tested against independent finite games."""
from copy import deepcopy
from itertools import product
import pytest
from scripts.leaper_explorer_truth import digest
from scripts.leaper_saved_child_bounds import propagate, summarize_children, meet


def root(hid, ply, bounds=None, coop=None):
    return dict(id=hid, ply=ply, fingerprint='fp', wdl_bounds=bounds or [-1, 1],
                wdl_fork=None, cooperative_decisive=coop,
                universal_draw=None if coop is None else not coop, action_bounds=[])


def edge(hid, ply, ac, *, terminal='ongoing', winner=None, parent=0, child=1):
    return dict(child_id=hid, child_ply=ply, action={'id':ac}, terminal=terminal,
                terminal_winner=winner, parent_mover=parent, child_mover=child)


def packet(truth, rows):
    return dict(format='leaper-saved-child-bounds-v1', input_digest=digest(truth), rows=rows)


def row(hid, ply, children):
    return dict(id=hid, fingerprint='fp', ply=ply, children=children)


def test_exhaustive_interval_choices_contain_every_discrete_completion():
    intervals = [[-1,-1], [-1,0], [-1,1], [0,0], [0,1], [1,1]]
    for bs in product(intervals, repeat=3):
        result = summarize_children([dict(wdl_bounds=b, cooperative_decisive=None) for b in bs])
        possible = list(product(*(range(b[0], b[1]+1) for b in bs)))
        assert result['wdl_bounds'] == [min(max(v) for v in possible), max(max(v) for v in possible)]
        forks = {len(set(v)) > 1 for v in possible}
        assert result['wdl_fork'] is (next(iter(forks)) if len(forks)==1 else None)


def test_descending_ply_closes_a_saved_loss_then_parent_win_without_new_expansion():
    t = dict(roots=[root('a',0), root('b',1)])
    q = packet(t, [row('a',0,[edge('b',1,'ab')]),
                   row('b',1,[edge('terminal',2,'bt',terminal='checkmate',winner=0,parent=1,child=0)])])
    out, changes = propagate(t,q)
    assert [r['wdl_bounds'] for r in out['roots']] == [[1,1],[-1,-1]]
    assert [r['id'] for r in changes] == ['b','a']
    assert all(r['cooperative_decisive'] for r in out['roots'])
    assert t['roots'][0]['wdl_bounds'] == [-1,1]


def test_missing_ongoing_child_remains_unknown_even_if_one_saved_draw_exists():
    t = dict(roots=[root('a',0),root('draw',1,[0,0],False)])
    q = packet(t,[row('a',0,[edge('draw',1,'a'),edge('missing',1,'b')])])
    r = propagate(t,q)[0]['roots'][0]
    assert r['wdl_bounds']==[0,1] and r['wdl_fork'] is None
    assert r['cooperative_decisive'] is None


def test_full_history_identity_never_falls_back_to_matching_position_or_prefix():
    t = dict(roots=[root('a',0),root('same_position_other_history',1,[-1,-1],True)])
    q = packet(t,[row('a',0,[edge('not_saved_history',1,'x')])])
    r = propagate(t,q)[0]['roots'][0]
    assert r['wdl_bounds']==[-1,1] and r['wdl_fork'] is False


def test_same_side_move_does_not_negate_and_switched_move_does():
    t = dict(roots=[root('a',0),root('b',1,[1,1],True)])
    q = packet(t,[row('a',0,[edge('b',1,'x',parent=0,child=0)])])
    assert propagate(t,q)[0]['roots'][0]['wdl_bounds']==[1,1]
    q['rows'][0]['children'][0]['child_mover']=1
    assert propagate(t,q)[0]['roots'][0]['wdl_bounds']==[-1,-1]


def test_known_win_does_not_make_all_actions_winning_or_close_fork_false():
    t = dict(roots=[root('a',0),root('b',1,[-1,-1],True)])
    q = packet(t,[row('a',0,[edge('b',1,'x'),edge('missing',1,'y')])])
    r = propagate(t,q)[0]['roots'][0]
    assert r['wdl_bounds']==[1,1] and r['wdl_fork'] is None
    assert r['action_bounds'][1]['wdl_bounds']==[-1,1]


def test_cooperative_children_are_not_minimax_wins():
    t = dict(roots=[root('a',0),root('b',1,[0,0],True)])
    q = packet(t,[row('a',0,[edge('b',1,'x')])])
    r = propagate(t,q)[0]['roots'][0]
    assert r['wdl_bounds']==[0,0] and r['cooperative_decisive'] is True
    assert r['universal_draw'] is False


def test_no_contest_does_not_prove_draw_or_no_cooperative_path():
    t = dict(roots=[root('a',0)])
    q = packet(t,[row('a',0,[edge('nc',1,'x',terminal='no_contest')])])
    r = propagate(t,q)[0]['roots'][0]
    assert r['wdl_bounds']==[-1,1] and r['cooperative_decisive'] is None


@pytest.mark.parametrize('change', ['source','duplicate','rank','rule','child_rule','old_action','conflict'])
def test_invalid_source_rank_rule_coverage_or_contradiction_rejects(change):
    t = dict(roots=[root('a',0),root('b',1,[-1,-1],True)])
    if change=='old_action':
        t['roots'][0]['action_bounds']=[dict(action={'id':'omitted'},wdl_bounds=[0,0])]
    if change=='conflict': t['roots'][0]['wdl_bounds']=[-1,-1]
    if change=='child_rule': t['roots'][1]['fingerprint']='other'
    q = packet(t,[row('a',0,[edge('b',1,'x')])])
    if change=='source': q['input_digest']='bad'
    if change=='duplicate': q['rows'] += deepcopy(q['rows'])
    if change=='rank': q['rows'][0]['children'][0]['child_ply']=0
    if change=='rule': q['rows'][0]['fingerprint']='other'
    with pytest.raises(ValueError): propagate(t,q)


def test_integer_intervals_reject_bool_and_contradictory_intersections():
    with pytest.raises(ValueError): meet([False,1],[-1,1])
    with pytest.raises(ValueError): meet([-1,-1],[0,1])


def test_actual_core_history_tree_matches_independent_fixed_player_minimax():
    """Small constructed H3 integration control; no new experiment sample."""
    from scripts.leaper_microgames import make_rules
    from generic_chess.rules.compiler import compile_ruleset_for_execution
    from generic_chess.core.transition import initial_state, legal_successors
    from scripts.leaper_saved_child_bounds import edge as actual_edge
    from scripts.leaper_design import state_sha
    c=compile_ruleset_for_execution(make_rules(horizon=3))
    states={};edges={};exact={}
    def walk(s):
        if s in exact:return exact[s]
        if s.terminal_status.is_terminal:
            t=s.terminal_status
            value=0 if t.winner is None else 1 if t.winner==0 else -1
        else:
            es=list(legal_successors(s,c));edges[s]=es;states[state_sha(s)]=s
            values=[walk(ch)for _,ch in es]
            value=(max if s.position.side_to_move==0 else min)(values)
        exact[s]=value
        return value
    walk(initial_state(c))
    roots=[root(h,s.ply_count)for h,s in states.items()]
    for r in roots:r['fingerprint']=c.ruleset_fingerprint
    t=dict(roots=roots)
    rows=[dict(id=h,ply=s.ply_count,fingerprint=c.ruleset_fingerprint,
               children=[actual_edge(s,a,ch)for a,ch in edges[s]])for h,s in states.items()]
    out,_=propagate(t,packet(t,rows))
    assert len(out['roots'])>10
    for r in out['roots']:
        s=states[r['id']];sign=1 if s.position.side_to_move==0 else -1
        assert r['wdl_bounds']==[sign*exact[s]]*2
        assert r['wdl_fork']==(len({exact[ch]for _,ch in edges[s]})>1)


@pytest.mark.parametrize('damage',['omitted','wrong_child_history','terminal_winner','mover'])
def test_independent_core_verifier_rejects_forged_edge_or_missing_legal_action(damage):
    import json
    from scripts.leaper_microgames import make_rules
    from generic_chess.rules.compiler import compile_legacy_ruleset_for_semantic_execution as compile_ruleset_for_execution
    from generic_chess.rules.schema import ruleset_to_dict
    from generic_chess.session.session import GameSession
    from generic_chess.session.serialization import serialize_game_record
    from generic_chess.core.transition import legal_successors
    from scripts.leaper_saved_child_bounds import edge as actual_edge,verify
    from scripts.leaper_design import state_sha
    c=compile_ruleset_for_execution(make_rules(horizon=3));s=GameSession(c)
    record=json.loads(serialize_game_record(s.to_record()));hid=state_sha(s.state)
    r=root(hid,0);r.update(fingerprint=c.ruleset_fingerprint,record_id='record')
    t=dict(roots=[r],rules={c.ruleset_fingerprint:ruleset_to_dict(make_rules(horizon=3))},
           records={'record':record})
    children=[actual_edge(s.state,a,ch)for a,ch in legal_successors(s.state,c)]
    assert len(children)>1
    q=packet(t,[dict(id=hid,ply=0,fingerprint=c.ruleset_fingerprint,children=children)])
    if damage=='omitted':q['rows'][0]['children'].pop()
    if damage=='wrong_child_history':children[0]['child_id']='same_position_wrong_history'
    if damage=='terminal_winner':children[0]['terminal_winner']=0
    if damage=='mover':children[0]['child_mover']=children[0]['parent_mover']
    with pytest.raises(ValueError,match='Core successor'):
        verify(t,q)
