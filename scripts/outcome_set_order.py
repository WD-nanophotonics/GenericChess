"""Conservative coordinatewise certificates for complete outcome sets."""


def set_order(candidate, baseline):
    """Prove min_X u >= min_Y u for every common isotone u, or return unknown.

    Every x needs a baseline y <= x. Different x may use different y; this is
    not a coupling, average outcome or componentwise-minimum construction.
    Caller owns completeness, common perspective and terminal/task semantics.
    """
    if not candidate or not baseline:
        raise ValueError('two complete nonempty outcome sets required')
    width = len(next(iter(candidate.values())))
    rows = list(candidate.values())+list(baseline.values())
    if not width or any(len(v)!=width or any(type(x) is not int for x in v) for v in rows):
        raise ValueError('rectangular exact integer vectors required')
    witnesses = {}
    unmatched = []
    for action, x in candidate.items():
        eligible = sorted(k for k,y in baseline.items() if all(a>=b for a,b in zip(x,y)))
        if eligible:witnesses[action] = eligible[0]
        else:unmatched.append(action)
    return dict(weak_order_proved=not unmatched, witnesses=witnesses,
                unmatched=sorted(unmatched), strict_improvement_proved=False)
