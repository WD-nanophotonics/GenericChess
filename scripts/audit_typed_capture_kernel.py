"""Exact sparse intrinsic incidence; no material vector or goal labels."""
from collections import defaultdict
from fractions import Fraction
import hashlib
from itertools import combinations
import json
from pathlib import Path
import sys
from time import monotonic

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from generic_chess.rules.compiler import compile_semantic_ruleset
from generic_chess.rules.standard_shogi import build_standard_shogi_ruleset
from generic_chess.rules.western_chess import build_western_chess_ruleset
from scripts.intrinsic_action_events import collect_intrinsic_board_events

PROTOCOL = 'docs/research/TYPED_CAPTURE_KERNEL_PROTOCOL.md'
PROTOCOL_SHA = 'ce48349d480ba49b669f0949e6cd258a4d4dc60994654ae4cb2112433fed293b'


def cube_holds(cube, source, victim=None):
    """Evaluate an occupancy cube on the declared one/two-token board."""
    if victim == source:
        raise ValueError('actor and victim must occupy distinct squares')
    for square, allowed in cube:
        if not set(allowed) <= {'empty', 'own', 'enemy'}:
            raise ValueError('unsupported occupancy label')
        actual = 'own' if square == source else 'enemy' if square == victim else 'empty'
        if actual not in allowed:
            return False
    return True


def sparse_incidence(audit, checkpoint=lambda: None):
    """Union capture existence across destinations and promotion alternatives."""
    if not audit['coverage_complete']:
        raise ValueError('unsupported intrinsic semantics')
    supports = {owner: set() for owner in (0, 1)}
    edges = {owner: set() for owner in (0, 1)}
    for key, cubes in audit['events'].items():
        checkpoint()
        owner, _type, source, _target, _state, removals, _result = key
        if len(removals) > 1:
            raise ValueError('multiple-victim action outside sparse scope')
        victim = removals[0][0] if removals else None
        if any(cube_holds(cube, source, victim) for cube in cubes):
            supports[owner].add(source)
            if victim is not None:
                edges[owner].add((source, victim))
    return supports, edges


def rational_rank(matrix):
    if not matrix or not matrix[0] or any(len(row) != len(matrix[0]) for row in matrix):
        raise ValueError('nonempty rectangular matrix required')
    rows = [[Fraction(value) for value in row] for row in matrix]
    rank = 0
    for column in range(len(rows[0])):
        pivot = next((r for r in range(rank, len(rows)) if rows[r][column]), None)
        if pivot is None:
            continue
        rows[rank], rows[pivot] = rows[pivot], rows[rank]
        scale = rows[rank][column]
        rows[rank] = [value / scale for value in rows[rank]]
        for r in range(rank + 1, len(rows)):
            factor = rows[r][column]
            rows[r] = [x - factor * y for x, y in zip(rows[r], rows[rank])]
        rank += 1
        if rank == len(rows):
            break
    return rank


def matrix_report(types, supports, edges, checkpoint=lambda: None):
    matrix = []
    per_pair = {}
    for actor in types:
        row = []
        for victim in types:
            owners = []
            for owner in (0, 1):
                checkpoint()
                sources = supports[actor][owner]
                targets = supports[victim][1 - owner]
                pairs = len(sources) * len(targets) - len(sources & targets)
                if not pairs:
                    raise ValueError('empty pair population; never renormalize')
                captures = sum(source in sources and target in targets
                               for source, target in edges[actor][owner])
                owners.append({'pairs': pairs, 'captures': captures,
                               'probability': str(Fraction(captures, pairs))})
            per_pair[f'{actor}/{victim}'] = owners
            row.append(sum((Fraction(o['probability']) for o in owners), Fraction(0)) / 2)
        matrix.append(row)
    columns = defaultdict(list)
    for column, type_id in enumerate(types):
        columns[tuple(row[column] for row in matrix)].append(type_id)
    minor = None
    for r1, r2 in combinations(range(len(types)), 2):
        for c1, c2 in combinations(range(len(types)), 2):
            determinant = matrix[r1][c1] * matrix[r2][c2] - matrix[r1][c2] * matrix[r2][c1]
            if determinant:
                minor = {'rows': [types[r1], types[r2]], 'columns': [types[c1], types[c2]],
                         'determinant': str(determinant)}
                break
        if minor is not None:
            break
    rank = rational_rank(matrix)
    if (rank > 1) != (minor is not None):
        raise AssertionError('rank/minor disagreement')
    return {'matrix': [[str(v) for v in row] for row in matrix], 'rank': rank,
            'identical_column_groups': list(columns.values()), 'nonzero_minor': minor,
            'owner_pair_accounting': per_pair}


