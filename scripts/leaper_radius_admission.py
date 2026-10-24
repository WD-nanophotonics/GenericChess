"""Sharp radius-to-safe-input bound; a new family, no outcome panel."""
from pathlib import Path
from itertools import product,permutations
from collections import Counter
from datetime import datetime,timezone,timedelta
import argparse,json,time
from scripts import leaper_design as L
from scripts.leaper_safe_support import component_spans,polynomial,count_from_terms,evaluate_polynomial
from scripts.leaper_delayed_capture_witness import snapshot
from tools.local_agent.common import write_json


def offsets(r):return tuple((x,y)for x in range(-r,r+1)for y in range(-r,r+1)if x or y)


def terms_for_radius(r):
    constraints=[(0,1,((0,0),)),(0,2,((0,0),*L.offsets(3))),
      (0,3,((0,0),*L.offsets(5))),(1,2,((0,0),*offsets(r))),
      (1,3,((0,0),)),(2,3,((0,0),))]
    terms=Counter()
    for choices in product(*[(None,*o)for _,_,o in constraints]):
        selected=[(u,v,d)for(u,v,_),d in zip(constraints,choices)if d is not None]
        spans=component_spans(selected)
        if spans is not None:terms[spans]+=(-1)**len(selected)
    return [dict(spans=[list(z)for z in k],coefficient=v)for k,v in sorted(terms.items())if v]


