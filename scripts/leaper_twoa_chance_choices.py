"""Bound stochastic action quality on existing full-history decisions.

Q means optimal FUTURE oracle continuation versus Uniform defender, not the
return of the tested Player's future actions. Lower bounds use a simple
cooperative DAG with actual incoming repeat barriers; upper bounds omit repeat
stopping. Overlapping bounds are unresolved, never equal or DRAW labels.
"""
from collections import defaultdict,Counter
from fractions import Fraction as F
from functools import reduce
from math import lcm
from pathlib import Path
import argparse,gzip,json,time
from scripts import leaper_design as L
from scripts.leaper_explorer_truth import load
from scripts.leaper_cooperative_truth import cooperative_distances
from scripts.leaper_cooperative_certificate import decode_position
from scripts.leaper_microgames import role_stop_requested
from scripts.verify_leaper_twoa_graph import verify as verify_graph
from scripts.verify_leaper_twoa_safety import admission,SOURCE
from generic_chess.core.identity import repetition_identity_key
from generic_chess.core.transition import legal_successors
from generic_chess.core.actions import action_to_dict


def analyze(graph,c,docs,truth,output,*,seconds=1200):
    tick=time.perf_counter();positions=[decode_position(p,c.initial_position)for p in graph['positions']]
    indices={p:i for i,p in enumerate(positions)};key_index={repetition_identity_key(p,c):i for i,p in enumerate(positions)}
    edges=graph['edges'];sides=[p.side_to_move for p in positions];targets={int(i)for i,v in graph['terminals'].items()if v}
    ds,_=cooperative_distances(edges,targets)
    base=reduce(lcm,(len(es)for es in edges if es),1);rngbase=reduce(lcm,(len(es)for i,es in enumerate(edges)if sides[i]==1 and es),1)
    rows=[];need=defaultdict(set);counts=Counter()
    def guard():
        if role_stop_requested():raise RuntimeError('USER_STOP')
        if time.perf_counter()-tick>=seconds:raise RuntimeError('CHANCE_CHOICES_CAP_UNKNOWN_NO_REFILL')
    def lower(state):
        if state.terminal_status.is_terminal:return F(int(state.terminal_status.winner==0)),0
        root=indices[state.position];remaining=64-state.ply_count
        if root not in ds or ds[root]>remaining:return F(0),0
        blocked={key_index[k]for k,n in state.repetition_counts if n==3 and k in key_index};memo={i:1 for i in targets}
        def go(i):
            if i in memo:return memo[i]
            d=ds[i];good=[j for j in edges[i]if ds.get(j)==d-1 and(j not in blocked or j in targets)]
            if sides[i]==0:value=max((go(j)for j in good),default=0)*rngbase
            else:value=sum(go(j)for j in good)*(rngbase//len(edges[i]))
            memo[i]=value;return value
        value=F(go(root),rngbase**ds[root]);return value,len(memo)-len(targets)
    for game_row in truth['rows']:
        guard();game=json.loads(docs['forward/'+game_row['source_receipt']]);s=L.GameSession.replay(c,L.deserialize_game_record(json.dumps(game['initial_record'])))
        for q in game['queries']:
            if L.state_sha(s.state)!=q['state_sha256']:raise ValueError('chance-choice full prefix differs')
            played=L.match_action(s,q['action'])
            if s.state.position.side_to_move==0:
                branches=[]
                for a,ch in legal_successors(s.state,c):
                    j=indices[ch.position];lo,vertices=lower(ch);counts['lower_DAG_vertices']+=vertices;counts['Core_frontier_edges']+=1
                    h=64-ch.ply_count;need[h].add(j)
                    branches.append(dict(action=action_to_dict(a),vertex=j,remaining=h,actual_terminal=ch.terminal_status.is_terminal,lower=str(lo)))
                wire=action_to_dict(played);selected=next(k for k,a in enumerate(branches)if a['action']==wire)
                rows.append(dict(policy=game['policy'],seed=game['seed'],receipt=game_row['source_receipt'],ply=s.state.ply_count,state_sha=q['state_sha256'],selected=selected,actions=branches))
            s.submit(played)
        print('CHOICES',len(rows),game['policy'],flush=True)
    # One exact common-denominator DP supplies upper bounds only at requested
    # (physical child, remaining clock) pairs, not a large history-TT export.
    optimal=[int(i in targets)for i in range(len(edges))];den=1;bounds={}
    for j in need[0]:bounds[0,j]=F(optimal[j])
    for h in range(1,max(need)+1):
        guard();newden=den*base;new=[0]*len(edges)
        for i,es in enumerate(edges):
            if i in targets:new[i]=newden
            elif es:new[i]=max(optimal[j]for j in es)*base if sides[i]==0 else sum(optimal[j]for j in es)*(base//len(es))
        optimal,den=new,newden
        for j in need[h]:bounds[h,j]=F(optimal[j],den)
    summaries=defaultdict(Counter);strict=[]
    for row in rows:
        for a in row['actions']:
            # Actual terminals precede shadow continuation and clock labels.
            upper=F(a['lower'])if a['actual_terminal'] else bounds[a['remaining'],a['vertex']]
            a['upper']=str(upper)
            if F(a['lower'])>upper:raise ValueError('actual-history lower exceeds relaxed upper')
        selected=row['actions'][row['selected']];best=max(range(len(row['actions'])),key=lambda k:F(row['actions'][k]['lower']))
        gap=F(row['actions'][best]['lower'])-F(selected['upper'])
        row['best_lower_action']=best;row['certified_gap_lower']=str(max(F(0),gap))
        row['quality']='STRICT_ORACLE_CONTINUATION_INFERIOR'if gap>0 else 'UNRESOLVED_INTERVAL_OVERLAP'
        summaries[row['policy']]['contexts']+=1;summaries[row['policy']][row['quality']]+=1
        if gap>0:strict.append({k:v for k,v in row.items()if k!='actions'})
    for p in summaries:
        summaries[p]['games_with_strict']=len({r['seed']for r in strict if r['policy']==p})
    result=dict(status='PASS',summary={p:dict(v)for p,v in summaries.items()},counts=dict(counts),rows=rows,strict=strict,seconds=time.perf_counter()-tick,Player_queries=0,training_episodes=0,scope='All3804existing seat0decision histories, no new rollout. Strict regret concerns optimal FUTURE oracle control against Uniform defender; not the tested Player continuation or measured gain. Actual history/clock lower, no-repeat-stop upper, unresolved overlaps never imputed. Posthoc diagnostic states are not experiential training starts.')
    Path(output).write_text(json.dumps(result,indent=2),encoding='utf8');return result


def mechanisms(c,docs,choices):
    """Describe retained decision/PV data; do not attribute a causal price effect."""
    summaries=defaultdict(Counter);pvrows=[];same_context=defaultdict(dict)
    for row in choices['rows']:
        game=json.loads(docs['forward/'+row['receipt']]);q=game['queries'][row['ply']];d=q.get('decision')
        key=(row['seed'],row['state_sha']);same_context[key][row['policy']]=row
        if d is None:continue
        group=summaries[row['policy']];strict=row['quality']=='STRICT_ORACLE_CONTINUATION_INFERIOR';tag='strict_'if strict else 'all_'
        group['all_queries']+=1;group['all_score_'+str(d['score'])]+=1
        if strict:
            group['strict_queries']+=1;group['strict_score_'+str(d['score'])]+=1
            if d['completed_depth']>=64-row['ply']:group['strict_reported_depth_covers_remaining_clock']+=1
            record=game['final_record']|{'actions':game['final_record']['actions'][:row['ply']]}
            s=L.GameSession.replay(c,L.deserialize_game_record(json.dumps(record)))
            for raw in d['principal_variation']:s.submit(L.match_action(s,raw))
            ordinary=sum(p is not None and p.current_type_id=='A'for p in s.state.position.board)
            group['strict_PV_leaf_A'+str(ordinary)]+=1;group['strict_PV_leaf_'+s.result.status.value]+=1
            pvrows.append(dict(policy=row['policy'],seed=row['seed'],ply=row['ply'],state_sha=row['state_sha'],score=d['score'],completed_depth=d['completed_depth'],reported_selective_depth=d['selective_depth'],termination=d['termination_reason'],remaining=64-row['ply'],PV_plies=len(d['principal_variation']),PV_leaf_A=ordinary,PV_leaf_terminal=s.result.status.value))
    paired=Counter()
    for pair in same_context.values():
        if 'UNIT512'not in pair or 'UNIT65536'not in pair:continue
        low=pair['UNIT512'];high=pair['UNIT65536'];paired['same_seed_full_state_pairs']+=1
        if low['actions'][low['selected']]['action']==high['actions'][high['selected']]['action']:paired['same_selected_action']+=1
        la=low['actions'][low['selected']];ha=high['actions'][high['selected']]
        if F(la['lower'])>F(ha['upper']):paired['low_selected_Q_strictly_better']+=1
        elif F(ha['lower'])>F(la['upper']):paired['high_selected_Q_strictly_better']+=1
        else:paired['selected_Q_intervals_overlap']+=1
    return dict(summary={p:dict(v)for p,v in summaries.items()},paired=dict(paired),strict_PV_rows=pvrows,Player_queries=0,scope='RetainedserveddecisionsandliteralPVs,notnewqueries. Sameexternalfullstatepairsretainwithin-gameTT/budget/time-historydifferences;notisolateddepth/evaluatorcausality. completed/selective_depthmetadataisnotamaximumvisitedplycertificate. AllforcedWDLactionsareDRAW;strictlabelsrefertooptimaloraclecontinuationversusUniform,notminimaxillegalityoractualpolicygain.')


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--packet',type=Path,required=True);p.add_argument('--manifest',type=Path,required=True);p.add_argument('--truth',type=Path,required=True);p.add_argument('--graph-packet',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    if L.sha(a.packet)!=load(a.manifest)['packet_sha256']:raise ValueError('chance-choice packet hash differs')
    truth=load(a.truth)
    if truth['source_packet_sha256']!=L.sha(a.packet):raise ValueError('chance-choice truth source differs')
    docs=json.loads(gzip.decompress(a.packet.read_bytes()))['documents_utf8'];gp=load(a.graph_packet);c,_=admission(gp,load(SOURCE));receipt,graph=verify_graph(gp,load(SOURCE),return_graph=True)
    r=analyze(graph,c,docs,truth,a.output);print(json.dumps({k:v for k,v in r.items()if k not in ('rows','strict')}))
