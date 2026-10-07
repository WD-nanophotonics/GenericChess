"""Opt-in semantic opportunity projection; not full legal mobility or prices.

Independent occupancy is empty=1-d, friendly=enemy=d/2. Only simple actor
moves and target captures are projected. State guards and complex effects are
excluded explicitly. Anchor safety, promotion and custody utility are ignored.
No default evaluator or cache invokes this development candidate.
"""
from __future__ import annotations

import hashlib
from itertools import combinations

from ...rules.compiler import compile_semantic_ir
from ...rules.ir import geometry_candidates
from ...rules.schema import canonical_json
from .config import EvaluationConfig, MAX_STATIC_EVAL, config_hash
from .profile import PieceValueProfile, RuleSetEvaluationProfile, _drop_profile, _median


def _excluded(pattern, ir):
    reasons = []
    if pattern.target.kind not in ('target_empty', 'target_enemy'):
        reasons.append('target relation')
    if pattern.guards or pattern.slot_guards or pattern.square_zone_guards or pattern.postconditions:
        reasons.append('state/zone/postcondition')
    if any(p.kind not in ('path_clear', 'path_count_eq') or
           (p.kind == 'path_count_eq' and p.owner_filter != 'any') for p in pattern.path):
        reasons.append('unsupported path predicate')
    if any(ir.geometry[g].kind == 'drop' for g in pattern.geometry_ids):
        reasons.append('drop')
    moves = [e for e in pattern.effects if e.kind == 'move']
    if (len(moves) != 1 or moves[0].from_ref is None
            or moves[0].from_ref.kind != 'source' or moves[0].to_ref is None
            or moves[0].to_ref.kind != 'target' or moves[0].piece_owner != 'self'):
        reasons.append('not simple actor move')
    for effect in pattern.effects:
        if effect.kind == 'move':
            continue
        if not (effect.kind == 'remove' and effect.square_ref is not None
                and effect.square_ref.kind == 'target' and effect.piece_owner == 'opponent'):
            reasons.append('compound/state effect')
    if any(i.kind != 'own_anchor_safe' for i in pattern.invariants):
        reasons.append('non-anchor invariant')
    return sorted(set(reasons))


def _clear_union(paths, density):
    paths = [p for p in paths if not any(q < p for q in paths)]
    # This explicit complexity boundary declines unusual overlap, never silently
    # treats its probability as zero or restores a legacy movement fallback.
    if len(paths) > 12:
        raise ValueError('semantic projection supports at most12 incomparable paths per endpoint')
    return sum((-1) ** (count + 1) * (1 - density) ** len(set().union(*combo))
               for count in range(1, len(paths) + 1)
               for combo in combinations(paths, count))


def _path_intersection(events, density):
    """Joint probability of clear sets and exact occupied-count constraints.

    State tracks only constrained counts; cells shared by several paths update
    those counts together. Thus overlapping paths do not become independent.
    """
    clear = set().union(*(e[0] for e in events))
    counts = {(cells - clear, count) for _, cells, count in events if count is not None}
    if any(count < 0 or count > len(cells) for cells, count in counts):
        return 0.
    constraints = sorted(counts, key=lambda x: (sorted(x[0]), x[1]))
    states = {(0,) * len(constraints): 1.}
    for cell in sorted(set().union(*(cells for cells, _ in constraints))):
        mask = tuple(int(cell in cells) for cells, _ in constraints)
        next_states = {}
        for state, probability in states.items():
            next_states[state] = next_states.get(state, 0.) + probability * (1 - density)
            occupied = tuple(a + b for a, b in zip(state, mask))
            if all(n <= count for n, (_, count) in zip(occupied, constraints)):
                next_states[occupied] = next_states.get(occupied, 0.) + probability * density
        states = next_states
    return (1 - density) ** len(clear) * states.get(tuple(count for _, count in constraints), 0.)


def _path_union(events, density):
    if all(count is None for _, _, count in events):
        return _clear_union({clear for clear, _, _ in events}, density)
    if len(events) > 12:
        raise ValueError('semantic projection supports at most12 distinct path events per endpoint')
    return sum((-1) ** (count + 1) * _path_intersection(combo, density)
               for count in range(1, len(events) + 1)
               for combo in combinations(events, count))


def semantic_opportunity(compiled, type_id, config: EvaluationConfig):
    """Average both owners/all source squares; return explicit projection scope."""
    ir = compiled.ir if hasattr(compiled, 'ir') else compile_semantic_ir(compiled)
    return _semantic_opportunity(compiled, ir, type_id, config)


