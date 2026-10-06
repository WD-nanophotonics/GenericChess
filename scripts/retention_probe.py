"""Exact adversarial retention with an explicit probe information structure."""
from fractions import Fraction as F


def probe_values(rows):
    if not rows:
        raise ValueError('complete nonempty response set required')
    width = len(next(iter(rows.values())))
    if not width or any(len(v) != width or any(type(x) is not int or x not in (0,1) for x in v)
                        for v in rows.values()):
        raise ValueError('rectangular binary physical retention required')
    marginal = tuple(min(v[j] for v in rows.values()) for j in range(width))
    hidden = min(F(sum(v),width) for v in rows.values())
    revealed = F(sum(marginal),width)
    witnesses = [sorted(k for k,v in rows.items() if v[j] == marginal[j]) for j in range(width)]
    common = sorted(set.intersection(*(set(w) for w in witnesses)))
    return dict(hidden=hidden, revealed=revealed, marginal_minimum=marginal,
                marginal_witnesses=witnesses, common_witnesses=common,
                hidden_witnesses=sorted(k for k,v in rows.items() if F(sum(v),width)==hidden),
                marginal_vector_is_actual=bool(common))
