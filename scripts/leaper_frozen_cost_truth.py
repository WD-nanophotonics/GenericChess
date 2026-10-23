"""Join PRIMARY's retained Native decisions to AUX frozen history truth.

No new query, rule or policy campaign. Missing rule-domain matches remain
explicit unavailable coverage; timed returns are not requested-depth proofs.
"""
from collections import Counter,defaultdict
from pathlib import Path
import gzip,json,hashlib,time
from scripts.leaper_rule_coordinates import physical_action


def analyze(packet_path,bundle_path):
    tick=time.perf_counter();packet=json.loads(gzip.decompress(Path(packet_path).read_bytes()));bundle_path=Path(bundle_path);raw=bundle_path.read_bytes()
    if hashlib.sha256(raw).hexdigest()!=packet['source_bundle_sha256']:raise ValueError('fixed PRIMARY source differs')
    text=json.loads(gzip.decompress(raw))['documents_utf8'];metadata={r['seed']:r for r in json.loads(text['metadata.json'])['rows']};worlds={w['seed']:w for w in json.loads(text['inputs.json'])['worlds']}
    roots={(g['n'],g['mask'],r['rank']):r for g in packet['graphs']for r in g['roots']};rows=[];unmatched=[];groups=defaultdict(list)
    for budget in(32768,131072):
        data=json.loads(text[f'N{budget}.json'])
        for r in data['rows']:
            meta=metadata[r['seed']];key=meta['n'],meta['mask'],meta['support_rank'];root=roots.get(key)
            if root is None:
                unmatched.append(dict(seed=r['seed'],n=meta['n'],mask=meta['mask'],budget=budget,reason='No AUXfrozenendpointdomain, neverimputeWDL.'));continue
            w=worlds[r['seed']]
            if root['rule']!=w['rule']or root['record']!=w['roots'][0]['record']or root['state_sha']!=meta['initial_state_sha256']:raise ValueError('source fullrule/mu/history does not match truth')
            decision=r['decision'];action=list(physical_action(decision['action'],meta['n']))
            if root['action_keys'].count(action)!=1:raise ValueError('actual chosen action does not bind uniquely')
            index=root['action_keys'].index(action);truth=next(c for c in root['clocks']if c['H']==64);v=truth['actions'][index]
            row=dict(seed=r['seed'],n=meta['n'],mask=meta['mask'],source_rank=meta['support_rank'],budget=budget,
                root_WDL=truth['WDL'],chosen_action_WDL=v,inferior=v<truth['WDL'],root_fork=truth['fork'],
                actual_reason=decision['termination_reason'],actual_completed_depth=decision['completed_depth'],
                paid_nodes=decision['nodes']+decision['qnodes'],query_seconds=r['query_seconds'],action=action)
            rows.append(row);groups[meta['n'],budget].append(row)
    summary=[]
    for(n,budget),rr in sorted(groups.items()):
        summary.append(dict(n=n,budget=budget,matched=len(rr),rules=len({r['mask']for r in rr}),inferior=sum(r['inferior']for r in rr),
            root_forks=sum(r['root_fork']for r in rr),root_WIN=sum(r['root_WDL']==1 for r in rr),
            chosen_WDL_histogram=dict(Counter(str(r['chosen_action_WDL'])for r in rr)),
            reason_histogram=dict(Counter(r['actual_reason']for r in rr)),paid_nodes=sum(r['paid_nodes']for r in rr)))
    by=defaultdict(dict)
    for r in rows:by[r['seed']][r['budget']]=r
    paired=dict(roots=len(by),different_actions=sum(v[32768]['action']!=v[131072]['action']for v in by.values()),
        different_action_WDL=sum(v[32768]['chosen_action_WDL']!=v[131072]['chosen_action_WDL']for v in by.values()))
    return dict(source_bundle_sha256=packet['source_bundle_sha256'],matched_returns=len(rows),unmatched_returns=len(unmatched),rows=rows,unmatched=unmatched,summary=summary,paired=paired,seconds=time.perf_counter()-tick,
        scope='Posthoc actualrootdecisionquality oncompletefresh H64/repeat4 matches only. No newPlayer,policyutility,independentrulecalibration orlatentdepth64solve-cost. Twocapsmostlytimebound3s; paidnodes not4xcontrolledwork. Allunmatchedrows explicitlyunavailable; sourcesharedCore isnotindependentengine.')
