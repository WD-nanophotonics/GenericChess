"""One-update contract bound; static receipts, intercepted apply, no games."""
import math
import pytest
from generic_chess.learning.incremental import Model,Receipt,TDLeafEpisode


@pytest.mark.parametrize('n',[0,1,3,7])
@pytest.mark.parametrize('lam',[0.,.95,1.])
@pytest.mark.parametrize('outcome',[None,-1,0,1])
def test_frozen_observation_bound_does_not_require_fixed_policy(n,lam,outcome,monkeypatch):
    model=Model([1.,.731],scale=10.); episode=TDLeafEpisode(eta=.05,lam=lam)
    domain=((0,1),(1,-1),(-1,1),(0,-1))
    for i in range(n):
        phi=domain[i%len(domain)]
        episode.observe(model,Receipt(None,model.raw(phi),phi,False,(),0,True,0,0.,'static'))
    rows=tuple(episode.rows); seen=[]
    monkeypatch.setattr(model,'apply',lambda delta:seen.append(tuple(delta)))
    episode.finish(model,outcome)
    assert model.weights==[1.,.731] and len(seen)==1  # No fitted model.
    # Censored final row has no TD error; the earlier forward targets end at
    # the last prediction. Complete rows end at the literal scalar outcome.
    active=n if outcome is not None else max(0,n-1)
    for j,actual in enumerate(seen[0]):
        envelope=2*.05*sum(abs(rows[k][1][j]) for k in range(active))
        assert abs(actual)<=envelope+1e-15
        assert abs(actual)<=2*.05*active/10.+1e-15  # |free phi|<=1.
    assert seen[0][0]==0.  # Physical unit never moves.
    # Independently rewrite backward TD errors as convex forward targets.
    forward=[0.,0.]
    for k in range(active):
        if outcome is None:
            end=n-1; target=lam**(end-k-1)*rows[end][0]
        else:
            end=n; target=lam**(end-k-1)*outcome
        coefficients=[lam**(end-k-1)]
        for j in range(k+1,end):
            coefficient=(1-lam)*lam**(j-k-1)
            coefficients.append(coefficient);target+=coefficient*rows[j][0]
        assert math.isclose(sum(coefficients),1.,abs_tol=1e-15)
        assert -1.-1e-15<=target<=1.+1e-15
        for j,g in enumerate(rows[k][1]):forward[j]+=.05*(target-rows[k][0])*g
    assert seen[0]==pytest.approx(forward,abs=1e-15)


def test_mean_convergence_alone_does_not_bound_second_moment():
    from fractions import Fraction as F
    # A fixed one-observation process: phi0 withp.99 orphi10 withp.01,
    # terminal0. These are exact moments, not iterative training or game states.
    eta=F(1,20);prob=F(1,100)
    mean_factor=(1-prob)+prob*(1-eta*100)
    square_factor=(1-prob)+prob*(1-eta*100)**2
    assert mean_factor==F(19,20)<1
    assert square_factor==F(23,20)>1
    assert 1-2*eta+eta*eta*100==square_factor


@pytest.mark.parametrize('kind',['gradient','prediction','raw_inf'])
@pytest.mark.parametrize('prior',[False,True])
def test_nonfinite_observation_is_rejected_before_freezing_or_appending(kind,prior):
    model=Model([1.,1.],scale=1e-320 if kind=='gradient' else 10.)
    episode=TDLeafEpisode(eta=0.)
    if prior:
        # Saturated raw1 at tiny scale has representable zero gradient.
        phi=(1.,0.);episode.observe(model,Receipt(None,model.raw(phi),phi,False,(),0,True,0,0.,'valid'))
    before=episode.rows[:];snapshot=episode.snapshot
    phi=(-1.,1.)
    r=Receipt(None,0. if kind=='gradient' else float('inf') if kind=='raw_inf' else float('nan'),phi,False,(),0,True,0,0.,'invalid-numeric')
    with pytest.raises(ValueError,match='nonfinite TD observation'):
        episode.observe(model,r)
    assert episode.rows==before and episode.snapshot==snapshot
    assert model.weights==[1.,1.]


@pytest.mark.parametrize('kind',['gradient','prediction','raw_inf'])
def test_independent_arithmetic_rejects_same_invalid_observation_even_if_censored(kind):
    from scripts.verify_leaper_ab_learning import td_sum
    value=0. if kind=='gradient' else float('inf') if kind=='raw_inf' else float('nan')
    r=dict(value=value,pv_phi=(-1.,1.),pv_terminal=False)
    with pytest.raises(ValueError,match='nonfinite TD observation'):
        td_sum([1.,1.],[r],None,scale=1e-320 if kind=='gradient' else 10.)