def _semantic_opportunity(compiled, ir, type_id, config):
    total = compiled.board_shape.area if hasattr(compiled, 'ir') else compiled.board_size ** 2
    edges = {kind: [{} for _ in range(2 * total)]
             for kind in ('target_empty', 'target_enemy')}
    included, excluded = [], []
    for pattern in ir.patterns:
        if type_id not in pattern.type_ids:
            continue
        reasons = _excluded(pattern, ir)
        if reasons:
            excluded.append(dict(pattern=pattern.pattern_id, reasons=reasons))
            continue
        included.append(pattern.pattern_id)
        for gid in pattern.geometry_ids:
            geometry = ir.geometry[gid]
            if geometry.atom_source is not None and geometry.atom_source[0] != type_id:
                continue
            for owner in ('0', '1'):
                for source in range(total):
                    bucket = edges[pattern.target.kind][int(owner) * total + source]
                    for target, path in geometry_candidates(geometry, owner, source):
                        clear = frozenset(path) if any(p.kind == 'path_clear' for p in pattern.path) else frozenset()
                        count_guards = {p.count for p in pattern.path if p.kind == 'path_count_eq'}
                        # Two different exact counts on the same path are
                        # contradictory; no realization contributes opportunity.
                        if len(count_guards) > 1:
                            continue
                        count = next(iter(count_guards)) if count_guards else None
                        counted = frozenset(path) if count is not None else frozenset()
                        bucket.setdefault(target, set()).add((clear, counted, count))
    curves = []
    for density in config.density_points:
        quiet = sum(_path_union(paths, density) * (1 - density)
                    for bucket in edges['target_empty'] for paths in bucket.values()) / (2 * total)
        capture = sum(_path_union(paths, density) * density / 2
                      for bucket in edges['target_enemy'] for paths in bucket.values()) / (2 * total)
        curves.append(dict(density=density, quiet=quiet, capture=capture, total=quiet + capture))
    signature = canonical_json({kind: [
        [[target, sorted([[sorted(clear), sorted(cells), -1 if count is None else count]
                          for clear, cells, count in paths])] for target, paths in sorted(bucket.items())]
        for bucket in buckets] for kind, buckets in edges.items()})
    return dict(included=included, excluded=excluded,
                signature=hashlib.sha256(signature.encode('utf-8')).hexdigest(),
                quiet_endpoints=sum(map(len, edges['target_empty'])) / 2,
                capture_endpoints=sum(map(len, edges['target_enemy'])) / 2,
                curves=curves, raw=sum(w * c['total'] for w, c in zip(config.density_weights, curves)))


def build_semantic_opportunity_profile(compiled, config: EvaluationConfig):
    """Return (candidate profile, scope). Explicit use with Evaluator only.

    All types use the same projected opportunity law, normalized by the median
    non-anchor type. Hand scale and promotion differences reuse existing table
    conventions, not evidence for transfer/promotion utility. Dynamic terms
    remain owned by Evaluator and are not repaired by this static candidate.
    """
    if compiled.board_size is None:
        raise ValueError('candidate profile currently requires square-board legacy evaluation metadata')
    if (len(config.density_points) != len(config.density_weights)
            or not config.density_points or any(not 0 <= d <= 1 for d in config.density_points)
            or any(w < 0 for w in config.density_weights) or sum(config.density_weights) <= 0):
        raise ValueError('density law requires matched nonnegative weights and densities in[0,1]')
    # Existing legacy-to-IR lowering supplies the same projection boundary for
    # generated legacy rules. It is analysis only: search keeps its original
    # executable, with no artificial semantic action or executor conversion.
    semantic_input = hasattr(compiled, 'ir')
    ir = compiled.ir if semantic_input else compile_semantic_ir(compiled)
    rows = {pt.type_id: _semantic_opportunity(compiled, ir, pt.type_id, config)
            for pt in compiled.piece_types}
    median = _median([rows[pt.type_id]['raw'] for pt in compiled.piece_types if not pt.is_anchor])
    board = {}
    for pt in compiled.piece_types:
        if pt.is_anchor:
            board[pt.type_id] = 0
        elif median <= 0:
            board[pt.type_id] = 1
        else:
            board[pt.type_id] = max(1, min(MAX_STATIC_EVAL, round(
                config.normal_piece_median_value * rows[pt.type_id]['raw'] / median)))
    hand = {tid: min(MAX_STATIC_EVAL, round(value * config.hand_weight)) for tid, value in board.items()}
    gains = {pt.type_id: max(0, max((board[t] for t in pt.promotion_target_ids), default=0) - board[pt.type_id])
             if pt.is_promotable else 0 for pt in compiled.piece_types}
    pieces = {}
    for pt in compiled.piece_types:
        tid = pt.type_id
        freedom, drop_mobility = _drop_profile(compiled, tid, compiled.board_size)
        pieces[tid] = PieceValueProfile(
            type_id=tid, movement_signature=rows[tid]['signature'], raw_capability_score=rows[tid]['raw'],
            normalized_board_value=board[tid], normalized_hand_value=hand[tid],
            promotion_option_value=gains[tid], drop_freedom_ratio=freedom, drop_mobility=drop_mobility,
            is_anchor=pt.is_anchor, is_promotable=pt.is_promotable)
    profile = RuleSetEvaluationProfile(
        ruleset_fingerprint=compiled.ruleset_fingerprint, schema_version=1,
        evaluator_version='semantic-opportunity-v1', config_hash=config_hash(config), piece_profiles=pieces,
        board_value_by_type=board, hand_value_by_base_type=hand, promotion_gain_by_type=gains,
        median_non_anchor_value=_median([board[p.type_id] for p in compiled.piece_types if not p.is_anchor]))
    scope = dict(candidate='semantic-opportunity-v1', complete_legal_mobility=False,
                 ir_source='compiled_semantic' if semantic_input else 'existing_legacy_lowering',
                 law='Independent square occupancy: empty1-d, friend/enemy d/2; equal owner/source weighting.',
                 ignored='Anchor safety, future promotion/custody utility; excluded patterns listed per type. Hand scaling, promotion differences, drop diagnostics and dynamic terms retain legacy conventions, not validated semantic utility.',
                 types=rows)
    return profile, scope
