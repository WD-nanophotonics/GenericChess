"""Exact history/rank posthoc labels on one qualified four-actor source."""
from pathlib import Path
from collections import Counter
from copy import copy
from array import array
import argparse,gzip,hashlib,json,time
from scripts import leaper_design as L
from scripts.leaper_ab_learner_exposure import restore,write
from scripts.leaper_cooperative_certificate import decode_position,encode_position
from scripts.leaper_history_barrier_rank import solve
from scripts.leaper_microgames import role_stop_requested
from generic_chess.core.identity import repetition_identity_key

def admit_world(world):
    """Reuse fixed full-rule admission without decoding every graph position."""
    c=L.compile_rule(L.ruleset_from_dict(world['rule']))
    if c.ruleset_fingerprint!='173bd8ad8bc61414547559bea1bd9196f9d03f8fb5f3e0f35673f14c5108df77':
        raise ValueError('outside fixed four-actor rule')
    support=c.support;rule=L.ruleset_from_dict(world['rule'])
    if c.max_ply!=64 or c.repetition_limit!=4 or support.repetition_policy!='draw'or support.stalemate_result!='draw':
        raise ValueError('history/clock policy differs')
    if rule.capture_disposition!='remove_from_game'or rule.promotion_allowed or rule.promotion_forced or any(any(x)for masks in rule.drop_allowed.values()for x in masks):
        raise ValueError('capture/promotion/drop outside admission')
    if any(p.is_promotable or any(a.__class__.__name__!='LeapAtom'for a in p.movement_atoms)for p in rule.piece_types):
        raise ValueError('outside plain Leaper scope')
    if any(getattr(support,k)for k in('automatic_adjudications','consecutive_action_adjudications','no_progress_draw','pass_enabled'))or getattr(c,'repeated_cycle_target_conditions',())or getattr(support,'declarations',()):
        raise ValueError('extra history/terminal effect')
    return c

def load(graph,qualification,world):
    g=json.loads(gzip.decompress(graph.read_bytes()));q=L.load(qualification)
    c=admit_world(world)
    if g['rule']!=world['rule']or not q['verified']or q['sha256']!=L.sha(graph)or q['target_fingerprint']!=c.ruleset_fingerprint:
        raise ValueError('complete qualified source binding differs')
    ps=[decode_position(x,c.initial_position)for x in g['positions']]
    ix={p:i for i,p in enumerate(ps)}
    keys={repetition_identity_key(p,c):i for i,p in enumerate(ps)}
    if len(ix)!=len(ps)or len(keys)!=len(ps):raise ValueError('noninjective Position/repetition domain')
    sides=[p.side_to_move for p in ps]
    for i,ee in enumerate(g['edges']):
        if any(sides[i]==sides[j]for j in ee):raise ValueError('nonalternating graph')
    return g,c,ix,keys,sides

def clock_dp(graph,qualification,world,output):
    tick=time.perf_counter();g,c,ix,keys,sides=load(graph,qualification,world)
    ts={int(i):w for i,w in g['terminals'].items()};vs={int(i):v for i,v in g['relative_values'].items()};ranks={int(i):r for i,r in g['ranks'].items()}
    raw=[vs[i]*(1 if sides[i]==0 else-1)for i in range(len(sides))]
    values=[0 if i not in ts or ts[i]is None else 1 if ts[i]==0 else-1 for i in range(len(sides))];rows=[]
    limit=min(64,max(ranks.values(),default=0))
    for h in range(limit+1):
        if role_stop_requested():raise RuntimeError('USER_STOP')
        if values!=[raw[i]if raw[i]and ranks[i]<=h else 0 for i in range(len(sides))]:
            raise ValueError('independent finite-clock Bellman/rank equality differs')
        rows.append(dict(H=h,counts=dict(Counter(values)),sha256=hashlib.sha256(bytes(v+1 for v in values)).hexdigest()))
        future=[(0 if ts[i]is None else 1 if ts[i]==0 else-1)if i in ts else(max if sides[i]==0 else min)(values[j]for j in ee)for i,ee in enumerate(g['edges'])]
        if h==max(ranks.values(),default=0)and future!=values:raise ValueError('clock fixedpoint differs')
        values=future
    out=dict(verified=True,graph_sha256=L.sha(graph),vertices=len(sides),rows=rows,max_physical_rank=max(ranks.values(),default=0),seconds=time.perf_counter()-tick,
        scope='Independent full finite-clock max/min Bellman DP with bothwinningseats. Physical draw-only repeat stops require the separate incoming-barrier theorem; no policy expectation label.')
    write(output,out);return out

