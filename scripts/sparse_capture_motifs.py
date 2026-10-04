"""Joint three-token intrinsic threats; no sequential-play or value claims."""
from collections import defaultdict
from fractions import Fraction
import hashlib
from itertools import product
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
from scripts.audit_typed_capture_kernel import sparse_incidence

PROTOCOL = 'docs/research/SPARSE_THREAT_MOTIF_PROTOCOL.md'
PROTOCOL_SHA = '86b17497f0770646b25aa1a29dbc1e021a7a8f5a5973034bb4d9612ad6ce0275'


def bitset(squares):
    return sum(1 << s for s in set(squares))


def extra_token_mask(cubes, area, source, victim, extra_label):
    """All possible extra-token squares satisfying at least one exact cube."""
    if extra_label not in ('own', 'enemy') or not 0 <= source < area or not 0 <= victim < area or source == victim:
        raise ValueError('valid distinct source/victim and extra owner required')
    universe = ((1 << area) - 1) & ~(1 << source) & ~(1 << victim)
    result = 0
    for cube in cubes:
        mask = universe
        for square, labels in cube:
            allowed = set(labels)
            if not 0 <= square < area or not allowed <= {'empty', 'own', 'enemy'}:
                raise ValueError('invalid occupancy cube')
            fixed = 'own' if square == source else 'enemy' if square == victim else None
            if fixed is not None:
                if fixed not in allowed:
                    mask = 0
                    break
            elif 'empty' not in allowed:
                mask &= (1 << square) if extra_label in allowed else 0
            elif extra_label not in allowed:
                mask &= ~(1 << square)
        result |= mask
    return result


def triple_population(sources, victims, protected):
    return (len(sources) * len(victims) * len(protected)
            - len(sources & victims) * len(protected)
            - len(sources & protected) * len(victims)
            - len(victims & protected) * len(sources)
            + 2 * len(sources & victims & protected))


def capture_masks(audit, area, checkpoint=lambda: None):
    supports, edges = sparse_incidence(audit, checkpoint)
    grouped = {o: defaultdict(set) for o in (0, 1)}
    for key, cubes in audit['events'].items():
        checkpoint()
        owner, _type, source, _target, _state, removals, _result = key
        if removals:
            grouped[owner][source, removals[0][0]].update(cubes)
    masks = {}
    for owner in (0, 1):
        masks[owner] = {
            pair: {label: extra_token_mask(cubes, area, *pair, label)
                   for label in ('own', 'enemy')}
            for pair, cubes in grouped[owner].items()}
    return supports, edges, masks


def joint_counts(sources, victims, protected, actor_masks, victim_masks):
    """Count A, B and their intersection in one distinct triple population."""
    population = triple_population(sources, victims, protected)
    if population <= 0:
        raise ValueError('empty distinct triple population')
    protected_bits = bitset(protected)
    first = second = joint = 0
    outgoing = defaultdict(list)
    for (victim, target), masks in victim_masks.items():
        if victim in victims and target in protected:
            outgoing[victim].append((target, masks['enemy']))
    for source in sources:
        source_bit = 1 << source
        for victim in victims:
            if source == victim:
                continue
            available = protected_bits & ~source_bit & ~(1 << victim)
            a = actor_masks.get((source, victim), {}).get('own', 0) & available
            b = bitset(target for target, mask in outgoing[victim] if mask & source_bit) & available
            first += a.bit_count()
            second += b.bit_count()
            joint += (a & b).bit_count()
    if not 0 <= joint <= min(first, second) <= population:
        raise AssertionError('inconsistent joint accounting')
    return {'population': population, 'A': first, 'B': second, 'joint': joint}


def audit_ruleset(compiled, checkpoint=lambda: None):
    types = sorted({p.current_type_id for row in compiled.support.initial_position for p in row
                    if p is not None and not compiled.support.type_metadata[p.current_type_id].is_anchor})
    area = compiled.support.board_shape.area
    supports, edges, masks = {}, {}, {}
    for type_id in types:
        checkpoint()
        supports[type_id], edges[type_id], masks[type_id] = capture_masks(
            collect_intrinsic_board_events(compiled, type_id, max_candidates=100_000), area, checkpoint)
    rows = []
    dependencies = []
    for actor, victim, protected in product(types, repeat=3):
        owners = []
        for o in (0, 1):
            checkpoint()
            owners.append(joint_counts(supports[actor][o], supports[victim][1-o], supports[protected][o],
                                      masks[actor][o], masks[victim][1-o]))
        mean = lambda key: sum((Fraction(row[key], row['population']) for row in owners), Fraction(0)) / 2
        a, b, joint = mean('A'), mean('B'), mean('joint')
        covariance = joint - a * b
        row = {'types': [actor, victim, protected], 'owners': owners,
               'P_A': str(a), 'P_B': str(b), 'P_joint': str(joint), 'covariance': str(covariance)}
        rows.append(row)
        if covariance:
            dependencies.append(row)
    mutual = {}
    for actor, victim in product(types, repeat=2):
        owners = []
        for o in (0, 1):
            sources, targets = supports[actor][o], supports[victim][1-o]
            pairs = len(sources) * len(targets) - len(sources & targets)
            if not pairs:
                raise ValueError('empty mutual-capture pair population')
            joint = sum(s in sources and t in targets and (t, s) in edges[victim][1-o]
                        for s, t in edges[actor][o])
            owners.append({'population': pairs, 'mutual': joint})
        mutual[f'{actor}/{victim}'] = {'owners': owners,
            'probability': str(sum((Fraction(r['mutual'], r['population']) for r in owners), Fraction(0)) / 2)}
    return {'types': types, 'triple_strata': rows, 'mutual_pair_strata': mutual,
            'dependent_strata': len(dependencies), 'first_dependency': dependencies[0] if dependencies else None,
            'classification': 'DEPENDENCIES_PRESENT' if dependencies else 'FACTORIZED_IN_THIS_SCOPE'}


def audit():
    started = monotonic()

    def checkpoint():
        if monotonic() - started > 10:
            raise TimeoutError('10-second joint motif cap; no expanded retry')

    if hashlib.sha256((ROOT / PROTOCOL).read_bytes()).hexdigest() != PROTOCOL_SHA:
        raise ValueError('frozen motif protocol changed')
    games = {name: audit_ruleset(compile_semantic_ruleset(builder()), checkpoint)
             for name, builder in (('chess', build_western_chess_ruleset), ('shogi', build_standard_shogi_ruleset))}
    paths = [PROTOCOL, 'scripts/sparse_capture_motifs.py', 'scripts/audit_typed_capture_kernel.py',
             'scripts/intrinsic_action_events.py', 'scripts/intrinsic_occupancy_cubes.py',
             'generic_chess/rules/compiler.py', 'generic_chess/rules/ir.py',
             'generic_chess/rules/western_chess.py', 'generic_chess/rules/standard_shogi.py']
    checkpoint()
    return {'complete': True, 'scope': 'joint sparse intrinsic threats; not legal sequence/material/goal value',
            'material_vectors_produced': False, 'state_transitions': 0, 'games': games,
            'sha256': {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in paths},
            'elapsed_seconds': monotonic() - started}


if __name__ == '__main__':
    result = audit()
    if len(sys.argv) > 1:
        Path(sys.argv[1]).write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8', newline='\n')
    print(json.dumps({'complete': result['complete'], 'elapsed_seconds': result['elapsed_seconds'],
                     'games': {g: {'dependent_strata': r['dependent_strata'], 'strata': len(r['triple_strata']),
                                   'first_dependency': r['first_dependency']} for g, r in result['games'].items()}}, indent=2))
