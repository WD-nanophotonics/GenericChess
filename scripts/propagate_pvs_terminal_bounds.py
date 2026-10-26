"""Finite backward bounds over already checked one-step source edges.

No new game state is expanded. Missing child contexts remain [-1,1].
This is a partial-graph bound deduction, not a complete-game solver.
"""
from collections import Counter
from copy import deepcopy
import argparse,gzip,json,time
from pathlib import Path
from scripts.leaper_truth_compatibility import digest
from scripts.qualify_pvs_source_intake import git_bytes,BASE


def load(path):
    raw=Path(path).read_bytes()
    return json.loads(gzip.decompress(raw)if str(path).endswith('.gz')else raw)


def propagate(frontiers):
    start=time.perf_counter()
    games={g['game_id']:g for g in json.loads(gzip.decompress(git_bytes(BASE+'pilot/games.json.gz')))}
    source_by_key={};representatives={}
    for q in frontiers['queries']:
        r=frontiers['contexts'][q['context_sha256']]
        game=games[q['game_id']]
        record=deepcopy(game['final_record']);record['actions']=record['actions'][:r['context']['ply']]
        if digest(record)!=r['context']['record_sha256']:raise ValueError('parent record binding differs')
        key=(r['context']['ruleset_fingerprint'],r['context']['record_sha256'])
        if key in source_by_key and source_by_key[key]!=r:raise ValueError('same record has different frontier')
        source_by_key[key]=r;representatives[key]=(q,record)
    if len(source_by_key)!=frontiers['distinct_full_contexts']:raise ValueError('source context denominator differs')
    bounds={};details={};links=0;missing=0
    for key,r in sorted(source_by_key.items(),key=lambda item:item[1]['context']['ply'],reverse=True):
        q,record=representatives[key];children=[]
        for child in r['children']:
            record['actions'].append(child['action']);child_key=(key[0],digest(record));record['actions'].pop()
            if child['truth']=='CORE_TERMINAL':
                value=child['wdl_bounds'];status='CORE_TERMINAL'
            elif child_key in bounds:
                target=source_by_key[child_key]
                if target['context']['state_sha256']!=child['state_sha256'] or target['context']['ply']!=r['context']['ply']+1:
                    raise ValueError('record-bound child full state/clock differs')
                value=bounds[child_key];status='LINKED_CHECKED_CONTEXT';links+=1
            else:
                value=[-1,1];status='UNEXPANDED_UNKNOWN';missing+=1
            children.append(dict(action=child['action'],child_key=list(child_key),state_sha256=child['state_sha256'],
                                 bounds=value,authority=status,terminal=child['terminal']))
        op=max if r['context']['side_to_move']==0 else min
        b=[op(c['bounds'][j]for c in children)for j in (0,1)]
        old=r['root_WDL_outer_bounds']
        if b[0]<old[0]or b[1]>old[1]:raise ValueError('backward deduction widened a verified source bound')
        bounds[key]=b
        details[key]=dict(source_context_sha256=q['context_sha256'],case_id=q['case_id'],family=q['family'],
                         record_sha256=key[1],ruleset_fingerprint=key[0],state_sha256=r['context']['state_sha256'],
                         ply=r['context']['ply'],side_to_move=r['context']['side_to_move'],
                         one_step_bounds=old,derived_bounds=b,children=children)
    query_rows=[];counter=Counter()
    for q in frontiers['queries']:
        r=frontiers['contexts'][q['context_sha256']]
        key=(r['context']['ruleset_fingerprint'],r['context']['record_sha256']);d=details[key]
        child=next(c for c in d['children']if c['action']==q['actual_action'])
        exact=child['bounds'][0]==child['bounds'][1]
        counter['selected_exact_action_exposures']+=exact
        counter['selected_exact_ongoing_action_exposures']+=exact and q['actual_child_truth']=='UNKNOWN_ONGOING'
        counter['exact_root_exposures']+=d['derived_bounds'][0]==d['derived_bounds'][1]
        query_rows.append(dict(query_id=q['query_id'],game_id=q['game_id'],case_id=q['case_id'],
                              source_context_sha256=q['context_sha256'],fixed_seat0_root_bounds=d['derived_bounds'],
                              fixed_seat0_selected_action_bounds=child['bounds'],selected_child_source_truth=q['actual_child_truth']))
    result=dict(status='COMPLETE_DEDUCTION_FROM_CHECKED_SOURCE_EDGES',distinct_contexts=len(details),source_exposures=len(query_rows),
        checked_context_links=links,unexpanded_nonterminal_children=missing,
        exact_roots_before=sum(r['root_WDL_outer_bounds'][0]==r['root_WDL_outer_bounds'][1]for r in source_by_key.values()),
        exact_roots_after=sum(b[0]==b[1]for b in bounds.values()),
        tightened_distinct_roots=sum(d['one_step_bounds']!=d['derived_bounds']for d in details.values()),
        bounds_histogram=dict(Counter(str(b)for b in bounds.values())),query_counts=dict(counter),
        contexts=[details[k]for k in sorted(details)],queries=query_rows,seconds=time.perf_counter()-start,
        new_Core_successor_expansions=0,proof_authority='Separate existing finite-certificate verification required for new claimed strategy bounds',new_partial_graph_backward_passes=1,new_Player_calls=0,new_played_games=0,
        scope='New deductions on the already generated, full-record-bound finite partial source graph. Every missing child remains UNKNOWN; no deeper state expansion, terminal-score imputation, training or full-game solve. Exact zeros do not prove strict preferences or policy strength.')
    return result


def main():
    p=argparse.ArgumentParser();p.add_argument('--frontiers',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();r=propagate(load(a.frontiers));a.output.write_text(json.dumps(r,indent=2)+'\n')
    print(json.dumps({k:v for k,v in r.items()if k not in ('contexts','queries')}))
if __name__=='__main__':main()
