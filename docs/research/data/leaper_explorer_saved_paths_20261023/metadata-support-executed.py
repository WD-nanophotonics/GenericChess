from pathlib import Path
from collections import defaultdict,Counter
from scripts.leaper_saved_child_bounds import current_truth,propagate
from scripts.leaper_saved_suffix_transfer import apply as suffix_apply
from scripts.leaper_observed_path_proofs import apply as observed_apply
from scripts.leaper_explorer_truth import load,save,digest
from scripts.leaper_truth_views import initial_history_view
p=Path('artifacts/saved-child-bounds-d19a')
t=current_truth('docs/research/data/leaper_explorer_truth_20261023','docs/research/data/leaper_explorer_followup_20261023')
u,_=propagate(t,load(p/'edges.json.gz'));v=suffix_apply(u,load(p/'shortened-proofs.json.gz'));w=observed_apply(v,load(p/'observed-proofs.json.gz'))
views=dict(original_initial10=initial_history_view(w),saved_distinct_histories=w)
reports={}
for name,view in views.items():
    groups=defaultdict(list)
    for r in view['roots']:
        raw=view['rules'][r['fingerprint']]
        groups[raw['board_size'],r['actors']].append(r)
    rows=[]
    for (size,actors),rs in sorted(groups.items()):
        props={}
        for prop in ('wdl_fork','cooperative_decisive'):
            counts=Counter(str(r[prop])for r in rs);n=len(rs)
            props[prop]=dict(counts=dict(counts),prevalence_bounds=[counts['True']/n,(counts['True']+counts['None'])/n])
        rows.append(dict(board_size=size,actors=actors,denominator=len(rs),distinct_rules=len({r['fingerprint']for r in rs}),properties=props))
    reports[name]=dict(denominator=len(view['roots']),metadata_classes=len(groups),rows=rows)
assert reports['original_initial10']['metadata_classes']==1
assert reports['original_initial10']['rows'][0]['board_size']==4 and reports['original_initial10']['rows'][0]['actors']==6
report=dict(truth_digest=digest(w),reports=reports,
    finding='A deterministic board-size/actor-count-only predictor has one input class on the original10initials;it cannot vary by rule geometry there. With the same fit protocol this is the same information partition as a constant base-rate baseline. Different fitted outputs would reflect fitting/prior/randomization differences,not added geometry information. On saved-history mu,actor counts vary and metadata stratification is different.',
    consequence='PRIMARY should declare baseline information/fit protocols and may record equivalent baseline support instead of duplicating computation. Initial versus endogenous-history targets cannot be substituted to create feature variation.',
    scope='Observed support and descriptive truth counts only. No baseline or E0 probability is constructed,fit or scored;no calibration,accuracy or unseen-rule conclusion.')
save(p/'metadata-support.json',report);print(report)
