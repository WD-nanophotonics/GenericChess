"""Post-hoc reuse of frozen task2625 records; no games, training or search."""
from __future__ import annotations
from collections import Counter,defaultdict
import gzip,hashlib,json,subprocess
from pathlib import Path

BASE=Path(__file__).resolve().parents[1]
RUN=BASE/'results/dev_aux/task2625/run'
HISTORY='4d0fd6d4279e361927368ee656c9727d266ffb74'

def historical(path):
    return subprocess.check_output(['git','show',HISTORY+':'+str(path).replace('\\','/')],cwd=BASE)

def frozen_bytes(name):
    relative='results/dev_aux/task2625/run/'+name
    archive=gzip.decompress(historical(relative+'.gz'))
    local=RUN/name
    if local.exists()and local.read_bytes()!=archive:
        raise ValueError('local trace differs from immutable historical archive: '+name)
    return archive

def reanalyze(output):
    games_raw=frozen_bytes('eval-games.jsonl')
    assert hashlib.sha256(games_raw).hexdigest()=='7426c7f8c1d5834a59dbd5992fcae1b19a4e05e6601e8412ccae9de0bc9123e8'
    games=[json.loads(s)for s in games_raw.splitlines()]
    pairs=defaultdict(dict)
    for g in games:
        *key,endpoint=g['slot'];assert endpoint not in pairs[tuple(key)]
        pairs[tuple(key)][endpoint]=g
    assert len(games)==1024 and len(pairs)==512
    rows=[];wanted={};groups=Counter()
    for key,endpoints in sorted(pairs.items()):
        a,b=endpoints['TDLeaf'],endpoints['initial']
        assert a['initial_record']==b['initial_record']
        category=f"TD={a['reward']};initial={b['reward']}";groups[category]+=1
        x,y=a['final_record']['actions'],b['final_record']['actions'];start=len(a['initial_record']['actions'])
        split=next((i for i,(u,v)in enumerate(zip(x,y))if u!=v),None)
        row=dict(pair=key,category=category,TDLeaf_reward=a['reward'],initial_reward=b['reward'],
            split_ply=None if split is None else split-start,
            relation='identical_actions'if x==y else'prefix_only'if split is None else'action_divergence')
        if split is not None:
            assert split>=start
            for endpoint in('TDLeaf','initial'):wanted[tuple(key)+(endpoint,),split-start]=row
        rows.append(row)
    queries_raw=frozen_bytes('eval-queries.jsonl');qs={};query_count=0
    for line in queries_raw.splitlines():
        q=json.loads(line);query_count+=1;k=tuple(q['slot']),q['ply']
        if k in wanted:qs[k]=q
    split_counts=defaultdict(Counter)
    for row in rows:
        if row['split_ply']is None:
            split_counts[row['category']][row['relation']]+=1;continue
        key=tuple(row['pair']);ply=row['split_ply']
        a,b=(qs[key+(e,),ply]for e in('TDLeaf','initial'))
        assert a['record_before']==b['record_before']and a['actor']==b['actor']
        actor='candidate'if a['actor']==key[3]else'fixed_foe'
        row.update(first_actor=actor,complete_both=a['complete']and b['complete'],
            weights_equal=a['weights']==b['weights'],root_values_equal=a['value']==b['value'],
            requested_nodes_equal=a['requested_nodes']==b['requested_nodes'],
            TDLeaf_search_value=a['value'],initial_search_value=b['value'])
        if actor=='fixed_foe':assert a['weights']==b['weights']
        split_counts[row['category']][actor]+=1
    examples=[]
    for rewards in((1,-1),(-1,1)):
        candidates=[r for r in rows if(r['TDLeaf_reward'],r['initial_reward'])==rewards]
        for actor in('fixed_foe','candidate'):
            row=next((r for r in candidates if r.get('first_actor')==actor),None)
            if row is None:continue
            key=tuple(row['pair']);ply=row['split_ply']
            examples.append(dict(row,TDLeaf_game=pairs[key]['TDLeaf'],initial_game=pairs[key]['initial'],
                split_queries={e:qs[key+(e,),ply]for e in('TDLeaf','initial')}))
    source=historical('results/dev_aux/task2625/evaluate.py').decode('utf-8')
    assert '(endpoint == "TDLeaf") + ply'in source
    summary=dict(scope='Post-hoc finite paired trajectory analysis;not independent holdout or causal action-optimality test. No new search or games.',
        history_revision=HISTORY,game_sha256=hashlib.sha256(games_raw).hexdigest(),
        query_sha256=hashlib.sha256(queries_raw).hexdigest(),games=len(games),pairs=len(pairs),queries=query_count,
        categories=groups,first_divergence_by_category=dict(split_counts),
        fixed_foe_splits=sum(r.get('first_actor')=='fixed_foe'for r in rows),
        fixed_foe_equal_value_complete_splits=sum(r.get('first_actor')=='fixed_foe'and r['complete_both']and r['root_values_equal']and r['requested_nodes_equal']for r in rows),
        ordering_seed_caveat='Frozen evaluate.py adds (endpoint == TDLeaf) to the ordering seed. Fixed foe and shared history therefore do not imply identical random tie order. Endpoint differences are not isolated weight interventions.',
        missing_information='Logs store selected PV material features/value, not the complete PV action path or all alternative action values. Actual winning rollout does not certify optimality of the split action.')
    output=Path(output);output.mkdir(parents=True,exist_ok=False)
    for name,value in(('summary.json',summary),('pairs.json',rows),('examples.json',examples)):
        (output/name).write_text(json.dumps(value,indent=2),encoding='utf-8')
    print(json.dumps(summary,indent=2));return summary

if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('output')
    reanalyze(parser.parse_args().output)
