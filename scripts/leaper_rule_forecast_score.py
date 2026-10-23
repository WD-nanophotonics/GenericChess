"""Finite rule-level prevalence forecasts; existence is a different target.

PRIMARY may freeze one density/probability per rule and exact named mu instead
of a separate number at every history. Rate squared error and average binary
Brier loss have different meanings. Their paired absolute improvement agrees
because the common irreducible r*(1-r) term cancels. No forecasts are generated.
"""
from fractions import Fraction as F
import math
import argparse

from scripts.leaper_explorer_truth import load,save,rule_targets,digest,validate_probability_forecast
from scripts.leaper_explorer_compare import declared_freeze


def losses(probability,positive,unknown,n):
    """Exact finite-rate support, including nearest feasible integer numerator."""
    if (any(type(v)is not int for v in (positive,unknown,n)) or n<=0 or
        positive<0 or unknown<0 or positive+unknown>n):
        raise ValueError('valid finite property counts required')
    p=F(probability);lo=F(positive,n);hi=F(positive+unknown,n)
    if not 0<=p<=1:raise ValueError('probability outside [0,1]')
    k=p*n
    nearest={max(positive,min(positive+unknown,math.floor(k))),
             max(positive,min(positive+unknown,math.ceil(k)))}
    rate_low=min((p-F(j,n))**2 for j in nearest)
    rate_high=max((p-lo)**2,(p-hi)**2)
    bernoulli=[p*p+(1-2*p)*r for r in (lo,hi)]
    return dict(prevalence_bounds=list(map(float,(lo,hi))),
                rate_squared_error_bounds=list(map(float,(rate_low,rate_high))),
                mean_binary_brier_bounds=list(map(float,(min(bernoulli),max(bernoulli)))))


def paired_bounds(p,q,positive,unknown,n):
    # Both forecasts refer to the same UNKNOWN labels and same finite rate.
    p,q=F(p),F(q)
    bounds=[q*q-p*p+2*(p-q)*r for r in (F(positive,n),F(positive+unknown,n))]
    return list(map(float,(min(bounds),max(bounds))))


def validate(truth,packet):
    if packet.get('format')!='leaper-rule-prevalence-predictions-v1':
        raise ValueError('explicit rule prevalence format required; existence cannot be scored as a density')
    declaration=declared_freeze(packet)
    targets={(r['fingerprint'],prop):r|dict(property=prop,counts=counts)
             for r in rule_targets(truth)for prop,counts in r['properties'].items()}
    qs={}
    for q in packet['predictions']:
        key=q['fingerprint'],q['property']
        if key not in targets:raise ValueError('unknown rule/property')
        if key in qs:raise ValueError('duplicate rule forecast')
        if q['mu_id']!=targets[key]['mu_id']:raise ValueError('rule/mu mismatch')
        validate_probability_forecast(q);qs[key]=q
    return declaration,targets,qs


def score_rules(truth,model,baseline=None):
    declaration,targets,qs=validate(truth,model)
    bdecl=None;bs={}
    if baseline is not None:
        bdecl,_,bs=validate(truth,baseline)
        if declaration['forecast_id']==bdecl['forecast_id']:raise ValueError('distinct forecast IDs required')
    rows=[]
    for key,target in sorted(targets.items()):
        c=target['counts'];n=target['denominator'];q=qs.get(key);b=bs.get(key)
        row=dict(fingerprint=key[0],property=key[1],mu_id=target['mu_id'],split=target['split'],
                 denominator=n,truth=c,model_abstained=q is None,baseline_abstained=b is None,
                 model=None,baseline=None,paired_absolute_improvement_bounds=None)
        if q is not None:row['model']=dict(probability=q['probability'],**losses(q['probability'],c['positive'],c['unknown'],n))
        if b is not None:row['baseline']=dict(probability=b['probability'],**losses(b['probability'],c['positive'],c['unknown'],n))
        if q is not None and b is not None:
            row['paired_absolute_improvement_bounds']=paired_bounds(q['probability'],b['probability'],c['positive'],c['unknown'],n)
        rows.append(row)
    return dict(format='leaper-rule-prevalence-score-v1',truth_digest=digest(truth),
                model_digest=digest(model),baseline_digest=None if baseline is None else digest(baseline),
                declarations=dict(model=declaration,baseline=bdecl),rows=rows,
                note='Finite exposed support diagnostics only; not population calibration, IID inference or blind generalization. Rate error estimates a density; binary Brier scores a forecast for a mu-sampled history label. Their raw losses and skill ratios differ; paired absolute improvement is identical. UNKNOWN finite-rate endpoints and missing forecasts remain explicit. Any-deadzone over all legal histories, arbitrary opening-layout population and mu-support existence are not this target. Freeze declarations do not prove blinding. All old mu identifiers/supports remain unchanged by new truth labels.')


if __name__=='__main__':
    cli=argparse.ArgumentParser()
    for name in ('truth','model','output'):cli.add_argument('--'+name,required=True)
    cli.add_argument('--baseline');args=cli.parse_args()
    save(args.output,score_rules(load(args.truth),load(args.model),None if not args.baseline else load(args.baseline)))
