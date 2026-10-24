"""The explicit-world reader must bind full rules and every real Core edge."""
from collections import deque
from copy import deepcopy
from dataclasses import replace
import gzip,json
from pathlib import Path
import pytest
from scripts import leaper_design as L
from scripts.leaper_microgames import make_rules
from scripts.leaper_retrograde import fresh_state
from scripts.leaper_cooperative_certificate import encode_position
from scripts.verify_leaper_ab_deadzone import verify
from generic_chess.core.transition import legal_successors

@pytest.fixture
def bare_graph(tmp_path):
    rule=make_rules(width=3,horizon=64)
    ordinary=next(p for p in rule.piece_types if not p.is_anchor)
    rule=replace(rule,piece_types=(rule.piece_types[0],replace(ordinary,type_id='A'),replace(ordinary,type_id='B')),
        drop_allowed={t:((False,)*9,)*2 for t in('A','B')})
    board=[[None]*3 for _ in range(3)]
    board[0][0]=rule.initial_position[0][0]
    board[2][2]=rule.initial_position[2][2]
    rule=replace(rule,initial_position=tuple(map(tuple,board)))
    raw=L.ruleset_to_dict(rule);c=L.compile_rule(rule);ps=[c.initial_position];ix={ps[0]:0};edges=[]
    q=deque([0])
    while q:
        i=q.popleft();ss=fresh_state(ps[i],c);ee=[]
        assert not ss.terminal_status.is_terminal
        for a,ch in legal_successors(ss,c):
            p=ch.position
            if p not in ix:ix[p]=len(ps);ps.append(p);q.append(ix[p])
            ee.append(ix[p])
        edges.append(ee)
    graph=dict(rule=raw,positions=[encode_position(p,c.initial_position)for p in ps],edges=edges,
        relative_values={i:0 for i in range(len(ps))},ranks={},terminals={})
    p=tmp_path/'graph.json.gz';p.write_bytes(gzip.compress(json.dumps(graph).encode(),mtime=0))
    return p,dict(rule=raw),graph,tmp_path/'receipt.json'

def test_explicit_full_source_is_checked_under_its_own_rule(bare_graph):
    p,w,g,out=bare_graph;r=verify(p,out,source_world=w,seconds=10)
    assert r['verified']and r['counts']['vertices']==len(g['positions'])and r['universal_draw']

def test_same_positions_with_a_different_complete_source_are_not_silently_adopted(bare_graph):
    p,w,g,out=bare_graph;bad=deepcopy(w);bad['rule']['max_ply']=63
    with pytest.raises(ValueError,match='complete source rule'):verify(p,out,source_world=bad)

def test_omitted_actual_defender_choice_is_rejected(bare_graph):
    p,w,g,out=bare_graph;assert len(g['edges'][0])>1
    g['edges'][0]=g['edges'][0][:-1];p.write_bytes(gzip.compress(json.dumps(g).encode(),mtime=0))
    with pytest.raises(ValueError,match='complete actual frontier'):verify(p,out,source_world=w)


@pytest.fixture
def response_case(bare_graph):
    from fractions import Fraction
    from scripts.leaper_ab_learner_exposure import restore
    from generic_chess.learning.incremental import FixedScaleSessionEnv,Model,SessionChoice
    from generic_chess.core.actions import action_to_dict
    p,w,g,receipt=bare_graph;base=p.parent/'evidence';(base/'cost').mkdir(parents=True);(base/'uniform').mkdir();(base/'graph').mkdir()
    verify(p,base/'graph/qualification.json',source_world=w)
    c=L.compile_rule(L.ruleset_from_dict(w['rule']));s=L.GameSession(c);initial=L.record_value(s.to_record());pv=[]
    for _ in range(4):
        a=s.legal_actions()[0];pv.append(L.record_value(SessionChoice('ACTION',action=a)));s.submit(a)
    terminal=s.state.terminal_status.is_terminal;phi=None if terminal else list(FixedScaleSessionEnv(s,unit_type='A').features());r=dict(complete=True,completed_depth=4,action=pv[0],pv_choices=pv,pv_phi=phi,pv_terminal=terminal,value=0,nodes=1)
    source=L.GameSession(c);sha=L.state_sha(source.state);row=dict(events=[dict(kind='candidate',state_sha256=sha,receipt=r)])
    cfg=dict(world=dict(rule=w['rule'],roots=[dict(record=initial)]));(base/'cost/plan.json').write_text(json.dumps(cfg))
    cost=base/'cost/game-000.json';cost.write_text(json.dumps(row))
    first=L.match_action(source,r['action']['action']);source.submit(first);children=source.legal_actions();k=len(children)
    nodes=[dict(parent=None,action=None,kind='candidate',children=[1],query=0,state_sha256=sha,ply=0,mass=[1,1]),
        dict(parent=0,action=action_to_dict(first),kind='Uniform',children=list(range(2,2+k)),state_sha256=L.state_sha(source.state),ply=1,mass=[1,1])]
    nodes.extend(dict(parent=1,action=action_to_dict(a),kind=None)for a in children)
    tree=dict(nodes=nodes,frontier=[dict(prefix=i,mass=[1,k])for i in range(2,2+k)],unresolved_response_mass=[0,1])
    treefile=base/'tree.gz';treefile.write_bytes(gzip.compress(json.dumps(tree).encode(),mtime=0))
    qfile=base/'queries.gz';qfile.write_bytes(gzip.compress((json.dumps(dict(prefix=0,state_sha256=sha,reused=True,origin='actual',receipt=r))+'\n').encode(),mtime=0))
    spec=dict(world=cfg['world'],source_cost_sha256=L.sha(cost),graph_sha256=L.sha(p))
    (base/'uniform/spec.json').write_text(json.dumps(spec))
    result=dict(tree_sha256=L.sha(treefile),queries_sha256=L.sha(qfile),counts=dict(expanded_prefixes=2,Uniform_prefixes=1,reused_actual_receipts=1),unresolved_mass=[1,1],WIN0_bounds=[[0,1],[1,1]],leaf_mass={})
    (base/'uniform/result.json').write_text(json.dumps(result))
    return base,p,qfile,treefile,base/'verification.json'

def test_exact_rational_mass_and_posthoc_no_mate_frontier(response_case):
    from scripts.verify_leaper_four_actor_packet import bounds
    base,p,q,t,out=response_case;r=bounds(base,p,q,t,out)
    assert r['original_frozen_WIN0_bounds']==[[0,1],[1,1]]
    assert r['posthoc_WIN0_bounds']==[[0,1],[0,1]]

def test_uniform_omission_cannot_hide_in_probability_mass(response_case):
    from scripts.verify_leaper_four_actor_packet import bounds
    base,p,q,t,out=response_case;tree=json.loads(gzip.decompress(t.read_bytes()));tree['nodes'][1]['children'].pop()
    t.write_bytes(gzip.compress(json.dumps(tree).encode(),mtime=0));r=json.loads((base/'uniform/result.json').read_text());r['tree_sha256']=L.sha(t);(base/'uniform/result.json').write_text(json.dumps(r))
    with pytest.raises(ValueError,match='every legal action'):bounds(base,p,q,t,out)

def test_queued_unknown_mass_is_not_an_outcome_label(response_case):
    from scripts.verify_leaper_four_actor_packet import bounds
    base,p,q,t,out=response_case;r=json.loads((base/'uniform/result.json').read_text());r['WIN0_bounds']=[[0,1],[0,1]];(base/'uniform/result.json').write_text(json.dumps(r))
    with pytest.raises(ValueError,match='probability bounds'):bounds(base,p,q,t,out)


