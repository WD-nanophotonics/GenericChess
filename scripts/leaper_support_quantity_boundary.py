"""Quantity and bounded-range boundary for admission counts, not WDL."""
from pathlib import Path
from itertools import permutations
from collections import Counter
from datetime import datetime,timezone,timedelta
import json,time,argparse
from scripts import leaper_design as L
from scripts.leaper_safe_support import orbit
from scripts.leaper_delayed_capture_witness import snapshot
from generic_chess.core.movement import RayAtom
from tools.local_agent.common import write_json


def quantity_weights():
    weights=Counter()
    for u,a1,a2,v,b in permutations(range(9),5):
        if max(abs(u%3-v%3),abs(u//3-v//3))<=1:continue
        if orbit(u%3-b%3,u//3-b//3)&5:continue
        j=orbit(v%3-a1%3,v//3-a1//3)|orbit(v%3-a2%3,v//3-a2//3)
        weights[j]+=1
    return dict(sorted(weights.items()))


def quantity_literal(mask):
    total=0
    for u,a1,a2,v,b in permutations(range(9),5):
        if max(abs(u%3-v%3),abs(u//3-v//3))<=1:continue
        if orbit(u%3-b%3,u//3-b//3)&5:continue
        if any(orbit(v%3-a%3,v//3-a//3)&mask for a in(a1,a2)):continue
        total+=1
    return total


def mobius(counts):
    c=list(counts)
    for bit in(1,2,4,8,16):
        for s in range(32):
            if s&bit:c[s]-=c[s^bit]
    return c


def pair_attack(dx,dy,ray):
    a,b=sorted((abs(dx),abs(dy)))
    return a>0 and b==2*a if ray else(a,b)==(1,2)


def pair_count_literal(n,ray):
    return sum(not pair_attack(v%n-u%n,v//n-u//n,ray)for u,v in permutations(range(n*n),2))


def pair_formula(n,ray):
    if not ray:return n**4-9*n*n+24*n-16
    return (3*n**4-5*n**3+9*n*n-(4 if n%2==0 else 7)*n)//3


def royal_rule(n,ray,cells):
    board=[None]*(n*n)
    for p,owner in zip(cells,(0,1)):board[p]=L.Piece(owner,'K','K')
    atoms=tuple(RayAtom(d)if ray else L.LeapAtom(d)for d in L.offsets(8))
    return L.RuleSet(board_size=n,piece_types=(L.PieceType('K','K',atoms,is_anchor=True),),
        initial_position=tuple(tuple(board[n*y:n*y+n])for y in range(n)),
        drop_allowed={},max_ply=6,repetition_limit=2,stalemate_result='draw',capture_disposition='remove_from_game')


def measure(plan,output):
    start=datetime.now(timezone.utc);tick=time.perf_counter()
    deadline=datetime.fromisoformat(plan['started_at'])+timedelta(seconds=plan['cost']['absolute_analysis_validation_cap_seconds'])
    def gate():
        if datetime.now(timezone.utc)>=deadline:raise RuntimeError('original general-support deadline')
    gate();write_json(output/'registration.json',dict(plan=plan,source_sha256=L.sha(Path(__file__)),deadline=deadline.isoformat()))
    weights=quantity_weights();counts=[sum(w for j,w in weights.items()if not(j&s))for s in range(32)]
    literal=[quantity_literal(s)for s in range(32)];coeff=mobius(counts)
    quantity=dict(n=3,WhiteAs=2,B_mask=5,weights=weights,labeled_counts=counts,literal_labeled_counts=literal,mobius_coefficients=coeff,unlabeled_counts=[x//2 for x in counts],mixed_W_N_at_A22=counts[31]-counts[23]-counts[30]+counts[22])
    write_json(output/'quantity.json',quantity)
    boundary=[]
    for n in plan['fixed_counts']['boundary']['n_values']:
        gate()
        for ray in(False,True):
            boundary.append(dict(n=n,ray=ray,literal=pair_count_literal(n,ray),formula=pair_formula(n,ray)))
    core=[]
    for cells in plan['fixed_counts']['boundary']['Core_only_n5_selected_safe_and_unsafe_placements']:
        for ray in(False,True):
            gate();r=royal_rule(5,ray,cells);item=dict(n=5,ray=ray,cells=cells,rule=L.ruleset_to_dict(r,include_metadata=True))
            write_json(output/'latest-input.json',item)
            try:item.update(admitted=True,root=snapshot(L.GameSession(L.compile_rule(r))))
            except Exception as exc:item.update(admitted=False,error_type=type(exc).__name__,error=str(exc))
            core.append(item);write_json(output/'latest-Core-control.json',item)
    gate();m=dict(started_at=start.isoformat(),ended_at=datetime.now(timezone.utc).isoformat(),producer_seconds_before_final_write=time.perf_counter()-tick,quantity=quantity,boundary_counts=boundary,Core_controls=core,new_Player_queries=0,new_graph_or_solver_calls=0)
    write_json(output/'measurements.json',m);return m


def qualify(m):
    q=m['quantity'];assert (q['n'],q['WhiteAs'],q['B_mask'])==(3,2,5), 'quantity scope labels mismatch'
    weights={int(k):v for k,v in q['weights'].items()}
    assert weights==quantity_weights()
    assert all(j.bit_count()<=2 and w>0 and w%2==0 for j,w in weights.items())
    counts=[sum(w for j,w in weights.items()if not(j&s))for s in range(32)]
    assert counts==q['labeled_counts']==q['literal_labeled_counts']
    assert q['unlabeled_counts']==[x//2 for x in counts]
    coeff=mobius(counts);assert coeff==q['mobius_coefficients']
    assert all(c==(-1)**s.bit_count()*sum(w for j,w in weights.items()if(j&s)==s)for s,c in enumerate(coeff))
    assert all(c==0 for s,c in enumerate(coeff)if s.bit_count()>2)
    assert q['mixed_W_N_at_A22']==counts[31]-counts[23]-counts[30]+counts[22]>0
    assert [(r['n'],r['ray'])for r in m['boundary_counts']]==[(n,ray)for n in range(2,10)for ray in(False,True)]
    for r in m['boundary_counts']:assert r['literal']==r['formula']==pair_formula(r['n'],r['ray'])
    controls=m['Core_controls'];assert len(controls)==4
    assert [(r['n'],r['cells'],r['ray'])for r in controls]==[(5,c,ray)for c in([0,12],[0,14])for ray in(False,True)], 'complete range control coverage required'
    for row in controls:
        r=royal_rule(5,row['ray'],row['cells']);assert row['rule']==L.ruleset_to_dict(r,include_metadata=True)
        expected=not row['ray']or row['cells']==[0,12]
        assert row['admitted']==expected
        if expected:assert row['root']==snapshot(L.GameSession(L.compile_rule(r)))and row['root']['check']==[False,False]
        else:assert 'INITIAL_ANCHOR_ATTACKED'in row['error']
    return dict(status='PASS',quantity_mixed_W_N_labeled=q['mixed_W_N_at_A22'],quantity_mixed_W_N_unlabeled=q['mixed_W_N_at_A22']//2,quantity_degree=2,quantity_third_and_higher_coefficients_zero=True,
        n5_ordered_safe_pairs=dict(Knight=pair_formula(5,False),Nightrider=pair_formula(5,True)),
        boundary='UnboundedKnight-ray orderedpair counts have distinct even/odd constituents, hence not one eventual polynomial. No claim the bounded-offset proof covers rays.',
        scope='Fresh initializer-family admission only. Two-anchorKnight/Ray control is outside the currentK8fouractorlab and only tests the range boundary; no outcome, learner, graph or default change. Quantity labels dividedby2! foridenticalAs, not assumed additive value.',new_Player_queries=0,new_graph_or_solver_calls=0)


def main():
    p=argparse.ArgumentParser();p.add_argument('--plan',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    if a.output.exists():raise ValueError('NEW output required')
    a.output.mkdir(parents=True)
    try:
        m=measure(json.loads(a.plan.read_text(encoding='utf-8-sig')),a.output);q=qualify(m);write_json(a.output/'qualification.json',q);print(json.dumps(q))
    except Exception as exc:write_json(a.output/'failure.json',dict(type=type(exc).__name__,message=str(exc)));raise


if __name__=='__main__':main()
