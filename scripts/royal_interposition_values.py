"""Exact values of the declared passive-source royal law, not game values."""
from fractions import Fraction as F


def moment(law,t):
    if type(t) is not int or t<0:raise ValueError('nonnegative integer time')
    if law=='geometric_half':return F(1,2**t)
    if law=='linear_mixture':return F(2,(t+1)*(t+2))
    raise ValueError('unknown shared duration law')


def population(law):
    rows=[]
    for r in range(8):
        total=sum((moment(law,9-j) for j in range(r+1,8)),F(0))
        n=7-r
        rows.append(dict(rank=r,legal_count=n,legal_resampling=total/n if n else F(0),
                         fixed_attempt=total/63,removed_fraction=F(63-n,63)))
    legal=sum((x['legal_resampling'] for x in rows),F(0))/8
    fixed=sum((x['fixed_attempt'] for x in rows),F(0))/8
    return dict(rows=rows,legal=legal,fixed=fixed,reweighting=legal-fixed,
                empty_mass=F(1,8),conditional_nonempty=legal*F(8,7))
