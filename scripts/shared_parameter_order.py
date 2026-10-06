"""Research-only pointwise order gates; no production alpha-beta replacement."""
from fractions import Fraction as F
from scripts.multiaffine_envelope_certificate import exact_row, cube_min, min_envelope_lower


def _negative(rows): return [tuple(-x for x in row) for row in rows]


def certify_order(first, second, *, first_kind, second_kind, denominator,
                  retained_id, discarded_id, proofs=None, pair_witness=None,
                  checkpoint=None):
    if first_kind not in ('min', 'max') or second_kind not in ('min', 'max'):
        raise ValueError('explicit min/max envelopes required')
    if not first or not second or len(first) > 64 or len(second) > 64 or len(first)*len(second) > 4096:
        raise ValueError('bounded complete row tables required')
    if any(not isinstance(x, str) or not x for x in (retained_id, discarded_id)) or retained_id == discarded_id:
        raise ValueError('distinct canonical choice identities required')
    first = list(map(exact_row, first)); second = list(map(exact_row, second))
    denominator = exact_row(denominator)
    dmin = cube_min(denominator, checkpoint)
    dmax = -cube_min(tuple(-x for x in denominator), checkpoint)
    if dmin <= 0: raise ValueError('shared denominator must be strictly positive everywhere')
    if (first_kind, second_kind) == ('min', 'min'):
        if proofs is None: raise ValueError('supplied min-envelope certificates required')
        lower = min_envelope_lower(first, second, proofs, checkpoint)['lower']
    elif (first_kind, second_kind) == ('max', 'max'):
        if proofs is None: raise ValueError('supplied reverse negated-envelope certificates required')
        lower = min_envelope_lower(_negative(second), _negative(first), proofs, checkpoint)['lower']
    elif (first_kind, second_kind) == ('min', 'max'):
        lower = min(cube_min(tuple(a-b for a, b in zip(row_a, row_b)), checkpoint)
                    for row_a in first for row_b in second)
    else:
        if (not isinstance(pair_witness, (tuple, list)) or len(pair_witness) != 2
                or any(type(i) is not int for i in pair_witness)):
            raise ValueError('supplied global pair witness required')
        i, j = pair_witness
        if not 0 <= i < len(first) or not 0 <= j < len(second):
            raise ValueError('pair witness out of range')
        lower = cube_min(tuple(a-b for a, b in zip(first[i], second[j])), checkpoint)
    normalized = lower/(dmax if lower >= 0 else dmin)
    return dict(numerator_lower=lower, normalized_lower=normalized,
        denominator_range=(dmin, dmax), value_cutoff_proved=lower >= 0,
        canonical_action_prune_proved=lower > 0 or lower == 0 and retained_id < discarded_id,
        scope='complete same-domain oriented rational envelopes and positive common denominator; supplied-proof sufficient only')
