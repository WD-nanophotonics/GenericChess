"""Real frozen Core-history controls for bounded cooperative paths/suffixes."""
from pathlib import Path
import pytest

from generic_chess.core.actions import action_from_dict
from generic_chess.rules.schema import ruleset_from_dict
from generic_chess.rules.compiler import compile_legacy_ruleset_for_semantic_execution as compile_rule
from scripts.leaper_cooperative_certificate import root_session
from scripts.leaper_cooperative_path_probe import search
from scripts.leaper_suffix_truth import SuffixTree,Limit
from scripts.leaper_explorer_truth import load


@pytest.fixture(scope='module')
def inputs():
    p=Path('docs/research/data/leaper_explorer_truth_20261023')
    truth=load(p/'truth.json.gz');coop=load(p/'cooperative.json')
    q=min((q for q in coop['rows']if q['cooperative_decisive']),key=lambda q:len(q['witness']))
    c=compile_rule(ruleset_from_dict(truth['rules'][q['fingerprint']]))
    _,s=root_session(truth,q['id'],c)
    return truth,c,s,q


def test_depth_cap_is_unknown_never_absence(inputs):
    _,c,s,_=inputs
    out=search(s.state,c,depth=0,nodes=1,seconds=10)
    assert out['status']=='DEPTH_CAP_UNKNOWN'
    assert out['cooperative_decisive'] is out['universal_draw'] is None
    assert out['witness'] is None and out['stats']['completed_depth']==0


def test_real_literal_path_returns_decisive_terminal_with_actual_history(inputs):
    truth,c,_,q=inputs
    _,s=root_session(truth,q['id'],c)
    out=search(s.state,c,depth=len(q['witness']),nodes=100000,seconds=10)
    assert out['status']=='WITNESS'
    for ac in out['witness']:s.submit(action_from_dict(ac))
    assert s.result.winner is not None and s.result.winner==out['terminal_winner']


@pytest.mark.parametrize('kwargs',[dict(depth=17),dict(depth=True),dict(nodes=0),dict(nodes=100001),dict(seconds=float('nan')),dict(seconds=float('inf')),dict(seconds=True)])
def test_invalid_budget_rejects_before_work(inputs,kwargs):
    _,c,s,_=inputs;spec=dict(depth=1,nodes=10,seconds=10);spec.update(kwargs)
    with pytest.raises(ValueError):search(s.state,c,**spec)


def test_suffix_tree_keeps_actual_clock_and_all_draw_children(inputs):
    truth,_,_,_=inputs
    hid='0329f3145f76a8c2aa7a70224a85cfabd3f2c46b533e4d0dc30569649736e277'
    r=next(r for r in truth['roots']if r['id']==hid)
    c=compile_rule(ruleset_from_dict(truth['rules'][r['fingerprint']]))
    _,s=root_session(truth,hid,c)
    tree=SuffixTree(nodes=100,seconds=10)
    future,value,witness=tree.solve(s.state,c)
    assert future=={0} and value==0 and witness is None
    assert tree.nodes==3 and tree.edges==2


def test_partial_suffix_does_not_return_a_negative_label(inputs):
    truth,_,_,_=inputs
    r=next(r for r in truth['roots']if r['rule_remaining']==1)
    c=compile_rule(ruleset_from_dict(truth['rules'][r['fingerprint']]))
    _,s=root_session(truth,r['id'],c)
    tree=SuffixTree(nodes=1,seconds=10)
    with pytest.raises(Limit,match='NODE_CAP_UNKNOWN'):tree.solve(s.state,c)
    assert tree.nodes==1
