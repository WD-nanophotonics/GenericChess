"""Three shared unit-box variables; supplied lower-bound certificates only."""
from fractions import Fraction as F

def exact_row(row):
    if len(row)!=8 or any(type(x) is not int and not isinstance(x,F) for x in row):
        raise ValueError('eight exact rational monomial coefficients required')
    return tuple(map(F,row))

def cube_min(row,checkpoint=None):
    row=exact_row(row);values=[]
    for vertex in range(8):
        if checkpoint is not None:checkpoint()
        # At a unit-cube vertex only monomials contained in that vertex survive.
        values.append(sum((c for mask,c in enumerate(row) if mask&vertex==mask),F(0)))
    return min(values)

def min_envelope_lower(first,second,combinations,checkpoint=None):
    if not first or not second or len(first)>64 or len(second)>64 or len(first)*len(second)>4096 or len(combinations)!=len(first):
        raise ValueError('bounded complete tables and one proof per first row required')
    first=list(map(exact_row,first));second=list(map(exact_row,second));bounds=[]
    for row,proof in zip(first,combinations):
        if len(proof)!=len(second) or any(type(x) is not int and not isinstance(x,F) for x in proof):
            raise ValueError('complete exact convex combination required')
        weights=tuple(map(F,proof))
        if any(w<0 for w in weights) or sum(weights)!=1:raise ValueError('nonnegative unit-mass proof required')
        polynomial=tuple(row[k]-sum((w*b[k] for w,b in zip(weights,second)),F(0)) for k in range(8))
        bounds.append(cube_min(polynomial,checkpoint))
    return dict(lower=min(bounds),row_bounds=bounds,
                scope='shared3D unit box, complete finite min envelopes; supplied polynomial lower certificate only')
