"""Exact small fixed-policy TD identities; no engine, training or sampling.

These rational arithmetic controls qualify the conditional mathematical spec,
not the actual nonlinear learner or any game. No parameter is fitted/updated.
"""
from fractions import Fraction as F
from itertools import product


def mm(a, b):
    return tuple(tuple(sum(x*y for x,y in zip(row,col)) for col in zip(*b)) for row in a)


def transpose(a):
    return tuple(zip(*a))


def add(a, b, sign=1):
    return tuple(tuple(x+sign*y for x,y in zip(row,col)) for row,col in zip(a,b))


def scale(a, c):
    return tuple(tuple(c*x for x in row) for row in a)


def eye(n):
    return tuple(tuple(F(i==j) for j in range(n)) for i in range(n))


def finite_resolvent(k, lam):
    # Only the declared three-state acyclic toy kernels are admitted here.
    n=len(k); power=eye(n); result=power
    for _ in range(1,n):
        power=mm(power,scale(k,lam)); result=add(result,power)
    assert mm(power,scale(k,lam)) == scale(eye(n),0)
    assert mm(add(eye(n),scale(k,lam),-1),result)==eye(n)
    return result


def paths(k, root, terminals):
    """Every possible toy chain path including which terminal sign occurs."""
    # Enumerate the declared terminal distribution exactly, without sampling.
    # This is not a game or action search.
    def walk(state, prefix, mass):
        row=k[state]; terminal=1-sum(row)
        if terminal:
            for z,p in terminals[state]: yield prefix+(state,),z,mass*terminal*p
        for child,p in enumerate(row):
            if p: yield from walk(child,prefix+(state,),mass*p)
    for state,p in enumerate(root):
        if p: yield from walk(state,(),p)


def path_increment(features, values, sequence, terminal, lam):
    elig=[F(0)]*len(features[0]); total=elig[:]
    for index,state in enumerate(sequence):
        elig=[lam*e+x for e,x in zip(elig,features[state])]
        target=values[sequence[index+1]] if index+1<len(sequence) else terminal
        for j,e in enumerate(elig): total[j]+=(target-values[state])*e
    return tuple(total)


def verify_case(k, root, phi, theta, offset, lam, terminals):
    n=len(k); one=tuple((F(1),) for _ in range(n)); zero=scale(eye(n),0)
    rootrow=(tuple(root),)
    d=mm(rootrow,finite_resolvent(k,F(1)))[0]
    assert all(x>0 for x in d)
    diag=tuple(tuple(d[i] if i==j else F(0) for j in range(n)) for i in range(n))
    resolvent=finite_resolvent(k,lam)
    kl=scale(mm(k,resolvent),1-lam)
    start=mm(rootrow,resolvent)
    assert mm((d,),add(eye(n),kl,-1))==start
    assert all(x>=0 for row in kl for x in row)
    assert all(x[0]<=1 for x in mm(kl,one))
    al=mm(mm(mm(transpose(phi),diag),resolvent),mm(add(eye(n),k,-1),phi))
    off=tuple((v,) for v in offset)
    rewards=tuple(((1-sum(row))*sum(z*p for z,p in terminal),)
                  for row,terminal in zip(k,terminals))
    bl=mm(mm(mm(transpose(phi),diag),resolvent),add(rewards,add(mm(k,off),off,-1)))
    expected=add(bl,mm(al,tuple((v,) for v in theta)),-1)
    values=tuple(a+sum(x*w for x,w in zip(row,theta)) for a,row in zip(offset,phi))
    actual=[F(0)]*len(theta); mass=F(0); visit=[F(0)]*n
    for sequence,z,p in paths(k,root,terminals):
        mass+=p
        inc=path_increment(phi,values,sequence,z,lam)
        actual=[v+p*x for v,x in zip(actual,inc)]
        for state in sequence: visit[state]+=p
    assert mass==1 and tuple(visit)==d
    assert tuple(actual)==tuple(v[0] for v in expected)
    # An independent scalar expansion checks every term in the energy identity.
    for y in product(map(F,(-2,-1,0,1,2)),repeat=n):
        ky=mm(kl,tuple((v,) for v in y)); ksum=mm(kl,one)
        lhs=2*sum(d[i]*y[i]*(y[i]-ky[i][0]) for i in range(n))
        rhs=sum(d[i]*kl[i][j]*(y[i]-y[j])**2 for i in range(n) for j in range(n))
        rhs+=sum(start[0][i]*y[i]**2+d[i]*(1-ksum[i][0])*y[i]**2 for i in range(n))
        assert lhs==rhs
        assert lhs>0 if any(y) else lhs==0
    if lam==1:
        assert kl==zero
        assert al==mm(mm(transpose(phi),diag),phi)
    return {'paths':sum(1 for _ in paths(k,root,terminals)), 'occupancy':tuple(map(str,d)),
            'lambda':str(lam),'A':tuple(tuple(map(str,row)) for row in al)}


