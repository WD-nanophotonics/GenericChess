"""Independent integrity audit for closed task2606 logs; no outcome imputation."""
from collections import Counter, defaultdict
from pathlib import Path
import json

D = Path('results/dev_aux/task2606')
def load(name): return json.loads((D/name).read_text(encoding='utf-8'))
def rows(name):
    with (D/name).open(encoding='utf-8') as f:
        for line in f:
            if line.strip(): yield json.loads(line)

def main():
    plan, train = load('plan.json'), load('result.json')
    expected = [tuple(x) for x in plan['arms_order']]
    arms = [tuple((a['generator_seed'], a['seed'], a['method'])) for a in train['arms']]
    assert len(arms) == len(set(arms)), 'duplicate completed training arm'
    assert arms == expected[:len(arms)], 'training arm order/identity mismatch'
    qr = list(rows('queries.jsonl')); gr = list(rows('games.jsonl'))
    arm_nodes, actor_nodes, game_queries = Counter(), defaultdict(Counter), Counter()
    observed, incomplete_observed = Counter(), Counter()
    for q in qr:
        k=(q['generator_seed'],q['seed'],q['method'])
        arm_nodes[k]+=q['nodes']; game_queries[q['gameid']]+=1
        actor_nodes[k]['candidate' if q['actor']==q['color'] else 'fixed_opponent']+=q['nodes']
        assert q['learner_actor']==(q['actor']==q['color'])
        assert q['observed']==(q['complete'] and q['actor']==q['color'])
        if q['observed']: observed[k]+=1
        if q['observed'] and not q['complete']: incomplete_observed[k]+=1
    assert not any(incomplete_observed.values())
    assert len({g['gameid'] for g in gr})==len(gr)
    for a,k in zip(train['arms'],arms):
        assert arm_nodes[k]==a['nodes']
        assert a['nodes']<=plan['nodes_per_arm']
        if a['cause']=='TOTAL_NODES': assert a['nodes']==plan['nodes_per_arm']
        assert a['observations']==observed[k]
    game_ids={g['gameid'] for g in gr}
    assert set(game_queries).issubset(game_ids)
    assert all(game_queries.get(g['gameid'],0)==g['queries'] for g in gr)
    assert sum(a['nodes'] for a in train['arms'])==train['nodes']
    assert train['nodes']<=plan['target_training_nodes']
    out={'training_status':train['status'],'planned_arms':len(expected),'completed_arms':len(arms),'unique_training_games':len(gr),'query_rows':len(qr),'paid_nodes':train['nodes'],'per_arm_nodes_match_query_sums':True,'roles_and_observation_schedule':'PASS','incomplete_observations':sum(incomplete_observed.values()),'unknown_training_games':sum(g['outcome'] is None for g in gr),'candidate_nodes_by_method':{m:sum(actor_nodes[k]['candidate'] for k in actor_nodes if k[2]==m) for m in plan['methods']},'opponent_nodes_by_method':{m:sum(actor_nodes[k]['fixed_opponent'] for k in actor_nodes if k[2]==m) for m in plan['methods']}}
    if (D/'eval-result.json').exists():
        ep, er=load('eval-plan.json'),load('eval-result.json'); eg=list(rows('eval-games.jsonl')); eq=list(rows('eval-queries.jsonl'))
        slots=[tuple(x) for x in ep['slots']]; seen=[tuple(x['slot']) for x in eg]
        assert len(seen)==len(set(seen)), 'duplicate eval slot'
        assert set(seen)==set(slots), 'eval games not exact registered slot set'
        assert len(eg)==er['actual'] and er['expected']==len(slots)
        if er['status']=='COMPLETE': assert er['missing']==0
        else: assert er['missing']>0
        assert all(x['outcome'] in (-1,0,1,None) for x in eg)
        assert all((x['outcome'] is None)==(x['reward'] is None) for x in eg)
        assert sum(x['nodes'] for x in eg)==er['nodes']
        assert sum(x['queries'] for x in eg)==er['queries']
        out['evaluation']={'status':er['status'],'registered_slots':len(slots),'unique_actual_slots':len(set(seen)),'game_rows':len(eg),'query_rows':len(eq),'nodes':er['nodes'],'unknown_outcomes':sum(x['outcome'] is None for x in eg),'duplicate_slots':0,'missing_slots':len(set(slots)-set(seen)),'exact_slot_set':('PASS' if set(seen)==set(slots) else 'PARTIAL_REGISTERED_PREFIX')}
    (D/'integrity-audit.json').write_text(json.dumps(out,indent=2,sort_keys=True)+'\n',encoding='utf-8')
    print(json.dumps(out,indent=2))
if __name__=='__main__': main()
