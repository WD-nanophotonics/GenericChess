"""Paired sampling-law truth contrasts on the existing frozen full histories.

Different laws share each UNKNOWN label. Bound their difference directly;
subtracting marginal prevalence intervals needlessly drops that information.
No E0 forecast, policy execution, new rule or oracle TRAIN selection is made.
"""
from fractions import Fraction as F
from itertools import combinations
from pathlib import Path
import argparse

from scripts.leaper_explorer_truth import PROPERTIES, load, save, digest, materialize


def normalize(weights):
    if not weights or any(type(w) not in (int,F) or w<0 for w in weights.values()):
        raise ValueError('nonnegative integer/rational weights required')
    total=sum(weights.values())
    if not total:raise ValueError('nonzero law required')
    return {hid:F(w,total) for hid,w in weights.items() if w}


def contrast(labels,first,second):
    a,b=normalize(first),normalize(second)
    if (a.keys()|b.keys())-labels.keys():raise ValueError('unknown law support history')
    constant=F(0);unknown=[]
    for hid in a.keys()|b.keys():
        y=labels[hid]
        if y is not None and type(y)is not bool:raise ValueError('boolean/UNKNOWN label required')
        coeff=b.get(hid,F(0))-a.get(hid,F(0))
        if y is None:unknown.append((hid,coeff))
        else:constant+=coeff*int(y)
    lower=constant+sum((min(F(0),w)for _,w in unknown),F(0))
    upper=constant+sum((max(F(0),w)for _,w in unknown),F(0))
    tv=sum((abs(a.get(h,F(0))-b.get(h,F(0)))for h in a.keys()|b.keys()),F(0))/2
    ranked=sorted(((hid,abs(w))for hid,w in unknown if w),key=lambda x:(-x[1],x[0]))
    width=upper-lower
    # Uniform unit-cost independent-label diagnostic, not a forecast of actual
    # solver work. One certificate may label many histories or none.
    needed=[]
    for tolerance in (F(1,100),F(1,20),F(1,10)):
        remain=width;k=0
        while remain>tolerance and k<len(ranked):
            remain-=ranked[k][1];k+=1
        needed.append(dict(max_remaining_width=str(tolerance),queries=k,
                           residual_width=str(remain)))
    return dict(second_minus_first_bounds=list(map(str,(lower,upper))),
                interval_width=str(width),total_variation=str(tv),
                shared_support_mass=str(1-tv),known_contribution=str(constant),
                unknown_labels=len(unknown),unknown_nonzero_coefficients=len(ranked),
                unit_independent_label_query_bounds=needed)


def run(folder,supplement_file=None,local_file=None):
    p=Path(folder);raw=load(p/'truth.json.gz')
    truth=materialize(raw,load(p/'cooperative.json'),load(p/'observed-suffixes.json.gz'))
    if supplement_file is not None:
        from scripts.leaper_explorer_supplement import apply_supplement
        truth=apply_supplement(truth,load(supplement_file))
    if local_file is not None:
        from scripts.leaper_local_truth import apply_layer
        truth=apply_layer(truth,load(local_file))
    context=load(p/'source-context.json.gz')
    laws=dict(
       uniform_distinct_ongoing_histories={r['id']:1 for r in truth['roots']},
       distinct_record_decision_visits={r['id']:len(r['origins'])for r in truth['roots']},
       reference_decision_visits={r['id']:sum(len(context['records'][o['record_id']])for o in r['origins'])for r in truth['roots']},
       one_frozen_initial_history_per_rule={r['id']:int(r['ply']==0)for r in truth['roots']})
    distributions={name:dict(denominator=sum(ws.values()),
           support=sum(w>0 for w in ws.values()),
           distribution_digest=digest(sorted((h,str(w))for h,w in normalize(ws).items())))
           for name,ws in laws.items()}
    rows=[]
    for first,second in combinations(laws,2):
        for prop in PROPERTIES:
            labels={r['id']:r[prop]for r in truth['roots']}
            rows.append(dict(first=first,second=second,property=prop,
                             **contrast(labels,laws[first],laws[second])))
    return dict(format='leaper-sampling-contrast-v1',truth_digest=digest(raw),
          materialized_digest=digest(truth),context_digest=digest(context),
          distributions=distributions,rows=rows,
          scope='Exact descriptive transport contrasts on this finite exposed support only. Independent UNKNOWN labels are a relaxation of game relations; bounds remain conservative. Unit independent-label query counts certify residual interval width under that abstraction, not necessary solver calls/time and not a request to launch them. No prediction errors, generalization or initial legal-layout population inference. Distribution digests normalize weights and are separate from the historical prediction-contract mu identifiers.')


if __name__=='__main__':
    cli=argparse.ArgumentParser();cli.add_argument('--folder',default='docs/research/data/leaper_explorer_truth_20261023');cli.add_argument('--output',required=True);cli.add_argument('--supplement');cli.add_argument('--local-layer')
    args=cli.parse_args();result=run(args.folder,args.supplement,args.local_layer);save(args.output,result)
    print(__import__('json').dumps(result))
