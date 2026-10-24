"""Admission factorization and a two-attacker boundary control, no WDL."""
from pathlib import Path
from itertools import permutations
from dataclasses import replace
from collections import Counter
from datetime import datetime,timezone
import json,time,argparse
from scripts import leaper_design as L
from scripts.leaper_safe_support import orbit,direct_count,rule
from scripts.leaper_delayed_capture_witness import snapshot
from tools.local_agent.common import write_json

BITS=(0,1,2,4,8,16)


def contingency(n):
    matrix=[[0]*6 for _ in range(6)]
    for u,v in permutations(range(n*n),2):
        if max(abs(u%n-v%n),abs(u//n-v//n))<=1:continue
        cells=set(range(n*n))-{u,v};aa=Counter();bb=Counter();same=Counter()
        for z in cells:
            i=BITS.index(orbit(v%n-z%n,v//n-z//n))
            j=BITS.index(orbit(u%n-z%n,u//n-z//n))
            aa[i]+=1;bb[j]+=1;same[i,j]+=1
        for i in range(6):
            for j in range(6):matrix[i][j]+=aa[i]*bb[j]-same[i,j]
    return matrix


def permutation_contingency(n):
    # Separate literal four-actor placements; no product-minus-intersection.
    matrix=[[0]*6 for _ in range(6)]
    for u,a,v,b in permutations(range(n*n),4):
        if max(abs(u%n-v%n),abs(u//n-v//n))<=1:continue
        i=BITS.index(orbit(v%n-a%n,v//n-a//n))
        j=BITS.index(orbit(u%n-b%n,u//n-b//n))
        matrix[i][j]+=1
    return matrix


def evaluate(matrix,a,b):
    return sum(matrix[i][j]for i,x in enumerate(BITS)for j,y in enumerate(BITS)
               if not a&x and not b&y)


def bilinear(matrix):
    return dict(constant=sum(map(sum,matrix)),A_linear=[-sum(matrix[i])for i in range(1,6)],
                B_linear=[-sum(matrix[i][j]for i in range(6))for j in range(1,6)],
                AB_cross=[row[1:]for row in matrix[1:]])


def evaluate_bilinear(p,a,b):
    return (p['constant']+sum(x for i,x in enumerate(p['A_linear'])if a&(1<<i))
            +sum(x for j,x in enumerate(p['B_linear'])if b&(1<<j))
            +sum(p['AB_cross'][i][j]for i in range(5)for j in range(5)if a&(1<<i)and b&(1<<j)))


def measure(plan,output):
    start=datetime.now(timezone.utc);tick=time.perf_counter();rows=[]
    deadline=datetime.fromisoformat(plan['parent_absolute_deadline'])
    write_json(output/'registration.json',dict(plan=plan,source_sha256=L.sha(Path(__file__))))
    for n in plan['boards']:
        if datetime.now(timezone.utc)>=deadline:raise RuntimeError('original parent deadline')
        matrix=contingency(n);independent=permutation_contingency(n);p=bilinear(matrix)
        row=dict(n=n,matrix=matrix,literal_permutation_matrix=independent,bilinear=p,selected_counts={str(a):evaluate(matrix,a,5)for a in(22,23,30,31)})
        rows.append(row);write_json(output/'latest-matrix.json',row)
    # Fixed extra-A scope control: K0a1,A1c2,A2b1,K1c3,Bb2.
    cells=plan['counterexample_cells'];assert cells==[0,5,1,8,4]
    cases=[]
    for a in (22,23,30):
        base=rule(3,a,5,[0,5,8,4]);board=[list(r)for r in base.initial_position]
        board[0][1]=L.Piece(0,'A','A');rr=replace(base,initial_position=tuple(tuple(r)for r in board))
        item=dict(A=a,rule=L.ruleset_to_dict(rr,include_metadata=True))
        write_json(output/('input-extra-A-'+str(a)+'.json'),item)
        try:
            item['root']=snapshot(L.GameSession(L.compile_rule(rr)));item['admitted']=True
        except Exception as exc:
            item.update(admitted=False,exception_type=type(exc).__name__,exception=str(exc))
        cases.append(item);write_json(output/'latest-extra-A.json',item)
    m=dict(started_at=start.isoformat(),ended_at=datetime.now(timezone.utc).isoformat(),producer_seconds_before_final_write=time.perf_counter()-tick,rows=rows,extra_A_control=cases,new_Player_queries=0,new_graph_or_solver_calls=0)
    write_json(output/'measurements.json',m);return m


def qualify(m):
    identities=0
    for row in m['rows']:
        matrix=row['matrix'];assert matrix==row['literal_permutation_matrix'], 'independent contingency mismatch'
        assert all(matrix[i][j]==matrix[j][i]for i in range(6)for j in range(6)), 'role-symmetry mismatch'
        assert bilinear(matrix)==row['bilinear']
        for a in range(32):
            for b in range(32):
                assert evaluate(matrix,a,b)==evaluate_bilinear(row['bilinear'],a,b);identities+=1
        for a in (22,23,30,31):
            assert row['selected_counts'][str(a)]==direct_count(row['n'],a,5)
        assert row['selected_counts']['23']+row['selected_counts']['30']-row['selected_counts']['31']==row['selected_counts']['22']
    old,wa,kn=m['extra_A_control'];assert old['A']==22 and old['admitted']
    assert old['root']['check']==[False,False]
    assert [(x['A'],x['admitted'])for x in m['extra_A_control']]==[(22,True),(23,False),(30,False)]
    assert all('INITIAL_ANCHOR_ATTACKED'in x['exception']for x in(wa,kn)), 'must be actual anchor-safety rejection, not any compiler failure'
    return dict(status='PASS',contingency_boards=[x['n']for x in m['rows']],algebraic_mask_identity_checks=identities,
        exact_support_formula='T-sum_i A_i*x_i-sum_j B_j*y_j+sum_ij C_ij*x_i*y_j for exactly one ordinary actor per role.',
        single_A_lattice='With Bfixed, support intersection maps to mask union and support union maps to mask intersection, because one A-to-K displacement has at mostone active orbit bit.',
        extra_A_counterexample='n3 K0a1,A1c2,A2b1,K1c3,Bb2: A22 admitted; A23 and A30 each fail INITIAL_ANCHOR_ATTACKED by different actors. Single-A union law fails after actor splitting.',
        scope='Initial safe admission only; finite deterministic combinatorial identities, not independent samples or WDL/learning claims. Zero mask is algebraic no-attack reference, not an asserted compilable empty movement type.',new_Player_queries=0,new_graph_or_solver_calls=0)


def main():
    p=argparse.ArgumentParser();p.add_argument('--plan',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    if a.output.exists():raise ValueError('NEW output required')
    a.output.mkdir(parents=True);m=measure(json.loads(a.plan.read_text(encoding='utf-8-sig')),a.output)
    q=qualify(m);write_json(a.output/'qualification.json',q);print(json.dumps(q))


if __name__=='__main__':main()
