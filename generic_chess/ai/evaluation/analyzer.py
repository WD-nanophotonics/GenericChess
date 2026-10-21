"""Static movement capability analysis for one piece type."""

from __future__ import annotations

from dataclasses import dataclass

from ...core.coordinates import BoardShape, _shape
from ...core.movement import LeapAtom, RayAtom, MovementAtom, empty_mobility
from ...rules.schema import canonical_json
from .config import EvaluationConfig
from .mobility import mobility_density_curve
from .movement_graph import MovementGraphMetrics, graph_metrics


@dataclass(frozen=True, slots=True)
class MovementCapabilityProfile:
    """Geometry-only capability of a piece type (owner-relative, board-shape aware)."""

    movement_signature: str
    density_points: tuple[float, ...]
    expected_mobility: tuple[float, ...]
    empty_board_mobility: float
    coverage_ratio: float
    reachable_pair_ratio: float
    average_shortest_path: float | None
    directional_asymmetry: float
    graph_metrics: MovementGraphMetrics | None
    analyzer_version: str


def movement_signature(atoms: tuple[MovementAtom, ...]) -> str:
    """Canonical, order-insensitive signature of a movement atom set."""
    entries = set()
    for atom in atoms:
        if isinstance(atom, LeapAtom):
            entries.add(("L", atom.offset[0], atom.offset[1]))
        elif isinstance(atom, RayAtom):
            entries.add(
                ("R", atom.direction[0], atom.direction[1], atom.max_steps or -1)
            )
    return canonical_json(sorted(entries))


def profile_movement_atoms(compiled, type_id: str) -> tuple[MovementAtom, ...]:
    """Return the geometry-only movement projection used by static profiles.

    Legacy compiled rules use their declared atoms unchanged. Semantic IR rules
    instead union direct board ``move(source,target)`` leap/ray geometries.
    This is a potential-geometry feature: it deliberately does not model target
    occupancy, invariants, compound effects, non-clear path constraints, or their
    frequencies. Guarded, slot-guarded and auxiliary-effect patterns are
    excluded. If no simple semantic pattern is eligible, existing legacy atoms
    remain the fallback. Unsupported eligible geometry fails visibly instead
    of silently pricing a semantic-only type as immobile.
    """
    ir = getattr(compiled, "ir", None)
    legacy_compiled = getattr(compiled, "_legacy_compiled", None) or compiled
    legacy_types = getattr(legacy_compiled, "types_by_id", {})
    if ir is None:
        legacy = legacy_types.get(type_id)
        return tuple(legacy.movement_atoms) if legacy is not None else ()

    atoms: set[MovementAtom] = set()
    has_direct_move = False
    for pattern in ir.patterns:
        if type_id not in pattern.type_ids:
            continue
        move_effects = [effect for effect in pattern.effects if effect.kind == "move"]
        if len(move_effects) != 1:
            continue
        direct = any(
            effect.from_ref is not None
            and effect.to_ref is not None
            and effect.from_ref.kind == "source"
            and effect.to_ref.kind == "target"
            for effect in move_effects
        )
        if not direct:
            continue
        has_direct_move = True
        if pattern.guards or pattern.slot_guards:
            continue
        # An ordinary ray's path-clear semantics are exactly what RayAtom's
        # occupancy model already expresses. Other path predicates are not.
        if any(predicate.kind != "path_clear" for predicate in pattern.path):
            continue
        if any(effect.kind in ("set_token", "clear_token", "set_bool", "clear_right")
               for effect in pattern.effects):
            continue
        for geometry_id in pattern.geometry_ids:
            geometry = ir.geometry[geometry_id]
            if geometry.kind == "drop":
                continue
            if not geometry.owner_relative:
                raise ValueError(
                    f"default static profile cannot collapse owner-asymmetric "
                    f"semantic geometry for {type_id}; supply evaluator_override"
                )
            if geometry.kind == "leap":
                if geometry.offset is None:
                    raise ValueError(f"semantic leap for {type_id} has no offset")
                atoms.add(LeapAtom(tuple(geometry.offset)))
            elif geometry.kind == "ray":
                if geometry.direction is None or geometry.min_steps not in (None, 1):
                    raise ValueError(
                        f"default static profile cannot represent semantic ray "
                        f"for {type_id}; supply evaluator_override"
                    )
                atoms.add(RayAtom(tuple(geometry.direction), geometry.max_steps))
            else:
                raise ValueError(
                    f"default static profile cannot represent semantic geometry "
                    f"{geometry.kind!r} for {type_id}; supply evaluator_override"
                )
    if not atoms:
        legacy = legacy_types.get(type_id)
        if legacy is not None and legacy.movement_atoms:
            return tuple(legacy.movement_atoms)
        if has_direct_move:
            raise ValueError(
                f"static profile has no simple geometry for semantic-only "
                f"movement {type_id}; supply evaluator_override"
            )
    return tuple(sorted(atoms, key=repr))


def _directional_asymmetry(n: int | BoardShape, atoms: tuple[MovementAtom, ...]) -> float:
    shape = _shape(n)
    forward = backward = 0
    for idx in range(shape.area):
        from ...core.coordinates import index_to_square
        square = index_to_square(idx, shape)
        # Count behavioral destinations, like the graph and occupancy curve.
        # Atom multiplicity is encoding, not extra directional opportunity.
        for target in empty_mobility(shape, 0, square, atoms):
            if target.rank > square.rank:
                forward += 1
            elif target.rank < square.rank:
                backward += 1
    denom = forward + backward
    if denom == 0:
        return 0.0
    return abs(forward - backward) / denom


def build_movement_capability(
    n: int | BoardShape,
    atoms: tuple[MovementAtom, ...],
    config: EvaluationConfig,
) -> MovementCapabilityProfile:
    signature = movement_signature(atoms)
    curve = mobility_density_curve(
        n,
        atoms,
        config.density_points,
        signature=signature,
        version=config.evaluator_version,
        mc_samples=config.mc_samples,
    )
    metrics = graph_metrics(n, atoms)
    return MovementCapabilityProfile(
        movement_signature=signature,
        density_points=config.density_points,
        expected_mobility=curve,
        empty_board_mobility=metrics.average_out_degree,
        coverage_ratio=_coverage_ratio(n, atoms),
        reachable_pair_ratio=metrics.reachable_pair_ratio,
        average_shortest_path=metrics.average_shortest_path,
        directional_asymmetry=_directional_asymmetry(n, atoms),
        graph_metrics=metrics,
        analyzer_version=config.evaluator_version,
    )


def _coverage_ratio(n: int | BoardShape, atoms: tuple[MovementAtom, ...]) -> float:
    from ...core.coordinates import index_to_square
    from ...core.movement import atom_targets

    shape = _shape(n)
    covered: set[int] = set()
    for idx in range(shape.area):
        square = index_to_square(idx, shape)
        for atom in atoms:
            for target in atom_targets(shape, 0, square, atom):
                covered.add(target.rank * shape.width + target.file)
    return len(covered) / shape.area
