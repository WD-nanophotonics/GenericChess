"""Finite-density versus sampled-binary loss, independent exact reference."""
from copy import deepcopy
from fractions import Fraction as F
from itertools import product
import pytest

from scripts.leaper_rule_forecast_score import losses,paired_bounds,score_rules


def test_finite_density_lower_loss_is_not_continuous_interval_optimism():
    # With one unknown binary label only rates0 or1 are possible; p=.5 does
    # not achieve zero density error even though it lies inside interval[0,1].
    got=losses(.5,0,1,1)
    assert got['rate_squared_error_bounds']==[.25,.25]
    assert got['mean_binary_brier_bounds']==[.25,.25]


def test_exact_loss_ranges_match_every_feasible_label_count():
    for n in range(1,8):
        for positive in range(n+1):
            for unknown in range(n-positive+1):
                for p in (0,.1,.5,.9,1):
                    rates=[F(k,n)for k in range(positive,positive+unknown+1)]
                    errors=[(F(p)-r)**2 for r in rates]
                    binary=[F(p)**2+(1-2*F(p))*r for r in rates]
                    got=losses(p,positive,unknown,n)
                    assert got['rate_squared_error_bounds']==pytest.approx(list(map(float,(min(errors),max(errors)))))
                    assert got['mean_binary_brier_bounds']==pytest.approx(list(map(float,(min(binary),max(binary)))))


def test_paired_absolute_gain_equal_for_rate_and_binary_losses():
    for p,q in product((0,.2,.5,.9,1),repeat=2):
        gains=[]
        for k in range(1,4):
            r=F(k,4);p0,q0=F(p),F(q)
            rate=(q0-r)**2-(p0-r)**2
            binary=(q0*q0+(1-2*q0)*r)-(p0*p0+(1-2*p0)*r)
            assert rate==binary;gains.append(rate)
        assert paired_bounds(p,q,1,2,4)==pytest.approx(list(map(float,(min(gains),max(gains)))))


def fixture():
    truth=dict(rules={'A':{}},roots=[dict(id=str(i),fingerprint='A',mu_id='mu',
       family='f',split='exposed',wdl_bounds=[-1,1],wdl_fork=y,
       cooperative_decisive=None,universal_draw=None)for i,y in enumerate((True,False,None))])
    packet=dict(format='leaper-rule-prevalence-predictions-v1',freeze=dict(
        forecast_id='test',information_set='synthetic test only',frozen_at='fixture',truth_access='fixture exposed'),
        predictions=[dict(fingerprint='A',property='wdl_fork',mu_id='mu',probability=.5,source_sha='a'*40,cost=dict(nodes=1))])
    return truth,packet


def test_absent_rule_prediction_remains_missing_and_unknown_baseline_not_half():
    truth,p=fixture();out=score_rules(truth,p)
    r=next(r for r in out['rows']if r['property']=='wdl_fork')
    assert not r['model_abstained']and r['baseline_abstained']
    assert r['paired_absolute_improvement_bounds']is None
    missing=next(r for r in out['rows']if r['property']=='universal_draw')
    assert missing['model']is None


@pytest.mark.parametrize('field,value',[
    ('mu_id','different-law'),('property','any_legal_deadzone_exists'),
    ('probability',True),('probability',float('nan')),('source_sha','x'),('cost',{})])
def test_rule_forecast_binding_rejects_ambiguous_or_invalid_input(field,value):
    truth,p=fixture();p['predictions'][0][field]=value
    with pytest.raises(ValueError):score_rules(truth,p)


def test_rule_duplicate_is_not_a_second_vote_and_same_id_is_not_a_baseline():
    truth,p=fixture();p['predictions']*=2
    with pytest.raises(ValueError):score_rules(truth,p)
    truth,p=fixture()
    with pytest.raises(ValueError):score_rules(truth,p,deepcopy(p))
