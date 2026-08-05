"""Analytic expected mobility and deterministic Monte-Carlo fallback."""

from __future__ import annotations

import hashlib
import math
import random

from ...core.coordinates import Square, index_to_square
from ...core.movement import LeapAtom, RayAtom, MovementAtom


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


def _leap_target_count(n: int, square: Square, offset: tuple[int, int]) -> int:
    nf, nr = square.file + offset[0], square.rank + offset[1]
    return 1 if (0 <= nf < n and 0 <= nr < n) else 0


def _ray_path_length(n: int, square: Square, direction: tuple[int, int], max_steps: int | None) -> int:
    df, dr = direction
    cur = square
    steps = 0
    while max_steps is None or steps < max_steps:
        nf, nr = cur.file + df, cur.rank + dr
        if not (0 <= nf < n and 0 <= nr < n):
            break
        steps += 1
        cur = Square(nf, nr)
    return steps


def analytic_mobility_at_density(
    n: int,
    atoms: tuple[MovementAtom, ...],
    density: float,
) -> float:
    """Exact expected per-square pseudo-targets under the independent model."""
    friendly = density / 2.0
    total = 0.0
    for idx in range(n * n):
        square = index_to_square(idx, n)
        per_square = 0.0
        for atom in atoms:
            if isinstance(atom, LeapAtom):
                k = _leap_target_count(n, square, atom.offset)
                per_square += expected_leap_mobility(k, friendly)
            else:
                k = _ray_path_length(n, square, atom.direction, atom.max_steps)
                per_square += expected_ray_direction_mobility(k, density, friendly)
        total += per_square
    return total / (n * n)


def _seed_for(fingerprint: str, signature: str, density: float, version: str) -> int:
    raw = f"{fingerprint}|{signature}|{density:.6f}|{version}".encode("utf-8")
    return int.from_bytes(hashlib.sha256(raw).digest()[:8], "little")


def monte_carlo_mobility_at_density(
    n: int,
    atoms: tuple[MovementAtom, ...],
    density: float,
    fingerprint: str,
    signature: str,
    version: str,
    samples: int,
) -> float:
    """Deterministic occupancy-sampling fallback for overlapping/hybrid atoms."""
    rng = random.Random(_seed_for(fingerprint, signature, density, version))
    total = 0.0
    for _ in range(samples):
        occupied: list[int] = []
        owner: dict[int, int] = {}
        for idx in range(n * n):
            if rng.random() < density:
                occupied.append(idx)
                owner[idx] = 0 if rng.random() < 0.5 else 1
        occ_set = set(occupied)
        for idx in range(n * n):
            square = index_to_square(idx, n)
            for atom in atoms:
                if isinstance(atom, LeapAtom):
                    nf, nr = square.file + atom.offset[0], square.rank + atom.offset[1]
                    if 0 <= nf < n and 0 <= nr < n:
                        tidx = nr * n + nf
                        if tidx not in occ_set or owner[tidx] == 1:
                            total += 1.0
                else:
                    df, dr = atom.direction
                    cur = square
                    steps = 0
                    while atom.max_steps is None or steps < atom.max_steps:
                        nf, nr = cur.file + df, cur.rank + dr
                        if not (0 <= nf < n and 0 <= nr < n):
                            break
                        steps += 1
                        tidx = nr * n + nf
                        if tidx not in occ_set:
                            total += 1.0
                            cur = Square(nf, nr)
                        elif owner[tidx] == 1:
                            total += 1.0
                            break
                        else:
                            break
    return total / (samples * n * n)


def mobility_density_curve(
    n: int,
    atoms: tuple[MovementAtom, ...],
    density_points: tuple[float, ...],
    *,
    fingerprint: str,
    signature: str,
    version: str,
    mc_samples: int,
) -> tuple[float, ...]:
    use_mc = atoms_overlap(atoms)
    curve = []
    for density in density_points:
        if use_mc:
            curve.append(
                monte_carlo_mobility_at_density(
                    n, atoms, density, fingerprint, signature, version, mc_samples
                )
            )
        else:
            curve.append(analytic_mobility_at_density(n, atoms, density))
    return tuple(curve)
