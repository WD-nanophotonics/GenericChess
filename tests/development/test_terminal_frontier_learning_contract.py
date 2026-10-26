"""Static learner contract controls, not rollout or training experiments."""
import gzip,json
from math import tanh
from pathlib import Path
import pytest
from scripts.leaper_truth_compatibility import bind_context
from scripts.leaper_terminal_frontier import terminal_frontier
from generic_chess.learning.incremental import FixedScaleSessionEnv,Model,TDLeafEpisode

@pytest.fixture
def horizon_context():
    c=json.loads(gzip.decompress(Path('tests/fixtures/terminal_frontier_source_controls.json.gz').read_bytes()))['max_ply_control']
    return bind_context(c['rule'],c['record'])

@pytest.mark.parametrize('B_weight',[-3.,0.,1.,4.])
def test_ungated_fixed_unit_material_cannot_exactly_fit_this_horizon_zero(horizon_context,B_weight):
    env=FixedScaleSessionEnv(horizon_context.session,unit_type='A',use_runtime=False)
    phi=env.features();weights=[1.]*len(phi)
    for i,name in enumerate(env.names):
        if name==('board','B'):weights[i]=B_weight
    model=Model(weights,fixed=0,scale=10)
    assert phi[0]==-1 and all(x==0 for x in phi[1:])
    assert model.raw(phi)==-1 and model.prediction(phi)==pytest.approx(tanh(-.1))
    assert terminal_frontier(horizon_context)['root_WDL_outer_bounds']==[0,0]
    # This contrasts a static material value with rule truth, not a search score.

def terminal_receipt(ctx,monkeypatch):
    from generic_chess.learning import mainline_search as adapter
    ctx.session.submit(ctx.session.legal_actions()[0])
    env=FixedScaleSessionEnv(ctx.session,unit_type='A',use_runtime=False)
    model=Model([1.]*len(env.names))
    def forbid_Player(*args,**kwargs):raise AssertionError('no Player construction permitted in this terminal-path control')
    monkeypatch.setattr(adapter,'AlphaBetaPlayer',forbid_Player)
    receipt=adapter.search(env,model,depth=1,nodes=1,seconds=1)
    return model,receipt

def test_actual_terminal_fastpath_returns_truth_without_Player(horizon_context,monkeypatch):
    model,r=terminal_receipt(horizon_context,monkeypatch)
    assert r.complete and r.nodes==0 and r.value==0
    assert r.pv_terminal and r.pv_phi is None and r.reason=='terminal'

def test_terminal_observation_does_not_evaluate_a_material_gradient(horizon_context,monkeypatch):
    model,r=terminal_receipt(horizon_context,monkeypatch)
    def forbid_gradient(phi):raise AssertionError('terminal leaf has no trainable material gradient')
    monkeypatch.setattr(model,'gradient',forbid_gradient)
    before=model.weights[:];episode=TDLeafEpisode()
    episode.observe(model,r)
    assert model.weights==before
    assert episode.rows==[(0.,tuple(0. for _ in model.weights))]
    # No finish/apply call or model training is performed here.

def test_algebra_only_incoming_terminal_target_can_have_credit_when_final_metric_is_zero():
    from scripts.verify_leaper_ab_learning import td_sum
    before=[1.,1.]
    receipts=[{'value':1.,'pv_phi':[0.,1.],'pv_terminal':False},
              {'value':0.,'pv_phi':None,'pv_terminal':True}]
    after,stats=td_sum(before,receipts,0.,eta=.05,lam=.95,scale=10.)
    p=tanh(.1);expected=1.-.05*p*(1.-p*p)/10.
    assert after==pytest.approx([1.,expected],abs=1e-15)
    assert after[1]<1. and stats['changed'] and stats['terminal_credit_l1']==0.
    # Pure receipt-arithmetic counterexample, no actual receipt or fitted model.

def test_algebra_only_missing_terminal_target_is_not_a_draw():
    from scripts.verify_leaper_ab_learning import td_sum
    before=[1.,1.];receipt={'value':1.,'pv_phi':[0.,1.],'pv_terminal':False}
    after,stats=td_sum(before,[receipt],None)
    assert after==before and stats['samples']==0 and stats['censored']