def run(cost,graph,qualification,output):
    tick=time.perf_counter();cfg=L.load(cost/'plan.json');row=L.load(cost/'game-000.json')
    g,c,ix,keys,sides=load(graph,qualification,cfg['world']);ts={int(i):w for i,w in g['terminals'].items()}
    # Once B is removed, every legal future stays in the zero-B subdomain.
    # This checks every physical edge there, not only the returned PVs.
    without_B={i for i,p in enumerate(g['positions'])if '6'not in p[1]and '3'not in p[1]}
    if any(j not in without_B for i in without_B for j in g['edges'][i]):
        raise ValueError('B-free subdomain is not closed')
    invariant=dict(vertices=len(without_B),edges=sum(len(g['edges'][i])for i in without_B),
        proposition='Every legal continuation after removal of B has zero free board-B and hand gradients under the unchanged fixed-A material model. No promotion/drop/creation is admitted; all capture ordering is equal. This is a full future-domain invariant, stronger than zero selected-PV Jacobian, but does not establish policy independence before B is removed or a global learner ceiling.')
    cache={};cache_receipts=[]
    def label(s):
        if s.state.terminal_status.is_terminal:
            return dict(value=0 if s.result.winner is None else 1 if s.result.winner==0 else-1,basis='actual_terminal',rank=0)
        i=ix.get(s.state.position)
        if i is None:return dict(value=None,basis='outside_qualified_domain',rank=None)
        cc={keys[k]:n for k,n in s.state.repetition_counts if k in keys}
        b=tuple(sorted(j for j,k in cc.items()if k==3 and j!=i and j not in ts))
        if b not in cache:
            if role_stop_requested():raise RuntimeError('USER_STOP')
            reduction,(_,_,values,ranks)=solve(g['edges'],sides,ts,i,cc,limit=4,remaining=64-s.state.ply_count)
            if reduction['blocked']!=list(b):raise ValueError('incoming barrier selection differs')
            cache[b]=(array('b',(values[j]for j in range(len(sides)))),array('I',(ranks.get(j,2**32-1)for j in range(len(sides)))),len(cache_receipts))
            cache_receipts.append(dict(blocked=list(b),value_digest=hashlib.sha256(bytes(values[j]+1 for j in range(len(sides)))).hexdigest(),decisive=len(ranks),max_rank=max(ranks.values(),default=0)))
        values,ranks,proof=cache[b];raw=values[i]*(1 if sides[i]==0 else-1);rank=None if ranks[i]==2**32-1 else ranks[i];remaining=64-s.state.ply_count
        value=raw if raw==0 or rank<=remaining else 0
        return dict(value=value,basis='barrier_rank_with_clock'if raw==value else'clock_cutoff_DRAW',rank=rank,barrier_value=raw,remaining=remaining,proof=proof,vertex=i,root_count=cc.get(i,0))
    roots=[]
    for source in cfg['world']['roots']:
        s=restore(c,source['record']);roots.append(dict(index=source['index'],state_sha256=L.state_sha(s.state),truth=label(s)))
    s=restore(c,row['initial_record']);queries=[];allactions=L.deserialize_game_record(json.dumps(row['final_record'])).actions
    events={e['state_sha256']:e for e in row['events']if e['kind']=='candidate'};totals=Counter()
    for action in allactions:
        sha=L.state_sha(s.state);event=events.get(sha)
        if event is not None:
            own=label(s);arms=[];chosen=None
            for a in s.legal_actions():
                child=copy(s);child.submit(a);v=label(child)
                arms.append(dict(action=L.record_value(a),truth=v))
                if a==action:chosen=v
            if own['value']is not None and all(a['truth']['value']is not None for a in arms):
                optimum=(max if s.state.position.side_to_move==0 else min)(a['truth']['value']for a in arms)
                if optimum!=own['value']:raise ValueError('actual complete-history frontier Bellman mismatch')
                totals['complete_frontiers']+=1;totals['forks']+=int(len({a['truth']['value']for a in arms})>1)
                totals['suboptimal']+=int(chosen['value']!=own['value'])
            r=event['receipt'];leaf=copy(s)
            for choice in r['pv_choices']:leaf.submit(L.match_action(leaf,choice['action']))
            pv=label(leaf);totals['queries']+=1;totals['root_'+str(own['value'])]+=1;totals['PV_'+str(pv['value'])]+=1
            queries.append(dict(ply=s.state.ply_count,state_sha256=sha,root=own,arms=arms,chosen=chosen,PV=pv,phi=r['pv_phi'],PV_record=L.record_value(leaf.to_record())))
        s.submit(action)
    out=dict(verified=True,producer_sha256=L.sha(Path(__file__)),graph_sha256=L.sha(graph),qualification_sha256=L.sha(qualification),source_cost_sha256=L.sha(cost/'game-000.json'),
        original_roots=roots,queries=queries,counts=dict(totals),barrier_solves=cache_receipts,post_capture_invariant=invariant,seconds=time.perf_counter()-tick,
        scope='Posthoc complete actual histories/clock and allrootlegalfrontiers; no oracle labels in original episode/TD or root selection. Exact WDL under admitted position-local legality, injective keys, alternating play, automatic draw-only repeat4/clockH64 and static terminal precedence; no Uniform payoff or general rules quotient.')
    write(output,out);return out

