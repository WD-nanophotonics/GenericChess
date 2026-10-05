"""Small rational dual witnesses, not optimized prices or gameplay labels."""
from fractions import Fraction as F


def box_lower(coefficients,boxes):
    if set(coefficients)-set(boxes):raise ValueError('unsupported coefficient coordinate')
    if any(F(lo)>F(hi) for lo,hi in boxes.values()):raise ValueError('inverted box')
    return sum((F(c)*F(boxes[t][0 if F(c)>=0 else 1]) for t,c in coefficients.items()),F(0))


def certified_lower(coefficients,boxes,constraints,multipliers):
    """constraints is a declared map ID -> (normal vector, proved lower).

    The caller owns each proof and shared-law scope. Empty/missing proof IDs
    cannot silently become constraints; no source quality is certified here.
    """
    residual={t:F(c) for t,c in coefficients.items()};constant=F(0)
    for key,multiplier in multipliers.items():
        if key not in constraints:raise ValueError('missing constraint proof')
        lam=F(multiplier)
        if lam<0:raise ValueError('negative dual multiplier')
        normal,lower=constraints[key]
        if set(normal)-set(boxes):raise ValueError('unsupported constraint coordinate')
        constant+=lam*F(lower)
        for t,a in normal.items():residual[t]=residual.get(t,F(0))-lam*F(a)
    return max(box_lower(coefficients,boxes),constant+box_lower(residual,boxes))
