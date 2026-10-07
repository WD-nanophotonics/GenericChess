"""Independent geometry and compiled metadata controls; no public moves/goals."""
from fractions import Fraction as F
from itertools import permutations
from generic_chess.rules.compiler import compile_semantic_ruleset
from generic_chess.rules.western_chess import build_western_chess_ruleset


def ray(s,d,b):
    dx,dy=d[0]-s[0],d[1]-s[1]
    if not (dx==0 or dy==0 or abs(dx)==abs(dy)) or s==d:
        return False
    steps=max(abs(dx),abs(dy));ux=(dx>0)-(dx<0);uy=(dy>0)-(dy<0)
    return all((s[0]+k*ux,s[1]+k*uy)!=b for k in range(1,steps+1))


def test_queen_two_step_obstruction_partition_independently():
    for n in (3,4,5,6):
        squares=[(x,y) for x in range(n) for y in range(n)]
        third=0
        for s,d,b in permutations(squares,3):
            if not (s[0]==d[0] or s[1]==d[1]) or ray(s,d,b):
                continue
            # Independent direct candidate check, not the odd-distance formula.
            found=any(q not in (s,d,b) and ray(s,q,b) and ray(q,d,b) for q in squares)
            length=abs(s[0]-d[0])+abs(s[1]-d[1])
            axis=s[0] if s[0]==d[0] else s[1]
            expected=length%2==1 and length>max(axis,n-1-axis)
            assert (not found)==expected
            third+=not found
        formula=sum(4*(n-k)*sum(max(x,n-1-x)<k for x in range(n))*(k-1)
                    for k in range(1,n,2))
        assert third==formula


def test_chess_same_population_counts_and_shared_discount_order():
    total=64*63*62
    lengths=[*range(1,8),8,*range(7,0,-1)]*2
    diag=sum(k*(k-1) for k in lengths)
    blocked=sum(k*(k-1)*(k-2)//3 for k in lengths)
    assert (diag,blocked)==(560,784)
    r3=64*2*7*6//3;r1=64*14*62-r3;r2=total-r1-r3
    q3=sum(4*(8-k)*sum(max(x,7-x)<k for x in range(8))*(k-1) for k in (1,3,5,7))
    q1=(64*14+diag)*62-r3-blocked;q2=total-q1-q3
    b1=diag*62-blocked;bzero=2*32*32*62+8*30;unknown=total-b1-bzero
    assert (r1,r2,r3)==(53760,194432,1792)
    assert (q1,q2,q3)==(87696,162048,240)
    assert (b1,bzero,unknown)==(33936,127216,88832)
    for i in range(1,100):
        g=F(i,100)
        r=(r1*g+r2*g**2+r3*g**3)/total
        q=(q1*g+q2*g**2+q3*g**3)/total
        upper=(b1*g+unknown*g**2)/total
        assert q-r==g*(1-g)*(33936+1552*g)/total>0
        assert r-upper>0


def test_bishop_opposite_and_endpoint_traps_are_disjoint():
    n=8;squares=[(x,y) for x in range(n) for y in range(n)]
    corners={(0,0):(1,1),(0,7):(1,6),(7,0):(6,1),(7,7):(6,6)}
    source={(s,d,b) for s,b in corners.items() for d in squares
            if d not in (s,b) and (sum(s)-sum(d))%2==0}
    target={(s,d,b) for d,b in corners.items() for s in squares
            if s not in (d,b) and (sum(s)-sum(d))%2==0}
    assert len(source)==len(target)==120 and not source&target
    assert all((sum(s)-sum(d))%2==0 for s,d,b in source|target)


def test_compiled_b_r_q_source_contract_has_no_hidden_promotion_or_guards():
    c=compile_semantic_ruleset(build_western_chess_ruleset())
    for tid in ('B','R','Q'):
        board=[]
        for p in c.ir.patterns:
            if tid not in p.type_ids:
                continue
            if all(c.ir.geometry[g].kind=='drop' for g in p.geometry_ids):
                assert not any(any(mask) for mask in c.support.drop_allowed[tid])
                continue
            board.append(p)
            assert p.name in (tid.lower()+'_quiet',tid.lower()+'_capture')
            assert p.promotion_mode=='none' and not p.guards and not p.slot_guards
            assert not p.square_zone_guards and not p.postconditions
            assert [i.kind for i in p.invariants]==['own_anchor_safe']
            assert all(g.kind=='ray' for g in (c.ir.geometry[g] for g in p.geometry_ids))
            assert [x.kind for x in p.path]==['path_clear']
            assert [x.kind for x in p.effects]==(['move'] if p.target.kind=='target_empty' else ['remove','move'])
            if p.target.kind=='target_enemy':
                assert p.effects[0].disposition=='remove_from_game'
        assert len(board)==2