def direct(n,r):
    board=set(range(n*n));total=0
    for u,v in permutations(range(n*n),2):
        if max(abs(u%n-v%n),abs(u//n-v//n))<=1:continue
        aa={x for x in board-{u,v}if max(abs(x%n-v%n),abs(x//n-v//n))>r}
        bb={x for x in board-{u,v}if (u%n-x%n,u//n-x//n)not in L.offsets(5)}
        total+=len(aa)*len(bb)-len(aa&bb)
    return total


def rule(n,r):
    cells=[0,n*n-1,n*(n-1),n-1];board=[None]*(n*n)
    for sq,owner,tid in zip(cells,(0,0,1,1),('K','A','K','B')):board[sq]=L.Piece(owner,tid,tid)
    types=tuple(L.PieceType(t,t,tuple(L.LeapAtom(d)for d in o),is_anchor=(t=='K'))for t,o in(('K',L.offsets(3)),('A',offsets(r)),('B',L.offsets(5))))
    return L.RuleSet(board_size=n,piece_types=types,initial_position=tuple(tuple(board[n*y:n*y+n])for y in range(n)),drop_allowed={t:((False,)*(n*n),)*2 for t in('A','B')},max_ply=6,repetition_limit=2,stalemate_result='draw',capture_disposition='remove_from_game')


def measure(plan,output):
    start=datetime.now(timezone.utc);tick=time.perf_counter();deadline=datetime.fromisoformat(plan['started_at'])+timedelta(seconds=plan['resources']['absolute_analysis_validation_cap_seconds'])
    def gate():
        if datetime.now(timezone.utc)>=deadline:raise RuntimeError('original radius-family deadline')
    gate();inputs={str((r,n)):L.ruleset_to_dict(rule(n,r),include_metadata=True)for r in(2,3)for n in(r+1,r+2)}
    reg=dict(plan=plan,inputs=inputs,source_sha256=L.sha(Path(__file__)),deadline=deadline.isoformat());write_json(output/'registration.json',reg)
    rows=[];controls=[]
    for r in(2,3):
        gate();terms=terms_for_radius(r);p=polynomial(terms);counts=[]
        for n in(r+1,r+2,r+3):
            gate();counts.append(dict(n=n,positive_parts=count_from_terms(terms,n),direct=direct(n,r),polynomial=evaluate_polynomial(p,n)))
            write_json(output/'latest-count.json',counts[-1])
        rows.append(dict(radius=r,offset_cardinality=len(offsets(r)),terms=terms,polynomial=p,counts=counts))
        for n in(r+1,r+2):
            gate();rr=rule(n,r);item=dict(radius=r,n=n,rule=L.ruleset_to_dict(rr,include_metadata=True))
            try:item.update(admitted=True,root=snapshot(L.GameSession(L.compile_rule(rr))))
            except Exception as exc:item.update(admitted=False,error_type=type(exc).__name__,error=str(exc))
            controls.append(item);write_json(output/'latest-control.json',item)
    gate();m=dict(started_at=start.isoformat(),ended_at=datetime.now(timezone.utc).isoformat(),producer_seconds_before_final_write=time.perf_counter()-tick,rows=rows,controls=controls,planned_Core_initializations=4,new_Player_queries=0,new_graph_or_solver_calls=0)
    write_json(output/'measurements.json',m);return reg,m


def qualify(reg,m):
    assert [x['radius']for x in m['rows']]==[2,3]
    for row in m['rows']:
        r=row['radius'];assert row['offset_cardinality']==(2*r+1)**2-1
        terms=terms_for_radius(r);assert row['terms']==terms
        p=polynomial(terms);assert p==row['polynomial']
        assert p['8']==1 and p.get('7',0)==0
        assert p['6']==-(21+(2*r+1)**2)and p['5']==24+2*(2*r+1)*r*(r+1)
        assert max(max(z)for t in terms for z in t['spans'])<=r+3
        assert [x['n']for x in row['counts']]==[r+1,r+2,r+3]
        for c in row['counts']:
            n=c['n'];assert c['positive_parts']==c['direct']==count_from_terms(terms,n)==direct(n,r)
            assert c['polynomial']==evaluate_polynomial(p,n)
            if n==r+1:assert c['direct']==0
            else:assert c['direct']>0
            if n>=r+3:assert c['polynomial']==c['direct']
    assert [(x['radius'],x['n'])for x in m['controls']]==[(r,n)for r in(2,3)for n in(r+1,r+2)]
    for x in m['controls']:
        r,n=x['radius'],x['n'];rr=rule(n,r)
        assert x['rule']==L.ruleset_to_dict(rr,include_metadata=True)==reg['inputs'][str((r,n))]
        assert x['admitted']==(n==r+2)
        if x['admitted']:assert x['root']==snapshot(L.GameSession(L.compile_rule(rr)))and x['root']['check']==[False,False]
        else:assert 'INITIAL_ANCHOR_ATTACKED'in x['error']
    assert m['planned_Core_initializations']==4 and m['ended_at']<=reg['deadline']
    return dict(status='PASS',radii=[2,3],admission_thresholds=[4,5],leading_n6=[row['polynomial']['6']for row in m['rows']],leading_n5=[row['polynomial']['5']for row in m['rows']],
        theorem='For K8+oneA/B and fixed finite union-of-offsets maxnormr, n>=max(3,r+2)admits commonfourcornerinitializer. SaturatedA demonstrates sharpness forr>=2,B5. Positive-support monotonic undercoordinateboardembedding; not WDL monotonic.',
        scope='A new explicitlyradius-indexed initializer family, not executionofoneunchangedRuleSetacrossboards or recoveryofundefinedn3matched-effect. Finiteoffset only; rays/effects/history and search complexity not inferred.',planned_Core_initializations=4,new_Player_queries=0,new_graph_or_solver_calls=0)


def main():
    p=argparse.ArgumentParser();p.add_argument('--plan',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    if a.output.exists():raise ValueError('NEW output required')
    a.output.mkdir(parents=True)
    try:
        reg,m=measure(json.loads(a.plan.read_text(encoding='utf-8-sig')),a.output);q=qualify(reg,m);write_json(a.output/'qualification.json',q);print(json.dumps(q))
    except Exception as exc:write_json(a.output/'failure.json',dict(type=type(exc).__name__,message=str(exc)));raise


if __name__=='__main__':main()
