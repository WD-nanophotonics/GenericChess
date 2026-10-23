"""Literal Core verification of a finite chance-controller LOWER certificate.

Zero-labelled abort edges are conservative success accounting, never DRAW or
UNKNOWN imputation. The certificate does not claim a best-response solution.
Upper bounds require the separately reproduced complete finite-clock DP.
"""
from collections import Counter
from fractions import Fraction
from pathlib import Path
import argparse,json,time
from scripts import leaper_design as L
from scripts.leaper_explorer_truth import load
from scripts.leaper_cooperative_certificate import decode_position
from scripts.leaper_retrograde import fresh_state
from scripts.leaper_microgames import role_stop_requested
from scripts.verify_leaper_twoa_safety import admission,SOURCE
from generic_chess.core.identity import repetition_identity_key
from generic_chess.core.transition import legal_successors


def verify(packet,certificate,*,seconds=60):
    tick=time.perf_counter();c,_=admission(packet,load(SOURCE));counts=Counter();results=[]
    if c.declarations:raise ValueError('chance controller excludes declarations')
    positions=[decode_position(p,c.initial_position)for p in packet['positions']];indices={p:i for i,p in enumerate(positions)}
    key_index={repetition_identity_key(p,c):i for i,p in enumerate(positions)}
    for policy in certificate['policies']:
        s=L.GameSession.replay(c,L.deserialize_game_record(json.dumps(policy['record'])))
        if L.state_sha(s.state)!=policy['root_state_sha'] or s.state.position!=positions[policy['root']]:raise ValueError('chance full root binding differs')
        if s.state.terminal_status.is_terminal or policy['remaining']!=64-s.state.ply_count:raise ValueError('chance clock differs')
        pre=dict(s.state.repetition_counts);blocked=set(policy['blocked'])
        expected={key_index[k]for k,n in pre.items()if n==3 and k in key_index}
        if blocked!=expected:raise ValueError('chance arrival barriers differ from actual count3')
        rows={r['vertex']:r for r in policy['vertices']}
        if len(rows)!=len(policy['vertices'])or policy['root']not in rows:raise ValueError('chance missing/duplicate vertex')
        base=policy['base'];adj={};start=rows[policy['root']]['distance']
        if type(base)is not int or base<1 or not 0<start<=policy['remaining']:raise ValueError('chance distance/base outside bound')
        for i,row in rows.items():
            if role_stop_requested():raise RuntimeError('USER_STOP')
            if time.perf_counter()-tick>=seconds:raise RuntimeError('CHANCE_VERIFY_CAP_UNKNOWN')
            if type(i)is not int or not 0<=i<len(positions):raise ValueError('chance invalid physical vertex')
            d=row['distance'];num=int(row['numerator']);den=int(row['denominator'])
            if type(d)is not int or not 0<=d<=start or den!=base**d or not 0<num<=den:raise ValueError('chance probability/potential invalid')
            actual=fresh_state(positions[i],c);counts['Core_vertices']+=1;adj[i]=[]
            if actual.terminal_status.is_terminal:
                if actual.terminal_status.winner!=0 or d!=0 or num!=den or row['selected_action_indices']or row['positive_action_indices']:
                    raise ValueError('chance success leaf is not actual target mate')
                continue
            if d==0:raise ValueError('ongoing chance leaf')
            choices=list(legal_successors(actual,c));counts['Core_frontier_edges']+=len(choices)
            selected=row['selected_action_indices'];positive=row['positive_action_indices']
            if len(selected)!=len(set(selected))or len(positive)!=len(set(positive))or not set(positive)<=set(selected):raise ValueError('duplicate/unselected chance action')
            if positions[i].side_to_move==0:
                if len(selected)!=1:raise ValueError('one attacker control action required')
            elif selected!=list(range(len(choices)))or base%len(choices):raise ValueError('Uniform denominator/frontier incomplete')
            if any(type(k)is not int or not 0<=k<len(choices)for k in selected):raise ValueError('illegal chance action index')
            subtotal=0
            for k in positive:
                _,child=choices[k];j=indices.get(child.position);counts['positive_Core_edges']+=1
                if j not in rows or rows[j]['distance']!=d-1:raise ValueError('chance positive potential does not decrease')
                if j in blocked and not(child.terminal_status.is_terminal and child.terminal_status.winner==0):raise ValueError('chance enters repeat4 before success')
                subtotal+=int(rows[j]['numerator']);adj[i].append(j)
            expected=subtotal*(base if positions[i].side_to_move==0 else base//len(choices))
            if expected!=num:raise ValueError('chance probability recurrence differs')
        seen={policy['root']};pending=list(seen)
        while pending:
            for j in adj[pending.pop()]:
                if j not in seen:seen.add(j);pending.append(j)
        if seen!=set(rows):raise ValueError('unreachable chance annotations')
        root=rows[policy['root']]
        if Fraction(int(root['numerator']),int(root['denominator']))!=Fraction(policy['lower']):raise ValueError('root lower bound differs')
        results.append(dict(root_state_sha=policy['root_state_sha'],lower=policy['lower'],potential=start,success_support_vertices=len(rows)))
    return dict(verified=True,counts=dict(counts),rows=results,seconds=time.perf_counter()-tick,Player_queries=0,scope='Complete actualCore defense denominators, one attacker action, exact weighted probability recurrence and strictly decreasing simple path potential. Actual full incoming count3/remaining clock bound every successful branch; abort reward0 is only conservative probability accounting. No policy gain or optimality claim.')


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--graph-packet',type=Path,required=True);p.add_argument('--certificate',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();r=verify(load(a.graph_packet),load(a.certificate));a.output.write_text(json.dumps(r,indent=2),encoding='utf8');print(json.dumps(r))