def tail_check(cost,truth,output):
    """Independent explicit public-Session minimax on four actual late roots.

    No graph, rank, barriers or model scores enter this recursion. Bounded
    incomplete trees stay UNKNOWN and are not retried.
    """
    output.mkdir(parents=True,exist_ok=False);cfg=L.load(cost/'plan.json');row=L.load(cost/'game-000.json')
    selected=[e for e in row['events']if e['kind']=='candidate'][-4:]
    spec=dict(source_cost_sha256=L.sha(cost/'game-000.json'),truth_sha256=L.sha(truth),producer_sha256=L.sha(Path(__file__)),
        plies=[e['ply']for e in selected],per_case_nodes=150000,per_case_seconds=240,whole_seconds=600,
        selection='Last4actual candidate prefixes in original record order, independent of truth/value; no graph/model enters explicit Session recursion. No experimental Player or training.',
        stop='One exclusive verification; capped/missing remainUNKNOWN, no retries/extensions.')
    write(output/'spec.json',spec)
    with(output/'execution.json').open('x',encoding='utf8')as f:json.dump(dict(started=time.time()),f)
    c=L.compile_rule(L.ruleset_from_dict(cfg['world']['rule']));labels={q['ply']:q['root']['value']for q in L.load(truth)['queries']};tick=time.perf_counter();rows=[]
    class End(Exception):pass
    for event in selected:
        if time.perf_counter()-tick>=600 or role_stop_requested():break
        record=dict(row['final_record']);record['actions']=record['actions'][:event['ply']];s=restore(c,record)
        assert L.state_sha(s.state)==event['state_sha256'];began=time.perf_counter();nodes=0
        def walk(current):
            nonlocal nodes
            nodes+=1
            if nodes>=150000 or time.perf_counter()-began>=240 or time.perf_counter()-tick>=600 or role_stop_requested():raise End()
            if current.state.terminal_status.is_terminal:
                return 0 if current.result.winner is None else 1 if current.result.winner==0 else-1
            actor=current.state.position.side_to_move;best=-2 if actor==0 else 2
            for action in current.legal_actions():
                child=copy(current);child.submit(action);v=walk(child)
                best=(max if actor==0 else min)(best,v)
                if best==(1 if actor==0 else-1):break
            return best
        value=None
        try:value=walk(s)
        except End:pass
        if value is not None and value!=labels[event['ply']]:raise ValueError('explicit actual-history minimax differs from barrier/rank truth')
        result=dict(ply=event['ply'],state_sha256=event['state_sha256'],record=record,complete=value is not None,value=value,rank_reduction_value=labels[event['ply']],nodes=nodes,seconds=time.perf_counter()-began)
        rows.append(result);write(output/f"case-{event['ply']}.json",result);print(result['ply'],result['complete'],value,nodes,result['seconds'],flush=True)
    result=dict(verified=all(r['complete']for r in rows)and len(rows)==len(selected),rows=rows,unstarted=[e['ply']for e in selected[len(rows):]],seconds=time.perf_counter()-tick,
        scope='Bounded independent explicit full public Session histories to actual terminal, no graph/attractor/leaf model or new Player. Incomplete comparisons UNKNOWN; accepted completed cases only corroborate this finite source, not universal semantics.')
    write(output/'result.json',result);return result

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('mode',choices=('clock','trace','tail'));a=ap.parse_args()
    cost=Path('artifacts/leaper-four-actor-learner-cost-20261024');p=Path('artifacts/leaper-four-actor-truth-20261024')
    if a.mode=='clock':print(clock_dp(p/'domain.json.gz',p/'qualification.json',L.load(cost/'plan.json')['world'],p/'clock.json')['seconds'])
    elif a.mode=='trace':print(run(cost,p/'domain.json.gz',p/'qualification.json',p/'trace-truth.json')['counts'])
    else:tail_check(cost,p/'trace-truth.json',p/'tail')

