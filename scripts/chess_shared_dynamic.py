"""Opt-in development residual: fixed weights, one attack map per owner/leaf.

Semantic pseudo-attacks include Pawn capture geometry and state guards, but
ignore pins, own-anchor safety and postconditions. Empty anchor destinations
are tested in the current occupancy, not after vacating the anchor square.
This is not a legal escape count or a calibrated positional evaluation.
"""
from time import perf_counter

from generic_chess.ai.evaluation.config import EvaluationConfig, MAX_STATIC_EVAL
from generic_chess.core.attacks import pseudo_attacks
from generic_chess.core.coordinates import square_to_index
from generic_chess.core.movement import LeapAtom, RayAtom
from generic_chess.native.semantic import is_square_attacked, pack_position
from generic_chess.core.semantic_executor import _sources_by_owner_type
from generic_chess.rules.ir import geometry_candidates


def semantic_attack_maps(position, engine):
    """One-pass equivalent of the author's per-square S0/S1 attack predicate.

    Reuse exact bindings/path/guards; intentionally do not test target occupancy,
    promotion, S3/S4 or perform trial moves, just like is_square_attacked.
    This research helper depends on the existing private author predicates.
    """
    engine._ensure_match(position)
    sources = _sources_by_owner_type(position)
    out = [set(), set()]
    for owner in (0, 1):
        for pattern in engine._patterns:
            if pattern.target.kind != 'target_enemy':
                continue
            for tid in pattern.type_ids:
                for source, piece in sources.get((owner, tid), ()):
                    for gid in pattern.geometry_ids:
                        geometry = engine.ir.geometry.get(gid)
                        if geometry is None or geometry.kind == 'drop':
                            continue
                        if geometry.atom_source is not None and geometry.atom_source[0] != tid:
                            continue
                        for target, path in geometry_candidates(geometry, str(owner), source):
                            if target in out[owner]:
                                continue
                            binding = engine._make_binding(pattern, gid, tid, piece,
                                source, target, None, path, position)
                            if engine._path_holds(pattern.path, position, binding, owner) and engine._guards_hold(
                                    pattern, position, binding, owner):
                                out[owner].add(target)
    return tuple(frozenset(s) for s in out)


class CachedSharedDynamic:
    """Preserve material/order prices; choose legacy or semantic attack sets.

    No cross-position cache, side flip, history mutation or new native API.
    The legacy mode isolates repeated-map overhead from semantic changes.
    """
    def __init__(self, base, compiled, *, provider=None, semantic=False, bulk=False):
        if semantic and (provider is None or provider.compiled != compiled):
            raise ValueError('semantic shared dynamics require a matching native provider')
        self.base = base
        self.compiled = compiled
        self.provider = provider
        self.semantic = semantic
        self.bulk = bulk
        if bulk and not semantic:
            raise ValueError('bulk backend requires semantic dynamics')
        self.config = EvaluationConfig()
        self.dynamic_calls = 0
        self.dynamic_seconds = 0.0
        self.queries = 0

    def __getattr__(self, name):
        return getattr(self.base, name)

    def terms(self, state):
        start = perf_counter()
        p = state.position
        n = self.compiled.board_size
        if self.semantic and self.bulk:
            attacks = semantic_attack_maps(p, self.provider.engine)
        elif self.semantic:
            rules = self.provider.native_rules
            packed = pack_position(rules, self.provider._state_only_payload(p, state.ply_count))
            attacks = tuple(frozenset(i for i in range(n*n)
                if is_square_attacked(rules, packed, i, owner)) for owner in (0, 1))
            self.queries += 2*n*n
        else:
            attacks = tuple(frozenset(square_to_index(sq, n) for sq in
                pseudo_attacks(p, owner, self.compiled)) for owner in (0, 1))
        escapes, checks = [0, 0], [False, False]
        for owner in (0, 1):
            anchor = next((i for i, piece in enumerate(p.board) if piece is not None
                and piece.owner == owner and
                self.compiled.types_by_id[piece.current_type_id].is_anchor), None)
            if anchor is None:
                continue
            checks[owner] = anchor in attacks[1-owner]
            piece_type = self.compiled.types_by_id[p.board[anchor].current_type_id]
            for atom in piece_type.movement_atoms:
                if isinstance(atom, LeapAtom) and max(map(abs, atom.offset)) <= 1:
                    dx, dy = atom.offset
                elif isinstance(atom, RayAtom) and atom.max_steps == 1:
                    dx, dy = atom.direction
                else:
                    continue
                x, y = anchor % n+dx, anchor//n+dy
                if 0 <= x < n and 0 <= y < n:
                    target = y*n+x
                    if p.board[target] is None and target not in attacks[1-owner]:
                        escapes[owner] += 1
        counts = [len(a) for a in attacks]
        white = self.config.dynamic_mobility_weight*(counts[0]-counts[1])
        white += self.config.anchor_escape_weight*(escapes[0]-escapes[1])
        white += self.config.anchor_escape_weight*10*(int(checks[1])-int(checks[0]))
        residual = white if p.side_to_move == 0 else -white
        self.dynamic_calls += 1
        self.dynamic_seconds += perf_counter()-start
        return dict(attack_counts=counts, empty_escapes=escapes, checks=checks, residual=residual)

    def evaluate(self, state):
        value = self.base.evaluate(state)+100*self.terms(state)['residual']
        if abs(value) >= MAX_STATIC_EVAL:
            raise ValueError('shared dynamic/static mate separation failed')
        return value
