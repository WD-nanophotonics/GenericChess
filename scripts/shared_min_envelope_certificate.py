"""Exact lower-bound certificates; no solver, samples, states or goal labels."""
from fractions import Fraction as F

def rational(x):
    if type(x) is not int and not isinstance(x,F):
        raise ValueError('exact rational required')
    return F(x)

def affine_box_min(row,box):
    if len(row)!=len(box)+1:raise ValueError('affine dimension mismatch')
    result=rational(row[0])
    for coefficient,pair in zip(row[1:],box):
        if len(pair)!=2:raise ValueError('box pair required')
        lo,hi=map(rational,pair);coefficient=rational(coefficient)
        if lo>hi:raise ValueError('reversed box')
        result+=coefficient*(lo if coefficient>=0 else hi)
    return result

def min_envelope_margin_lower(first,second,box,combinations):
    """Certify min(first)-min(second) for the SAME box parameter vector.

    Each first-row proof is a distribution over second rows. The best such
    proof may be found by LP, but this interface only verifies given proofs.
    Returned lower bounds may be loose; no upper bound or completeness claim.
    Scores are owner/root-oriented by the caller BEFORE constructing rows.
    """
    if not first or not second or len(first)>64 or len(second)>64 or len(box)>7:
        raise ValueError('nonempty bounded row tables required')
    if len(first)*len(second)>4096 or len(combinations)!=len(first):
        raise ValueError('bounded one proof per candidate row required')
    first=[tuple(map(rational,row)) for row in first]
    second=[tuple(map(rational,row)) for row in second]
    for row in first+second:affine_box_min(row,box)
    bounds=[]
    for row,proof in zip(first,combinations):
        weights=tuple(map(rational,proof))
        if len(weights)!=len(second) or any(w<0 for w in weights) or sum(weights)!=1:
            raise ValueError('nonnegative complete convex combination required')
        combined=tuple(row[k]-sum((w*b[k] for w,b in zip(weights,second)),F(0)) for k in range(len(row)))
        bounds.append(affine_box_min(combined,box))
    return {'lower':min(bounds),'row_bounds':tuple(bounds),
            'scope':'complete finite min envelopes, fixed shared coefficients; lower bound only'}
