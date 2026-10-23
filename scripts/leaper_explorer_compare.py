"""Descriptive paired forecast comparison on exact matched frozen histories.

No predictor is created here. PRIMARY supplies both real frozen E0 and baseline
outputs. UNKNOWN labels are shared by both forecasts; subtracting independently
bounded Brier losses would discard that pairing. Bounds below relax cross-
history game constraints, so they are conservative for actual reachable truth.
"""
from __future__ import annotations

import argparse
import math
from collections import defaultdict

from scripts.leaper_explorer_truth import PROPERTIES, load, save, score, digest


def improvement_bounds(model, baseline, label):
    """Baseline Brier minus model Brier; positive means model has smaller loss."""
    if any(type(p) not in (int, float) or not math.isfinite(p) or not 0 <= p <= 1
           for p in (model, baseline)):
        raise ValueError('finite probabilities in [0,1] required')
    if label is not None and type(label) is not bool:
        raise ValueError('boolean or UNKNOWN truth required')
    values = [(baseline-int(y))**2 - (model-int(y))**2
              for y in (False, True) if label is None or y == label]
    return [min(values), max(values)]


def declared_freeze(packet):
    """Retain declarations without mistaking them for independently proved blinding."""
    meta = packet.get('freeze')
    if not isinstance(meta, dict):
        raise ValueError('paired comparison requires a frozen forecast declaration')
    for key in ('forecast_id', 'information_set', 'frozen_at', 'truth_access'):
        if not isinstance(meta.get(key), str) or not meta[key].strip():
            raise ValueError('missing forecast freeze field: '+key)
    return dict(meta)


def compare(truth, model, baseline):
    # Reuse the maintained source/cost/probability/exact-history/mu/duplicate
    # validation; don't create a second permissive join implementation.
    model_score, baseline_score = score(truth, model), score(truth, baseline)
    declarations = dict(model=declared_freeze(model), baseline=declared_freeze(baseline))
    if declarations['model']['forecast_id'] == declarations['baseline']['forecast_id']:
        raise ValueError('distinct forecast IDs required')
    by_id={r['id']:r for r in truth['roots']}
    if len(by_id) != len(truth['roots']):
        raise ValueError('duplicate truth history')
    models={(q['id'],q['property']):q for q in model['predictions']}
    baselines={(q['id'],q['property']):q for q in baseline['predictions']}
    cases=[]
    groups=defaultdict(list)
    for key in sorted(models.keys() & baselines.keys()):
        hid, prop=key
        r=by_id[hid];p=models[key]['probability'];q=baselines[key]['probability']
        bounds=improvement_bounds(p,q,r[prop])
        item=dict(id=hid, fingerprint=r['fingerprint'], mu_id=r['mu_id'],
                  property=prop, split=r['split'], truth=r[prop],
                  model_probability=p, baseline_probability=q,
                  improvement_bounds=bounds,
                  model_error=None if r[prop] is None else ('FP' if p>=.5 else 'FN') if (p>=.5)!=r[prop] else None,
                  baseline_error=None if r[prop] is None else ('FP' if q>=.5 else 'FN') if (q>=.5)!=r[prop] else None)
        cases.append(item);groups[prop,r['split']].append(item)
    rows=[]
    for prop in PROPERTIES:
        for split in sorted({r['split'] for r in by_id.values()}):
            universe=[r for r in by_id.values() if r['split']==split]
            matched=groups[prop,split]
            n=len(universe);k=len(matched);known=[r for r in matched if r['truth'] is not None]
            sums=[sum(r['improvement_bounds'][i] for r in matched) for i in (0,1)]
            mbs=sum((r['model_probability']-int(r['truth']))**2 for r in known)
            bbs=sum((r['baseline_probability']-int(r['truth']))**2 for r in known)
            rules=[]
            for fp in sorted({r['fingerprint'] for r in universe}):
                total=sum(r['fingerprint']==fp for r in universe)
                selected=[r for r in matched if r['fingerprint']==fp]
                absent=total-len(selected)
                rules.append([(sum(r['improvement_bounds'][0] for r in selected)-absent)/total,
                              (sum(r['improvement_bounds'][1] for r in selected)+absent)/total])
            rows.append(dict(property=prop,split=split,denominator=n,paired=k,
                 paired_known=len(known),paired_unknown=k-len(known),unpaired=n-k,
                 paired_support_improvement_bounds=None if not k else [s/k for s in sums],
                 whole_denominator_improvement_bounds=[(sums[0]-(n-k))/n,(sums[1]+n-k)/n],
                 equal_rule_whole_improvement_bounds=[sum(r[i] for r in rules)/len(rules) for i in (0,1)],
                 known_paired_model_brier=None if not known else mbs/len(known),
                 known_paired_baseline_brier=None if not known else bbs/len(known),
                 known_paired_brier_skill=None if bbs==0 else 1-mbs/bbs,
                 skill_undefined_reason=('no paired known labels' if not known else 'baseline has zero paired known loss') if bbs==0 else None))
    return dict(format='leaper-explorer-paired-score-v1',truth_digest=digest(truth),
                model_digest=digest(model),baseline_digest=digest(baseline),
                declarations=declarations,rows=rows,cases=cases,
                individual_scores=dict(model=model_score,baseline=baseline_score),
                note='Finite exposed matched-input diagnostics, not a population calibration or IID/generalization claim. Freeze/truth-access declarations are supplied provenance, not independent proof of blinding. Known skill is conditional on shared coverage and undefined at zero baseline loss. Whole bounds include [-1,1] for every unpaired item; those are missing evaluation, not measured forecast utility. Shared-label bounds allow binary labels independently across histories and are conservative under game constraints. Threshold .5 is fixed; cases retain concrete FP/FN with exact histories.')


if __name__ == '__main__':
    cli=argparse.ArgumentParser()
    for name in ('truth','model','baseline','output'):
        cli.add_argument('--'+name,required=True)
    args=cli.parse_args()
    save(args.output,compare(load(args.truth),load(args.model),load(args.baseline)))
