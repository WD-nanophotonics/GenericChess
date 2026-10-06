"""Exact duration-image geometry and static choices, no law selection."""
from fractions import Fraction as F


def exact_vertices(prior):
    if any(lo != hi for table in prior.cdf.values() for lo, hi in table.values()):
        raise ValueError('exact CDFs required; uncertain corners are only an outer cover')
    return {h: {mode: F(table[h][0], prior.cdf[prior.normalizer][h][0])
                for mode, table in prior.cdf.items()} for h in prior.horizons}


def affine_rank(vertices, *, max_updates=512):
    if not vertices: raise ValueError('nonempty vertices required')
    rows = list(vertices.values()); modes = sorted(rows[0])
    if any(set(row) != set(modes) for row in rows): raise ValueError('common mode coordinates required')
    matrix = [[F(row[m])-F(rows[0][m]) for m in modes] for row in rows[1:]]
    pivot = 0; updates = 0
    for col in range(len(modes)):
        found = next((i for i in range(pivot, len(matrix)) if matrix[i][col]), None)
        if found is None: continue
        matrix[pivot], matrix[found] = matrix[found], matrix[pivot]
        scale = matrix[pivot][col]; matrix[pivot] = [x/scale for x in matrix[pivot]]
        for i in range(pivot+1, len(matrix)):
            if not matrix[i][col]: continue
            factor = matrix[i][col]
            matrix[i] = [a-factor*b for a, b in zip(matrix[i], matrix[pivot])]
            updates += len(modes)
            if updates > max_updates: raise ValueError('rational elimination cap')
        pivot += 1
    return dict(affine_rank=pivot, updates=updates, modes=modes)


def realize_vertex_weights(prior, weights):
    if set(weights)-set(prior.horizons): raise ValueError('known horizon weights required')
    if any(type(x) is not int and not isinstance(x, F) for x in weights.values()):
        raise ValueError('exact convex weights required')
    if any(x < 0 for x in weights.values()) or sum(weights.values(), F(0)) != 1:
        raise ValueError('convex weights required')
    unnormalized = {h: F(x)/prior.cdf[prior.normalizer][h][0] for h, x in weights.items()}
    total = sum(unnormalized.values(), F(0))
    return {h: x/total for h, x in unnormalized.items()}


def universal_static_choice(vertices, features):
    if not vertices or not features or any(not isinstance(k, str) or not k for k in features):
        raise ValueError('nonempty vertices and canonical choice table required')
    modes = set(next(iter(vertices.values())))
    if any(set(v) != modes for v in vertices.values()): raise ValueError('common vertex modes required')
    if any(set(f)-modes or any(type(n) is not int for n in f.values()) for f in features.values()):
        raise ValueError('known signed integer inventory coordinates required')
    rows = {}
    for h, vertex in vertices.items():
        scores = {k: sum(F(n)*vertex[m] for m, n in f.items()) for k, f in features.items()}
        best = max(scores.values()); ties = sorted(k for k, value in scores.items() if value == best)
        rows[h] = dict(selected=ties[0], tie_set=ties, scores=scores)
    winners = {row['selected'] for row in rows.values()}
    common_ties = sorted(set.intersection(*(set(row['tie_set']) for row in rows.values())))
    return dict(selected=next(iter(winners)) if len(winners) == 1 else None,
                universal_canonical= len(winners) == 1, common_maximizers=common_ties,
                vertex_policies=rows)
