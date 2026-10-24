"""Exact fresh-safe support, not a game graph or outcome solver.

The finite pair-constraint inclusion/exclusion method keeps collisions, Royal
adjacency and both directed ordinary-to-Royal attacks distinct. Component
translation spans yield a positive-part formula and a stable polynomial for n>=5.
"""
from pathlib import Path
from collections import Counter
from itertools import product, permutations
from datetime import datetime, timezone, timedelta
import argparse, json, time
from scripts import leaper_design as L
from scripts.leaper_delayed_capture_witness import snapshot
from tools.local_agent.common import write_json


def orbit(dx,dy):
    x,y=sorted((abs(dx),abs(dy)))
    return {(0,1):1,(1,1):2,(0,2):4,(1,2):8,(2,2):16}.get((x,y),0)


def safe(cells,n,a,b):
    u,x,v,y=cells
    if len(set(cells))!=4 or any(type(z)is not int or not 0<=z<n*n for z in cells):return False
    if max(abs(u%n-v%n),abs(u//n-v//n))<=1:return False
    return not (orbit(v%n-x%n,v//n-x//n)&a or orbit(u%n-y%n,u//n-y//n)&b)


def direct_count(n,a,b):
    cells=set(range(n*n))
    # Independent coordinate classifier rather than imported orbit tables.
    forbidden_a={v:{x for x in cells if orbit(x%n-v%n,x//n-v//n)&a} for v in cells}
    forbidden_b={u:{x for x in cells if orbit(x%n-u%n,x//n-u//n)&b} for u in cells}
    count=0
    for u,v in permutations(range(n*n),2):
        if max(abs(u%n-v%n),abs(u//n-v//n))<=1:continue
        aa=cells-{u,v}-forbidden_a[v];bb=cells-{u,v}-forbidden_b[u]
        count+=len(aa)*len(bb)-len(aa&bb)
    return count


def brute(n,a,b):
    return sum(safe(p,n,a,b)for p in permutations(range(n*n),4))


def offset_constraints(a,b):
    # Coordinates are (K0,A,K1,B); symmetric leap atoms make orientation exact.
    return [(0,1,((0,0),)),(0,2,((0,0),*L.offsets(3))),
            (0,3,((0,0),*L.offsets(b))),(1,2,((0,0),*L.offsets(a))),
            (1,3,((0,0),)),(2,3,((0,0),))]


def component_spans(selected):
    graph=[[]for _ in range(4)]
    for u,v,(dx,dy) in selected:
        graph[u].append((v,dx,dy));graph[v].append((u,-dx,-dy))
    assigned={};spans=[]
    for start in range(4):
        if start in assigned:continue
        assigned[start]=(0,0);stack=[start];points=[]
        while stack:
            u=stack.pop();x,y=assigned[u];points.append((x,y))
            for v,dx,dy in graph[u]:
                want=(x+dx,y+dy)
                if v in assigned:
                    if assigned[v]!=want:return None
                else:assigned[v]=want;stack.append(v)
        spans.append((max(p[0]for p in points)-min(p[0]for p in points),
                      max(p[1]for p in points)-min(p[1]for p in points)))
    return tuple(sorted(spans))


def span_terms(a,b):
    constraints=offset_constraints(a,b);terms=Counter();consistent=0;total=0
    for choices in product(*[(None,*offsets)for _,_,offsets in constraints]):
        total+=1;selected=[(u,v,d)for (u,v,_),d in zip(constraints,choices)if d is not None]
        spans=component_spans(selected)
        if spans is None:continue
        consistent+=1;terms[spans]+=(-1)**len(selected)
    return [dict(spans=[list(x)for x in k],coefficient=v)for k,v in sorted(terms.items())if v],dict(total_offset_assignments=total,consistent_assignments=consistent)


def polynomial(terms):
    coefficients=Counter()
    for term in terms:
        p={0:term['coefficient']}
        for sx,sy in term['spans']:
            next_p=Counter()
            for degree,value in p.items():
                for k,c in ((2,1),(1,-sx-sy),(0,sx*sy)):next_p[degree+k]+=value*c
            p=dict(next_p)
        coefficients.update(p)
    return {str(k):v for k,v in sorted(coefficients.items())if v}


def count_from_terms(terms,n):
    total=0
    for t in terms:
        value=t['coefficient']
        for sx,sy in t['spans']:value*=max(0,n-sx)*max(0,n-sy)
        total+=value
    return total


def evaluate_polynomial(coeff,n):
    return sum(v*n**int(k)for k,v in coeff.items())


def rule(n,a,b,cells):
    board=[None]*(n*n)
    for sq,owner,tid in zip(cells,(0,0,1,1),('K','A','K','B')):board[sq]=L.Piece(owner,tid,tid)
    return L.RuleSet(board_size=n,piece_types=tuple(L.PieceType(t,t,
        tuple(L.LeapAtom(v)for v in L.offsets(mask)),is_anchor=(t=='K'))
        for t,mask in (('K',3),('A',a),('B',b))),
        initial_position=tuple(tuple(board[n*y:n*y+n])for y in range(n)),
        drop_allowed={t:((False,)*(n*n),)*2 for t in ('A','B')},max_ply=6,
        repetition_limit=2,stalemate_result='draw',capture_disposition='remove_from_game')


def measure(plan,output):
    start=datetime.now(timezone.utc);tick=time.perf_counter()
    deadline=datetime.fromisoformat(plan['started_at'])+timedelta(seconds=plan['cost']['hard_preparation_analysis_cap_seconds'])
    def gate():
        if datetime.now(timezone.utc)>=deadline:raise RuntimeError('Original support-analysis inclusive cap; no extension')
    reg=dict(plan=plan,source_sha256=L.sha(Path(__file__)),started_at=start.isoformat(),deadline=deadline.isoformat())
    write_json(output/'registration.json',reg)
    cases=[]
    for a in plan['count_targets']['A_masks']:
        gate();b=plan['count_targets']['B_mask'];terms,work=span_terms(a,b);coeff=polynomial(terms)
        rows=[]
        for n in plan['count_targets']['boards']:
            gate();row=dict(n=n,inclusion_exclusion=count_from_terms(terms,n),direct=direct_count(n,a,b),polynomial=evaluate_polynomial(coeff,n),brute=brute(n,a,b)if n<=4 else None)
            rows.append(row);write_json(output/'latest-count.json',row)
        cases.append(dict(A=a,B=b,terms=terms,polynomial=coeff,work=work,counts=rows))
    maximal=[]
    for ia,ib in product(range(5),repeat=2):
        gate();a=31^(1<<ia);b=31^(1<<ib)
        witnesses=[p for p in permutations(range(9),4)if safe(p,3,a,b)]
        witness=witnesses[0]if witnesses else None
        row=dict(A=a,B=b,missing_A=1<<ia,missing_B=1<<ib,count=len(witnesses),placement=witness)
        if witness is not None:
            rr=rule(3,a,b,witness);row['rule']=L.ruleset_to_dict(rr,include_metadata=True)
            write_json(output/'latest-input.json',row)
            row['root']=snapshot(L.GameSession(L.compile_rule(rr)))
        maximal.append(row);write_json(output/'latest-maximal-pair.json',row)
    corners=[0,15,12,3];rr=rule(4,31,31,corners)
    corner=dict(n=4,A=31,B=31,placement=corners,rule=L.ruleset_to_dict(rr,include_metadata=True))
    write_json(output/'corner-input.json',corner);corner['root']=snapshot(L.GameSession(L.compile_rule(rr)))
    gate()
    m=dict(started_at=start.isoformat(),ended_at=datetime.now(timezone.utc).isoformat(),producer_seconds_before_final_write=time.perf_counter()-tick,cases=cases,maximal_proper_pairs=maximal,universal_n4_witness=corner,new_Player_queries=0,new_graph_or_solver_calls=0)
    write_json(output/'measurements.json',m)
    return reg,m


def qualify(reg,m):
    assert [c['A']for c in m['cases']]==[23,30,31]
    for case in m['cases']:
        a,b=case['A'],case['B'];assert b==5
        reconstructed,work=span_terms(a,b)
        assert case['terms']==reconstructed and case['work']==work, 'complete translation terms required'
        assert case['polynomial']==polynomial(reconstructed), 'polynomial not bound to translation terms'
        assert [r['n']for r in case['counts']]==reg['plan']['count_targets']['boards']
        coeff=case['polynomial'];assert coeff['8']==1 and coeff.get('7',0)==0
        assert coeff['6']==-(14+len(L.offsets(a))+len(L.offsets(b)))
        assert max(max(x)for t in case['terms']for x in t['spans'])<=5
        for row in case['counts']:
            assert row['inclusion_exclusion']==count_from_terms(reconstructed,row['n']), 'translation count mismatch'
            assert row['direct']==direct_count(row['n'],a,b), 'independent direct count mismatch'
            assert row['polynomial']==evaluate_polynomial(coeff,row['n']), 'retained polynomial value mismatch'
            assert row['inclusion_exclusion']==row['direct'], 'independent support count mismatch'
            if row['brute']is not None:assert row['brute']==row['direct']
            if row['n']>=5:assert row['polynomial']==row['direct'], 'stable polynomial mismatch'
    by={c['A']:c for c in m['cases']}
    assert by[31]['counts'][0]['direct']==0
    assert by[23]['counts'][0]['direct']==152
    assert by[31]['counts'][1]['direct']>0
    maxpairs=m['maximal_proper_pairs'];assert len(maxpairs)==25
    assert {(x['missing_A'],x['missing_B'])for x in maxpairs}==set(product((1,2,4,8,16),repeat=2))
    for row in maxpairs:
        assert row['A']==31^row['missing_A'] and row['B']==31^row['missing_B'], 'missing-bit rule binding mismatch'
        assert row['count']==brute(3,row['A'],row['B']), 'maximal pair count mismatch'
        assert row['count']>0 and safe(row['placement'],3,row['A'],row['B'])
        rr=rule(3,row['A'],row['B'],row['placement'])
        assert L.ruleset_to_dict(rr,include_metadata=True)==row['rule']
        assert snapshot(L.GameSession(L.compile_rule(rr)))==row['root']
        assert row['root']['check']==[False,False]
    row=m['universal_n4_witness'];assert row['placement']==[0,15,12,3]
    assert (row['n'],row['A'],row['B'])==(4,31,31)
    assert row['rule']==L.ruleset_to_dict(rule(4,31,31,row['placement']),include_metadata=True)
    assert snapshot(L.GameSession(L.compile_rule(L.ruleset_from_dict(row['rule']))))==row['root']
    assert row['root']['check']==[False,False]
    return dict(status='PASS',cases=[dict(A=c['A'],B=c['B'],polynomial=c['polynomial'],counts=c['counts'])for c in m['cases']],
        proper_pair_min_count=min(x['count']for x in maxpairs),maximal_proper_pairs=25,
        n3_support_theorem='For A/Bnonempty5orbit masks, safe fresh support nonempty iff both masks differfrom31. Any multiple-rulecommon support equals support of their orbitwise A/Bunions.',
        n4_and_larger='All such rule intersections have a common fourcorner initializer; distances>=3 evade every allowed ordinary leap and Royal adjacency.',
        stable_polynomial_domain='n>=5,degree8,n7=0,n6=-(14+|Aoffsets|+|Boffsets|); all-n finite positive-part formula retained.',
        scope='Fresh safe admission only, not root ongoing/WDL, full-history identity, Player/TT timing or learner equivalence. No safety relaxation or denominator substitution.',new_Player_queries=0,new_graph_or_solver_calls=0)


def main():
    p=argparse.ArgumentParser();p.add_argument('--plan',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    if a.output.exists():raise ValueError('NEW output required')
    a.output.mkdir(parents=True)
    plan=json.loads(a.plan.read_text(encoding='utf-8-sig'))
    try:
        reg,m=measure(plan,a.output);q=qualify(reg,m);write_json(a.output/'qualification.json',q)
        print(json.dumps(q))
    except Exception as exc:
        write_json(a.output/'failure.json',dict(type=type(exc).__name__,message=str(exc)));raise


if __name__=='__main__':main()