def verify_inventory_boxes():
    cases=0
    for n0 in product(range(3),repeat=2):
      for n1 in product(range(3),repeat=2):
       for dw in product((F(-2),F(-1,2),F(0),F(1,2),F(2)),repeat=2):
        for c in (F(-3),F(0),F(3)):
            lo=c+sum(min(-b*d,a*d) for a,b,d in zip(n0,n1,dw))
            hi=c+sum(max(-b*d,a*d) for a,b,d in zip(n0,n1,dw))
            values=[c+sum(d*x for d,x in zip(dw,phi)) for phi in
                    product(*(range(-b,a+1) for a,b in zip(n0,n1)))]
            assert min(values)==lo and max(values)==hi
            assert max(map(abs,values))==max(abs(lo),abs(hi))
            cases+=1
    return dict(boxes=cases,exact_endpoint_checks='PASS',initial_hand_offset_required=True)


def main():
    phi=((F(1),F(0)),(F(1),F(1)),(F(0),F(2)))
    theta=(F(2,3),F(-1,4)); offset=(F(1,5),F(-1,7),F(0))
    cases=[]
    for p01,p02,p12 in product((F(0),F(1,4),F(1,2)),repeat=3):
        if p01+p02>1: continue
        k=((F(0),p01,p02),(F(0),F(0),p12),(F(0),F(0),F(0)))
        for root in ((F(1,2),F(1,3),F(1,6)),(F(1),F(0),F(0))):
            # Cover sparse start support with all states still reachable.
            if root[1]==0 and (p01==0 or (p02==0 and p12==0)): continue
            for terminals in (
                (((F(-1),F(1,2)),(F(1),F(1,2))),)*3,
                (((F(1),F(1)),),((F(-1),F(1)),),((F(-1),F(1,3)),(F(1),F(2,3))))):
                for lam in (F(0),F(1,2),F(19,20),F(1)):
                    cases.append(verify_case(k,root,phi,theta,offset,lam,terminals))
    # Wrong arbitrary state weights cannot inherit occupancy stability.
    # Two-state chain 0->1->terminal, feature(1,2), payoffmean0.
    # Its on-trajectory occupancy is(1,1), so A=3>0. Weight(10,1)
    # gives A=-6; implied initial mass(10,-9) is not a probability law.
    assert F(1)*(1-2)+F(1)*2*2==3
    assert F(10)*(1-2)+F(1)*2*2==-6
    return {'kind':'exact abstract Markov algebra, not learning/game evidence',
            'cases':len(cases),'energy_vectors':len(cases)*125,
            'path_formula_and_occupancy_verified':True,'sample_cases':[cases[0],cases[-1]],
            'inventory_bound':verify_inventory_boxes(),
            'new_engine_calls':0,'training_updates':0}


if __name__=='__main__':
    import json
    print(json.dumps(main(),indent=2))
