"""Exact independent-occupancy mobility and explicit sampling diagnostics."""

from __future__ import annotations

import hashlib
import math
import random
from collections import Counter

from ...core.coordinates import BoardShape, Square, _shape, index_to_square
from ...core.movement import LeapAtom, RayAtom, MovementAtom, atom_targets


def expected_leap_mobility(
    valid_target_count: int,
    friendly_occupancy_probability: float,
) -> float:
    return valid_target_count * (1.0 - friendly_occupancy_probability)


def expected_ray_direction_mobility(
    path_length: int,
    occupancy_probability: float,
    friendly_occupancy_probability: float,
) -> float:
    prefix_clear = 1.0
    total = 0.0
    for _ in range(path_length):
        total += prefix_clear * (1.0 - friendly_occupancy_probability)
        prefix_clear *= 1.0 - occupancy_probability
    return total


def _canonical_direction(df: int, dr: int) -> tuple[int, int]:
    g = math.gcd(abs(df), abs(dr))
    return (df // g, dr // g)


def atoms_overlap(atoms: tuple[MovementAtom, ...]) -> bool:
    """True when analytic per-atom sums would double count overlapping targets."""
    kinds = {type(a).__name__ for a in atoms}
    if len(kinds) > 1:
        return True
    directions: set[tuple[int, int]] = set()
    for atom in atoms:
        if isinstance(atom, LeapAtom):
            d = _canonical_direction(*atom.offset)
        else:
            d = _canonical_direction(*atom.direction)
        if d in directions:
            return True
        directions.add(d)
    return False


def _empty_prefix_histogram(
    shape: BoardShape, atoms: tuple[MovementAtom, ...],
) -> tuple[tuple[int, int], ...]:
    counts: Counter[int] = Counter()
    for idx in range(shape.area):
        square = index_to_square(idx, shape)
        prefixes: dict[Square, int] = {}
        for atom in atoms:
            for step, target in enumerate(atom_targets(shape, 0, square, atom)):
                required = 0 if isinstance(atom, LeapAtom) else step
                prefixes[target] = min(required, prefixes.get(target, required))
        counts.update(prefixes.values())
    return tuple(sorted(counts.items()))


def _prefix_expectation(histogram, area: int, density: float) -> float:
    return ((1.0 - density / 2.0)
            * math.fsum(count * (1.0 - density) ** k for k, count in histogram)
            / area)


def analytic_mobility_at_density(
    n: int | BoardShape,
    atoms: tuple[MovementAtom, ...],
    density: float,
) -> float:
    """Exact per-square pseudo-target expectation for supported leap/ray atoms.

    Primitive rays to one endpoint share its unique straight prefix; a direct
    leap needs no empty prefix and dominates that condition. Endpoint events
    can be dependent: linearity still permits summing their probabilities.
    This is geometry, not cannon/blocked-leg semantics or material calibration.
    Integer counts and sorted prefix lengths remove atom-order roundoff.
    """
    shape = _shape(n)
    return _prefix_expectation(_empty_prefix_histogram(shape, atoms), shape.area, density)


def _seed_for(signature: str, density: float, version: str) -> int:
    raw = f"{signature}|{density:.6f}|{version}".encode("utf-8")
    return int.from_bytes(hashlib.sha256(raw).digest()[:8], "little")


def monte_carlo_mobility_at_density(
    n: int | BoardShape,
    atoms: tuple[MovementAtom, ...],
    density: float,
    signature: str,
    version: str,
    samples: int,
) -> float:
    """Deterministic occupancy-sampling fallback for overlapping/hybrid atoms.

    Targets are de-duplicated per starting square so overlapping atoms never
    double count the same destination.
    """
    shape = _shape(n)
    rng = random.Random(_seed_for(signature, density, version))
    total = 0.0
    for _ in range(samples):
        occupied: list[int] = []
        owner: dict[int, int] = {}
        for idx in range(shape.area):
            if rng.random() < density:
                occupied.append(idx)
                owner[idx] = 0 if rng.random() < 0.5 else 1
        occ_set = set(occupied)
        for idx in range(shape.area):
            square = index_to_square(idx, shape)
            targets: set[int] = set()
            for atom in atoms:
                if isinstance(atom, LeapAtom):
                    nf, nr = square.file + atom.offset[0], square.rank + atom.offset[1]
                    if 0 <= nf < shape.width and 0 <= nr < shape.height:
                        tidx = nr * shape.width + nf
                        if tidx not in occ_set or owner[tidx] == 1:
                            targets.add(tidx)
                else:
                    df, dr = atom.direction
                    cur = square
                    steps = 0
                    while atom.max_steps is None or steps < atom.max_steps:
                        nf, nr = cur.file + df, cur.rank + dr
                        if not (0 <= nf < shape.width and 0 <= nr < shape.height):
                            break
                        steps += 1
                        tidx = nr * shape.width + nf
                        if tidx not in occ_set:
                            targets.add(tidx)
                            cur = Square(nf, nr)
                        elif owner[tidx] == 1:
                            targets.add(tidx)
                            break
                        else:
                            break
            total += len(targets)
    return total / (samples * shape.area)


def mobility_density_curve(
    n: int | BoardShape,
    atoms: tuple[MovementAtom, ...],
    density_points: tuple[float, ...],
    *,
    signature: str,
    version: str,
    mc_samples: int,
) -> tuple[float, ...]:
    """Exact independent-occupancy curve for supported movement primitives.

    Legacy sampling keywords remain accepted for caller compatibility; they
    do not affect this exact quantity. The explicit Monte-Carlo helper remains
    available for diagnostics and recovery of the previous approximation.
    """
    shape = _shape(n)
    histogram = _empty_prefix_histogram(shape, atoms)
    return tuple(_prefix_expectation(histogram, shape.area, density)
                 for density in density_points)
