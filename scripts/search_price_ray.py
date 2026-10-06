"""Exact affine-line certificate for saved fixed finite material trees."""
from fractions import Fraction as F


def affine_line_certificate(vectors,weights):
    rows=list(vectors)
    if not rows or not weights:raise ValueError('nonempty vectors and parameter family')
    width=len(rows[0])
    if not width or any(len(v)!=width or any(type(x) is not int for x in v) for v in rows):raise ValueError('integer rectangular features')
    if any(len(w)!=width or any(type(x) is not int and not isinstance(x,F) for x in w) for w in weights):raise ValueError('exact rectangular parameters')
    c=tuple(rows[0]);d=next((tuple(b-a for a,b in zip(c,v)) for v in rows if tuple(v)!=c),None)
    if d is None:return dict(affine_line=True,constant=True,common=c,full_choice_invariant=True,reason='all leaf vectors equal')
    j=next(i for i,x in enumerate(d) if x);ts=[]
    for v in rows:
        t=F(v[j]-c[j],d[j])
        if any(F(b-a)!=t*x for a,b,x in zip(c,v,d)):
            return dict(affine_line=False,constant=False,full_choice_invariant=False,reason='noncollinear leaf contrasts; sensitivity still unproved')
        ts.append(t)
    projections=[sum(F(a)*b for a,b in zip(w,d)) for w in weights]
    signs=[(x>0)-(x<0) for x in projections]
    same=bool(signs[0]) and len(set(signs))==1
    return dict(affine_line=True,constant=False,common=c,direction=d,leaf_parameters=ts,
      projections=projections,projection_signs=signs,full_choice_invariant=same,
      reason='common strict projection sign; fixed min/max tree premise required' if same else 'zero or changing projection sign; no invariance certificate')
