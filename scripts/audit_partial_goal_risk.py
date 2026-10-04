"""Exact finite-measure risk certification with sound partial goal labels."""
from fractions import Fraction as F
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]


def quadratic_bounds(a, b, c, lo, hi):
    if lo > hi:
        raise ValueError('reversed interval')
    points = [lo, hi]
    if a:
        vertex = -b / (2 * a)
        if lo <= vertex <= hi:
            points.append(vertex)
    values = [a*x*x + b*x + c for x in points]
    return min(values), max(values)


def certify(intervals, predictions, baselines, weights, rho=F(9, 10)):
    count = len(intervals)
    if not count or any(len(xs) != count for xs in (predictions, baselines, weights)):
        raise ValueError('nonempty equal-length inputs required')
    if any(not isinstance(x, (int, F)) for xs in (predictions, baselines, weights) for x in xs):
        raise ValueError('exact rational inputs required')
    if not isinstance(rho, (int, F)) or not 0 < rho <= 1:
        raise ValueError('rho outside (0,1]')
    if sum(weights) != 1 or any(w < 0 for w in weights):
        raise ValueError('probability weights required')
    totals = {'candidate_risk': [F(0), F(0)], 'baseline_risk': [F(0), F(0)], 'margin': [F(0), F(0)]}
    for interval, p, b, w in zip(intervals, predictions, baselines, weights):
        if len(interval) != 2 or any(not isinstance(x, (int, F)) for x in interval):
            raise ValueError('exact rational interval pair required')
        lo, hi = map(F, interval)
        if not -1 <= lo <= hi <= 1:
            raise ValueError('goal interval outside [-1,1]')
        p, b, w, rho = map(F, (p, b, w, rho))
        bounds = {'candidate_risk': quadratic_bounds(F(1), -2*p, p*p, lo, hi),
                  'baseline_risk': quadratic_bounds(F(1), -2*b, b*b, lo, hi),
                  'margin': quadratic_bounds(rho-1, 2*(p-rho*b), rho*b*b-p*p, lo, hi)}
        for key, pair in bounds.items():
            for index in (0, 1):
                totals[key][index] += w * pair[index]
    verdict = ('certified_improvement' if totals['baseline_risk'][0] > 0 and totals['margin'][0] >= 0
               else 'certified_failure' if totals['margin'][1] < 0 else 'inconclusive')
    return {**totals, 'verdict': verdict}


def audit():
    partial = certify([(1, 1), (-1, -1), (-1, 1), (-1, 1)],
                      [F(1, 2), F(-1, 2), 0, 0], [0]*4,
                      [F(3, 8), F(3, 8), F(1, 8), F(1, 8)])
    unknown = certify([(-1, 1)], [0], [0], [1])
    failure = certify([(1, 1)], [-1], [0], [1])
    encode = lambda r: {key: list(map(str, value)) if isinstance(value, list) else value for key, value in r.items()}
    return {'protocol_sha256': hashlib.sha256((ROOT / 'docs/research/PARTIAL_GOAL_RISK_PROTOCOL.md').read_bytes()).hexdigest(),
            'program_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            'partial_label_mass': '1/4', 'partial_control': encode(partial),
            'all_unknown_control': encode(unknown), 'wrong_sign_control': encode(failure)}


if __name__ == '__main__':
    result = audit()
    Path(sys.argv[1]).write_text(json.dumps(result, indent=2)+'\n', encoding='utf-8', newline='\n')
    print(json.dumps(result, indent=2))
