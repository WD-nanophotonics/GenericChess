"""Random generation of piece types (the only place randomness may appear)."""

from __future__ import annotations

import random
from math import gcd

from ..core.movement import LeapAtom, RayAtom, MovementAtom
from ..core.pieces import PieceType
from .config import GenerationError


KING_ATOMS = tuple(
    LeapAtom((df, dr)) for df in (-1, 0, 1) for dr in (-1, 0, 1) if (df, dr) != (0, 0)
)


def make_anchor_type() -> PieceType:
    """The fixed anchor type: a king with all eight adjacent leaps."""
    return PieceType(
        type_id="K",
        name="King",
        movement_atoms=KING_ATOMS,
        is_anchor=True,
        is_promotable=False,
        promotion_target_ids=(),
    )


def ordinary_type_ids(board_size: int) -> tuple[str, ...]:
    """Default ordinary type IDs for the generated setups.

    ``P`` is the promotable front type; ``X`` is the even-board companion;
    ``A, B, C, ...`` fill the outer back-rank pairs.
    """
    pairs = (board_size - 1) // 2
    ids: list[str] = ["P"]
    if board_size % 2 == 0:
        ids.append("X")
        pairs = (board_size - 2) // 2
    for i in range(pairs):
        ids.append(chr(ord("A") + i))
    return tuple(ids)


def _has_forward(atom: MovementAtom) -> bool:
    dr = atom.offset[1] if isinstance(atom, LeapAtom) else atom.direction[1]
    return dr > 0


def _has_backward(atom: MovementAtom) -> bool:
    dr = atom.offset[1] if isinstance(atom, LeapAtom) else atom.direction[1]
    return dr < 0


def derive_is_promotable(atoms: tuple[MovementAtom, ...]) -> bool:
    """Default derivation: forward move present and no backward move."""
    return any(_has_forward(a) for a in atoms) and not any(_has_backward(a) for a in atoms)


def _random_leap(rng: random.Random, max_delta: int) -> LeapAtom:
    while True:
        df = rng.randint(-max_delta, max_delta)
        dr = rng.randint(-max_delta, max_delta)
        if (df, dr) != (0, 0):
            return LeapAtom((df, dr))


def _random_ray(rng: random.Random, max_component: int) -> RayAtom:
    while True:
        df = rng.randint(-max_component, max_component)
        dr = rng.randint(-max_component, max_component)
        if (df, dr) != (0, 0) and gcd(abs(df), abs(dr)) == 1:
            return RayAtom((df, dr))


def _random_forward_leap(rng: random.Random, max_delta: int) -> LeapAtom:
    return LeapAtom((rng.randint(-max_delta, max_delta), rng.randint(1, max_delta)))


def _random_forward_ray(rng: random.Random, max_component: int) -> RayAtom:
    while True:
        df = rng.randint(-max_component, max_component)
        dr = rng.randint(1, max_component)
        if (df, dr) != (0, 0) and gcd(abs(df), abs(dr)) == 1:
            return RayAtom((df, dr))


def _random_atom(rng: random.Random, is_ray: bool, cfg) -> MovementAtom:
    if is_ray:
        return _random_ray(rng, cfg.max_ray_component)
    return _random_leap(rng, cfg.max_leap_delta)


def _mirror_atoms(
    atoms: tuple[MovementAtom, ...], symmetry: str
) -> tuple[MovementAtom, ...]:
    """Apply left-right mirroring and dedupe, keeping relative order."""
    if symmetry != "bilateral":
        return tuple(dict.fromkeys(atoms))
    mirrored: list[MovementAtom] = []
    for atom in atoms:
        if isinstance(atom, LeapAtom):
            df, dr = atom.offset
            for cand in ((df, dr), (-df, dr)):
                if cand != (0, 0) and LeapAtom(cand) not in mirrored:
                    mirrored.append(LeapAtom(cand))
        else:
            df, dr = atom.direction
            for cand in ((df, dr), (-df, dr)):
                if cand != (0, 0) and RayAtom(cand, atom.max_steps) not in mirrored:
                    mirrored.append(RayAtom(cand, atom.max_steps))
    return tuple(mirrored)


def generate_ordinary_types(
    rng: random.Random,
    cfg,
    type_ids: tuple[str, ...],
    force_promotable_ids: set[str] | frozenset[str] = frozenset(),
) -> tuple[PieceType, ...]:
    """Generate the ordinary (non-anchor) piece types for one attempt."""
    leap_weight = cfg.leap_probability
    ray_weight = cfg.ray_probability
    types: list[PieceType] = []
    for tid in type_ids:
        atoms: tuple[MovementAtom, ...] = ()
        for _ in range(200):  # bounded retries for the forward/forced constraints
            count = rng.randint(cfg.min_atoms_before_mirroring, cfg.max_atoms_before_mirroring)
            is_ray = rng.random() * (leap_weight + ray_weight) >= leap_weight
            raw: list[MovementAtom] = []
            for _ in range(count):
                raw.append(_random_atom(rng, is_ray, cfg))
            if not any(_has_forward(a) for a in raw):
                forward = (
                    _random_forward_ray(rng, cfg.max_ray_component)
                    if is_ray
                    else _random_forward_leap(rng, cfg.max_leap_delta)
                )
                raw.append(forward)
            atoms = _mirror_atoms(tuple(raw), cfg.movement_symmetry)
            promotable = derive_is_promotable(atoms)
            if tid in force_promotable_ids and not promotable:
                continue  # retry until the forced type is promotable
            break
        else:
            raise GenerationError(f"could not generate a valid piece type {tid!r}")

        name = {"P": "Pawn", "X": "Companion"}.get(tid, f"Piece {tid}")
        types.append(
            PieceType(
                type_id=tid,
                name=name,
                movement_atoms=atoms,
                is_promotable=derive_is_promotable(atoms),
                promotion_target_ids=(),  # assigned after the full pool is known
            )
        )
    return tuple(types)
