"""Static movement capability analysis for one piece type."""

from __future__ import annotations

from dataclasses import dataclass

from ...core.movement import LeapAtom, RayAtom, MovementAtom
from ...rules.schema import canonical_json
from .config import EvaluationConfig
from .mobility import mobility_density_curve
from .movement_graph import MovementGraphMetrics, graph_metrics


@dataclass(frozen=True, slots=True)
class MovementCapabilityProfile:
    """Geometry-only capability of a piece type (owner-relative, board-size aware)."""

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


def _directional_asymmetry(n: int, atoms: tuple[MovementAtom, ...]) -> float:
    forward = backward = sideways = 0
    for idx in range(n * n):
        from ...core.coordinates import index_to_square
        from ...core.movement import atom_targets

        square = index_to_square(idx, n)
        for atom in atoms:
            for target in atom_targets(n, 0, square, atom):
                if target.rank > square.rank:
                    forward += 1
                elif target.rank < square.rank:
                    backward += 1
                else:
                    sideways += 1
    denom = forward + backward
    if denom == 0:
        return 0.0
    return abs(forward - backward) / denom


def build_movement_capability(
    n: int,
    atoms: tuple[MovementAtom, ...],
    config: EvaluationConfig,
    *,
    fingerprint: str,
) -> MovementCapabilityProfile:
    signature = movement_signature(atoms)
    curve = mobility_density_curve(
        n,
        atoms,
        config.density_points,
        fingerprint=fingerprint,
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


def _coverage_ratio(n: int, atoms: tuple[MovementAtom, ...]) -> float:
    from ...core.coordinates import index_to_square
    from ...core.movement import atom_targets

    covered: set[int] = set()
    for idx in range(n * n):
        square = index_to_square(idx, n)
        for atom in atoms:
            for target in atom_targets(n, 0, square, atom):
                covered.add(target.rank * n + target.file)
    return len(covered) / (n * n) if n * n else 0.0
