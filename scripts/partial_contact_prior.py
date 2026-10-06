"""Exact shared-duration virtual prior; caller supplies qualified CDF scope."""
from fractions import Fraction as F


def _exact(value):
    if type(value) is int or isinstance(value, F):
        return F(value)
    raise ValueError('exact integer/rational required, not float/bool')


class PartialContactPrior:
    """No source tables/geometry; semantic provenance remains caller-owned."""
    def __init__(self, cumulative, total, *, normalizer='R'):
        if type(total) is not int or total <= 0 or normalizer not in cumulative:
            raise ValueError('positive total and explicit normalizer required')
        if not cumulative or any(not isinstance(k, str) or not k for k in cumulative):
            raise ValueError('nonempty named modes required')
        horizons = set(cumulative[normalizer])
        finite = sorted((int(h) for h in horizons if h != 'infinity'))
        if (not finite or finite != list(range(1, max(finite)+1))
                or horizons != {str(h) for h in finite} | {'infinity'}):
            raise ValueError('consecutive positive horizons and finite limit required')
        self.horizons = tuple(str(h) for h in finite)+('infinity',)
        self.total = total; self.normalizer = normalizer; self.cdf = {}
        for mode, table in cumulative.items():
            if set(table) != horizons:
                raise ValueError('shared horizon domain required')
            last = (0, 0); copied = {}
            for h in self.horizons:
                row = table[h]
                if not isinstance(row, (list, tuple)) or len(row) != 2:
                    raise ValueError('two CDF endpoints required')
                lo, hi = row
                if any(type(v) is not int for v in row) or not 0 <= lo <= hi <= total:
                    raise ValueError('bounded exact integer CDF required')
                if lo < last[0] or hi < last[1]:
                    raise ValueError('monotone CDF bounds required')
                last = (lo, hi); copied[h] = last
            self.cdf[mode] = copied
        r = self.cdf[normalizer]
        if any(lo != hi or lo <= 0 for lo, hi in r.values()):
            raise ValueError('positive exact normalizer at all positive horizons required')
        if any(row[1] > r[h][0] for table in self.cdf.values() for h, row in table.items()):
            raise ValueError('normalizer dominance not qualified')

    def duration(self, masses):
        if set(masses) - ({'0'} | set(self.horizons)):
            raise ValueError('unsupported horizon; no implicit tail fold')
        p = {h: _exact(v) for h, v in masses.items()}
        if any(v < 0 for v in p.values()) or sum(p.values(), F(0)) != 1:
            raise ValueError('probability masses required')
        active = [(h, p.get(h, F(0))) for h in self.horizons if p.get(h, 0)]
        if not active:
            raise ValueError('all-zero duration gives undefined normalized prior')
        denom = sum((v*self.cdf[self.normalizer][h][0] for h, v in active), F(0))
        raw = {mode: tuple(sum((v*table[h][i] for h, v in active), F(0))/self.total
                           for i in (0, 1)) for mode, table in self.cdf.items()}
        normalized = {mode: (lo*self.total/denom, hi*self.total/denom)
                      for mode, (lo, hi) in raw.items()}
        return dict(raw=raw, normalized=normalized, normalizer_raw=denom/self.total)

    def difference(self, delta):
        if set(delta) - set(self.cdf) or any(type(v) is not int for v in delta.values()):
            raise ValueError('known modes and signed integer inventory differences required')
        rows = {}
        for h in self.horizons:
            lower = sum(v*self.cdf[mode][h][0 if v >= 0 else 1] for mode, v in delta.items())
            upper = sum(v*self.cdf[mode][h][1 if v >= 0 else 0] for mode, v in delta.items())
            r = self.cdf[self.normalizer][h][0]
            rows[h] = (F(lower, r), F(upper, r))
        lo = min(x[0] for x in rows.values()); hi = max(x[1] for x in rows.values())
        return dict(lower=lo, upper=hi, strict_order_proved=lo > 0,
                    weak_order_proved=lo >= 0, reverse_strict_proved=hi < 0,
                    horizon_bounds=rows)