def audit_ruleset(compiled, checkpoint=lambda: None):
    types = sorted({piece.current_type_id for row in compiled.support.initial_position
                    for piece in row if piece is not None
                    and not compiled.support.type_metadata[piece.current_type_id].is_anchor})
    if not types:
        raise ValueError('no initial ordinary current types')
    area = compiled.support.board_shape.area
    supports, edges, coverage = {}, {}, {}
    for type_id in types:
        checkpoint()
        audit = collect_intrinsic_board_events(compiled, type_id, max_candidates=100_000)
        supports[type_id], edges[type_id] = sparse_incidence(audit, checkpoint)
        coverage[type_id] = {k: v for k, v in audit.items() if k != 'events'}
        coverage[type_id]['event_count'] = len(audit['events'])
    all_squares = {type_id: {owner: set(range(area)) for owner in (0, 1)} for type_id in types}
    baseline = matrix_report(types, all_squares, edges, checkpoint)
    if baseline['rank'] > 1 or len(baseline['identical_column_groups']) != 1:
        raise AssertionError('all-square independent target-type control failed')
    active = matrix_report(types, supports, edges, checkpoint)
    return {'types': types, 'board_area': area,
            'active_support_sizes': {t: [len(supports[t][o]) for o in (0, 1)] for t in types},
            'capture_edge_counts': {t: [len(edges[t][o]) for o in (0, 1)] for t in types},
            'coverage': coverage, 'all_square': baseline, 'active': active,
            'classification': 'INFORMATION_PRESENT' if active['rank'] > 1 else 'NO_NEW_COUPLING'}


def audit():
    started = monotonic()

    def checkpoint():
        if monotonic() - started > 10:
            raise TimeoutError('10-second incidence cap; no larger-budget retry')

    if hashlib.sha256((ROOT / PROTOCOL).read_bytes()).hexdigest() != PROTOCOL_SHA:
        raise ValueError('frozen protocol changed')
    games = {}
    for name, builder in (('chess', build_western_chess_ruleset),
                          ('shogi', build_standard_shogi_ruleset)):
        games[name] = audit_ruleset(compile_semantic_ruleset(builder()), checkpoint)
    inputs = [PROTOCOL, 'scripts/audit_typed_capture_kernel.py', 'scripts/intrinsic_action_events.py',
              'scripts/intrinsic_occupancy_cubes.py', 'scripts/audit_static_semantic_material_prior_v2a.py',
              'scripts/audit_static_semantic_material_prior_v2d.py',
              'generic_chess/rules/compiler.py', 'generic_chess/rules/ir.py',
              'generic_chess/rules/western_chess.py', 'generic_chess/rules/standard_shogi.py']
    checkpoint()
    return {'scope': 'sparse intrinsic capture incidence, NOT material/goal/hand value',
            'complete': True, 'material_vectors_produced': False, 'state_transitions': 0,
            'sha256': {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in inputs},
            'games': games, 'elapsed_seconds': monotonic() - started}


if __name__ == '__main__':
    result = audit()
    if len(sys.argv) > 1:
        Path(sys.argv[1]).write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8', newline='\n')
    print(json.dumps({'complete': result['complete'], 'elapsed_seconds': result['elapsed_seconds'],
                      'games': {g: {k: v for k, v in row.items() if k not in ('coverage', 'all_square', 'active')}
                                for g, row in result['games'].items()}}, indent=2))
