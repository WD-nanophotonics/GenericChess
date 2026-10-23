"""Exact nominal headroom bounds for the frozen two-A histories.

The attacker is a hypothetical oracle controller and the defender chooses
uniformly among actual legal moves. A shortest-path DAG gives an attainable
lower bound. Removing repeat stopping gives an optimistic finite-clock MDP
upper bound. Neither is the measured utility of a served Player or learner.
"""
from collections import Counter,defaultdict
from fractions import Fraction
from functools import reduce
from math import lcm
from pathlib import Path
import argparse,hashlib,json,time
from scripts import leaper_design as L
from scripts.leaper_cooperative_truth import cooperative_distances
from scripts.leaper_cooperative_certificate import decode_position
from scripts.leaper_explorer_truth import load
from scripts.leaper_microgames import role_stop_requested
from scripts.verify_leaper_twoa_graph import verify as verify_graph
from scripts.verify_leaper_twoa_safety import admission,SOURCE
from generic_chess.core.identity import repetition_identity_key


def shortest_dag_lower(edges,sides,targets,blocked=(),remaining=64):
    """Only decreasing-distance replies earn reward; all others earn zero.

    One chosen attacker action per DAG vertex; Uniform defender retains its
    FULL legal denominator, including abort replies. Distances strictly drop,
    so paths are simple. A prior count3 arrival aborts before any later move.
    """
    blocked=set(blocked);targets=set(targets)
    distances,_=cooperative_distances(edges,targets,blocked)
    base=reduce(lcm,(len(es) for i,es in enumerate(edges)if sides[i]==1 and es),1)
    numerators={i:1 for i in targets};layers=defaultdict(list);choices={}
    for i,d in distances.items():
        if d:layers[d].append(i)
    for d in range(1,min(remaining,max(layers,default=0))+1):
        for i in layers[d]:
            good=[(k,j)for k,j in enumerate(edges[i])if distances.get(j)==d-1 and(j not in blocked or j in targets)]
            if sides[i]==0:
                if good:
                    k,j=max(good,key=lambda kj:numerators.get(kj[1],0));choices[i]=k
                    numerators[i]=numerators.get(j,0)*base
                else:numerators[i]=0
            else:
                numerators[i]=sum(numerators.get(j,0)for _,j in good)*(base//len(edges[i]))
    return dict(distances=distances,numerators=numerators,choices=choices,base=base)


def shadow_bounds(edges,sides,targets,roots,remaining,guard=lambda:None,progress=lambda row:None):
    """Exact integer Bellman DP, one common denominator per layer.

    Two controls: maximum attacker probability versus Uniform defender, and
    Uniform at BOTH seats. All draw terminals and H64 exits earn zero. Only
    repeat stopping is omitted; no positive actual reward is thereby removed.
    """
    targets=set(targets);base=reduce(lcm,(len(es)for es in edges if es),1);den=1
    optimal=[int(i in targets)for i in range(len(edges))];uniform=list(optimal);rows=[]
    for h in range(1,max(remaining)+1):
        guard();newden=den*base;oo=[0]*len(edges);uu=[0]*len(edges)
        for i,es in enumerate(edges):
            if i in targets:oo[i]=uu[i]=newden
            elif es:
                oo[i]=(max(optimal[j]for j in es)*base if sides[i]==0 else sum(optimal[j]for j in es)*(base//len(es)))
                uu[i]=sum(uniform[j]for j in es)*(base//len(es))
        optimal,uniform,den=oo,uu,newden
        for k,(root,budget)in enumerate(zip(roots,remaining)):
            if h==budget:rows.append(dict(root=k,horizon=h,optimal_upper=str(Fraction(optimal[root],den)),uniform_upper=str(Fraction(uniform[root],den))))
        progress(dict(horizon=h,denominator_bits=den.bit_length(),root0_optimal_upper=str(Fraction(optimal[roots[0]],den))))
    return dict(rows=rows,base=base,arithmetic_edges=sum(map(len,edges))*max(remaining),scope='Exact rational no-repeat-stop finite-clock Bellman DP; maximum over attacker policies versus fixedUniformdefender, and fixedUniformboth control. Upper bounds on actual repeat4 probability, not actual served-player utility.')


def safety_probability(edges,sides,goals,root,horizon,guard=lambda:None):
    """Minimum draw-survival chance, Uniform defense; -1 abort, -2 draw.

    The attacker is adversarially free to MINIMIZE survival, and every defense
    action keeps its full Uniform denominator. A verified draw safety set must
    contain all attacker choices. New repeat stopping can only increase draw
    probability, so omitting those stops preserves this LOWER bound.
    """
    goals=set(goals);base=reduce(lcm,(len(es)for i,es in enumerate(edges)if sides[i]==1 and es),1)
    value=[1]*len(edges);den=1
    for h in range(1,horizon+1):
        guard();newden=den*base;new=[newden if i in goals else 0 for i in range(len(edges))]
        for i,es in enumerate(edges):
            if i in goals:continue
            if not es:raise ValueError('ongoing safety vertex has no moves')
            vv=[0 if j==-1 else den if j==-2 else value[j]for j in es]
            if sides[i]==0:
                if -1 in es:raise ValueError('attacker frontier leaves declared safety')
                new[i]=min(vv)*base
            else:new[i]=sum(vv)*(base//len(es))
        value,den=new,newden
    return Fraction(value[root],den)


def history_chance_gap(graph,c,safety,pair,barrier_chance):
    """Same Position/clock, different optimal chance value under Uniform."""
    from scripts.generic_session_certificate_json import decode_session_certificate
    from scripts.generic_session_win_proof import verify_session_certificate
    tick=time.perf_counter()
    win=L.GameSession.replay(c,L.deserialize_game_record(json.dumps(pair['record'])))
    draw=L.GameSession.replay(c,L.deserialize_game_record(json.dumps(safety['roots'][0]['record'])))
    if win.state.position!=draw.state.position or win.state.ply_count!=draw.state.ply_count:raise ValueError('history chance controlled pair differs')
    if barrier_chance['policies'][0]['root_state_sha']!=L.state_sha(draw.state)or barrier_chance['policies'][0]['record']!=L.record_value(draw.to_record()):raise ValueError('history chance lower belongs to a different full history')
    decoded,proof=decode_session_certificate(c,pair['proof']);receipt=verify_session_certificate(decoded,proof,seconds=30,max_nodes=1000)
    if not receipt['verified']or decoded.state!=win.state:raise ValueError('chance-one forcing certificate differs')
    raw_index={tuple(raw):i for i,raw in enumerate(graph['positions'])};local={raw_index[tuple(raw)]:i for i,raw in enumerate(safety['positions'])}
    root=safety['roots'][0]['local_root'];barriers=set(safety['barriers']);goals={r['index']for r in safety['safety_rows']if 'goal'in r}
    mate_targets={int(i)for i,v in graph['terminals'].items()if v}
    cooperative=cooperative_distances(graph['edges'],mate_targets)[0]
    from generic_chess.core.identity import repetition_identity_key
    pre=dict(draw.state.repetition_counts)
    for i in barriers:
        p=decode_position(safety['positions'][i],c.initial_position)
        if pre.get(repetition_identity_key(p,c),0)!=3:raise ValueError('history chance barrier not bound to count3')
    edges=[];sides=[];terms={int(i):v for i,v in graph['terminals'].items()}
    for i,raw in enumerate(safety['positions']):
        gi=raw_index[tuple(raw)];side=raw[0];sides.append(side)
        if terms.get(gi,0):raise ValueError('scoring terminal inside draw safety')
        if i in goals:
            goal=safety['safety_rows'][i].get('goal')
            if goal=='single_color_obstruction':
                if gi in cooperative:raise ValueError('claimed no-mate exit can reach actual mate')
            elif goal=='literal_draw':
                if gi not in terms or terms[gi]!=0:raise ValueError('claimed literal draw is not terminal')
            elif goal=='prior_arrival_draw':
                if i not in barriers or i==root:raise ValueError('current root is not a future draw arrival')
            else:raise ValueError('unsupported draw-safety exit')
            edges.append([]);continue
        ee=[]
        for gj in graph['edges'][gi]:
            j=local.get(gj)
            if terms.get(gj,0):ee.append(-1) # actual mate precedes repeat
            elif j in barriers:ee.append(-2)
            elif j is None:ee.append(-1)
            else:ee.append(j)
        if side==0 and -1 in ee:raise ValueError('history chance attacker can escape safety')
        if side==1 and all(j==-1 for j in ee):raise ValueError('history chance defense has no safe action')
        edges.append(ee)
    def guard():
        if role_stop_requested():raise RuntimeError('USER_STOP')
        if time.perf_counter()-tick>=300:raise RuntimeError('HISTORY_CHANCE_GAP_CAP_UNKNOWN')
    probability=safety_probability(edges,sides,goals,root,64-draw.state.ply_count,guard)
    upper=1-probability;lower=Fraction(barrier_chance['policies'][0]['lower'])
    if not Fraction(0)<probability<=1 or lower>upper:raise ValueError('history chance lower/upper contradiction')
    return dict(verified=True,root_ply=draw.state.ply_count,same_position=True,same_clock=True,WIN_history_optimal_uniform_value='1',DRAW_history_optimal_uniform_bounds=[str(lower),str(upper)],defender_draw_probability_lower=str(probability),same_position_value_gap_lower=str(probability),any_position_only_value_max_error_lower=str(probability/2),safety_vertices=len(edges),literal_WIN_proof=receipt,seconds=time.perf_counter()-tick,Player_queries=0,scope='Exactfrozenfullhistoriesonly: sameRule/Position/clock butdifferentoptimalchancevalueunderUniformdefense. VerifiedsafetyandallattackerchoicesgivelowerdrawprobabilityagainstANYcontroller;extraactualrepetitiononlyhelpsdraw. Notintrinsicpieceprices, populationlearnergainorarequirementofperfectcalibrationbeforelearning.')


def analyze(packet,graph,c,output,*,seconds=900):
    tick=time.perf_counter();output=Path(output);output.mkdir(parents=True,exist_ok=False)
    def guard():
        if role_stop_requested():raise RuntimeError('USER_STOP')
        if time.perf_counter()-tick>=seconds:raise RuntimeError('RANDOM_HEADROOM_CAP_UNKNOWN_NO_REFILL')
    positions=[decode_position(p,c.initial_position)for p in graph['positions']];indices={p:i for i,p in enumerate(positions)}
    keys={repetition_identity_key(p,c):i for i,p in enumerate(positions)}
    sides=[p.side_to_move for p in positions];targets={int(i)for i,v in graph['terminals'].items()if v};edges=graph['edges']
    roots=[];remaining=[];lower=[];policies=[]
    for sr in packet['roots']:
        guard();s=L.GameSession.replay(c,L.deserialize_game_record(json.dumps(sr['record'])));root=indices[s.state.position];budget=64-s.state.ply_count
        blocked={keys[k]for k,n in s.state.repetition_counts if n==3 and k in keys}
        table=shortest_dag_lower(edges,sides,targets,blocked,budget);distance=table['distances'].get(root)
        probability=Fraction(table['numerators'].get(root,0),table['base']**distance)if distance is not None and distance<=budget else Fraction(0)
        # The controller is defined at every successful DAG node. Export only
        # the success-support reachable from this root; off-support reward0.
        pending=[root];seen=set();vertices=[]
        while pending:
            i=pending.pop()
            if i in seen:continue
            seen.add(i);d=table['distances'][i]
            selected=[] if not d else [table['choices'][i]]if sides[i]==0 else list(range(len(edges[i])))
            good=[]
            for k in selected:
                j=edges[i][k]
                if table['distances'].get(j)==d-1 and(j not in blocked or j in targets)and table['numerators'].get(j,0)>0:
                    good.append(k);pending.append(j)
            vertices.append(dict(vertex=i,distance=d,numerator=str(table['numerators'].get(i,0)),denominator=str(table['base']**d),selected_action_indices=selected,positive_action_indices=good))
        policy=dict(root=root,record=sr['record'],root_state_sha=L.state_sha(s.state),remaining=budget,blocked=sorted(blocked),base=table['base'],lower=str(probability),vertices=vertices)
        policies.append(policy);lower.append(dict(root=len(roots),lower=str(probability),cooperative_distance=distance,success_support_vertices=len(vertices)))
        roots.append(root);remaining.append(budget)
    progress=[]
    def report(row):
        progress.append(row)
        if row['horizon']%8==0:print('HEADROOM',row['horizon'],row['denominator_bits'],flush=True)
    upper=shadow_bounds(edges,sides,targets,roots,remaining,guard,report)
    for lo in lower:
        hi=next(r for r in upper['rows']if r['root']==lo['root'])
        if Fraction(lo['lower'])>Fraction(hi['optimal_upper']):raise ValueError('attainable lower exceeds optimistic upper')
        lo.update(hi);lo['lower_minus_uniform_upper']=str(Fraction(lo['lower'])-Fraction(hi['uniform_upper']))
    result=dict(status='PASS',source_sha='303cb4c6d6d5e706be04f9df20ec6746556d1fc2',source_graph_sha256=hashlib.sha256(json.dumps(packet,sort_keys=True,separators=(',',':')).encode()).hexdigest(),rule_fingerprint=c.ruleset_fingerprint,rows=lower,policies=policies,upper=upper,progress=progress,seconds=time.perf_counter()-tick,Player_queries=0,training_episodes=0,scope='Hypothetical explicitly oracle-controlled chance headroom on two previously frozen complete0/4histories. Not an experiential training start, new rollout, actual learner gain, learned material price, actual no-repeat policy utility, or PRIMARY campaign/default. Static forcedDRAW and positive utility against aUniformdefender are different estimands.')
    (output/'result.json').write_text(json.dumps(result,indent=2),encoding='utf8');return result


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--graph-packet',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();packet=load(a.graph_packet);source=load(SOURCE);c,_=admission(packet,source)
    receipt,graph=verify_graph(packet,source,return_graph=True);r=analyze(packet,graph,c,a.output)
    print(json.dumps({k:v for k,v in r.items()if k not in ('policies','progress')}))
