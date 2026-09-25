"""Opt-in, source-specific capture eligibility diagnostics.

The regular attack/check path intentionally remains the existing boolean
query. This module is called only by diagnostics that need to associate an
attacking source square with an externally reconstructed piece identity.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..rules.ir import geometry_candidates
from .coordinates import Square, in_bounds, index_to_square, square_to_index
from .position import Position


@dataclass(frozen=True, slots=True)
class CaptureSourceEvidence:
    """Pseudo-attack and legal-capture sources for one occupied enemy target.

    ``pseudo_attack_sources`` follows the engine's attacked-square contract:
    it applies compiled movement/path/guard eligibility but does not test the
    attacker's own-anchor safety (so pinned pieces can appear).
    ``pseudo_capture_sources`` further requires the semantic action to
    explicitly remove the target; for legacy rules it uses their ordinary
    enemy-destination capture geometry. It also ignores own-anchor safety.
    ``legal_capture_sources`` includes that safety test and is ``None`` when
    ``by_owner`` is not the side to move; legal captures are only asserted for
    the actual mover in the supplied position.
    """

    target: Square
    by_owner: int
    pseudo_attack_sources: tuple[Square, ...]
    pseudo_capture_sources: tuple[Square, ...]
    legal_capture_sources: tuple[Square, ...] | None


def _legacy_pseudo_sources(
    position: Position, target: Square, by_owner: int, compiled
) -> tuple[Square, ...]:
    shape = position.board_shape
    target_index = square_to_index(target, shape)
    sources: set[Square] = set()
    for source, piece in enumerate(position.board):
        if piece is None or piece.owner != by_owner:
            continue
        tid = piece.current_type_id
        for leap_targets in compiled.leap_targets[tid][by_owner][source]:
            if target in leap_targets:
                sources.add(index_to_square(source, shape))
        for ray_path in compiled.ray_paths[tid][by_owner][source]:
            for candidate in ray_path:
                candidate_index = square_to_index(candidate, shape)
                if candidate == target:
                    sources.add(index_to_square(source, shape))
                    break
                if position.board[candidate_index] is not None:
                    break
    return tuple(sorted(sources))


def _semantic_pseudo_sources(
    position: Position,
    target_index: int,
    by_owner: int,
    engine,
    *,
    captures_only: bool = False,
) -> tuple[Square, ...]:
    """Mirror SemanticEngine's S0+S1 attacked-square eligibility per source.

    Keep ``SemanticEngine.is_square_attacked`` untouched: it is called from
    normal legality paths and remains an allocation-free early-exit boolean.
    This explicit diagnostic repeats its compiled candidate, path, and guard
    predicates only when the caller requests source provenance.
    """
    sources_by_owner_type = _engine_sources_by_owner_type(position)
    source_indices: set[int] = set()
    for pattern in engine._patterns:
        if pattern.target.kind != "target_enemy":
            continue
        if captures_only and not _semantic_action_removes_target(pattern):
            continue
        for tid in pattern.type_ids:
            for source, piece in sources_by_owner_type.get((by_owner, tid), ()):
                for geometry_id in pattern.geometry_ids:
                    geometry = engine.ir.geometry.get(geometry_id)
                    if geometry is None or geometry.kind == "drop":
                        continue
                    if (
                        geometry.atom_source is not None
                        and geometry.atom_source[0] != tid
                    ):
                        continue
                    for candidate, path in geometry_candidates(
                        geometry, str(by_owner), source
                    ):
                        if candidate != target_index:
                            continue
                        binding = engine._make_binding(
                            pattern,
                            geometry_id,
                            tid,
                            piece,
                            source,
                            target_index,
                            None,
                            path,
                            position,
                        )
                        if engine._path_holds(
                            pattern.path, position, binding, by_owner
                        ) and engine._guards_hold(
                            pattern, position, binding, by_owner
                        ):
                            source_indices.add(source)
    return tuple(
        index_to_square(source, position.board_shape)
        for source in sorted(source_indices)
    )


def _engine_sources_by_owner_type(position: Position):
    # Import lazily so ordinary Core imports and execution do not pay for the
    # optional semantic provenance machinery.
    from .semantic_executor import _sources_by_owner_type

    return _sources_by_owner_type(position)


def _legal_sources(position: Position, target: Square, by_owner: int, compiled, engine):
    if by_owner != position.side_to_move:
        return None
    target_index = square_to_index(target, position.board_shape)
    if engine is not None:
        patterns = {pattern.pattern_id: pattern for pattern in engine._patterns}
        actions = engine.iter_legal_actions(position)
        return tuple(
            sorted(
                {
                    index_to_square(action.source, position.board_shape)
                    for action in actions
                    if action.source is not None
                    and action.target == target_index
                    and _semantic_action_removes_target(
                        patterns[action.pattern_id]
                    )
                }
            )
        )

    from .actions import action_is_board, action_source_square, action_target_square
    from .movegen import iter_legal_actions_from_position

    return tuple(
        sorted(
            {
                source
                for action in iter_legal_actions_from_position(position, compiled)
                if action_is_board(action)
                and action_target_square(action) == target
                and (source := action_source_square(action)) is not None
            }
        )
    )


def _semantic_action_removes_target(pattern) -> bool:
    """Whether this semantic pattern explicitly removes its enemy target.

    ``target_enemy`` alone is not proof of capture: a generic action may use
    an occupied enemy square as a condition while changing something else.
    The executor requires destination occupancy to be removed before moving a
    piece onto it, so an explicit target removal is the sound capture witness.
    """
    return any(
        effect.kind == "remove"
        and effect.square_ref is not None
        and effect.square_ref.kind == "target"
        and effect.piece_owner in ("opponent", "any")
        for effect in pattern.effects
    )


def query_capture_sources(
    position: Position, target: Square, by_owner: int, compiled
) -> CaptureSourceEvidence:
    """Return source squares eligible to capture the enemy on ``target``.

    This is deliberately an explicit diagnostic, not an attack-map/cache or a
    hook in move generation. It accepts only a target currently occupied by
    the opponent. ``pseudo_attack_sources`` mirrors attacked-square semantics;
    ``pseudo_capture_sources`` requires an actual target-removal effect but
    still ignores own-anchor safety; ``legal_capture_sources`` additionally
    uses the ordinary legal-action authority for the side to move.
    """
    pseudo_sources, pseudo_capture_sources, engine = _query_pseudo_sets(
        position, target, by_owner, compiled
    )

    return CaptureSourceEvidence(
        target=target,
        by_owner=by_owner,
        pseudo_attack_sources=pseudo_sources,
        pseudo_capture_sources=pseudo_capture_sources,
        legal_capture_sources=_legal_sources(
            position, target, by_owner, compiled, engine
        ),
    )


def _query_pseudo_sets(position: Position, target: Square, by_owner: int, compiled):
    if by_owner not in (0, 1):
        raise ValueError("by_owner must be 0 or 1")
    if not in_bounds(target, position.board_shape):
        raise ValueError("target square is outside the board")
    from .semantic_executor import semantic_engine_for

    engine = semantic_engine_for(compiled)
    if engine is not None:
        engine._ensure_match(position)
    else:
        from .errors import ensure_ruleset_match

        ensure_ruleset_match(position, compiled)
    target_index = square_to_index(target, position.board_shape)
    victim = position.board[target_index]
    if victim is None or victim.owner == by_owner:
        raise ValueError("target must contain a piece owned by the opponent")

    if engine is None:
        pseudo = _legacy_pseudo_sources(position, target, by_owner, compiled)
        return pseudo, pseudo, None
    attacks = _semantic_pseudo_sources(position, target_index, by_owner, engine)
    captures = _semantic_pseudo_sources(
        position, target_index, by_owner, engine, captures_only=True
    )
    return attacks, captures, engine


def query_pseudo_capture_sources(
    position: Position, target: Square, by_owner: int, compiled
) -> tuple[Square, ...]:
    """Return capture-capable pseudo-threat sources without legal movegen.

    This explicit read-only query applies only compiled capture geometry and
    guards. It is valid off-turn and intentionally ignores own-anchor safety.
    """
    _attacks, captures, _engine = _query_pseudo_sets(
        position, target, by_owner, compiled
    )
    return captures
