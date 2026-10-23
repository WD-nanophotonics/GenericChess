"""Apply existing strict AUX scorers to real PRIMARY H6 forecast objects."""
from scripts.leaper_explorer_truth import score,digest
from scripts.leaper_explorer_compare import compare
from scripts.leaper_rule_forecast_score import score_rules

PAIRS=[(m,b)for m in('geometric_cooperative','oneply_augmented_cooperative','v2_exposed_colour_plus_oneply')for b in('uninformative_cooperative','same_board_roster_cooperative')]+[('oneply_augmented_cooperative','geometric_cooperative'),('v2_exposed_colour_plus_oneply','oneply_augmented_cooperative'),('geometric_wdl_fork','uninformative_wdl_fork'),('geometric_wdl_fork','same_board_roster_wdl_fork')]


def evaluate(truth,forecasts):
    hist=forecasts['history_forecasts'];rates=forecasts['rule_prevalence_forecasts']
    result=dict(format='leaper-H6-strict-score-handoff-v1',truth_digest=digest(truth),
        forecasts_digest=digest(forecasts),forecast_execution_sha=forecasts['execution_sha'],
        history_scores={},family_rate_scores={},paired_history={},paired_family_rates={},table=[])
    for name,packet in hist.items():
        props={r['property']for r in packet['predictions']}
        if len(props)!=1:raise ValueError('one declared target per model required')
        result['history_scores'][name]=score(truth,packet)
        result['family_rate_scores'][name]=score_rules(truth,rates[name])
    for model,base in PAIRS:
        key=model+'-versus-'+base;conditional=compare(truth,hist[model],hist[base]);rate=score_rules(truth,rates[model],rates[base])
        result['paired_history'][key]={k:v for k,v in conditional.items()if k not in('cases','individual_scores')}
        result['paired_family_rates'][key]=rate
        prop=hist[model]['predictions'][0]['property']
        for split in ('all','calibration','reserved_validation'):
            roots=[r for r in truth['roots']if split=='all'or r['split']==split]
            fps={r['fingerprint']for r in roots};n=len(fps)
            rows=[r for r in conditional['rows']if r['property']==prop and(split=='all'or r['split']==split)]
            if sum(r['paired_known']for r in rows)!=len(roots)or any(r['paired_unknown']or r['unpaired']for r in rows):
                raise ValueError('headline requires all same-support truth and predictions')
            weights={s:len({r['fingerprint']for r in roots if r['split']==s})for s in {r['split']for r in roots}}
            conditional_gain=[sum(r['equal_rule_whole_improvement_bounds'][i]*weights[r['split']]for r in rows)/n for i in(0,1)]
            rr=[r for r in rate['rows']if r['property']==prop and r['fingerprint']in fps]
            if len(rr)!=n or any(r['model_abstained']or r['baseline_abstained']for r in rr):raise ValueError('unmatched family rate inputs')
            rate_gain=[sum(r['paired_absolute_improvement_bounds'][i]for r in rr)/n for i in(0,1)]
            result['table'].append(dict(pair=key,property=prop,split=split,families=n,histories=len(roots),
                conditional_Brier_gain=conditional_gain,family_rate_MSE_gain=rate_gain,
                sign='baseline-minus-model loss, positive favours model',weighting='equaldefinedfamilies; uniform admitted initial layouts within each'))
    result['scope']='Actual frozenv1 versus separately exposedv2, same3616fullhistories/11definedfamilies; unavailable12th means full12score UNDEFINED. Rootconditional forecasts and family-mean rate forecasts are distinct targets. No probability refit, confidence/generalization/strength claim or synthetic predictions.'
    return result
