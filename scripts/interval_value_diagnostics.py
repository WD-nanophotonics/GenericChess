"""Pure arithmetic diagnostics for already-qualified fixed-seat WDL bounds.

No truth admission, Core/search, optimizer, model update or training target.
Caller must bind complete rule/history identity and declare prediction semantics.
"""
from fractions import Fraction
from math import isfinite, nextafter, inf
from numbers import Real

WDL = (-1, 0, 1)


def _number(value, name):
    if isinstance(value, bool) or not isinstance(value, Real) or not isfinite(value):
        raise ValueError(name + " must be finite real, not bool")
    return float(value)


def _prediction(value):
    value = _number(value, "prediction")
    if not -1 <= value <= 1:
        raise ValueError("prediction must be a declared bounded value, not a raw search score")
    return value


def _bounds(bounds):
    if not isinstance(bounds, (tuple, list)) or len(bounds) != 2:
        raise ValueError("two ordered WDL bounds required")
    lo, hi = (_number(x, "bound") for x in bounds)
    if lo not in WDL or hi not in WDL or lo > hi:
        raise ValueError("bounds must be ordered deterministic WDL endpoints")
    return lo, hi



def _down(exact):
    value = float(exact)
    return nextafter(value, -inf) if Fraction(value) > exact else value


def _up(exact):
    value = float(exact)
    return nextafter(value, inf) if Fraction(value) < exact else value


def _verdict(lower, upper):
    return ("A_STRICTLY_LOWER_SCALAR_ERROR" if upper < 0 else
            "B_STRICTLY_LOWER_SCALAR_ERROR" if lower > 0 else
            "EQUAL_SCALAR_ERROR" if lower == upper == 0 else
            "UNRESOLVED_SCALAR_ERROR_ORDER")


def actor_view(prediction, fixed_seat0_bounds, actor):
    """Change BOTH scalar and endpoints, without interpreting child side-to-move."""
    p = _prediction(prediction)
    lo, hi = _bounds(fixed_seat0_bounds)
    if type(actor) is not int or actor not in (0, 1):
        raise ValueError("actor must be explicit seat 0 or 1")
    return (p, (lo, hi)) if actor == 0 else (-p, (-hi, -lo))


def loss_envelope(prediction, bounds):
    """Outer risk bounds, NOT fitted labels or confidence intervals.

    WDL truth is discrete. Continuous distance is only an optimistic relaxation;
    unlike discrete minimum error it supplies no constraint inside UNKNOWN.
    Derivative bounds describe possible point-target derivatives, not TDLeaf.
    """
    p = _prediction(prediction)
    lo, hi = _bounds(bounds)
    feasible = tuple(v for v in WDL if lo <= v <= hi)
    p, lo, hi = Fraction(p), Fraction(lo), Fraction(hi)
    nearest_continuous = min(hi, max(lo, p))
    residual = p - nearest_continuous
    return {
        "feasible_WDL": feasible,
        "continuous_relaxation_lower": _down(residual ** 2),
        "deterministic_WDL_lower": _down(min((p - v) ** 2 for v in feasible)),
        "squared_error_upper": _up(max((p - lo) ** 2, (p - hi) ** 2)),
        "continuous_constraint_derivative": float(2 * residual),
        "point_target_derivative_bounds": (_down(2 * (p - hi)), _up(2 * (p - lo))),
        "numeric_scope": "Exact binary-input rational arithmetic; reported scalar bounds rounded outward",
        "meaning": "Conditional scalar-error diagnostics only; no selected truth or training target",
    }


def paired_loss_difference(prediction_a, prediction_b, bounds):
    """Bounds on error(A)-error(B) at the SAME unknown state value.

    The squared target cancels. Subtracting two independent risk intervals
    would lose this shared-truth dependence and can miss a provable difference.
    """
    a, b = _prediction(prediction_a), _prediction(prediction_b)
    lo, hi = _bounds(bounds)
    a, b, lo, hi = map(Fraction, (a, b, lo, hi))
    def difference(v):
        return (a - b) * (a + b - 2 * v)
    values = (difference(lo), difference(hi))
    lower, upper = min(values), max(values)
    return {"lower": _down(lower), "upper": _up(upper),
            "exact_lower": str(lower), "exact_upper": str(upper),
            "verdict": _verdict(lower, upper),
            "numeric_scope": "Verdict uses exact rational binary-input endpoints; displayed bounds round outward",
            "meaning": "Same-context scalar error, not policy quality or search accuracy"}


def weighted_outer_summary(rows):
    """Aggregate predeclared nonnegative weights; no independence assumption.

    Each row is (weight, predictionA, predictionB, qualifiedWDLbounds).
    These remain outer bounds when values are coupled by a common game tree.
    They are not a claim that all endpoint completions are jointly realizable.
    """
    rows = list(rows)
    if not rows:
        raise ValueError("nonempty explicit-weight rows required")
    total = Fraction(0)
    sums = dict.fromkeys(("a_lower", "a_upper", "b_lower", "b_upper",
                          "paired_lower", "paired_upper"), Fraction(0))
    for weight, a, b, bounds in rows:
        weight = _number(weight, "weight")
        if weight < 0:
            raise ValueError("negative weight")
        av, bv = loss_envelope(a, bounds), loss_envelope(b, bounds)
        diff = paired_loss_difference(a, b, bounds)
        weight = Fraction(weight)
        total += weight
        for name, value in (("a_lower", av["deterministic_WDL_lower"]),
                            ("a_upper", av["squared_error_upper"]),
                            ("b_lower", bv["deterministic_WDL_lower"]),
                            ("b_upper", bv["squared_error_upper"]),
                            ("paired_lower", Fraction(diff["exact_lower"])),
                            ("paired_upper", Fraction(diff["exact_upper"]))):
            sums[name] += weight * Fraction(value)
    try:
        total_float = float(total)
    except OverflowError:
        raise ValueError("finite total weight required") from None
    if total <= 0 or not isfinite(total_float):
        raise ValueError("positive finite weight sum required")
    return {"total_weight": total_float,
            **{key: (_down if key.endswith('lower') else _up)(value / total)
               for key, value in sums.items()},
            "paired_verdict": _verdict(sums['paired_lower'], sums['paired_upper']),
            "numeric_scope": "Binary-input rational weighted sums; reported bounds round outward",
            "meaning": "Weighted same-context scalar-error OUTER bounds; no calibration, sampling or strength claim"}


def choice_regret_difference(bounds, choice_a, choice_b, *, actor):
    """Minimax actor-regret(A)-regret(B) on ONE identical history.

    Common best-action value cancels, so a complete frontier/root value is not
    required. Caller still owes legality and full-rule/history identity for BOTH
    supplied actions. This says nothing about different continuation policies.
    Repeating the same action is exactly zero, not an independent interval pair.
    """
    values = tuple(_bounds(b) for b in bounds)
    if not values or type(actor) is not int or actor not in (0, 1):
        raise ValueError("nonempty action bounds and explicit actor required")
    if any(type(i) is not int or not 0 <= i < len(values) for i in (choice_a, choice_b)):
        raise ValueError("both choices must index supplied legal-action bounds")
    if choice_a == choice_b:
        return {"lower": 0., "upper": 0., "meaning": "Same action, same history: identical minimax action regret"}
    alo, ahi = values[choice_a]
    blo, bhi = values[choice_b]
    lo, hi = blo - ahi, bhi - alo
    if actor == 1:
        lo, hi = -hi, -lo
    return {"lower": lo, "upper": hi,
            "meaning": "Conditional minimax actor-regret difference only; common root value cancels"}
