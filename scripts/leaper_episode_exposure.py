"""Data-only episode event bounds, not history-density or policy IID claims."""
from collections import Counter
from scripts.leaper_explorer_truth import digest


def event_bounds(values):
    if any(v is not None and type(v)is not bool for v in values):
        raise ValueError('boolean or UNKNOWN event labels required')
    positives=[i for i,v in enumerate(values)if v is True]
    missing=[i for i,v in enumerate(values)if v is None]
    upper=min(positives)if positives else None
    lower=min(positives+missing)if positives or missing else None
    return dict(occurs=True if positives else None if missing else False,
                first_ply_lower=lower,first_ply_upper=upper,
                first_ply_exact=upper if upper is not None and not any(i<upper for i in missing)else None,
                unknown_histories=len(missing),known_event_visits=len(positives))


def run(truth,context):
    by_origin={(o['record_id'],o['ply']):r for r in truth['roots']for o in r['origins']}
    rows=[]
    for rid,record in truth['records'].items():
        forks=[];critical=[]
        for ply,action in enumerate(record['actions']):
            r=by_origin[rid,ply];forks.append(r['wdl_fork'])
            chosen=next((a['wdl_bounds']for a in r['action_bounds']if a['action']==action),None)
            root=r['wdl_bounds']
            critical.append(False if r['wdl_fork']is False else None if chosen is None else (
                True if chosen[1]<root[0]else False if chosen[0]>=root[1]else None))
        rows.append(dict(record_id=rid,reference_weight=len(context['records'][rid]),
                         actions=len(forks),fork=event_bounds(forks),guarantee_loss=event_bounds(critical)))
    summaries={}
    for law in ('distinct_records','source_references'):
        summaries[law]={}
        for prop in ('fork','guarantee_loss'):
            counts=Counter();known_first=Counter()
            for r in rows:
                weight=1 if law=='distinct_records'else r['reference_weight'];event=r[prop]
                counts[str(event['occurs'])]+=weight
                if event['first_ply_exact']is not None:known_first[event['first_ply_exact']]+=weight
            summaries[law][prop]=dict(episode_event_counts=dict(counts),exact_first_ply_counts=dict(known_first))
    return dict(format='leaper-episode-exposure-v1',truth_digest=digest(truth),context_digest=digest(context),
                rows=rows,summaries=summaries,
                scope='Whether and when a saved full episode encounters a known WDL fork or guarantee loss. UNKNOWN earlier histories prevent exact first-event timing. Reference weights are duplicate frozen controller references, not independent games or fresh policy probabilities. Density of event visits, probability of at least one event and first-event timing are different targets. A small initial-root action disagreement rate alone cannot bound whole-game utility differences.')
