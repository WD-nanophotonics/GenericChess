"""Exact fresh initializer law and immediate-mate entry region, B5 only."""
from pathlib import Path
from dataclasses import replace
from itertools import permutations
from datetime import datetime,timezone
import argparse,json,time
from scripts import leaper_design as L
from scripts.leaper_corner_capacity_law import rule as five_rule,d4
from scripts.leaper_parity_scope import adjacent
from scripts.leaper_rule_coordinates import physical_action
from scripts.leaper_delayed_capture_witness import snapshot
from tools.local_agent.common import write_json


def attacks_from(sq,n,offsets):
    x,y=sq%n,sq//n
    return {(y+dy)*n+x+dx for dx,dy in offsets if 0<=x+dx<n and 0<=y+dy<n}


def mu_count(n):
    cells=set(range(n*n));aa={v:attacks_from(v,n,L.offsets(22))for v in cells}
    bb={u:attacks_from(u,n,L.offsets(5))for u in cells};count=0
    for u,v in permutations(range(n*n),2):
        if adjacent((u%n,u//n),(v%n,v//n)):continue
        a=cells-{u,v}-aa[v];b=cells-{u,v}-bb[u]
        count+=len(a)*len(b)-len(a&b)
    return count


def brute_mu(n):
    count=0;aa=set(L.offsets(22));bb=set(L.offsets(5))
    for k,a,v,b in permutations(range(n*n),4):
        if max(abs(k%n-v%n),abs(k//n-v//n))<=1:continue
        if(v%n-a%n,v//n-a//n)in aa:continue
        if(k%n-b%n,k//n-b//n)in bb:continue
        count+=1
    return count


def incoming(n):
    rows={}
    canonical=[2,2*n+2,0,n]
    for k,post,v,b in d4(canonical,n):
        px,py=post%n,post//n
        for dx,dy in L.offsets(22):
            ax,ay=px-dx,py-dy
            if not(0<=ax<n and 0<=ay<n):continue
            a=ay*n+ax
            if a in(k,v,b):continue
            if(v%n-a%n,v//n-a//n)in set(L.offsets(22)):continue
            if(k%n-b%n,k//n-b//n)in set(L.offsets(5)):continue
            cells=(k,a,v,b);key=(cells,('A',a,post,None))
            rows[key]=dict(placement=list(cells),action_key=['A',a,post,None])
    return list(rows.values())


def fresh_rule(n,mask,cells):
    r=five_rule(mask,5);board=[None]*(n*n)
    for sq,owner,tid in zip(cells,(0,0,1,1),('K','A','K','B')):
        board[sq]=L.Piece(owner,tid,tid)
    return replace(r,board_size=n,initial_position=tuple(tuple(board[n*y:n*y+n])for y in range(n)),
                   drop_allowed={t:((False,)*(n*n),)*2 for t in('A','B')})


def measure(output):
    tick=time.perf_counter();started=datetime.now(timezone.utc).isoformat()
    write_json(output/'registration.json',dict(started_at=started,source_sha256=L.sha(Path(__file__)),
        B_mask=5,boards=[3,4,5],predicted_immediate_mate_roots=[0,24,64],cap_seconds=600,
        law='Uniform over paired full rules with common safe physical fresh initializer, not one hidden fixedRuleSet'))
    cohorts=[]
    for n in(3,4,5):
        if time.perf_counter()-tick>=600:raise RuntimeError('frozen cap')
        total=mu_count(n);brute=brute_mu(n)if n<=4 else None
        rows=incoming(n);cases=[]
        for row in rows:
            high=fresh_rule(n,22,row['placement']);low=fresh_rule(n,6,row['placement'])
            states=[];shared=None
            for mask,rule in((6,low),(22,high)):
                c=L.compile_rule(rule);s=L.GameSession(c);root=snapshot(s)
                actions={physical_action(L.record_value(a),n):a for a in s.legal_actions()}
                k=tuple(row['action_key']);exists=k in actions
                if mask==6:shared=exists
                after=None
                if exists:s.submit(actions[k]);after=snapshot(s)
                states.append(dict(mask=mask,rule=L.ruleset_to_dict(rule,include_metadata=True),
                                   root=root,action_present=exists,after=after))
            cases.append(dict(**row,shared=shared,states=states))
            write_json(output/'latest-raw-positive.json',cases[-1])
        cohorts.append(dict(n=n,mu_count=total,independent_brute_count=brute,positive_cases=cases))
    return dict(started_at=started,ended_at=datetime.now(timezone.utc).isoformat(),seconds=time.perf_counter()-tick,
                cohorts=cohorts,new_Player_queries=0,new_graph_or_solver_calls=0)


def qualify(m):
    summary=[]
    for row in m['cohorts']:
        n=row['n'];expected={3:0,4:24,5:64}[n]
        assert len(row['positive_cases'])==expected
        if n<=4:assert row['independent_brute_count']==row['mu_count']
        keys={tuple(x['placement'])for x in row['positive_cases']}
        assert len(keys)==expected
        shared=sum(c['shared']for c in row['positive_cases'])
        assert shared=={3:0,4:24,5:40}[n]
        for case in row['positive_cases']:
            low,high=case['states']
            assert low['root']['state']['position']['board']==high['root']['state']['position']['board']
            assert low['root']['state']['terminal_status']['status']=='ongoing'
            assert high['action_present']and high['after']['result']['status']=='checkmate'
            assert high['after']['result']['winner']==0
            if case['shared']:
                assert low['after']['result']['status']=='ongoing'
        summary.append(dict(n=n,mu_count=row['mu_count'],immediate_mate_roots=expected,
                            shared_winning_actions=shared,new_winning_actions=expected-shared,
                            exact_immediate_mate_probability=f'{expected}/{row["mu_count"]}',
                            approximate_probability=expected/row['mu_count']))
    return dict(status='PASS',summary=summary,
                interpretation='Exact geometric fresh initializer incidence of at least one immediate mate. Other n4/n5 rootWDL and total forcedWIN rate UNKNOWN; n3 zero all-mate entry proven separately.',
                asymptotic='For n>=5 the local inverse-corner templates fit fully:64 distinct roots. mu_n=n^8+O(n^6) because only finite-local attacks/royal adjacency/collisions are excluded. Immediate incidence is Theta(n^-8), not an assertion about overall game difficulty or WIN rate.',
                new_Player_queries=0,new_graph_or_solver_calls=0)


def main():
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    if a.output.exists():raise ValueError('NEW output required')
    a.output.mkdir(parents=True);m=measure(a.output);write_json(a.output/'measurements.json',m)
    q=qualify(m);write_json(a.output/'qualification.json',q);print(json.dumps(q))


if __name__=='__main__':main()
